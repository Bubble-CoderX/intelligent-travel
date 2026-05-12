"""知识库自动调研：LLM 直接生成景点知识 → 保存 Markdown → 向量化入库。"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import chromadb

from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

# 复用 rag_service 的 ChromaDB 连接
_knowledge_client = chromadb.PersistentClient(
    path=str(Path(__file__).resolve().parent.parent.parent / "db" / "chroma_knowledge")
)
_knowledge_collection = _knowledge_client.get_or_create_collection(
    name="spot_knowledge",
    metadata={"hnsw:space": "cosine"},
)

# ── LLM 知识生成 Prompt ────────────────────────────────
KNOWLEDGE_GEN_PROMPT = """你是「AI智游伴」的知识编辑。请根据你的知识，为景点「{spot_name}」生成一份详尽的旅游知识文档。

## 文档结构（必须包含以下板块）

1. **简介** — 2-3 句话介绍景点的基本信息（位置、级别、特色）
2. **历史文化** — 核心历史事件、建造背景、文化意义、名人典故，300-400字
3. **主要看点** — 5-8 个核心景点/看点，每个 1-2 句话描述
4. **游玩建议** — 推荐游览路线、最佳季节、建议游玩时长
5. **实用信息** — 门票价格、开放时间、交通方式、注意事项

## 要求
- 语言生动有趣，像一位导游在向朋友介绍
- 用 Markdown 格式，板块用二级标题（##）分隔
- 信息尽量准确，不确定的标注"建议出发前确认"
- 控制在 800-1500 字
- 直接输出 Markdown，不要包裹在代码块中
"""


def has_local_knowledge(spot_name: str) -> bool:
    """检查指定景点是否已有本地知识文件。"""
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', spot_name)
    return (KNOWLEDGE_DIR / f"{safe_name}.md").exists()


async def _generate_knowledge(spot_name: str) -> str:
    """用 LLM 直接生成景点知识文档。"""
    prompt = KNOWLEDGE_GEN_PROMPT.format(spot_name=spot_name)
    answer = await call_llm(
        messages=[{"role": "user", "content": f"请为景点「{spot_name}」生成旅游知识文档"}],
        system_prompt=prompt,
        temperature=0.3,
        max_tokens=2000,
    )
    return answer


def _save_knowledge_file(spot_name: str, content: str) -> Path:
    """将策展内容保存为 Markdown 文件。"""
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', spot_name)
    file_path = KNOWLEDGE_DIR / f"{safe_name}.md"
    file_path.write_text(content, encoding="utf-8")
    logger.info("知识文件已保存：%s", file_path)
    return file_path


def _vectorize_single(spot_name: str, content: str) -> int:
    """将单个景点知识文档向量化入库，返回入库的段落数。"""
    chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
    if not chunks:
        return 0

    safe_name = re.sub(r'[\\/:*?"<>|]', '_', spot_name)
    ids = [f"{safe_name}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"spot_name": safe_name, "chunk_index": i} for i in range(len(chunks))]

    _knowledge_collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )
    logger.info("向量化入库：%s（%d 个段落）", spot_name, len(chunks))
    return len(chunks)


async def auto_expand(spot_name: str) -> dict:
    """自动调研管线：LLM 生成知识 → 保存 → 向量化。返回结果摘要。"""
    logger.info("开始自动调研：「%s」", spot_name)

    # 1. LLM 直接生成知识文档
    content = await _generate_knowledge(spot_name)
    if not content or len(content.strip()) < 50:
        return {"status": "generate_failed", "message": "LLM 生成结果过短，无法入库"}

    # 2. 保存文件
    _save_knowledge_file(spot_name, content)

    # 3. 向量化入库
    chunk_count = _vectorize_single(spot_name, content)

    return {
        "status": "ok",
        "spot_name": spot_name,
        "chunk_count": chunk_count,
        "content_length": len(content),
    }
