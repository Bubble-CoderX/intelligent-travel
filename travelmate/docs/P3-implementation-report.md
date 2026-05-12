# P3 实施报告：行程风格对比 + 知识库自动调研

> 项目：AI智游伴 TravelMate
> 阶段：P3（长期优化项）
> 实施日期：2026-05-12
> 前置依赖：P0（TripCard重设计 + KNOWLEDGE兜底 + 会话管理 + 偏好面板）、P1（错误恢复 + 消息菜单 + 导出）、P2（天气 + 问候 + 美化 + 预算 + 清单）已全部完成

---

## 一、功能概述

P3 包含两个锦上添花的优化功能：

| 编号 | 功能 | 优先级 | 改动规模 |
|------|------|--------|----------|
| P3-⑭ | 行程风格对比 | P3 | 后端 5 文件 + 前端 5 文件（含 1 新建） |
| P3-⑬ | 知识库自动调研 | P3 | 后端 5 文件（含 2 新建） + 前端 1 文件 |

---

## 二、P3-⑭ 行程风格对比

### 2.1 设计思路

给行程生成功能增加「风格」维度，同一目的地可选择不同旅行风格生成不同行程。TripCard 上提供"换种风格"按钮，一键切换重新生成。

**三种风格定义**：

| 风格 | 代码 | 标识 | 每日景点数 | 特点 |
|------|------|------|-----------|------|
| 紧凑打卡型 | `compact` | ⚡ | 5-7 个 | 早出晚归，高效打卡，适合时间有限的旅行者 |
| 休闲度假型 | `leisure` | 🌴 | 2-3 个 | 慢节奏享受，留足休息时间，适合放松心情 |
| 深度文化型 | `culture` | 📚 | 3-5 个 | 侧重博物馆、历史遗迹、民俗体验 |

### 2.2 数据流

```
用户输入"帮我规划杭州3天旅行"
  ↓
ChatInput.vue 检测旅行关键词（规划/行程/旅游/旅行/出游/几天/游玩/度假/攻略/出行）
  ↓
显示 StyleSelector（3个风格 chip 按钮）
  ↓
用户点击「🌴 休闲度假」
  ↓
ChatInput emit('send', text, 'leisure')
  ↓
ChatContainer.handleSend(text, 'leisure')
  ↓
chatStore.sendMessage(text, true, undefined, 'leisure')
  ↓
POST /chat { message: "帮我规划杭州3天旅行", trip_style: "leisure" }
  ↓
chat.py → route_intent(..., trip_style="leisure")
  ↓
intent_router → generate_trip_plan(..., style="leisure")
  ↓
STYLE_INSTRUCTIONS["leisure"] 注入 TRIP_PLAN_PROMPT
  ↓
LLM 生成休闲风格行程（每天 2-3 景点）
  ↓
TripCard 显示 "🌴 休闲度假型" 标签 + "🔄 换种风格" 按钮
  ↓
点击"换种风格" → ChatContainer 显示 StyleSelector → 选择新风格 → 重新发送原消息
```

### 2.3 后端改动详情

#### 文件 1：`backend/app/models/schemas.py`

**改动类型**：字段新增

ChatRequest 模型新增 `trip_style` 字段：

```python
class ChatRequest(BaseModel):
    """对话请求。"""
    message: str = Field(..., description="用户输入的消息")
    device_id: str = Field(..., description="设备唯一标识")
    session_id: str | None = Field(default=None, description="会话 ID")
    trip_style: str | None = Field(default=None, description="行程风格：compact/leisure/culture")  # 新增
```

#### 文件 2：`backend/app/utils/trip_prompts.py`

**改动类型**：新增常量 + 修改 Prompt 模板

新增 `STYLE_INSTRUCTIONS` 字典，定义三种风格的 Prompt 注入指令：

