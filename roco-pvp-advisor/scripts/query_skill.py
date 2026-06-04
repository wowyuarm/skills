#!/usr/bin/env python3
"""查询技能详情。wiki 实时查优先，DB 兜底。
用法: python3 scripts/query_skill.py --name 技能名 [--learners]"""

import json
import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
from scripts.db import get_skill, search_skills, get_skill_learners


def main():
    import argparse
    parser = argparse.ArgumentParser(description="查询洛克王国世界技能详情")
    parser.add_argument("--name", "-n", type=str, required=True, help="技能名称")
    parser.add_argument("--learners", "-l", action="store_true", help="列出能学此技能的精灵")
    args = parser.parse_args()

    skill = get_skill(args.name)
    if not skill:
        matches = search_skills(args.name, limit=5)
        if matches:
            print(json.dumps({
                "error": f"未找到精确匹配: {args.name}",
                "hints": [s.get("name", s.get("技能名称", "")) for s in matches]
            }, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"error": f"未找到: {args.name}"}, ensure_ascii=False))
        sys.exit(1)

    result = {
        "name": skill.get("name", skill.get("技能名称", "")),
        "element": skill.get("element", skill.get("属性", "")),
        "category": skill.get("category", skill.get("技能类别", "")),
        "power": skill.get("power", skill.get("威力", 0)) or 0,
        "energy_cost": skill.get("energy_cost", skill.get("耗能", 0)) or 0,
        "effect": skill.get("effect", skill.get("效果", skill.get("description", ""))),
        "source": skill.get("_source", "db"),
    }

    if args.learners:
        result["learners"] = get_skill_learners(result["name"])

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
