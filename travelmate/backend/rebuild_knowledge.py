"""一键重建知识库：删除所有旧文件，用新版prompt重新生成。

用法：
    cd travelmate/backend
    python rebuild_knowledge.py              # 重建全部城市
    python rebuild_knowledge.py 广州 成都     # 只重建指定城市
    python rebuild_knowledge.py --list       # 只列出待重建城市
"""

import asyncio
import sys
from pathlib import Path

# 确保能找到 app 模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.knowledge_expander import (
    KNOWLEDGE_DIR,
    auto_expand,
    has_local_knowledge,
    _knowledge_collection,
)

# 默认城市列表
DEFAULT_CITIES = [
    "广州", "北京", "成都", "上海", "杭州", "西安",
    "重庆", "三亚", "厦门", "大理", "深圳", "南京",
    "武汉", "长沙", "昆明",
]


async def rebuild_all(cities: list[str], skip_existing: bool = False):
    """重建知识库。"""
    print(f"\n{'='*50}")
    print(f"  知识库重建 — 共 {len(cities)} 个城市")
    print(f"{'='*50}\n")

    success = 0
    failed = 0
    skipped = 0

    for i, city in enumerate(cities, 1):
        # 检查是否已有本地知识
        if skip_existing and has_local_knowledge(city):
            print(f"[{i}/{len(cities)}] 跳过 {city}（已有知识库）")
            skipped += 1
            continue

        print(f"[{i}/{len(cities)}] 生成 {city}...", end=" ", flush=True)
        try:
            result = await auto_expand(city)
            if result.get("status") == "ok":
                chunks = result.get("chunk_count", 0)
                print(f"OK（{chunks} 段落）")
                success += 1
            else:
                print(f"WARN: {result.get('message', '未知错误')}")
                failed += 1
        except Exception as exc:
            print(f"FAIL: {exc}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"  完成：{success} 成功 / {failed} 失败 / {skipped} 跳过")
    print(f"{'='*50}\n")


def list_cities():
    """列出待重建城市。"""
    print("\n默认城市列表：")
    for city in DEFAULT_CITIES:
        status = "[已有]" if has_local_knowledge(city) else "[待生成]"
        print(f"  {city} — {status}")
    print(f"\n用法: python rebuild_knowledge.py 广州 成都  # 只重建指定城市")
    print(f"      python rebuild_knowledge.py            # 重建全部城市")
    print(f"      python rebuild_knowledge.py --skip     # 跳过已有城市")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--list" in args:
        list_cities()
    elif "--skip" in args:
        asyncio.run(rebuild_all(DEFAULT_CITIES, skip_existing=True))
    elif args:
        asyncio.run(rebuild_all(args))
    else:
        asyncio.run(rebuild_all(DEFAULT_CITIES))
