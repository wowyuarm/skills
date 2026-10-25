#!/usr/bin/env python3
"""重置后验证：功能通、身份已换、旧身份无残留、自定义配置仍在。

四项全过才算完成。任何一项 FAIL 都说明没做完。

用法:
    python3 verify_reset.py --old-id <旧ID> [--old-id <旧ID2>]
    python3 verify_reset.py --old-id <旧设备ID> --skip-run

--skip-run 跳过实际调用（不想消耗额度时用，但那样不算完整验证）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
WIN = Path("/mnt/c/Users")
GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}PASS{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"{RED}FAIL{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}WARN{RESET} {msg}")


def find_windows_user() -> Path | None:
    if not WIN.is_dir():
        return None
    for d in WIN.iterdir():
        if (d / ".claude").is_dir() or (d / "AppData/Local/Claude-3p").is_dir():
            return d
    return None


def run_claude(cli: str | list[str], timeout: int = 90) -> tuple[bool, str]:
    cmd = [cli] if isinstance(cli, str) else cli
    try:
        proc = subprocess.run(cmd + ["-p", "reply OK"], capture_output=True,
                              text=True, timeout=timeout)
    except FileNotFoundError:
        return False, "命令不存在"
    except subprocess.TimeoutExpired:
        return False, "超时"
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0 and "OK" in out, out.strip().splitlines()[-1][:120] if out else ""


def run_windows_cli(win: Path, timeout: int = 120) -> tuple[bool, str]:
    """通过 PowerShell 调 Windows 侧 claude。

    直接 subprocess 调 claude.cmd 会因 .cmd 是批处理而报 "too many arguments"，
    必须经过 shell 解析。
    """
    ps = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    if not Path(ps).exists():
        return False, "PowerShell 不可用"
    # PowerShell 不认 /mnt/c/... 路径，转成 Windows 风格
    native = str(win).replace("/mnt/c/", "C:\\").replace("/", "\\")
    script = f'cd "{native}"; claude -p "reply OK" 2>&1 | Select-Object -Last 1'
    try:
        proc = subprocess.run([ps, "-NoProfile", "-Command", script],
                              capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "超时"
    # PowerShell 在中文 Windows 上输出 GBK，不能直接 text=True
    out = ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", "replace").strip()
    return "OK" in out, out.splitlines()[-1][:120] if out else ""


def check_identity(path: Path, label: str, old_ids: list[str]) -> bool:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{label}: 读取失败 {exc}")
        return False
    stale = []
    for field in ("userID", "machineID"):
        value = d.get(field)
        if not value:
            print(f"       {field}: 不存在")
            continue
        if value in old_ids:
            stale.append(field)
            print(f"       {field}: {value[:16]}… ← 仍是旧值")
        else:
            print(f"       {field}: {value[:16]}… ← 已换新")
    if stale:
        fail(f"{label}: 仍是旧值 {stale}")
        return False
    ok(f"{label}: 身份已换新")
    return True


def check_residue(win: Path | None, old_ids: list[str]) -> bool:
    roots = [HOME / ".claude"]
    if win:
        roots += [win / ".claude", win / "AppData/Local/Claude-3p",
                  win / "AppData/Local/Claude", win / "AppData/Roaming/Claude"]
    total = 0
    for old in old_ids:
        hits = []
        for root in roots:
            if not root.is_dir():
                continue
            for f in root.rglob("*"):
                if not f.is_file():
                    continue
                try:
                    if f.stat().st_size > 50_000_000:
                        continue
                    if old.encode() in f.read_bytes():
                        hits.append(str(f))
                except Exception:
                    pass
        if hits:
            total += len(hits)
            fail(f"旧 ID {old[:8]}… 命中 {len(hits)} 个文件")
            for h in hits[:5]:
                print(f"       {h}")
        else:
            ok(f"旧 ID {old[:8]}… 0 命中")
    return total == 0


def check_custom_config() -> bool:
    settings = HOME / ".claude/settings.json"
    if not settings.exists():
        warn("WSL settings.json 不存在")
        return True
    try:
        d = json.loads(settings.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"settings.json 解析失败: {exc}")
        return False
    env = d.get("env", {})
    facts = {
        "base_url": env.get("ANTHROPIC_BASE_URL", ""),
        "model": d.get("model", ""),
        "模型组": len(d.get("modelPicker", {}).get("options", [])),
        "hooks": len(d.get("hooks", {})),
        "插件": len(d.get("enabledPlugins", {})),
        "权限模式": d.get("permissions", {}).get("defaultMode", ""),
    }
    empty = [k for k, v in facts.items() if not v]
    if empty:
        fail(f"自定义配置缺失: {empty}")
        return False
    for k, v in facts.items():
        print(f"       {k}: {v}")
    ok("自定义配置完整")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old-id", action="append", required=True,
                    help="要确认无残留的旧 ID，可重复")
    ap.add_argument("--skip-run", action="store_true", help="跳过实际调用")
    args = ap.parse_args()

    win = find_windows_user()
    failed = False

    print("== 1 功能验证")
    if args.skip_run:
        warn("已跳过（--skip-run）")
    else:
        good, detail = run_claude("claude")
        (ok if good else fail)(f"WSL CLI: {detail}")
        failed |= not good
        if win:
            good, detail = run_windows_cli(win)
            (ok if good else fail)(f"Windows CLI: {detail}")
            failed |= not good

    print("\n== 2 身份已换")
    failed |= not check_identity(HOME / ".claude.json", "WSL", args.old_id)
    if win and (win / ".claude.json").exists():
        failed |= not check_identity(win / ".claude.json", "Windows CLI", args.old_id)

    print("\n== 3 旧身份无残留")
    failed |= not check_residue(win, args.old_id)

    print("\n== 4 自定义配置仍在")
    failed |= not check_custom_config()

    print()
    if failed:
        print(f"{RED}未通过{RESET}：见上方 FAIL 项")
        return 1
    print(f"{GREEN}全部通过{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
