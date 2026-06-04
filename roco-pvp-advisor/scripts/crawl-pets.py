#!/usr/bin/env python3
"""
仅爬取精灵数据，存入 data/pets.json。
用法: python3 scripts/crawl-pets.py
"""

import json, re, time, urllib.request, urllib.error, urllib.parse, os

API = "https://wiki.biligame.com/rocom/api.php"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT = os.path.join(DATA_DIR, "pets.json")
PROGRESS = os.path.join(DATA_DIR, "crawl_pets_progress.json")

UA = "roco-pvp-advisor/1.0 (wiki crawler)"
BATCH_SIZE = 5
BATCH_DELAY = 8
RETRY_MAX = 5


def api_call(params: dict) -> dict | None:
    qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"{API}?{qs}"
    for attempt in range(1, RETRY_MAX + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 567:
                wait = min(15 * (2 ** attempt), 120)
                print(f"  [rate-limit] 等 {wait}s (第 {attempt}/{RETRY_MAX})...")
                time.sleep(wait)
                continue
            print(f"  [HTTP {e.code}] {url}")
            return None
        except Exception as e:
            if attempt < RETRY_MAX:
                time.sleep(min(10 * (2 ** attempt), 60))
                continue
            print(f"  [error] {e}")
            return None
    return None


def get_category_members(category: str) -> list[str]:
    names = []
    cmcontinue = None
    while True:
        params = {"action": "query", "list": "categorymembers",
                  "cmtitle": category, "cmlimit": "max", "format": "json"}
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


def parse_wikitext_template(text: str) -> dict:
    m = re.match(r'\{\{(.+?)\n', text)
    if not m:
        return {}
    inner = text[len(m.group(0)):]
    if inner.endswith("}}"):
        inner = inner[:-2]
    result = {"_template": m.group(1).strip()}
    for part in re.split(r'\n\|', inner):
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip().lstrip("|")] = v.strip()
    return result


def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def parse_pet(wikitext: str) -> dict | None:
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
        "skills": d.get("技能", ""),
        "bloodline_skills": d.get("血脉技能", ""),
        "skill_stones": d.get("可学技能石", ""),
        "prev_evo": d.get("精灵初阶名称", ""),
    }


def _save_progress(results: dict, failed: list, next_idx: int):
    with open(PROGRESS, "w") as f:
        json.dump({"results": results, "failed": failed, "next_idx": next_idx}, f, ensure_ascii=False)


def crawl_pages(names: list[str], parser) -> dict[str, dict]:
    results = {}
    failed = []
    total = len(names)
    start_idx = 0

    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS) as f:
                p = json.load(f)
            results = p.get("results", {})
            failed = p.get("failed", [])
            start_idx = p.get("next_idx", 0)
            print(f"  [resume] 从 {start_idx}/{total} 继续 ({len(results)} 已完成)")
        except Exception:
            pass

    for i in range(start_idx, total, BATCH_SIZE):
        batch = names[i:i + BATCH_SIZE]
        for name in batch:
            data = api_call({"action": "parse", "page": name, "prop": "wikitext", "format": "json"})
            if not data or "parse" not in data:
                failed.append(name)
                continue
            parsed = parser(data["parse"]["wikitext"]["*"])
            if parsed:
                results[name] = parsed
            else:
                failed.append(name)

        done = min(i + BATCH_SIZE, total)
        print(f"  [{done}/{total}] ok={len(results)} fail={len(failed)}")
        _save_progress(results, failed, i + BATCH_SIZE)

        if failed:
            retry = list(failed)
            failed.clear()
            for name in retry:
                time.sleep(2)
                data = api_call({"action": "parse", "page": name, "prop": "wikitext", "format": "json"})
                if data and "parse" in data:
                    parsed = parser(data["parse"]["wikitext"]["*"])
                    if parsed:
                        results[name] = parsed
                        continue
                failed.append(name)
            _save_progress(results, failed, i + BATCH_SIZE)

        if i + BATCH_SIZE < total:
            time.sleep(BATCH_DELAY)

    if os.path.exists(PROGRESS):
        os.remove(PROGRESS)
    return results


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("[1/2] 获取精灵列表...")
    names = get_category_members("Category:精灵")
    print(f"  共 {len(names)} 个精灵\n")

    print("[2/2] 爬取精灵详情...")
    pets = crawl_pages(names, parse_pet)
    print(f"  完成: {len(pets)} 个\n")

    with open(OUTPUT, "w") as f:
        json.dump(pets, f, ensure_ascii=False, indent=2)
    print(f"→ {OUTPUT} ({len(pets)} 条)")


if __name__ == "__main__":
    main()