```python
STYLE_INSTRUCTIONS = {
    "compact": "⚡ **紧凑打卡型**：每天安排 5-7 个景点，早出晚归...",
    "leisure": "🌴 **休闲度假型**：每天安排 2-3 个景点，慢节奏享受旅程...",
    "culture": "📚 **深度文化型**：侧重博物馆、历史遗迹、民俗体验...",
    "default": "",
}
```

在 `TRIP_PLAN_PROMPT` 中新增 `{style_instructions}` 占位符，位于目的地信息之后：

```python
TRIP_PLAN_PROMPT = """你是一位经验丰富的旅行规划师「AI智游伴」。请根据以下信息为用户生成一份详细的结构化旅行行程。

{style_instructions}     # ← 新增占位符

## 目的地信息
...
```

将原来的硬编码 `每天安排 3-5 个景点` 改为由风格指令控制：

```python
## 要求
1. 严格按照上方「行程风格」的指引安排每天的景点数量和节奏  # ← 原为"每天安排 3-5 个景点"
```

#### 文件 3：`backend/app/services/trip_service.py`

**改动类型**：函数签名扩展 + Prompt 格式化修改

```python
# 新增导入
from app.utils.trip_prompts import TRIP_PLAN_PROMPT, STYLE_INSTRUCTIONS

# 函数签名增加 style 参数
async def generate_trip_plan(
    device_id: str, destination: str, days: int, style: str = "default"
) -> dict[str, Any]:

    # ... 收集数据 ...

    style_instructions = STYLE_INSTRUCTIONS.get(style, "")  # 新增

    prompt = TRIP_PLAN_PROMPT.format(
        destination=destination,
        days=days,
        poi_text=poi_text,
        weather_text=weather_text,
        preferences_text=preferences_text,
        style_instructions=style_instructions,  # 新增
    )
```

#### 文件 4：`backend/app/services/intent_router.py`

**改动类型**：函数签名扩展 + 参数透传

```python
async def route_intent(user_message: str, device_id: str, session_id: str | None = None,
                       trip_style: str | None = None) -> dict:  # 新增 trip_style 参数

    # 在 TRIP_PLAN 分支中传递 style 参数
    result = await generate_trip_plan(device_id, destination, int(trip_days),
                                       style=trip_style or "default")
```

#### 文件 5：`backend/app/api/chat.py`

**改动类型**：请求参数透传 + metadata 增强

```python
# 传递 trip_style 到 route_intent
result = await route_intent(req.message, req.device_id, session_id=session_id,
                            trip_style=req.trip_style)

# metadata 中加入 trip_style
if intent == "TRIP_PLAN":
    # ... 现有逻辑 ...
    metadata["trip_style"] = req.trip_style or "default"
```

### 2.4 前端改动详情

#### 文件 6（新建）：`frontend/src/components/chat/StyleSelector.vue`

**组件职责**：渲染 3 个风格选择 chip 按钮。

```vue
<script setup lang="ts">
const emit = defineEmits<{ select: [style: string] }>()

const styles = [
  { key: 'compact',  emoji: '⚡', label: '紧凑打卡',  desc: '每天5-7景点' },
  { key: 'leisure',  emoji: '🌴', label: '休闲度假',  desc: '每天2-3景点' },
  { key: 'culture',  emoji: '📚', label: '深度文化',  desc: '历史博物馆' },
]
</script>

<template>
  <div class="flex items-center gap-1.5 px-1 py-1">
    <span class="text-[11px] text-stone-400 shrink-0">风格：</span>
    <button v-for="s in styles" :key="s.key"
      class="inline-flex items-center gap-1 rounded-full border ..."
      @click="emit('select', s.key)">
      <span>{{ s.emoji }}</span>
      <span>{{ s.label }}</span>
      <span class="hidden text-[10px] sm:inline">· {{ s.desc }}</span>
    </button>
  </div>
</template>
```

#### 文件 7：`frontend/src/components/chat/ChatInput.vue`

**改动类型**：逻辑新增 + 模板结构调整

