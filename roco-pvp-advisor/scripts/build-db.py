#!/usr/bin/env python3
"""
从 data/skills.json + data/pets.json 构建 data/roco.db。
用法: python3 scripts/build-db.py
"""

import json, os, sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_JSON = os.path.join(BASE, "data", "skills.json")
PETS_JSON = os.path.join(BASE, "data", "pets.json")
DB_PATH = os.path.join(BASE, "data", "roco.db")


def main():
    if not os.path.exists(SKILLS_JSON):
        print(f"错误: {SKILLS_JSON} 不存在，请先运行 crawl-skills.py")
        return
    if not os.path.exists(PETS_JSON):
        print(f"错误: {PETS_JSON} 不存在，请先运行 crawl-pets.py")
        return

    with open(SKILLS_JSON) as f:
        skills = json.load(f)
    with open(PETS_JSON) as f:
        pets = json.load(f)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

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
    c.execute("""
        CREATE TABLE pokemon_skill (
            pokemon_id INTEGER,
            skill_id INTEGER,
            learn_type TEXT DEFAULT '自学',
            PRIMARY KEY (pokemon_id, skill_id)
        )
    """)
    c.execute("""
        CREATE TABLE evolution (
            from_name TEXT,
            to_name TEXT,
            PRIMARY KEY (from_name, to_name)
        )
    """)

    skill_ids = {}
    for _, s in skills.items():
        c.execute("""
            INSERT OR IGNORE INTO skill (name, element, category, power, energy_cost, effect)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (s["name"], s["element"], s["category"], s["power"], s["energy_cost"], s.get("effect", "")))
        skill_ids[s["name"]] = c.lastrowid or c.execute(
            "SELECT id FROM skill WHERE name = ?", (s["name"],)
        ).fetchone()[0]
    print(f"  skills: {len(skill_ids)} 条")

    for page_name, p in pets.items():
        c.execute("""
            INSERT INTO pokemon (name, element, element2, evo_stage, ability, ability_desc,
                                 base_hp, base_atk, base_spatk, base_def, base_spdef, base_speed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page_name, p["element"], p.get("element2", ""), p.get("evo_stage", ""),
            p["ability"], p.get("ability_desc", ""),
            p["base_hp"], p["base_atk"], p["base_spatk"],
            p["base_def"], p["base_spdef"], p["base_speed"],
        ))
        pid = c.lastrowid

        for skill_list, learn_type in [
            (p.get("skills", ""), "自学"),
            (p.get("bloodline_skills", ""), "血脉"),
            (p.get("skill_stones", ""), "技能石"),
        ]:
            for sn in skill_list.split(","):
                sn = sn.strip()
                if sn and sn in skill_ids:
                    c.execute("""INSERT OR IGNORE INTO pokemon_skill (pokemon_id, skill_id, learn_type)
                                VALUES (?, ?, ?)""", (pid, skill_ids[sn], learn_type))

        prev = p.get("prev_evo", "")
        if prev and prev != p["name"]:
            c.execute("INSERT OR IGNORE INTO evolution (from_name, to_name) VALUES (?, ?)",
                      (prev, p["name"]))

    conn.commit()

    pc = c.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]
    sc = c.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
    rc = c.execute("SELECT COUNT(*) FROM pokemon_skill").fetchone()[0]
    ec = c.execute("SELECT COUNT(*) FROM evolution").fetchone()[0]
    print(f"  数据库: {pc} 精灵, {sc} 技能, {rc} 学习关系, {ec} 进化链")
    print(f"  → {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    main()
