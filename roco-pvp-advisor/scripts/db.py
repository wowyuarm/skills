"""
洛克王国世界数据查询 — 先从 BiliGame Wiki 实时查，失败则从本地 DB 兜底。

数据源优先级: wiki API > roco.db (自爬)

DB 路径: data/roco.db
"""

import json
import re
import sqlite3
import urllib.request
import urllib.parse
import os

WIKI_API = "https://wiki.biligame.com/rocom/api.php"
USER_AGENT = "roco-pvp-advisor/1.0"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROCO_DB = os.path.join(BASE_DIR, "data", "roco.db")

_conn = None


def _get_conn():
    """获取 DB 连接，无 DB 则返回 None。"""
    global _conn
    if _conn:
        return _conn
    if not os.path.exists(ROCO_DB):
        return None
    _conn = sqlite3.connect(ROCO_DB)
    _conn.row_factory = sqlite3.Row
    return _conn


def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _wiki_parse(wikitext: str) -> dict:
    """解析 wiki 模板为 key-value。"""
    m = re.match(r'\{\{(.+?)\n', wikitext)
    if not m:
        return {}
    inner = wikitext[len(m.group(0)):]
    if inner.endswith("}}"):
        inner = inner[:-2]
    result = {"_template": m.group(1).strip()}
    for part in re.split(r'\n\|', inner):
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip().lstrip("|")] = v.strip()
    return result


def _wiki_call(params: dict) -> dict | None:
    qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"{WIKI_API}?{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return json.loads(resp.read())
    except Exception:
        pass
    return None


def _wiki_fetch_page(page_name: str) -> dict | None:
    """从 wiki 获取并解析一个页面。"""
    data = _wiki_call({
        "action": "parse", "page": page_name,
        "prop": "wikitext", "format": "json",
    })
    if not data or "parse" not in data:
        return None
    return _wiki_parse(data["parse"]["wikitext"]["*"])


def _wiki_get_pet(name: str) -> dict | None:
    """从 wiki 实时查精灵。"""
    d = _wiki_fetch_page(name)
    if not d or d.get("_template") not in ("精灵信息", "宠物信息"):
        return None

    return {
        "name": d.get("精灵名称", d.get("宠物名称", name)),
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
        "skills": d.get("技能", ""),
        "bloodline_skills": d.get("血脉技能", ""),
        "skill_stones": d.get("可学技能石", ""),
        "prev_evo": d.get("精灵初阶名称", ""),
        "_source": "wiki",
    }


def _wiki_get_skill(name: str) -> dict | None:
    """从 wiki 实时查技能。"""
    d = _wiki_fetch_page(name)
    if not d or d.get("_template") != "技能信息":
        return None

    return {
        "name": d.get("技能名称", name),
        "element": d.get("属性", ""),
        "category": d.get("技能类别", ""),
        "power": _safe_int(d.get("威力", 0)),
        "energy_cost": _safe_int(d.get("耗能", 0)),
        "effect": d.get("效果", ""),
        "_source": "wiki",
    }


def _row_to_dict(row) -> dict | None:
    return dict(row) if row else None


# ── 公共 API ──

def get_pet(name: str) -> dict | None:
    """查精灵：wiki 优先，失败则 DB 兜底。"""
    # 先试 wiki
    pet = _wiki_get_pet(name)
    if pet:
        return pet

    # 兜底 DB
    conn = _get_conn()
    if not conn:
        return None
    c = conn.cursor()

    c.execute("SELECT * FROM pokemon WHERE name = ?", (name,))
    row = c.fetchone()
    if row:
        return _row_to_dict(row)

    c.execute("SELECT * FROM pokemon WHERE name LIKE ? ORDER BY evo_stage DESC LIMIT 1",
              (f"{name}%",))
    row = c.fetchone()
    if row:
        return _row_to_dict(row)

    base = name.split("（")[0].split("(")[0]
    if base != name:
        c.execute("SELECT * FROM pokemon WHERE name LIKE ? ORDER BY evo_stage DESC LIMIT 1",
                  (f"{base}%",))
        row = c.fetchone()
        if row:
            return _row_to_dict(row)

    c.execute("SELECT * FROM pokemon WHERE name LIKE ? ORDER BY evo_stage DESC LIMIT 1",
              (f"%{name}%",))
    row = c.fetchone()
    return _row_to_dict(row)