1. 导入 StyleSelector 组件
2. 新增旅行关键词正则检测：`/规划|行程|旅游|旅行|出游|几天|游玩|度假|攻略|出行/`
3. `showStyleSelector` 计算属性：输入框内容匹配旅行关键词时显示
4. 新增 `handleStyleSelect(style)` 函数：选择风格后直接发送消息
5. `emit` 扩展：`send: [content: string, tripStyle?: string]`
6. 模板：在输入框上方条件渲染 `<StyleSelector>`

#### 文件 8：`frontend/src/stores/chat.ts`

**改动类型**：函数签名扩展 + payload 构建

```typescript
async function sendMessage(content: string, appendUserMsg = true,
                          existingUserMsgId?: string, tripStyle?: string) {
    // ... 现有逻辑 ...

    const payload: Record<string, any> = {
      message: content,
      device_id: getDeviceId(),
      session_id: sessionId.value,
    }
    if (tripStyle) payload.trip_style = tripStyle

    const res = await api.post('/chat', payload)
```

#### 文件 9：`frontend/src/components/chat/ChatContainer.vue`

**改动类型**：逻辑新增 + 模板新增

1. `switchingStyleMsg` ref：跟踪正在切换风格的消息（用于"换种风格"流程）
2. `handleSwitchStyle(msg)`：找到对应 user 消息，设置 switchingStyleMsg
3. `handleStyleSwitchSelect(style)`：选择新风格后重新发送原消息
4. TripCard 组件绑定新增 `:trip-style` 和 `@switch-style`
5. 模板新增风格切换面板（`switchingStyleMsg` 非 null 时显示）

#### 文件 10：`frontend/src/components/chat/TripCard.vue`

**改动类型**：Props 扩展 + 模板新增

1. 新增 `tripStyle` prop 和 `switchStyle` emit
2. `STYLE_LABELS` 字典：风格代码到 emoji+标签的映射
3. `currentStyleLabel` 计算属性：根据 tripStyle 返回标签
4. 模板 Header 区域：
   - 显示当前风格标签（如 `🌴 休闲度假型`）
   - "🔄 换种风格" 按钮，点击 emit `switchStyle`

---

## 三、P3-⑬ 知识库自动调研

### 3.1 设计思路

当 RAG 检索为空时（用户问了知识库中没有的景点），自动触发以下管线：

```
DuckDuckGo 搜索 → LLM 策展为结构化 Markdown → 保存到 knowledge/ 目录 → 向量化入库 ChromaDB → 用新知识回答
```

**核心原则**：用户无感知，回答时自动附带"🔍 已自动调研"标签。

### 3.2 数据流

```
用户问"平遥古城有什么历史？"
  ↓
KNOWLEDGE 意图 → query_knowledge("平遥古城有什么历史？")
  ↓
ChromaDB 检索为空（本地无"平遥古城"知识）
  ↓
_extract_spot_name("平遥古城有什么历史？") → "平遥古城"
  ↓
has_local_knowledge("平遥古城") → false
  ↓
auto_expand("平遥古城"):
  ├─ DuckDuckGo 搜索 "平遥古城 旅游攻略 景点介绍"
  │   → 返回 8 条搜索结果
  ├─ LLM 策展（CURATION_PROMPT）→ 结构化 Markdown
  ├─ 保存到 data/knowledge/平遥古城.md
  └─ 向量化入库 ChromaDB（_knowledge_collection.upsert）
  ↓
重新检索 → 找到"平遥古城"知识段落
  ↓
LLM 生成导游式回答
  ↓
返回 "🔍 已为你自动调研了「平遥古城」\n\n{回答}"
  ↓
前端 MessageBubble 检测到 "🔍 已为你自动调研了" 前缀
  ↓
显示绿色 "🔍 已自动调研" 标签
```

### 3.3 后端改动详情

#### 文件 11：`backend/requirements.txt`

**改动类型**：依赖新增

