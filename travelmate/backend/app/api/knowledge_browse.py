"""O18: 知识库浏览 API — 支持子目录分类浏览。"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-browse", tags=["knowledge-browse"])

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"

# 分类目录映射
CATEGORY_MAP = {
    "cities": "城市", "spots": "景点", "food": "美食",
    "culture": "非遗文化", "folk": "民俗", "history": "历史遗址",
    "nature": "名山大川", "ancient": "古城古镇", "museum": "博物馆",
}


def _parse_knowledge_file(filepath: Path, category: str = "") -> dict:
    """从 Markdown 文件中提取简要信息。"""
    content = filepath.read_text(encoding="utf-8")
    name = filepath.stem

    # 提取简介
    lines = content.split("\n")
    description = ""
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("|"):
            description = line[:100]
            break

    spot_count = len(re.findall(r'⭐|推荐等级|景点推荐|核心景点', content))
    food_count = len(re.findall(r'🔥|必吃|美食推荐|特色餐饮', content))
    size_kb = round(filepath.stat().st_size / 1024, 1)

    return {
        "city": name,
        "category": category,
        "file": filepath.name,
        "description": description,
        "spot_count": spot_count,
        "food_count": food_count,
        "size_kb": size_kb,
        "char_count": len(content),
    }


@router.get("/list")
async def list_knowledge(
    keyword: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """列出知识库中的所有内容，支持按分类和关键词筛选。"""
    if not KNOWLEDGE_DIR.exists():
        return {"items": [], "total": 0}

    items = []
    # 扫描所有子目录
    for subdir in sorted(KNOWLEDGE_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        cat_name = subdir.name
        if category and cat_name != category:
            continue
        for f in sorted(subdir.glob("*.md")):
            try:
                item = _parse_knowledge_file(f, cat_name)
                if keyword and keyword not in item["city"] and keyword not in item["description"]:
                    continue
                items.append(item)
            except Exception:
                continue

    total = len(items)
    items = items[offset:offset + limit]
    return {"items": items, "total": total}


@router.get("/categories")
async def list_categories():
    """获取知识库分类列表及每个分类的文件数。"""
    if not KNOWLEDGE_DIR.exists():
        return {"categories": []}

    categories = []
    for subdir in sorted(KNOWLEDGE_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        count = len(list(subdir.glob("*.md")))
        if count > 0:
            categories.append({
                "id": subdir.name,
                "name": CATEGORY_MAP.get(subdir.name, subdir.name),
                "count": count,
            })
    return {"categories": categories}


@router.get("/cities")
async def list_cities():
    """获取城市分类下的所有城市名称。"""
    cities_dir = KNOWLEDGE_DIR / "cities"
    if not cities_dir.exists():
        return {"cities": [], "total": 0}
    cities = sorted(f.stem for f in cities_dir.glob("*.md"))
    return {"cities": cities, "total": len(cities)}


@router.get("/{name}/content")
async def get_knowledge_content(name: str):
    """获取指定知识文件的完整内容（搜索所有子目录）。"""
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
    # 搜索所有子目录
    for subdir in KNOWLEDGE_DIR.iterdir():
        if not subdir.is_dir():
            continue
        filepath = subdir / f"{safe_name}.md"
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            return {"name": name, "category": subdir.name, "content": content, "char_count": len(content)}
    return {"error": f"未找到 {name} 的知识库"}
