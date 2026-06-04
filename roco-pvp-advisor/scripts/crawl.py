#!/usr/bin/env python3
"""
从 BiliGame Wiki 爬取洛克王国世界精灵和技能数据，存入本地 SQLite。

用法: python3 scripts/crawl.py

API: wiki.biligame.com/rocom (MediaWiki)
输出: data/roco.db (覆盖或新建)
"""

import json
import re
import sqlite3
import time
import urllib.request
import urllib.error
import urllib.parse
import os
import sys

API = "https://wiki.biligame.com/rocom/api.php"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "roco.db")

USER_AGENT = "roco-pvp-advisor/1.0 (wiki data crawler; contact: github)"

# 爬取参数
BATCH_SIZE = 5       # 每批爬取页面数（wiki限流严格，不宜太大）
BATCH_DELAY = 8      # 批次间等待秒数
MAX_DURATION = 1800  # 总超时秒数（30分钟）
RETRY_MAX = 5        # 单页失败重试次数
PROGRESS_FILE = os.path.join(os.path.dirname(DB_PATH), "crawl_progress.json")


def api_call(params: dict) -> dict:
    """调用 MediaWiki API，带重试。"""
    qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"{API}?{qs}"

    for attempt in range(1, RETRY_MAX + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 567:
                wait = min(15 * (2 ** attempt), 120)
                print(f"  [rate-limit] 等 {wait}s 重试 (第 {attempt}/{RETRY_MAX} 次)...")
                time.sleep(wait)
                continue
            print(f"  [HTTP {e.code}] {url}")
            return None
        except Exception as e:
            if attempt < RETRY_MAX:
                wait = min(10 * (2 ** attempt), 60)
                print(f"  [error] 等 {wait}s 重试: {e}")
                time.sleep(wait)
                continue
            print(f"  [error] 最终失败 {url}: {e}")
            return None
    return None


def get_category_members(category: str) -> list[str]:
    """获取分类下所有页面名称。"""
    names = []
    cmcontinue = None

    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "max",
            "format": "json",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        data = api_call(params)
        if not data:
            break

        for m in data.get("query", {}).get("categorymembers", []):
            names.append(m["title"])

        if "continue" in data:
            cmcontinue = data["continue"]["cmcontinue"]
            time.sleep(1)
        else:
            break

    return names


def _safe_int(val, default=0):
    """安全转 int，wiki 可能填 '-' 或空串。"""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def parse_wikitext_template(text: str) -> dict:
    """解析 {{模板名\n|key1=value1\n|key2=value2}} 格式。"""
    # 提取模板内容（去掉 {{ 和 }} 及模板名）
    m = re.match(r'\{\{(.+?)\n', text)
    if not m:
        return {}
    name = m.group(1).strip()
    # 找到模板参数部分
    inner = text[len(m.group(0)):]
    if inner.endswith("}}"):
        inner = inner[:-2]

    result = {"_template": name}
    # 按 \n| 分割参数
    parts = re.split(r'\n\|', inner)
    for part in parts:
        if "=" in part:
            key, _, value = part.partition("=")
            result[key.strip().lstrip("|")] = value.strip()
    return result


def crawl_pages(names: list[str], label: str, parser) -> dict[str, dict]:
    """批量爬取并解析页面，支持断点续传。"""
    results = {}
    failed = []
    start = time.time()
    total = len(names)

    # 尝试加载上次进度
    start_idx = 0
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                progress = json.load(f)
            if progress.get("label") == label:
                results = progress.get("results", {})
                failed = progress.get("failed", [])
                start_idx = progress.get("next_idx", 0)
                print(f"  [resume] 从第 {start_idx}/{total} 继续 ({len(results)} 已完成)")
        except Exception:
            pass

    for i in range(start_idx, total, BATCH_SIZE):
        if time.time() - start > MAX_DURATION:
            print(f"  [timeout] {total - len(results)}/{total} 未完成，已爬 {len(results)}")
            _save_progress(label, results, failed, i + BATCH_SIZE)
            break

        batch = names[i:i + BATCH_SIZE]
        for name in batch:
            data = api_call({
                "action": "parse",
                "page": name,
                "prop": "wikitext",
                "format": "json",
            })
            if not data or "parse" not in data:
                failed.append(name)
                continue

            wikitext = data["parse"]["wikitext"]["*"]
            parsed = parser(wikitext)
            if parsed:
                results[name] = parsed
            else:
                failed.append(name)

        done = min(i + BATCH_SIZE, total)
        ok_count = len(results)
        print(f"  [{label}] {done}/{total} ({ok_count} ok, {len(failed)} fail)")

        # 每批保存进度
        _save_progress(label, results, failed, i + BATCH_SIZE)

        # 重试失败项
        if failed:
            retry_failed = list(failed)
            failed.clear()
            for name in retry_failed:
                time.sleep(2)
                data = api_call({
                    "action": "parse",
                    "page": name,
                    "prop": "wikitext",
                    "format": "json",
                })
                if data and "parse" in data:
                    parsed = parser(data["parse"]["wikitext"]["*"])
                    if parsed:
                        results[name] = parsed
                        continue
                failed.append(name)
            _save_progress(label, results, failed, i + BATCH_SIZE)

        if i + BATCH_SIZE < total:
            time.sleep(BATCH_DELAY)

    # 完成，清除进度文件
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    return results


def _save_progress(label: str, results: dict, failed: list, next_idx: int):
    """保存爬取进度。"""
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "label": label,
            "results": results,
            "failed": failed,
            "next_idx": next_idx,
        }, f, ensure_ascii=False)