```
duckduckgo-search>=6.0.0
```

安装命令：`pip install duckduckgo-search>=6.0.0`
安装后额外依赖：`primp>=0.15.0`、`lxml>=5.3.0`

#### 文件 12（新建）：`backend/app/services/knowledge_expander.py`

**核心模块**：自动调研管线的完整实现。

| 函数 | 职责 | 依赖 |
|------|------|------|
| `has_local_knowledge(spot_name)` | 检查景点是否已有本地知识文件 | pathlib |
| `_search_web(query, max_results)` | DuckDuckGo 搜索 | duckduckgo_search |
| `_curate_knowledge(spot_name, search_results)` | LLM 策展为结构化 Markdown | call_llm |
| `_save_knowledge_file(spot_name, content)` | 保存为 .md 文件 | pathlib |
| `_vectorize_single(spot_name, content)` | 单文件向量化入库 | chromadb |
| `auto_expand(spot_name)` | 完整管线：搜索→策展→保存→向量化 | 以上所有 |

**LLM 策展 Prompt（CURATION_PROMPT）要点**：
- 标题用景点名称
- 分为：简介、历史文化、主要看点、游玩建议、实用信息（门票/交通/开放时间）
- 语言生动有趣，像导游在向朋友介绍
- 800-1500 字
- 去掉广告和无关信息

**ChromaDB 复用策略**：
```python
# 复用 rag_service 的 ChromaDB 连接
_knowledge_client = chromadb.PersistentClient(
    path=str(Path(__file__).resolve().parent.parent.parent / "db" / "chroma_knowledge")
)
_knowledge_collection = _knowledge_client.get_or_create_collection(
    name="spot_knowledge",
    metadata={"hnsw:space": "cosine"},
)
```

分块策略与 `rag_service.load_knowledge_base()` 一致：按 `\n\n` 分割。

#### 文件 13：`backend/app/services/rag_service.py`

**改动类型**：query_knowledge() 新增自动调研分支

在「兜底 1：检索为空」分支中，新增自动调研逻辑：

```python
if not retrieved:
    spot_keyword = spot_name or _extract_spot_name(question)
    if spot_keyword:
        from app.services.knowledge_expander import auto_expand, has_local_knowledge
        if not has_local_knowledge(spot_keyword):
            try:
                expand_result = await auto_expand(spot_keyword)
                if expand_result.get("status") == "ok":
                    retrieved = retrieve_knowledge(question, spot_keyword, top_k=5)
                    if retrieved:
                        # ... 生成回答 ...
                        return f"🔍 已为你自动调研了「{spot_keyword}」\n\n{answer}"
            except Exception as exc:
                logger.warning("自动调研失败：%s", exc)
```

新增辅助函数 `_extract_spot_name(question)`：
- 使用正则提取中文字符片段（2 字以上）
- 去掉常见动词/介词
- 返回最长匹配

#### 文件 14（新建）：`backend/app/api/knowledge.py`

**新增 API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/knowledge/auto-expand` | 手动触发景点自动调研 |
| GET | `/knowledge/has-local` | 检查景点是否有本地知识 |

```python
@router.post("/auto-expand")
async def api_auto_expand(req: AutoExpandRequest):
    """手动触发景点知识自动调研。"""
    result = await auto_expand(req.spot_name)
    if result.get("status") == "no_results":
        raise HTTPException(status_code=404, detail=result["message"])
    return result
```

#### 文件 15：`backend/app/main.py`

**改动类型**：路由注册

```python
from app.api.knowledge import router as knowledge_router
# ...
app.include_router(knowledge_router)
```

### 3.4 前端改动详情

#### 文件 16：`frontend/src/components/chat/MessageBubble.vue`

**改动类型**：computed 新增 + 模板新增

1. 新增 computed `isAutoResearched`：
```typescript
const isAutoResearched = computed(() =>
  props.message.role === 'assistant' && /^🔍\s*已为你自动调研了/.test(props.message.content)
)
```

2. 在 assistant 消息模板中，内容之前插入绿色标签：
```vue
<div v-if="isAutoResearched"
  class="mb-2 inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-600">
  🔍 已自动调研
