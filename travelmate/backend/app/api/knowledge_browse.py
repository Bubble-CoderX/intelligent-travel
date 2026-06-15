"""O18: 知识库浏览 API — 列出所有知识文件 + 按城市/关键词筛选。"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-browse", tags=["knowledge-browse"])

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"


def _parse_knowledge_file(filepath: Path) -> dict:
    """从 Markdown 文件中提取简要信息。"""
    content = filepath.read_text(encoding="utf-8")
    city = filepath.stem  # 文件名即城市名

    # 提取简介（第一个段落）
    lines = content.split("\n")
    description = ""
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("|"):
            description = line[:100]
            break

    # 统计景点数
    spot_count = len(re.findall(r'⭐|推荐等级|景点推荐|核心景点', content))

    # 统计美食数
    food_count = len(re.findall(r'🔥|必吃|美食推荐|特色餐饮', content))

    # 文件大小
    size_kb = round(filepath.stat().st_size / 1024, 1)

    return {
        "city": city,
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
    limit: int = 50,
    offset: int = 0,
):
    """列出知识库中的所有城市及其摘要信息。"""
    if not KNOWLEDGE_DIR.exists():
        return {"items": [], "total": 0}

    items = []
    for f in sorted(KNOWLEDGE_DIR.glob("*.md")):
        try:
            item = _parse_knowledge_file(f)
            if keyword and keyword not in item["city"] and keyword not in item["description"]:
                continue
            items.append(item)
        except Exception:
            continue

    total = len(items)
    items = items[offset:offset + limit]
    return {"items": items, "total": total}


@router.get("/cities")
async def list_cities():
    """获取知识库中所有城市名称列表。"""
    if not KNOWLEDGE_DIR.exists():
        return {"cities": [], "total": 0}
    cities = sorted(f.stem for f in KNOWLEDGE_DIR.glob("*.md"))
    return {"cities": cities, "total": len(cities)}


@router.get("/{city}/content")
async def get_knowledge_content(city: str):
    """获取指定城市的完整知识库内容。"""
    filepath = KNOWLEDGE_DIR / f"{city}.md"
    if not filepath.exists():
        return {"error": f"未找到 {city} 的知识库"}
    content = filepath.read_text(encoding="utf-8")
    return {"city": city, "content": content, "char_count": len(content)}