def parse_pet(wikitext: str) -> dict | None:
    """解析 {{精灵信息|...}} 模板。"""
    d = parse_wikitext_template(wikitext)
    if d.get("_template") not in ("精灵信息", "宠物信息"):
        return None

    return {
        "name": d.get("精灵名称", d.get("宠物名称", "")),
        "element": d.get("主属性", ""),
        "element2": d.get("2属性", ""),
        "evo_stage": d.get("精灵阶段", ""),
        "ability": d.get("特性", ""),
        "ability_desc": d.get("特性描述", ""),
        "base_hp": _safe_int(d.get("生命", 0)),
        "base_atk": _safe_int(d.get("物攻", 0)),
        "base_spatk": _safe_int(d.get("魔攻", 0)),
        "base_def": _safe_int(d.get("物防", 0)),
        "base_spdef": _safe_int(d.get("魔防", 0)),
        "base_speed": _safe_int(d.get("速度", 0)),
        "skills": d.get("技能", ""),       # 逗号分隔的技能名
        "bloodline_skills": d.get("血脉技能", ""),
        "skill_stones": d.get("可学技能石", ""),
        "prev_evo": d.get("精灵初阶名称", ""),  # 上一进化形态
    }


def parse_skill(wikitext: str) -> dict | None:
    """解析 {{技能信息|...}} 模板。"""
    d = parse_wikitext_template(wikitext)
    if d.get("_template") != "技能信息":
        return None

    return {
        "name": d.get("技能名称", ""),
        "element": d.get("属性", ""),
        "category": d.get("技能类别", ""),
        "energy_cost": _safe_int(d.get("耗能", 0)),
        "power": _safe_int(d.get("威力", 0)),
        "effect": d.get("效果", ""),
    }