</div>
```

---

## 四、修改文件清单汇总

### 4.1 新建文件（3 个）

| 文件 | 说明 |
|------|------|
| `frontend/src/components/chat/StyleSelector.vue` | 行程风格选择器组件 |
| `backend/app/services/knowledge_expander.py` | 知识库自动调研核心模块 |
| `backend/app/api/knowledge.py` | 知识库管理 API |

### 4.2 修改文件（13 个）

| # | 文件 | 改动概述 |
|---|------|----------|
| 1 | `backend/app/models/schemas.py` | ChatRequest 新增 `trip_style` 字段 |
| 2 | `backend/app/utils/trip_prompts.py` | 新增 `STYLE_INSTRUCTIONS` + prompt 占位符 |
| 3 | `backend/app/services/trip_service.py` | `generate_trip_plan()` 新增 `style` 参数 |
| 4 | `backend/app/services/intent_router.py` | `route_intent()` 透传 `trip_style` |
| 5 | `backend/app/api/chat.py` | 传递 `trip_style` + metadata 增强 |
| 6 | `backend/requirements.txt` | 新增 `duckduckgo-search>=6.0.0` |
| 7 | `backend/app/services/rag_service.py` | 检索为空时触发 auto_expand |
| 8 | `backend/app/main.py` | 注册 knowledge_router |
| 9 | `frontend/src/components/chat/ChatInput.vue` | 旅行关键词检测 + StyleSelector |
| 10 | `frontend/src/stores/chat.ts` | `sendMessage()` 新增 `tripStyle` 参数 |
| 11 | `frontend/src/components/chat/ChatContainer.vue` | 风格切换逻辑 + StyleSelector 面板 |
| 12 | `frontend/src/components/chat/TripCard.vue` | 风格标签 + "换种风格"按钮 |
| 13 | `frontend/src/components/chat/MessageBubble.vue` | "已自动调研"绿色标签 |

---

## 五、关键设计决策

### 5.1 风格选择时机

**选择**：输入时选择（ChatInput 检测关键词后展示），而非生成后选择。

**原因**：风格影响 Prompt 注入，在 LLM 调用前确定比调用后重新生成更高效（减少 LLM 调用次数）。

### 5.2 自动调研触发条件

**选择**：仅在 RAG 检索为空时触发，而非每次都搜索。

**原因**：
- 减少不必要的网络请求和 LLM 调用（节省时间和 token）
- 已有本地知识的景点直接使用更高质量的本地内容
- DuckDuckGo 搜索质量不如人工编写的攻略文档

### 5.3 景点名称提取

**选择**：简单的正则启发式，而非 LLM 提取。

**原因**：
- 触发自动调研时已处于 RAG 调用中，额外调用 LLM 提取名称会增加延迟
- 正则方案对中文景点名（2+ 连续中文字符）的准确率已够用
- 如果提取错误，`auto_expand` 搜索不到结果会优雅降级为 LLM 通用知识

### 5.4 ChromaDB 连接复用

**选择**：`knowledge_expander.py` 独立创建 PersistentClient 连接，指向同一路径。

**原因**：
- ChromaDB PersistentClient 支持多连接指向同一目录（文件级锁）
- 避免 circular import（knowledge_expander 不依赖 rag_service 的全局变量）
- 简化测试：每个模块可独立测试

---

## 六、验证方法

### 6.1 行程风格对比

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 输入"帮我规划杭州3天旅行" | 输入框上方显示 3 个风格 chip：⚡紧凑打卡、🌴休闲度假、📚深度文化 |
| 2 | 点击「🌴 休闲度假」 | 消息发送，TripCard 头部显示 `🌴 休闲度假型` 标签 + `🔄 换种风格` 按钮 |
| 3 | 检查行程内容 | 每天 2-3 个景点（休闲风格特征） |
| 4 | 点击「🔄 换种风格」 | 输入框上方出现风格选择器（带"取消"按钮） |
| 5 | 选择「⚡ 紧凑打卡」 | 新 TripCard 生成，每天 5-7 个景点 |
| 6 | 输入"今天天气怎么样" | 不显示风格选择器（无旅行关键词） |

### 6.2 知识库自动调研

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 输入"西湖有什么特色" | 正常回答（本地知识库有西湖数据） |
| 2 | 输入"平遥古城的历史是什么" | 等待 10-30 秒，回复显示绿色标签 `🔍 已自动调研` |
| 3 | 检查文件 | `data/knowledge/平遥古城.md` 已创建 |
| 4 | 再次输入"平遥古城有什么好玩的" | 直接使用缓存知识回答（更快） |
| 5 | 手动触发 | POST `/knowledge/auto-expand` body: `{"spot_name": "张家界"}` |

### 6.3 异常场景

| 场景 | 预期行为 |
|------|----------|
| DuckDuckGo 搜索无结果 | 降级为 LLM 通用知识回答 |
| DuckDuckGo 网络超时 | try/except 静默捕获，降级为 LLM 通用知识 |
| LLM 策展失败 | 降级为 LLM 通用知识 |
| 用户不选风格直接发送 | 使用 `default` 风格（无额外指令） |

---

## 七、依赖安装

```bash
# 在 backend/venv 虚拟环境中执行
pip install duckduckgo-search>=6.0.0