def get_pet_skills(pet_name: str) -> list[dict]:
    """获取精灵可学技能：优先从 wiki 查精灵页面的技能列表，再补 DB 详情。"""
    # wiki 查精灵拿到技能名列表
    wiki_pet = _wiki_get_pet(pet_name)
    if wiki_pet and wiki_pet.get("skills"):
        skill_names = [s.strip() for s in wiki_pet["skills"].split(",") if s.strip()]
        skills = []
        for sn in skill_names:
            s = _wiki_get_skill(sn)
            if s:
                skills.append(s)
            else:
                # wiki 没拿到技能详情，从 DB 补
                db_s = get_skill(sn)
                if db_s:
                    skills.append(db_s)
        if skills:
            return skills

    # 兜底 DB
    conn = _get_conn()
    if not conn:
        return []
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT s.*
        FROM skill s
        JOIN pokemon_skill ps ON ps.skill_id = s.id
        JOIN pokemon p ON ps.pokemon_id = p.id
        WHERE p.name LIKE ?
        ORDER BY s.energy_cost, s.power DESC
    """, (f"{pet_name}%",))
    return [_row_to_dict(r) for r in c.fetchall()]


def get_skill(name: str) -> dict | None:
    """查技能：wiki 优先，失败则 DB 兜底。"""
    s = _wiki_get_skill(name)
    if s:
        return s

    conn = _get_conn()
    if not conn:
        return None
    c = conn.cursor()
    c.execute("SELECT * FROM skill WHERE name = ?", (name,))
    return _row_to_dict(c.fetchone())


def search_pets(keyword: str, element: str = None, limit: int = 20) -> list[dict]:
    """模糊搜索精灵（仅 DB，wiki 不支持搜索）。"""
    conn = _get_conn()
    if not conn:
        return []
    c = conn.cursor()
    query = "SELECT * FROM pokemon WHERE (name LIKE ? OR ability LIKE ?)"
    params = [f"%{keyword}%", f"%{keyword}%"]
    if element:
        query += " AND element = ?"
        params.append(element)
    query += f" LIMIT {limit}"
    c.execute(query, params)
    return [_row_to_dict(r) for r in c.fetchall()]


def search_skills(keyword: str, limit: int = 20) -> list[dict]:
    """模糊搜索技能（仅 DB）。"""
    conn = _get_conn()
    if not conn:
        return []
    c = conn.cursor()
    c.execute("SELECT * FROM skill WHERE name LIKE ? OR description LIKE ? OR effect LIKE ? LIMIT ?",
              (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
    return [_row_to_dict(r) for r in c.fetchall()]


def get_skill_learners(skill_name: str) -> list[str]:
    """哪些精灵能学这个技能（仅 DB）。"""
    conn = _get_conn()
    if not conn:
        return []
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT p.name FROM pokemon p
        JOIN pokemon_skill ps ON ps.pokemon_id = p.id
        JOIN skill s ON ps.skill_id = s.id
        WHERE s.name = ?
    """, (skill_name,))
    return [r[0] for r in c.fetchall()]


def get_evolution_chain(pet_name: str) -> list[str]:
    """获取进化链。先从 wiki 往上追溯，兜底 DB。"""
    # 用 wiki 往上追溯
    chain = []
    current = pet_name
    visited = set()
    while current and current not in visited:
        visited.add(current)
        d = _wiki_get_pet(current)
        if not d:
            break
        chain.insert(0, d["name"])
        prev = d.get("prev_evo", "")
        if prev and prev != current and prev not in visited:
            current = prev
        else:
            break

    # 如果 wiki 给的不完整，补 DB
    if len(chain) <= 1:
        try:
            conn = _get_conn()
            if not conn:
                return chain if chain else [pet_name]
            c = conn.cursor()
            db_chain = [pet_name]
            current = pet_name
            visited = {pet_name}
            while True:
                row = c.execute(
                    "SELECT from_name FROM evolution WHERE to_name = ? LIMIT 1",
                    (current,)
                ).fetchone()
                if not row or row[0] in visited:
                    break
                current = row[0]
                visited.add(current)
                db_chain.insert(0, current)
            return db_chain
        except Exception:
            pass

    return chain if chain else [pet_name]


def count_pets() -> int:
    conn = _get_conn()
    if not conn:
        return 0
    return conn.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]


def count_skills() -> int:
    conn = _get_conn()
    if not conn:
        return 0
    return conn.execute("SELECT COUNT(*) FROM skill").fetchone()[0]
