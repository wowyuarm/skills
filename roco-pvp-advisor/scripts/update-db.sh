#!/bin/bash
# 分批更新洛克王国世界 Wiki 数据 → 本地 roco.db
# 用法: bash scripts/update-db.sh
#
# 分三步，各自独立，挂了可单独重跑：
#   1. bash scripts/update-db.sh skills   → 只爬技能
#   2. bash scripts/update-db.sh pets     → 只爬精灵
#   3. bash scripts/update-db.sh build    → 从 skills.json + pets.json 建库
# 不带参数：跑全部三步

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

run_skills() {
    echo "=== [1/3] 爬取技能 ==="
    python3 "$SCRIPT_DIR/crawl-skills.py"
}

run_pets() {
    echo "=== [2/3] 爬取精灵 ==="
    python3 "$SCRIPT_DIR/crawl-pets.py"
}

run_build() {
    echo "=== [3/3] 构建数据库 ==="
    python3 "$SCRIPT_DIR/build-db.py"
    echo ""
    echo "验证..."
    python3 -c "
import sys; sys.path.insert(0, '$PROJECT_DIR')
from scripts.db import count_pets, count_skills
print(f'  roco.db: {count_pets()} 精灵, {count_skills()} 技能')
"
    echo ""
    echo "完成。"
}

case "${1:-}" in
    skills) run_skills ;;
    pets)   run_pets ;;
    build)  run_build ;;
    *)
        # 清理旧的单文件爬虫进度（新脚本用独立的 progress 文件）
        rm -f "$PROJECT_DIR/data/crawl_progress.json"
        run_skills
        run_pets
        run_build
        ;;
esac
