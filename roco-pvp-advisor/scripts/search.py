#!/usr/bin/env python3
"""搜索精灵或技能。用法: python3 scripts/search.py --type pet --keyword 关键词 [--element 属性]"""

import json
import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
from scripts.db import search_pets, search_skills


def main():
    import argparse
    parser = argparse.ArgumentParser(description="搜索洛克王国世界精灵/技能")
    parser.add_argument("--type", "-t", type=str, required=True,
                        choices=["pet", "skill"], help="搜索类型")
    parser.add_argument("--keyword", "-k", type=str, required=True, help="搜索关键词")
    parser.add_argument("--element", "-e", type=str, help="按属性筛选（仅 pet）")
    parser.add_argument("--limit", type=int, default=20, help="返回数量上限")
    args = parser.parse_args()

    if args.type == "pet":
        results = search_pets(args.keyword, element=args.element, limit=args.limit)
        output = [
            {
                "name": p["name"],
                "element": p["element"],
                "ability": p["ability"],
                "stats": {
                    "hp": p["base_hp"],
                    "atk": p["base_atk"],
                    "spatk": p["base_spatk"],
                    "def": p["base_def"],
                    "spdef": p["base_spdef"],
                    "spd": p["base_speed"],
                }
            }
            for p in results
        ]
    else:
        results = search_skills(args.keyword, limit=args.limit)
        output = [
            {
                "name": s["name"],
                "element": s["element"],
                "category": s["category"],
                "power": s["power"],
                "energy_cost": s["energy_cost"],
            }
            for s in results
        ]

    print(json.dumps({"count": len(output), "results": output}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
