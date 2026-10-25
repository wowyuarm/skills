#!/usr/bin/env python3
"""扫描 Claude 在本机的身份载体，输出清单供分类。

只读，不改任何文件。先跑这个，再按 SKILL.md 的流程决定动哪些。

用法:
    python3 scan_carriers.py              # 扫描全部
    python3 scan_carriers.py --json       # 输出 JSON
    python3 scan_carriers.py --old-id XXX # 顺便统计某个旧 ID 的残留

在 WSL 里跑可同时看到 Windows 侧（通过 /mnt/c）。
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import sqlite3
import sys
from pathlib import Path

HOME = Path.home()
WIN = Path("/mnt/c/Users")


def find_windows_user() -> Path | None:
    if not WIN.is_dir():
        return None
    for d in WIN.iterdir():
        if (d / ".claude").is_dir() or (d / "AppData/Local/Claude-3p").is_dir():
            return d
    return None


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def mask(value: str, keep: int = 8) -> str:
    if not value or len(value) <= keep:
        return value or ""
    return f"{value[:keep]}…({len(value)} chars)"


def scan_wsl() -> dict:
    out: dict = {"form": "WSL CLI", "root": str(HOME / ".claude"), "items": []}
    cj = read_json(HOME / ".claude.json")
    if cj:
        for field in ("userID", "machineID"):
            if field in cj:
                out["items"].append(
                    {"carrier": f".claude.json:{field}", "value": mask(cj[field]),
                     "kind": "identity", "note": "本地随机生成，删了自动换新"}
                )
        if "oauthAccount" in cj:
            acct = cj["oauthAccount"] or {}
            out["items"].append(
                {"carrier": ".claude.json:oauthAccount",
                 "value": f"{acct.get('emailAddress','')} / {mask(acct.get('accountUuid',''))}",
                 "kind": "identity", "note": "删了自动重建，但只恢复部分字段"}
            )
        if "customApiKeyResponses" in cj:
            n = len((cj["customApiKeyResponses"] or {}).get("approved", []))
            out["items"].append(
                {"carrier": ".claude.json:customApiKeyResponses", "value": f"{n} approved",
                 "kind": "identity", "note": "不重建，可安全删"}
            )

    cred = HOME / ".claude/.credentials.json"
    if cred.exists():
        d = read_json(cred) or {}
        o = d.get("claudeAiOauth", {})
        out["items"].append(
            {"carrier": ".credentials.json",
             "value": f"access={mask(o.get('accessToken',''),12)} sub={o.get('subscriptionType','')}",
             "kind": "credential", "note": "删了会 Not logged in；换占位 token 可保留结构"}
        )

    for rel, note in [
        (".claude/sessions", "运行中会话，含 pidDomain 的 machine-id"),
        (".claude/daemon/control.key", "进程通信密钥"),
        (".claude/remote/run", "daemon token + rpc socket"),
        (".claude/history.jsonl", "输入历史，含 project 路径"),
        (".claude/projects", "会话记录，属个人数据"),
        (".claude/plugins/marketplaces", "git remote 含 GitHub 用户名"),
        (".claude/backups", "自动备份的 .claude.json，含旧身份"),
    ]:
        p = HOME / rel
        if p.exists():
            out["items"].append(
                {"carrier": rel, "value": "存在", "kind": "review", "note": note}
            )

    cache = HOME / ".cache/claude-cli-nodejs"
    if cache.is_dir():
        # 目录名是项目路径的横线转义：/home/<user>/<project> -> -home-<user>-<project>
        # 只报家目录不在当前用户名下的，那是换过用户名后遗留的
        current = HOME.name
        legacy = []
        for d in cache.iterdir():
            parts = d.name.lstrip("-").split("-")
            if len(parts) >= 2 and parts[0] == "home" and parts[1] != current:
                legacy.append(d.name)
        if legacy:
            out["items"].append(
                {"carrier": ".cache/claude-cli-nodejs", "value": f"{len(legacy)} 个其他用户名目录",
                 "kind": "identity", "note": ", ".join(legacy[:3])}
            )

    versions = sorted(glob.glob(str(HOME / ".local/share/claude/versions/*")))
    if len(versions) > 1:
        out["items"].append(
            {"carrier": ".local/share/claude/versions", "value": f"{len(versions)} 个版本",
             "kind": "garbage", "note": "旧版本可删，仅保留软链指向的"}
        )
    return out


def scan_windows_cli(win: Path) -> dict:
    out: dict = {"form": "Windows CLI", "root": str(win / ".claude"), "items": []}
    cj = read_json(win / ".claude.json")
    if cj:
        for field in ("userID", "machineID"):
            if field in cj:
                out["items"].append(
                    {"carrier": f".claude.json:{field}", "value": mask(cj[field]),
                     "kind": "identity", "note": "与 WSL 独立的一套"}
                )
        if cj.get("oauthAccount"):
            out["items"].append(
                {"carrier": ".claude.json:oauthAccount", "value": "存在", "kind": "identity", "note": ""}
            )

    settings = read_json(win / ".claude/settings.json")
    if settings:
        env = settings.get("env", {})
        token = env.get("ANTHROPIC_AUTH_TOKEN", "")
        out["items"].append(
            {"carrier": ".claude/settings.json:env",
             "value": f"base_url={env.get('ANTHROPIC_BASE_URL','')} token={mask(token,10)}",
             "kind": "config",
             "note": "明文 key 要检查是否有副本" if token and token.startswith("sk-") else ""}
        )

    for bak in glob.glob(str(win / ".claude/settings*.bak*")) + glob.glob(str(win / ".claude/settings*.pebrel-bak")):
        out["items"].append(
            {"carrier": str(Path(bak).relative_to(win)), "value": "存在",
             "kind": "identity", "note": "备份文件，可能含同一把明文 key"}
        )
    return out


def scan_desktop(win: Path) -> dict:
    out: dict = {"form": "Windows Desktop", "root": "", "items": []}
    for cand in ("AppData/Local/Claude-3p", "AppData/Local/Claude", "AppData/Roaming/Claude"):
        p = win / cand
        if p.is_dir():
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            out["items"].append(
                {"carrier": cand, "value": f"{size // 1048576} MB", "kind": "location",
                 "note": "当前使用" if cand.endswith("Claude-3p") else "旧版或引导层"}
            )

    did = win / "AppData/Local/Claude-3p/ant-did"
    if did.exists():
        raw = did.read_text(encoding="utf-8").strip()
        try:
            decoded = base64.b64decode(raw).decode()
        except Exception:
            decoded = "(解码失败)"
        out["root"] = str(win / "AppData/Local/Claude-3p")
        out["items"].append(
            {"carrier": "Claude-3p/ant-did", "value": decoded, "kind": "identity",
             "note": "同时是四处目录名，改要连带迁移"}
        )
        short = decoded[:8]
        base = win / "AppData/Local/Claude-3p"
        refs = []
        for pat in (f"*{decoded}*", f"*{short}*"):
            refs += [str(Path(p).relative_to(base)) for p in glob.glob(str(base / "**" / pat), recursive=True)]
        if refs:
            out["items"].append(
                {"carrier": "ant-did 引用目录", "value": f"{len(set(refs))} 处",
                 "kind": "identity", "note": "; ".join(sorted(set(refs))[:4])}
            )

    for rel, note in [
        ("AppData/Local/Claude-3p/Local State", "os_crypt 是浏览器级密钥，改了波及全部网站"),
        ("AppData/Local/Claude-3p/Local Storage", "含 ccd-session-store、epitaxy-*"),
        ("AppData/Local/Claude-3p/IndexedDB", "网关模式本地存储"),
        ("AppData/Local/Claude-3p/Network/Cookies", "应用内 cookie"),
        ("AppData/Local/Claude-3p/DIPS", "防跨站跟踪数据库"),
        ("AppData/Local/Claude-3p/sentry", "遥测，删了立刻重建"),
        ("AppData/Local/Claude-3p/configLibrary", "网关配置，含 egress 白名单"),
    ]:
        p = win / rel
        if p.exists():
            out["items"].append({"carrier": rel.split("/", 3)[-1], "value": "存在",
                                 "kind": "browser" if "Storage" in rel or "Cookies" in rel else "review",
                                 "note": note})
    return out


def count_leveldb_keys(path: Path, needle: str = "claude") -> int | None:
    """读取 LevelDB 的实际 key。返回 None 表示 plyvel 不可用或读取失败。

    不能用 grep 扫 .ldb 文件：删除的 key 字节仍留在文件里，会误报。
    """
    try:
        import plyvel
    except ImportError:
        return None
    try:
        db = plyvel.DB(str(path), create_if_missing=False)
    except Exception:
        return None
    try:
        return sum(1 for k, _ in db if needle in k.decode("utf-8", "replace").lower())
    finally:
        db.close()


def scan_browsers(win: Path) -> list[dict]:
    results = []
    candidates = [
        ("Chrome", win / "AppData/Local/Google/Chrome/User Data"),
        ("Edge", win / "AppData/Local/Microsoft/Edge/User Data"),
        ("Vivaldi", win / "AppData/Local/Vivaldi/User Data"),
    ]
    wsl_chrome = HOME / ".config/google-chrome"
    if wsl_chrome.is_dir():
        candidates.append(("Chrome (WSL)", wsl_chrome))

    for name, root in candidates:
        profile = root / "Default"
        if not profile.is_dir():
            continue
        entry: dict = {"form": f"Browser: {name}", "root": str(profile), "items": []}

        cookies = profile / "Network/Cookies"
        if not cookies.exists():
            cookies = profile / "Cookies"
        if cookies.exists():
            try:
                con = sqlite3.connect(f"file:{cookies}?immutable=1", uri=True)
                rows = list(con.execute(
                    "select host_key, name from cookies where host_key like '%claude%' "
                    "or host_key like '%anthropic%'"))
                con.close()
                if rows:
                    names = sorted({r[1] for r in rows})
                    entry["items"].append(
                        {"carrier": "Network/Cookies", "value": f"{len(rows)} 条",
                         "kind": "credential",
                         "note": ", ".join(names[:8]) + (" …" if len(names) > 8 else "")}
                    )
            except Exception as exc:
                entry["items"].append(
                    {"carrier": "Network/Cookies", "value": "读取失败",
                     "kind": "credential", "note": f"{exc}（浏览器可能未关闭）"}
                )

        # IndexedDB 按目录名判断（目录名就是 origin），比扫字节可靠
        idb = profile / "IndexedDB"
        if idb.is_dir():
            dirs = [d.name for d in idb.iterdir()
                    if d.is_dir() and ("claude" in d.name.lower() or "anthropic" in d.name.lower())]
            if dirs:
                entry["items"].append(
                    {"carrier": "IndexedDB", "value": f"{len(dirs)} 个 origin",
                     "kind": "browser", "note": "; ".join(sorted(dirs)[:3])}
                )

        # LevelDB 读实际 key，不能 grep（已删 key 的字节仍在文件里）
        for sub in ("Local Storage", "Session Storage"):
            p = profile / sub / "leveldb"
            if not p.is_dir():
                p = profile / sub
            if not p.is_dir():
                continue
            n = count_leveldb_keys(p)
            if n is None:
                entry["items"].append(
                    {"carrier": sub, "value": "未检查",
                     "kind": "browser", "note": "需 pip install plyvel 才能读实际 key"}
                )
            elif n:
                entry["items"].append(
                    {"carrier": sub, "value": f"{n} 个 claude key", "kind": "browser", "note": ""}
                )

        if entry["items"]:
            results.append(entry)
    return results


def scan_system(win: Path) -> dict:
    out: dict = {"form": "System", "root": "", "items": []}
    if sys.platform == "win32":
        try:
            import winreg
            for hive, path in [
                (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\NativeMessagingHosts"),
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge\NativeMessagingHosts"),
            ]:
                try:
                    key = winreg.OpenKey(hive, path)
                    i = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(key, i)
                        except OSError:
                            break
                        if "anthropic" in sub.lower() or "claude" in sub.lower():
                            out["items"].append(
                                {"carrier": f"{path}\\{sub}", "value": "存在",
                                 "kind": "identity", "note": "原生消息宿主，默认值常为空（死链）"}
                            )
                        i += 1
                except FileNotFoundError:
                    pass
        except ImportError:
            pass
    return out


def grep_old_id(win: Path | None, old_id: str) -> list[str]:
    roots = [HOME / ".claude"]
    if win:
        roots += [
            win / "AppData/Local/Claude-3p",
            win / "AppData/Local/Claude",
            win / "AppData/Roaming/Claude",
            win / ".claude",
        ]
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
                if old_id.encode() in f.read_bytes():
                    hits.append(str(f))
            except Exception:
                pass
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--old-id", help="统计该 ID 的残留文件")
    args = ap.parse_args()

    win = find_windows_user()
    sections = [scan_wsl()]
    if win:
        sections.append(scan_windows_cli(win))
        sections.append(scan_desktop(win))
        sections += scan_browsers(win)
        sections.append(scan_system(win))

    if args.old_id:
        hits = grep_old_id(win, args.old_id)
        sections.append({
            "form": f"Residue: {args.old_id}",
            "root": "",
            "items": [{"carrier": h, "value": "命中", "kind": "residue", "note": ""} for h in hits]
            or [{"carrier": "(无)", "value": "0 命中", "kind": "residue", "note": "干净"}],
        })

    if args.json:
        print(json.dumps(sections, ensure_ascii=False, indent=2))
        return 0

    for sec in sections:
        if not sec["items"]:
            continue
        print(f"\n=== {sec['form']}")
        if sec["root"]:
            print(f"    {sec['root']}")
        for it in sec["items"]:
            note = f"  ← {it['note']}" if it["note"] else ""
            print(f"  [{it['kind']:10}] {it['carrier']}: {it['value']}{note}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
