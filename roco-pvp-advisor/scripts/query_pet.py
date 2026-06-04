#!/usr/bin/env python3
"""查询精灵详情。wiki 实时查优先，DB 兜底。
用法: python3 scripts/query_pet.py --name 精灵名 [--skills] [--evo]"""

import json
import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
from scripts.db import get_pet, get_pet_skills, get_evolution_chain


def main():
    import argparse
    parser = argparse.ArgumentParser(description="查询洛克王国世界精灵详情")
    parser.add_argument("--name", "-n", type=str, required=True, help="精灵名称")
    parser.add_argument("--skills", "-s", action="store_true", help="同时列出可学技能")
    parser.add_argument("--evo", "-e", action="store_true", help="同时列出进化链")
    args = parser.parse_args()

    pet = get_pet(args.name)
    if not pet:
        print(json.dumps({"error": f"未找到精灵: {args.name}"}, ensure_ascii=False))
        sys.exit(1)

    result = {
        "name": pet.get("name", pet.get("名称", "")),
        "element": pet.get("element", pet.get("属性", "")),
        "element2": pet.get("element2", pet.get("2属性", "")),
        "evo_stage": pet.get("evo_stage", pet.get("精灵阶段", "")),
        "ability": pet.get("ability", pet.get("特性", "")),
        "ability_desc": pet.get("ability_desc", pet.get("特性描述", pet.get("ability", ""))),
        "base_stats": {
            "hp": pet.get("base_hp", pet.get("生命种族值", 0)),
            "attack": pet.get("base_atk", pet.get("物攻种族值", 0)),
            "sp_attack": pet.get("base_spatk", pet.get("魔攻种族值", 0)),
            "defense": pet.get("base_def", pet.get("物防种族值", 0)),
            "sp_defense": pet.get("base_spdef", pet.get("魔防种族值", 0)),
            "speed": pet.get("base_speed", pet.get("速度种族值", 0)),
        },
        "source": pet.get("_source", "db"),
    }

    # 清理空值
    for k in ["element2", "evo_stage"]:
        if not result[k]:
            del result[k]

    if args.evo:
        result["evolution_chain"] = get_evolution_chain(result["name"])

    if args.skills:
        skills = get_pet_skills(result["name"])
        result["skills"] = [
            {
                "name": s.get("name", s.get("技能名称", "")),
                "element": s.get("element", s.get("属性", "")),
                "category": s.get("category", s.get("技能类别", "")),
                "power": s.get("power", s.get("威力", 0)) or 0,
                "energy_cost": s.get("energy_cost", s.get("耗能", 0)) or 0,
                "effect": s.get("effect", s.get("效果", s.get("description", ""))),
                "source": s.get("_source", "db"),
            }
            for s in skills
        ]

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