# 安装后验证
python -c "from duckduckgo_search import DDGS; print('OK')"
```

安装成功的额外依赖：
- `duckduckgo-search==8.1.1`
- `primp==1.2.3`（HTTP 客户端）
- `lxml==6.1.0`（XML 解析）

---

## 八、已知限制与后续优化

| 项目 | 限制 | 后续优化方向 |
|------|------|-------------|
| 景点名称提取 | 简单正则，对复杂句子可能不准确 | 可引入 LLM 提取或 NER 模型 |
| 策展质量 | 依赖搜索结果质量，部分冷门景点搜索结果少 | 多搜索引擎轮询、增加搜索维度 |
| 缓存一致性 | 手动编辑 knowledge/*.md 后 ChromaDB 不会自动更新 | 添加文件监听或定期重载机制 |
| 搜索限流 | DuckDuckGo 有频率限制 | 加入搜索结果缓存（Redis/TTL） |
| 风格样式 | 只有 3 种预设 | 可扩展为用户自定义风格组合 |

---

## 九、Git 提交说明

**Commit Message（建议）**：

```
feat(P3): 行程风格对比 + 知识库自动调研

P3-⑭ 行程风格对比:
- schemas.py: ChatRequest 新增 trip_style 字段
- trip_prompts.py: 新增 STYLE_INSTRUCTIONS 字典（compact/leisure/culture）
- trip_service.py: generate_trip_plan() 支持 style 参数
- intent_router.py: 透传 trip_style 到行程生成
- chat.py: 传递 trip_style + metadata 增强
- StyleSelector.vue: 新建风格选择器组件
- ChatInput.vue: 旅行关键词检测 + 风格选择器展示
- chat.ts: sendMessage() 支持 tripStyle 参数
- ChatContainer.vue: 风格切换逻辑（switchStyle 事件链）
- TripCard.vue: 风格标签 + "换种风格"按钮

P3-⑬ 知识库自动调研:
- requirements.txt: 新增 duckduckgo-search
- knowledge_expander.py: 新建自动调研管线（搜索→策展→入库）
- rag_service.py: 检索为空时自动触发调研 + 景点名提取
- knowledge.py: 新建 API 端点（/auto-expand, /has-local）
- main.py: 注册 knowledge_router
- MessageBubble.vue: "已自动调研"绿色标签
```