def build_db(pets: dict, skills: dict):
    """构建 SQLite 数据库。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # 技能表
    c.execute("""
        CREATE TABLE skill (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            element TEXT,
            category TEXT,
            power INTEGER DEFAULT 0,
            energy_cost INTEGER DEFAULT 0,
            description TEXT,
            effect TEXT
        )
    """)

    # 精灵表
    c.execute("""
        CREATE TABLE pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            element TEXT,
            element2 TEXT,
            evo_stage TEXT,
            ability TEXT,
            ability_desc TEXT,
            base_hp INTEGER DEFAULT 0,
            base_atk INTEGER DEFAULT 0,
            base_spatk INTEGER DEFAULT 0,
            base_def INTEGER DEFAULT 0,
            base_spdef INTEGER DEFAULT 0,
            base_speed INTEGER DEFAULT 0
        )
    """)

    # 精灵-技能关联表
    c.execute("""
        CREATE TABLE pokemon_skill (
            pokemon_id INTEGER,
            skill_id INTEGER,
            learn_type TEXT DEFAULT '自学',
            PRIMARY KEY (pokemon_id, skill_id)
        )
    """)

    # 进化链表
    c.execute("""
        CREATE TABLE evolution (
            from_name TEXT,
            to_name TEXT,
            PRIMARY KEY (from_name, to_name)
        )
    """)

    # 写入技能
    skill_ids = {}
    for name, s in skills.items():
        c.execute("""
            INSERT OR IGNORE INTO skill (name, element, category, power, energy_cost, effect)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (s["name"], s["element"], s["category"], s["power"], s["energy_cost"], s["effect"], s.get("description", "")))
        skill_ids[s["name"]] = c.lastrowid or c.execute(
            "SELECT id FROM skill WHERE name = ?", (s["name"],)
        ).fetchone()[0]

    print(f"  skills: {len(skill_ids)} 条写入")

    # 写入精灵
    for name, p in pets.items():
        c.execute("""
            INSERT INTO pokemon (name, element, element2, evo_stage, ability, ability_desc,
                                 base_hp, base_atk, base_spatk, base_def, base_spdef, base_speed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["name"], p["element"], p.get("element2", ""), p.get("evo_stage", ""),
            p["ability"], p.get("ability_desc", ""),
            p["base_hp"], p["base_atk"], p["base_spatk"],
            p["base_def"], p["base_spdef"], p["base_speed"],
        ))
        pokemon_id = c.lastrowid

        # 关联自学技能
        for skill_name in p.get("skills", "").split(","):
            skill_name = skill_name.strip()
            if skill_name and skill_name in skill_ids:
                c.execute("""
                    INSERT OR IGNORE INTO pokemon_skill (pokemon_id, skill_id, learn_type)
                    VALUES (?, ?, '自学')
                """, (pokemon_id, skill_ids[skill_name]))

        # 关联血脉技能
        for skill_name in p.get("bloodline_skills", "").split(","):
            skill_name = skill_name.strip()
            if skill_name and skill_name in skill_ids:
                c.execute("""
                    INSERT OR IGNORE INTO pokemon_skill (pokemon_id, skill_id, learn_type)
                    VALUES (?, ?, '血脉')
                """, (pokemon_id, skill_ids[skill_name]))

        # 关联技能石
        for skill_name in p.get("skill_stones", "").split(","):
            skill_name = skill_name.strip()
            if skill_name and skill_name in skill_ids:
                c.execute("""
                    INSERT OR IGNORE INTO pokemon_skill (pokemon_id, skill_id, learn_type)
                    VALUES (?, ?, '技能石')
                """, (pokemon_id, skill_ids[skill_name]))

        # 进化链
        prev = p.get("prev_evo", "")
        if prev and prev != p["name"]:
            c.execute("""
                INSERT OR IGNORE INTO evolution (from_name, to_name)
                VALUES (?, ?)
            """, (prev, p["name"]))

    conn.commit()

    # 统计
    pet_count = c.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]
    skill_count = c.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
    rel_count = c.execute("SELECT COUNT(*) FROM pokemon_skill").fetchone()[0]
    evo_count = c.execute("SELECT COUNT(*) FROM evolution").fetchone()[0]
    print(f"\n  数据库: {pet_count} 精灵, {skill_count} 技能, {rel_count} 学习关系, {evo_count} 进化链")

    conn.close()
    print(f"  → {DB_PATH}")


def main():
    print("=== 洛克王国世界 Wiki 爬虫 ===\n")

    # Step 1: 获取技能列表
    print("[1/4] 获取技能列表...")
    skill_names = get_category_members("Category:技能")
    print(f"  共 {len(skill_names)} 个技能\n")

    # Step 2: 爬取技能详情
    print("[2/4] 爬取技能详情...")
    skills = crawl_pages(skill_names, "skills", parse_skill)
    print(f"  完成: {len(skills)} 个\n")

    # Step 3: 获取精灵列表
    print("[3/4] 获取精灵列表...")
    pet_names = get_category_members("Category:精灵")
    print(f"  共 {len(pet_names)} 个精灵\n")

    # Step 4: 爬取精灵详情
    print("[4/4] 爬取精灵详情...")
    pets = crawl_pages(pet_names, "pets", parse_pet)
    print(f"  完成: {len(pets)} 个\n")

    # Step 5: 构建数据库
    print("构建数据库...")
    build_db(pets, skills)
    print("\n完成。")


if __name__ == "__main__":
    main()
