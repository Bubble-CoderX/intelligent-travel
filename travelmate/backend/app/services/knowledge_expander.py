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
KNOWLEDGE_GEN_PROMPT = """你是「AI智游伴」的知识编辑。请为目的地「{spot_name}」生成一份全面详尽的旅游知识文档。

## 文档结构（必须包含以下所有板块，内容要尽可能全面）

1. **目的地简介** — 3-5句话（位置、气候、特色、适合人群、最佳季节）

2. **核心景点推荐**（必须列出15-20个景点，覆盖主流和小众）
   - 每个景点包含：名称、位置、门票价格、游玩时长、简介（2-3句话）、是否适合带娃
   - 每个景点标注推荐等级：⭐⭐⭐⭐⭐必去 / ⭐⭐⭐⭐推荐 / ⭐⭐⭐小众 / ⭐⭐可选
   - 10-12个主流景点（必去的标志性景点）
   - 5-8个小众景点（本地人推荐、游客较少但体验好的地方）
   - 景点类型要多样化：历史古迹、自然景观、文艺打卡、亲子乐园、夜景观赏等

3. **特色餐饮推荐**（必须列出12-15道美食，覆盖全时段）
   - 早餐/早茶类：2-3道
   - 正餐/硬菜类：4-5道（火锅、烤肉、地方特色大菜等）
   - 小吃/街头类：3-4道
   - 甜品/饮品/下午茶类：2-3道
   - 每道菜包含：菜名、简短描述、人均价格（用**加粗**标注）、推荐餐厅/品牌
   - 每道菜标注推荐等级：🔥🔥🔥必吃 / 🔥🔥推荐 / 🔥小众

4. **住宿区域建议**（必须列出5-6个区域，覆盖不同预算）
   - 高档区（500-1000元/晚）
   - 中档区（200-500元/晚）
   - 经济区（100-200元/晚）
   - 景点旁（方便游览特定景区）
   - 交通枢纽旁（方便到达和离开）
   - 特色民宿区（有氛围感的住宿选择）
   - 每个区域包含：区域名、特点、酒店预算区间、适合人群

5. **经典行程路线**（必须给出5条不同主题的路线）
   - 2日游经典路线
   - 3日游经典路线
   - 5日游深度路线
   - 亲子专属路线（适合带小孩）
   - 美食专线路线
   - 每条路线按天数分段，每天列出上午/下午/晚上的安排

6. **实用信息**
   - 到达交通（飞机/高铁/自驾）
   - 市内交通（地铁/公交/打车）
   - 最佳旅游季节
   - 气候与穿衣建议
   - 注意事项与安全提示
   - 当地特色文化/习俗/禁忌

## 要求
- 语言生动有趣，像导游在向朋友介绍
- 用Markdown格式，板块用二级标题（##）分隔
- 价格信息尽量准确，不确定的标注"仅供参考"
- 内容要全面丰富，控制在2000-3000字
- 直接输出Markdown，不要包裹在代码块中
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
        max_tokens=4000,
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


# ── 用户反馈纠正闭环 ──────────────────────────────────

CORRECTION_EXTRACT_PROMPT = """你是信息纠正提取器。用户指出了一条关于景点的错误信息。

## 用户的纠正消息
{correction_message}

## 请提取以下信息（严格 JSON）
{{
  "spot_name": "被纠正的景点名称（从消息或上下文中推断）",
  "original_fact": "用户指出的错误信息（简短描述错误的部分）",
  "corrected_fact": "用户给出的正确信息（原样保留用户说法）"
}}

## 规则
- spot_name 必须是中文景点名（2字以上）
- 如果用户没有明确说景点名，从上下文推断最可能的景点
- 如果无法判断景点或纠正内容不明确，返回 {{"error": "无法判断"}}
- 只输出 JSON，不要输出其他内容
"""

CORRECTION_APPLY_PROMPT = """你是知识库编辑。请根据纠正信息，修改下面的景点知识文档。

## 纠正信息
景点：{spot_name}
错误内容：{original_fact}
正确内容：{corrected_fact}

## 当前文档内容
{document_content}

## 要求
1. 找到文档中包含错误信息的段落
2. 只修改错误的部分，保持其他内容不变
3. 保持 Markdown 格式不变
4. 输出修改后的完整文档
5. 直接输出文档内容，不要加解释
"""


def _find_spot_file(spot_name: str) -> Path | None:
    """查找景点对应的 .md 文件（支持模糊匹配）。"""
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', spot_name)
    exact = KNOWLEDGE_DIR / f"{safe_name}.md"
    if exact.exists():
        return exact
    # 模糊匹配：文件名包含关键词
    for f in KNOWLEDGE_DIR.glob("*.md"):
        if safe_name in f.stem or f.stem in safe_name:
            return f
    return None


async def correct_knowledge(correction_message: str) -> dict:
    """用户反馈纠正闭环：提取纠正信息 → 定位文件 → 修改 → 重新向量化。

    返回 {"status": "ok", "spot_name": "...", "applied": True/False}
    """
    logger.info("开始纠正流程：%s", correction_message)

    # 1. 用 LLM 提取纠正信息
    extract_prompt = CORRECTION_EXTRACT_PROMPT.format(correction_message=correction_message)
    raw = await call_llm(
        messages=[{"role": "user", "content": correction_message}],
        system_prompt=extract_prompt,
        temperature=0.0,
        max_tokens=300,
    )

    import json
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        # 尝试提取 JSON 片段
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                info = json.loads(match.group())
            except json.JSONDecodeError:
                return {"status": "parse_failed", "message": "无法解析纠正信息"}
        else:
            return {"status": "parse_failed", "message": "无法解析纠正信息"}

    if "error" in info:
        return {"status": "skipped", "message": info["error"]}

    spot_name = info.get("spot_name", "")
    original_fact = info.get("original_fact", "")
    corrected_fact = info.get("corrected_fact", "")

    if not spot_name or not corrected_fact:
        return {"status": "skipped", "message": "纠正信息不完整"}

    # 2. 查找对应的知识文件
    file_path = _find_spot_file(spot_name)
    if not file_path:
        return {"status": "no_file", "message": f"未找到「{spot_name}」的知识文件"}

    # 3. 读取当前文档内容
    current_content = file_path.read_text(encoding="utf-8")

    # 4. 用 LLM 修改文档中的错误
    apply_prompt = CORRECTION_APPLY_PROMPT.format(
        spot_name=spot_name,
        original_fact=original_fact,
        corrected_fact=corrected_fact,
        document_content=current_content,
    )
    updated_content = await call_llm(
        messages=[{"role": "user", "content": f"请根据纠正信息修改文档"}],
        system_prompt=apply_prompt,
        temperature=0.1,
        max_tokens=2000,
    )

    if not updated_content or len(updated_content.strip()) < 50:
        return {"status": "apply_failed", "message": "LLM 修改结果异常"}

    # 5. 保存修改后的文件
    file_path.write_text(updated_content, encoding="utf-8")
    logger.info("知识文件已更新：%s", file_path)

    # 6. 重新向量化
    chunk_count = _vectorize_single(spot_name, updated_content)

    return {
        "status": "ok",
        "spot_name": spot_name,
        "original_fact": original_fact,
        "corrected_fact": corrected_fact,
        "chunk_count": chunk_count,
    }
