"""RAG 景点知识服务：ChromaDB 向量检索 + LLM 生成导游式回答。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb

from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"

_knowledge_client = chromadb.PersistentClient(
    path=str(Path(__file__).resolve().parent.parent.parent / "db" / "chroma_knowledge")
)
_knowledge_collection = _knowledge_client.get_or_create_collection(
    name="spot_knowledge",
    metadata={"hnsw:space": "cosine"},
)

KNOWLEDGE_QA_PROMPT = """你是一位博学而生动的导游「AI智游伴」。请根据下方检索到的景点知识，用通俗有趣、富有感染力的语言回答用户的问题。

## 检索到的相关知识

{context}

## 回答要求

1. 像一位经验丰富的导游在向游客讲解，语言生动有趣
2. 适当加入历史典故或趣味小故事，让回答更有吸引力
3. 如果知识中包含游玩建议，可以自然地融入回答中
4. 回答长度控制在200-400字，不要太长
5. 如果检索到的知识不足以回答问题，坦诚告知并建议用户进一步了解

## 用户问题

{question}
"""


def load_knowledge_base() -> int:
    """扫描 knowledge 目录，将 Markdown 文档分块后向量化入库。返回加载的块数。"""
    if not KNOWLEDGE_DIR.exists():
        logger.warning("知识库目录不存在：%s", KNOWLEDGE_DIR)
        return 0

    total_chunks = 0
    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md")):
        spot_name = md_file.stem
        content = md_file.read_text(encoding="utf-8")
        chunks = [c.strip() for c in content.split("\n\n") if c.strip()]

        ids = [f"{spot_name}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"spot_name": spot_name, "chunk_index": i} for i in range(len(chunks))]

        if ids:
            _knowledge_collection.upsert(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
            )
            total_chunks += len(chunks)
            logger.info("加载景点知识：%s（%d 个段落）", spot_name, len(chunks))

    logger.info("知识库加载完成，共 %d 个段落", total_chunks)
    return total_chunks


def retrieve_knowledge(query: str, spot_name: str | None = None, top_k: int = 5) -> list[dict]:
    """从 ChromaDB 检索与 query 相关的知识段落。"""
    try:
        where_filter = {"spot_name": spot_name} if spot_name else None
        results = _knowledge_collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
        )
        docs = []
        if results["documents"] and results["documents"][0]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                docs.append({"text": doc, "spot_name": meta.get("spot_name", "")})
        return docs
    except Exception:
        logger.exception("知识检索失败")
        return []


async def query_knowledge(question: str, spot_name: str | None = None) -> str:
    """完整 RAG 流程：检索知识 → 双层兜底 → 调用 LLM 生成导游式回答。

    兜底策略：
    1. 检索为空（知识库中无相关内容） → LLM 通用知识 + 诚实标注来源
    2. 检索有结果但 spot_name 明确时无匹配 → 低置信度标记，LLM 自行判断
    3. 正常情况 → 知识库 Context 注入，高质量导游回答
    """
    retrieved = retrieve_knowledge(question, spot_name, top_k=5)

    # 【兜底 1】检索为空 → LLM 通用知识，诚实告知
    if not retrieved:
        fallback_prompt = (
            "你是「AI智游伴」的景点讲解员。知识库中没有检索到与用户问题直接相关的资料。\n"
            "请基于你的通用知识回答用户问题，语言生动有趣，像一位热情的导游。\n"
            "在回答末尾添加一句说明：'以上信息基于通用知识整理，如需更详尽的当地攻略，可以告诉我来补充哦～'\n\n"
            f"用户问题：{question}"
        )
        answer = await call_llm(
            messages=[{"role": "user", "content": question}],
            system_prompt=fallback_prompt,
            temperature=0.7,
            max_tokens=800,
        )
        return answer

    context = "\n\n".join(
        f"【{r['spot_name']}】{r['text']}" for r in retrieved
    )

    # 【兜底 2】spot_name 明确但检索结果中无匹配 → 低置信度 Context
    if spot_name:
        matching_chunks = [r for r in retrieved if r["spot_name"] == spot_name]
        if not matching_chunks:
            low_conf_prompt = (
                "你是「AI智游伴」的景点讲解员。\n"
                "知识库中没有找到关于该景点的直接资料，以下检索到的是一般性旅行相关内容，仅供参考：\n\n"
                f"{context}\n\n"
                "请基于你的通用知识回答用户问题。如果检索内容中有相关的部分可以引用，没有则可以忽略。\n"
                "语言保持生动有趣的导游风格。\n\n"
                f"用户问题：{question}"
            )
            answer = await call_llm(
                messages=[{"role": "user", "content": question}],
                system_prompt=low_conf_prompt,
                temperature=0.7,
                max_tokens=800,
            )
            return answer

    # 正常情况：有匹配的知识片段，高质量导游回答
    prompt = KNOWLEDGE_QA_PROMPT.format(context=context, question=question)
    answer = await call_llm(
        messages=[{"role": "user", "content": question}],
        system_prompt=prompt,
        temperature=0.7,
        max_tokens=800,
    )
    return answer
