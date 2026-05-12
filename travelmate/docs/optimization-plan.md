# AI智游伴 优化方案

> 基于对项目全部代码的审查（14个后端服务/工具文件、15个前端源文件），结合用户提供的参考界面，制定以下优化方案。
> 
> 当前项目状态：12个阶段全部完成 + 对话上下文与智能摘要压缩已实现。

---

## 目录

- [优化总览与优先级](#优化总览与优先级)
- [一、TripCard 行程卡片重设计（核心）](#一tripcard-行程卡片重设计核心)
- [二、会话管理系统](#二会话管理系统)
- [三、偏好管理面板](#三偏好管理面板)
- [四、行程导出（PDF/图片）](#四行程导出pdf图片)
- [五、错误恢复与重试机制](#五错误恢复与重试机制)
- [六、聊天消息操作菜单](#六聊天消息操作菜单)
- [七、预算估算器](#七预算估算器)
- [八、旅行准备清单自动生成](#八旅行准备清单自动生成)
- [九、聊天界面整体美化](#九聊天界面整体美化)
- [十、知识库扩充与 KNOWLEDGE 兜底逻辑](#十知识库扩充与-knowledge-兜底逻辑)
- [十一、行程风格对比](#十一行程风格对比)
- [十二、首页天气显示](#十二首页天气显示)
- [十三、会话启动主动问候](#十三会话启动主动问候)
- [附录A：数据结构对照](#附录a数据结构对照)

---

## 优化总览与优先级

| 优先级 | 模块 | 改造范围 | 预估工作量 |
|--------|------|----------|-----------|
| P0 | TripCard 重设计 | 后端 Prompt + trip_service + chat.py + 前端 TripCard 组件 | 中 |
| P0 | KNOWLEDGE 兜底逻辑 | rag_service.py 双层兜底（检索为空 + 相关性初筛） | 小 |
| P0 | 会话管理 | 后端 sessions API + 前端侧边栏 | 中 |
| P0 | 偏好管理面板 | 后端已有 API + 前端设置页 | 小 |
| P1 | 行程导出 | 后端已有 export_service + 前端按钮 | 小 |
| P1 | 错误恢复与重试 | 前端 store + MessageBubble | 小 |
| P1 | 消息操作菜单 | 前端 MessageBubble 长按/右键菜单 | 小 |
| P2 | 预算估算器 | 后端 trip_service Prompt 增强 | 小 |
| P2 | 旅行准备清单 | 后端新增 checklist 服务 + 前端展示 | 中 |
| P2 | 会话启动主动问候 | 后端 greet 端点 + 前端空会话检测 + LLM 生成个性化开场白 | 小 |
| P2 | 聊天界面整体美化 | 布局重构 + 暖色调配色 + 欢迎页 + 消息气泡打磨 + 暗色模式 | 中 |
| P2 | 首页天气显示 | 后端 IP 定位 + 天气接口 + 前端 header 天气组件 | 小 |
| P3 | 知识库内容扩充 | 后端 POST /knowledge/import + 新增 15+ .md 文档 | 中 |
| P3 | 行程风格对比 | 后端 Prompt 多风格生成 + 前端选择器 | 中 |

### 实施顺序（按依赖关系排列）

> 文档按模块编号，但实际实施需考虑依赖。以下为推荐执行顺序：

```
P0 ─ 先做，核心价值 + 修 Bug ─────────────────────

  ① 十  KNOWLEDGE 兜底      最快见效，只改 rag_service.py，5 分钟
        ↓ 无依赖，独立可做
  ② 一  TripCard 重设计      最大块，后端 Prompt + 前端组件，无外部依赖
        ↓ 无依赖，独立可做
  ③ 三  偏好管理面板         纯前端，后端 API 已就绪
        ↓ 无依赖，独立可做
  ④ 二  会话管理             为后续 UI 打基础（侧边栏骨架），前端为主
        ↓ 无依赖，独立可做，但建议在 TripCard 之后（避免分心）

P1 ─ 接着补体验短板 ─────────────────────────────

  ⑤ 五  错误恢复             store + MessageBubble 小改，独立
  ⑥ 六  消息操作菜单         MessageBubble 长按/右键，独立
  ⑦ 四  行程导出             后端 export_service 已有，加前端按钮 + API

P2 ─ 锦上添花，有先后依赖 ───────────────────────

  ⑧ 十二 首页天气            必须先做，因为 ↓
        ↓ ⑨ 依赖 ⑧ 的天气数据（三层定位 + 天气查询）
  ⑨ 十三 会话启动问候        依赖 ⑧；问候语里要嵌入天气
        ↓ ⑩ 依赖 ④ 的侧边栏布局 + ⑧ 的天气组件
  ⑩ 九   整体美化            放 P2 最后；等侧边栏和天气就位再统一调整
  ⑪ 七   预算估算器          无依赖，Prompt 微调
  ⑫ 八   旅行准备清单        无依赖，独立服务

P3 ─ 长期优化 ───────────────────────────────────

  ⑬ 十.6 知识库自动调研      DuckDuckGo → LLM → 自动入库
  ⑭ 十一 行程风格对比        后端 style 参数 + 前端选择器
```

**关键依赖链**：⑧ 首页天气 → ⑨ 会话问候 → ⑩ 整体美化（三者必须按此顺序）

**跟文档编号不一致的地方**：
- KNOWLEDGE 兜底放 P0 第一（最快正反馈）
- P1 里先⑤⑥再⑦（⑤⑥改动小无风险，⑦涉及后端）
- P2 里⑧→⑨→⑩的顺序比编号重要
- 预算估算器和旅行准备清单在 P2 中排后（依赖 P0 的 TripCard 改造着陆）

---

## 一、TripCard 行程卡片重设计（核心）

### 1.1 现状问题

**后端层**：`trip_prompts.py` 要求 LLM 输出 Markdown 格式；`trip_service.py` 将 Markdown 文本直接作为 `itinerary` 返回，存入 SQLite 的 `plan_json` 字段。

**前端层**：`TripCard.vue` 只接收 `summary`（Markdown 字符串）用 `markdown-it` 渲染为 HTML，没有任何结构化交互。

**矛盾点**：`schemas.py` 已定义了完整的数据模型（`Itinerary`、`DayPlan`、`SpotItem`、`MealItem`、`TransportItem`、`HotelItem`、`BudgetBreakdown`），共约 10 个 Pydantic 模型，字段覆盖时间、地点、经纬度、交通方式、餐饮、住宿、预算——但这些模型完全没有被使用。

### 1.2 改造目标

将参考界面（用户提供的图片）的设计语言还原为 TravelMate 的 TripCard 组件：

| 界面元素 | 图片来源 | 实现方式 |
|----------|----------|----------|
| 标题 + 天数标签 | 顶部 "杭州 三日游攻略" | TripCard Header |
| 标签页导航 | "行程总览 / Day1 / Day2" | Vue tab 组件 |
| 活动卡片 | 时间段 + 景点名 + 描述 + 位置 + 贴士 | 循环渲染 DayPlan.spots |
| 高亮提示框 | 黄色背景实用建议 | 渲染 SpotItem.description 中的 tips 字段 |
| 交通建议 | "打车约15分钟，费用约20元" | TransportItem 行内渲染 |
| 餐饮推荐 | "午餐推荐" 区块 | MealItem 卡片 |
| 底部导航 | "交通 / 美食 / 住宿" | 底部三标签汇总视图 |
| 景点图片 | 网格图片 | 高德 POI 照片或占位图 |

### 1.3 数据流改造

**改造前**：
```
User → intent_router → generate_trip_plan()
  → Prompt(Markdown) → LLM → Markdown 字符串
  → chat.py → reply=Mardown → TripCard 渲染 HTML
```

**改造后**：
```
User → intent_router → generate_trip_plan()
  → Prompt(JSON, 匹配 Itinerary Schema) → LLM → JSON 字符串
  → parse + Pydantic 校验 → Itinerary 对象
  → 存入 SQLite (plan_json = JSON 原文)
  → chat.py
    ├── reply = itinerary.summary (简短概述文本)
    └── metadata.trip_plan = itinerary.model_dump() (完整结构化数据)
  → TripCard 根据 trip_plan 渲染多标签结构化卡片
```

### 1.4 后端改造详情

#### 1.4.1 重写 `trip_prompts.py` 中的 TRIP_PLAN_PROMPT

将 Markdown 输出要求替换为结构化 JSON，格式对齐已有的 `Itinerary` 模型：

```python
TRIP_PLAN_PROMPT = """你是一位经验丰富的旅行规划师。请根据以下信息生成一份详细的旅行行程。

## 输出格式（严格 JSON，不要输出 Markdown）

{
  "summary": "行程总体概述，一句话",
  "days": [
    {
      "day_index": 1,
      "theme": "当日主题",
      "spots": [
        {
          "name": "景点名称",
          "start_time": "09:00",
          "end_time": "11:00",
          "description": "游玩说明",
          "location": "位置描述",
          "address": "详细地址",
          "tips": "实用小贴士"
        }
      ],
      "meals": [
        {
          "meal_type": "午餐",
          "name": "推荐餐厅",
          "notes": "特色菜、人均消费",
          "estimated_cost": 50
        }
      ],
      "transport": [
        {
          "mode": "打车",
          "from_place": "西湖",
          "to_place": "灵隐寺",
          "duration": "约15分钟",
          "estimated_cost": 20
        }
      ],
      "hotel": {
        "name": "推荐住宿",
        "level": "舒适型",
        "location": "西湖附近",
        "estimated_cost": 350
      }
    }
  ],
  "estimated_budget": 0,
  "budget_breakdown": {
    "transport": 0, "hotel": 0, "meals": 0, "tickets": 0, "other": 0, "total": 0
  },
  "tips": ["旅行建议1", "旅行建议2"],
  "food_summary": "全程美食概览",
  "transport_summary": "全程交通概览",
  "accommodation_summary": "住宿总览"
}

## 要求
- 每天安排 3-5 个景点，节奏合理
- 景点优先使用提供的 POI 数据中的真实地点
- 每两个景点间给出交通建议（步行/打车/公交）
- 根据天气给出穿衣、带伞建议
- 根据用户饮食偏好调整餐饮推荐
- 每个景点给出实用小贴士
- 直接输出 JSON，不要包裹在 ```json``` 代码块中
"""
```

#### 1.4.2 改造 `trip_service.py`

`generate_trip_plan()` 函数需改为：
1. 调用 LLM 获取 JSON 字符串
2. 尝试 `json.loads()` 解析
3. 若解析失败，用正则提取 JSON 片段重试（LLM 偶尔会多输出前后文字）
4. 用 `Itinerary(**parsed)` 做 Pydantic 校验（自动补全缺失字段的默认值）
5. 存入 SQLite 时保存 JSON 原文
6. 返回值新增 `summary`、`itinerary_json` 字段

```python
async def generate_trip_plan(device_id, destination, days) -> dict:
    # ... 收集 POI/天气/偏好数据 ...
    
    raw = await call_llm(...)  # LLM 返回 JSON 字符串
    
    # 解析 JSON（含容错处理）
    try:
        plan_dict = json.loads(raw)
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON 片段
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            plan_dict = json.loads(match.group())
        else:
            raise ValueError("LLM 返回无法解析")
    
    # Pydantic 校验（自动补全缺失字段默认值）
    itinerary = Itinerary(
        trip_id=f"trip_{uuid4().hex[:8]}",
        destination=destination,
        **plan_dict
    )
    
    # 存储
    _save_trip_to_db(device_id, destination, days, 
                     json.dumps(itinerary.model_dump(), ensure_ascii=False))
    
    return {
        "trip_id": itinerary.trip_id,
        "destination": destination,
        "days": days,
        "summary": itinerary.summary,           # 短概述 → 作为 reply
        "itinerary_json": itinerary.model_dump(), # 完整结构 → 进 metadata
    }
```

#### 1.4.3 改造 `chat.py` 中 TRIP_PLAN 分支

当前代码：
```python
if intent == "TRIP_PLAN":
    result = await generate_trip_plan(...)
    reply = result["itinerary"]  # 整段 Markdown
    metadata = {"destination": ..., "days": ...}
```

改为：
```python
if intent == "TRIP_PLAN":
    result = await generate_trip_plan(...)
    reply = result["summary"]                    # 概述文本
    metadata = {
        "trip_plan": result["itinerary_json"],   # 完整结构化数据
        "destination": result["destination"],
        "days": result["days"],
    }
```

### 1.5 前端 TripCard 重设计

#### 1.5.1 组件结构

```
TripCard.vue
├── Header
│   ├── 目的地名称 + "N日游" 
│   └── 天数标签
│
├── TabBar (标签页导航)
│   ├── 行程总览
│   ├── Day 1
│   ├── Day 2
│   ├── Day 3
│   └── ... (动态数量)
│
├── TabContent
│   ├── [行程总览] Tab
│   │   ├── summary 概述文本
│   │   ├── budget_breakdown 预算饼图或数值列表
│   │   └── tips 列表
│   │
│   └── [Day N] Tab
│       ├── 主题标题
│       ├── 活动卡片列表 (v-for spots)
│       │   ├── 时间范围标签 (start_time - end_time)
│       │   ├── 景点名称
│       │   ├── 描述文本
│       │   ├── 位置信息 (图标 + address)
│       │   ├── 贴士高亮框 (tips, 黄色/灰色背景)
│       │   └── 交通信息 (如果非首项: mode + duration + cost)
│       ├── 餐饮区块
│       │   └── 午餐/晚餐推荐卡片
│       └── 住宿建议 (如果有)
│
└── BottomNav (底部固定导航)
    ├── 🚗 交通 (transport_summary + 各天 transport 汇总)
    ├── 🍜 美食 (food_summary + 各天 meals 汇总)
    └── 🏨 住宿 (accommodation_summary + 各天 hotel 汇总)
```

#### 1.5.2 Props 接口设计

```typescript
interface TripCardProps {
  tripPlan: Itinerary     // 来自后端 metadata.trip_plan
  safetyWarning?: string  // 安全提醒横幅
}
```

#### 1.5.3 各子视图的渲染逻辑

**行程总览 Tab**：
- 大段 summary 文本
- 预算拆分为 交通/住宿/餐饮/门票/其他 五项，横向柱状图或列表
- tips 以编号列表展示

**Day N Tab**：
- 顶部主题横幅（如 "Day 1：西湖经典一日"）
- Vertical timeline 排列 spots：
  - 每个 spot 是一个卡片，左侧时间轴圆点
  - 卡片顶部：时间范围（如 `09:00 — 11:00`）+ 景点名
  - 卡片中部：描述文字
  - 卡片底部左侧：📍 位置名 + 地址
  - 贴士以黄色背景 `rounded-lg` 框展示
  - 景点间交通以虚线连接 + 小图标（🚶/🚕/🚌）+ 耗时
- 餐饮推荐以独立小卡片插入在合适的时间位置

**底部交通/美食/住宿弹层**：
- 点击底部三标签后，从底部滑出一个面板
- 交通面板：全天各段交通汇总表
- 美食面板：所有餐饮推荐列表
- 住宿面板：住宿建议 + 位置描述

### 1.6 兼容性处理

**LLM JSON 输出不稳定的应对策略**：

1. **Primary**: 直接 `json.loads()` 
2. **Fallback 1**: 正则提取 `{...}` 片段后重试
3. **Fallback 2**: 若完全无法解析，将原始文本渲染降级为旧版 Markdown TripCard

后端在 `trip_service.py` 中实现此容错逻辑，前端无需感知。

### 1.7 改造涉及文件清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/app/utils/trip_prompts.py` | 重写 | TRIP_PLAN_PROMPT 从 Markdown 改为 JSON |
| `backend/app/services/trip_service.py` | 改造 | 增加 JSON 解析 + Pydantic 校验 + 容错 |
| `backend/app/api/chat.py` | 小改 | TRIP_PLAN 分支 metadata 改为传 trip_plan |
| `frontend/src/components/chat/TripCard.vue` | 完全重写 | 多标签结构化卡片 |
| `frontend/src/components/chat/ChatContainer.vue` | 小改 | 向 TripCard 传递 trip_plan prop |

---

## 二、会话管理系统

### 2.1 现状

`session_id` 固定为 `"default"`，用户无法创建/切换/删除会话。Conversations 表虽然存了 `session_id` 字段，但前端完全没有会话管理 UI。

### 2.2 改造方案

#### 2.2.1 后端新增 API

```
GET    /sessions?device_id=xxx          → 返回会话列表
POST   /sessions                        → 创建新会话
DELETE  /sessions/{session_id}           → 删除会话（软删除或物理删除）
PUT    /sessions/{session_id}/rename     → 重命名会话
```

会话列表返回格式：
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "title": "杭州3天行程规划",    // 自动截取首条用户消息前20字
      "message_count": 12,
      "last_message": "明天天气怎么样",
      "created_at": "2026-05-10T...",
      "updated_at": "2026-05-11T..."
    }
  ]
}
```

#### 2.2.2 前端

在 `ChatContainer.vue` 左侧新增可折叠侧边栏：

- **新建会话按钮**（+ 图标）
- **会话列表**（按更新时间倒序）
  - 每项显示：标题、最后消息预览、时间
  - 点击切换 session_id → chatStore 切换当前会话
  - 左滑/长按显示删除按钮
- **当前活跃会话高亮**

#### 2.2.3 前端状态管理

`chatStore` 增加：
- `sessionId: string`（当前活跃会话 ID）
- `sessions: Session[]`（会话列表）
- `switchSession(id)` — 切换会话时重新加载该会话的消息历史
- `createSession()` — 创建新会话（清空消息列表，生成新 session_id）
- `deleteSession(id)` — 删除会话

---

## 三、偏好管理面板

### 3.1 现状

后端已提供完整的偏好 CRUD API（`GET/DELETE /memory/{device_id}/preferences`），但前端没有任何可视化界面让用户查看或编辑已保存的偏好。

### 3.2 改造方案

在 header 或侧边栏加一个"偏好设置"入口，点击后从右侧滑出抽屉面板：

- **偏好列表**：分类展示（饮食 / 出行 / 住宿 / 其他）
- **每条偏好**：显示 key → value，带删除按钮
- **手动添加**：选择 category → 输入 key → 输入 value
- **批量删除**：按 category 一键清除

前端只需调用已有的 `/memory/` API，无需后端改动。

---

## 四、行程导出（PDF/图片）

### 4.1 现状

后端已有 `export_service.py`（ReportLab），但前端没有触发导出的按钮。导出也从未在任何 API 端点被调用。

### 4.2 改造方案

在 TripCard 底部或右上角加两个按钮：

- **导出 PDF**：调用 `POST /trip/{trip_id}/export?format=pdf` → 后端用 ReportLab 生成 PDF → 返回文件流 → 浏览器下载
- **分享图片**：前端用 `html2canvas` 将 TripCard DOM 截图 → 下载 PNG

后端新增：
```
GET /trip/{trip_id}/export?format=pdf   → 返回 PDF 文件流
GET /trip/{trip_id}/export?format=json  → 返回 JSON 数据
```

---

## 五、错误恢复与重试机制

### 5.1 现状

前端 `sendMessage` 失败时只显示 "消息发送失败，请检查后端是否启动"，没有重试按钮，没有区分错误类型。

### 5.2 改造方案

**前端 store 层面**：

- 区分错误类型：`NetworkError`（网络不通）vs `ServerError`（500）vs `TimeoutError`
- 失败的消息在界面上标红，旁边显示"重新发送"按钮
- 点击重试：从 store 中取出原消息内容重新发送
- 连续失败 3 次后自动提示"请检查后端是否已启动"

**后端层面**：

- 对 LLM 调用增加 timeout + retry（1次）
- 对高德 API 调用增加 fallback（失败时行程生成仍继续，不含 POI 数据）

---

## 六、聊天消息操作菜单

### 6.1 改造方案

在 `MessageBubble.vue` 中，对每条消息增加右键菜单或长按弹出操作：

| 操作 | 适用消息 | 行为 |
|------|----------|------|
| 复制文本 | 全部 | 复制 content 到剪贴板 |
| 重新生成 | assistant | 用同一用户消息再次调用 LLM |
| 删除 | 全部 | 从 messages 数组中移除 + 从数据库删除 |
| 播报 | assistant（文本类） | TTS 朗读 |

长按触发（移动端）/ 右键触发（桌面端）。UI 为一个浮动在消息气泡旁的小菜单。

---

## 七、预算估算器

### 7.1 改造方案

在行程生成 Prompt 中已要求 LLM 输出 `budget_breakdown`，只需确保 LLM 认真填写即可。

在 TripCard 的"行程总览"标签中，将 `budget_breakdown` 以可视化方式展示——5 个横向柱状条（交通/住宿/餐饮/门票/其他 + 金额）。

不新增独立服务，仅增强 Prompt 对预算估算的重视。

---

## 八、旅行准备清单自动生成

### 8.1 方案

当用户确认了行程后（或行程生成完成后），AI 主动推送或提供一个"生成准备清单"按钮。

**后端新增** `checklist_service.py`：
- 接收 `destination, days, season, weather` 
- 调用 LLM 生成分类清单：
  - 📄 证件（身份证、护照等）
  - 👗 衣物（根据天气）
  - 💊 药品（高原反应药、防蚊虫等）
  - 📱 电子设备（充电宝、转换插头）
  - 🧴 日用品（防晒、洗漱）

前端在 TripCard 底部加"生成准备清单"按钮，点击后在聊天中插入一条结构化清单消息。

---

## 九、聊天界面整体美化

> 参照 Claude（Cowork）、豆包、ChatGPT 网页版的成熟设计语言，对 TravelMate 聊天界面进行整体视觉升级。核心理念：**简约布局 + 暖色点缀 + 精致排版**，避免纯白苍白感，也不过度花哨。

### 9.1 当前问题诊断

对比主流聊天产品，当前 TravelMate 的 UI 有以下差距：

| 维度 | 当前 TravelMate | Claude / 豆包 / ChatGPT | 差距 |
|------|----------------|------------------------|------|
| 布局 | 全宽聊天，无边栏 | 居中窄栏（max-w-3xl），左侧会话列表 | 散、无焦点 |
| 配色 | 纯白 + 标准蓝（bg-blue-600） | 暖灰色背景 + 品牌色点缀 | 显廉价 |
| 空状态 | 一行灰色文字 | 居中品牌标识 + 欢迎语 + 建议 | 冰冷 |
| 消息气泡 | 纯白底 + 简单圆角 | 微阴影 + 舒适间距 + 精致排版 | 粗糙 |
| 输入框 | 普通圆角 textarea | 大圆角 + 聚焦光环 + placeholder 引导 | 缺乏吸引力 |
| 动画 | 无过渡 | 消息滑入、加载跳动点、hover 微效 | 生硬 |
| 暗色模式 | 无 | 全局 dark 支持 | 缺失 |

### 9.2 整体配色方案

**设计原则**：暖而不腻，素而不白。取旅行主题的暖色调（日出橙、沙漠金、森林绿），但只用微量点缀。

```
主背景：     stone-50  (#FAFAF9)  — 暖白，比纯白多一分温度
卡片/气泡：   white     (#FFFFFF)  — 消息气泡的底
侧边栏：     stone-100 (#F5F5F4)  — 微暖灰
主文字：     stone-800 (#292524)  — 柔和黑
次要文字：   stone-500 (#78716C)  — 暖灰
品牌色：     amber-500 (#F59E0B)  — 旅行感暖橙（替换当前的 blue-600）
辅助色：     emerald-500 (#10B981) — 用于成功/完成状态
强调色：     sky-400   (#38BDF8)  — 用于链接/天气相关
边框：       stone-200 (#E7E5E4)  — 暖灰边框

user 气泡：  amber-500 → amber-600 微渐变（区别于冷冰冰的纯蓝）
AI 气泡：    white + stone-100 微边框 + 微阴影
系统消息：   amber-50  (#FFFBEB)  — 暖黄底
```

**为什么选 amber 而不是 blue**：
- 旅行 = 日出、沙漠、秋天、温暖 → amber 天然关联
- 市面上 blue 产品太多（ChatGPT、豆包、飞书全是蓝），amber 有辨识度
- 暖色调在白色背景上依然干净，不会显廉价

### 9.3 布局重构

**改造前**（全宽布局）：
```
┌─────────────────────────────────────────────┐
│  TravelMate  AI 智游伴                       │  ← header 全宽
├─────────────────────────────────────────────┤
│                                              │
│  消息列表（全宽，视觉焦点散）                   │
│                                              │
├─────────────────────────────────────────────┤
│  输入框（全宽）                                │
└─────────────────────────────────────────────┘
```

**改造后**（居中窄栏 + 左侧会话列表）：
```
┌──────┬───────────────────────────────────────┐
│      │  TravelMate 智游伴        ☀️ 深圳 26° │
│ 会话1 ├───────────────────────────────────────┤
│ 会话2 │                                       │
│ 会话3 │          消息列表（max-w-3xl）          │
│      │          居中，视觉聚焦                  │
│ +新建 │                                       │
│      ├───────────────────────────────────────┤
│      │          输入框（max-w-3xl）             │
└──────┴───────────────────────────────────────┘
```

左侧会话栏（约 260px，可折叠）是第二节"会话管理"的 UI 承载，两者合并实施。

### 9.4 欢迎页（空状态重设计）

替换当前的灰色一行字，设计一个有温度的欢迎页：

```
┌─────────────────────────────────────────────┐
│                                             │
│              🗺️                             │
│          TravelMate                         │
│         你的 AI 旅行伙伴                      │
│                                             │
│    我可以帮你规划行程、查天气、                │
│    推荐景点、讲解历史文化～                    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  🌤️ 深圳 今天晴 26°C                │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌────────────┬───────────┬──────────┐     │
│  │ 🗺️ 规划行程 │ 🌤️ 查天气 │ 🏯 景点推荐│     │
│  └────────────┴───────────┴──────────┘     │
│                                             │
│  或直接输入你想去的地方...                     │
└─────────────────────────────────────────────┘
```

包含：
- 品牌 Logo/Emoji 居中
- 一句定位语
- 当前天气卡片（复用十二节的天气数据）
- 三个快捷入口按钮（点击自动填充消息）
- 引导输入文字

### 9.5 消息气泡打磨

**当前问题**：用户气泡纯蓝底白字、AI 气泡纯白底，间距紧凑，缺少层次感。

**改造方案**：

**用户气泡**：
```
┌────────────────────────────────────┐
│  我想去杭州玩三天                    │  ← 左侧对齐文字
└────────────────────────────── 09:42│  ← 时间戳右对齐
```
- 背景：`bg-gradient-to-r from-amber-500 to-amber-600`（微渐变，比纯色有质感）
- 文字：`text-white`，字号 `text-sm`
- 圆角：`rounded-2xl rounded-br-md`（右侧小尾巴）
- 最大宽度：`max-w-[70%]`，靠右对齐
- 时间戳：气泡底部 `text-amber-200`，`text-[10px]`

**AI 气泡**：
```
┌────────────────────────────────────┐
│  好的！杭州是一座很美的城市...       │
│                                    │
│  📍 西湖风景区                      │  ← Markdown 渲染
│  ...                               │
│                          📢 播报   │  ← 操作按钮
└────────────────────────────────────┘
```
- 背景：`bg-white` + `border border-stone-100` + `shadow-sm`
- 文字：`text-stone-800`，字号 `text-sm`
- 圆角：`rounded-2xl rounded-bl-md`（左侧小尾巴）
- 最大宽度：`max-w-[75%]`，靠左对齐
- 播报按钮：底部右侧，小字灰色

**消息间距**：`space-y-4` → `space-y-6`（增加呼吸感，Claude 风格的宽松间距）

**Markdown 渲染**：prose 样式微调
- 标题：`text-base font-semibold text-stone-800`
- 列表：`my-1`，符号用 emerald 色
- 加粗：`font-semibold text-stone-700`
- 链接：`text-sky-500 underline`

### 9.6 输入框重设计

参照 ChatGPT 和豆包的输入区设计：

```
┌──────────────────────────────────────────────┐
│  ┌──────────────────────────────────────┐    │
│  │  告诉我你想去哪里旅行...          🎤  │    │  ← 大圆角输入框 + 语音按钮
│  │                                      │    │
│  └──────────────────────────────────────┘    │
│  提示：试试说"帮我规划一个周末短途旅行"          │  ← placeholder 引导
│                                    [发送 →]  │  ← 发送按钮
└──────────────────────────────────────────────┘
```

- 输入框：`rounded-2xl` 大圆角，`bg-stone-50`，`border-stone-200`
- 聚焦状态：`border-amber-400` + `ring-2 ring-amber-100`（暖色光环）
- placeholder：动态轮播引导文案（每 5 秒切换一条）：
  - "试试说'帮我规划一个周末短途旅行'"
  - "输入'杭州三天'马上生成行程"
  - "问'今天适合去哪里玩'获取推荐"
- 语音按钮：左侧或右侧，与现有麦克风图标保持一致
- 发送按钮：有内容时 amber-500 亮起，无内容时置灰

### 9.7 微交互与动画

| 元素 | 动画 | 实现 |
|------|------|------|
| 新消息出现 | 从下方滑入 + 淡入 | `transition-all duration-300 ease-out` |
| 加载指示器 | 三个跳动点（已有，优化颜色为 amber） | 现有实现 + amber bg |
| 按钮 hover | 微放大 + 阴影 | `hover:scale-105 hover:shadow-md transition-all` |
| 输入框聚焦 | 边框暖色过渡 | `transition-colors duration-200` |
| 侧边栏展开 | 平滑滑出 | `transition-transform duration-300` |
| 快速操作卡片 | hover 微上浮 | `hover:-translate-y-0.5 transition-transform` |

### 9.8 暗色模式

作为整体美化的一部分，同时实现暗色模式（避免后续单独补）：

```
🌞 浅色模式 → 🌙 暗色模式

主背景：    stone-50  →  stone-900 / neutral-950
卡片/气泡： white     →  stone-800
侧边栏：    stone-100 →  stone-900
主文字：    stone-800 →  stone-100
次要文字：  stone-500 →  stone-400
用户气泡：  amber-500 →  amber-600
AI 气泡：   white     →  stone-800 + border-stone-700
边框：      stone-200 →  stone-700
```

实现方式：
1. Tailwind `darkMode: 'class'`
2. 在 header 右侧添加 `☀️/🌙` 切换按钮
3. 状态存入 `localStorage`，并监听系统 `prefers-color-scheme`
4. 所有颜色使用 `dark:` 前缀变体

### 9.9 改造涉及文件

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `frontend/tailwind.config.js` | 改造 | 扩展颜色配置 + darkMode |
| `frontend/src/style.css` | 改造 | 全局基础样式、滚动条美化、prose 定制 |
| `frontend/src/components/chat/ChatContainer.vue` | 重写 | 新布局（侧边栏 + 居中栏）、欢迎页、天气卡片、快捷入口 |
| `frontend/src/components/chat/MessageBubble.vue` | 重写 | 新气泡样式、时间戳、悬停操作、问候特殊样式 |
| `frontend/src/components/chat/ChatInput.vue` | 改造 | 新输入框样式、动态 placeholder、聚焦光环 |
| `frontend/src/components/chat/TripCard.vue` | 受一节的改造影响 | 配色跟随新设计系统 |
| `frontend/src/App.vue` | 小改 | 全局 dark class 管理 |

### 9.10 优先级

**P2** — 纯前端工作，不涉及后端。建议在 P0 功能（TripCard 结构化 + 会话管理 + KNOWLEDGE 兜底）落地后再做，否则先美化再改功能会导致返工。与第二节"会话管理"的侧边栏 UI 合并实施。

---

## 十、知识库扩充与 KNOWLEDGE 兜底逻辑

### 10.1 当前两条路径的职责划分（重要）

行程规划（TRIP_PLAN）和景点知识（KNOWLEDGE）是两条完全独立的路径，知识库只影响后者：

```
【TRIP_PLAN 路径 — 不依赖知识库】
用户："去杭州玩三天"
  → 高德地图 POI 实时搜索(search_poi("杭州")) → 获取杭州真实景点/酒店/餐厅
  → 天气 API(get_weather_forecast("杭州")) → 获取杭州实时天气
  → 记忆系统(get_all_preferences) → 获取用户偏好
  → 拼入 Prompt → LLM 生成行程
结论：任何目的地都能规划，因为 POI 来自高德实时查询

【KNOWLEDGE 路径 — 依赖知识库】
用户："西湖有什么历史故事"
  → ChromaDB(spo_knowledge) 向量检索 → 在已有文档段落中找语义匹配
  → 检索结果作为 Context 注入 Prompt → LLM 生成导游式回答
结论：知识库决定回答的"精致度"
```

### 10.2 为什么问"西湖有什么历史故事"也能回答

当 KNOWLEDGE 路径执行时，ChromaDB 搜索不到西湖相关内容（5 份文档中没有杭州的），但代码中 `spot_name` 默认为 `None`（不按景点名过滤），所以 ChromaDB 会在所有文档中按语义匹配，可能检索到一些不相关但语义相似的段落（如其他城市关于"历史"的段落）。

然后 LLM 看到 Context 里没有西湖相关内容，但它**自己的训练数据里有西湖**——于是 LLM 会忽略知识库中不相关的片段，用训练数据直接回答。

**所以"能回答"不是因为知识库，而是因为 LLM 自身的通用知识兜了底。** 但这带来了两个问题。

### 10.3 当前的核心问题：不相关 Context 的干扰

当前 `rag_service.py` 中 `query_knowledge` 的逻辑：

```python
retrieved = retrieve_knowledge(question, spot_name, top_k=5)

if not retrieved:
    return "暂时没有找到关于这个问题的知识，你可以换个方式问问看～"
    # ← 直接放弃，连 LLM 通用知识都没用到

# 否则把检索结果（可能完全不相关）作为 Context 注入 Prompt
context = "\n\n".join(f"【{r['spot_name']}】{r['text']}" for r in retrieved)
```

两个问题同时存在：

| 问题 | 触发条件 | 后果 |
|------|----------|------|
| **检索为空时直接放弃** | 问非知识库目的地的景点 | 返回 "暂时没有找到" — 即使 LLM 可以回答 |
| **检索到不相关内容时仍注入** | 跨目的地语义误匹配（如问"西湖的历史"匹配到大理的"历史文化"段落） | LLM 收到一堆噪音 Context，虽然能自行判断忽略，但增加了 token 消耗和回答不稳定性 |

### 10.4 改造方案：双层兜底逻辑

在 `rag_service.py` 的 `query_knowledge()` 中增加兜底机制，核心思路：**让 LLM 始终能回答，但诚实标注信息来源**。

```python
async def query_knowledge(question: str, spot_name: str | None = None) -> str:
    retrieved = retrieve_knowledge(question, spot_name, top_k=5)

    if not retrieved:
        # 【兜底 1】知识库为空 → 用 LLM 通用知识，并诚实告知
        prompt = (
            "你是「AI智游伴」的景点讲解员。知识库中没有检索到与用户问题直接相关的资料。\n"
            "请基于你的通用知识回答用户问题，语言生动有趣。\n"
            "在回答末尾添加一句说明：'以上信息基于通用知识整理，如需更详尽的当地攻略，可以告诉我来补充哦～'\n\n"
            f"用户问题：{question}"
        )
        answer = await call_llm(
            messages=[{"role": "user", "content": question}],
            system_prompt=prompt,
            temperature=0.7,
            max_tokens=800,
        )
        return answer

    # 有检索结果，但做一次"相关性初筛"
    context = "\n\n".join(f"【{r['spot_name']}】{r['text']}" for r in retrieved)

    # 如果 spot_name 明确但检索结果中没有任何一段属于该景点，
    # 说明是跨目的地误匹配 → 标记为"低置信度 Context"
    if spot_name:
        matching_chunks = [r for r in retrieved if r['spot_name'] == spot_name]
        if not matching_chunks:
            # 【兜底 2】检索到的内容不相关 → 仍让 LLM 回答，但告知不要强行引用 Context
            prompt = (
                "你是「AI智游伴」的景点讲解员。\n"
                "知识库中没有找到关于该景点的直接资料，以下检索到的是一般性旅行相关内容，仅供参考：\n\n"
                f"{context}\n\n"
                "请基于你的通用知识回答用户问题。如果检索内容中有相关的部分可以引用，没有则可以忽略。\n"
                "语言保持生动有趣的导游风格。\n\n"
                f"用户问题：{question}"
            )
        else:
            # 正常情况：有匹配的知识片段
            prompt = KNOWLEDGE_QA_PROMPT.format(context=context, question=question)
    else:
        # 没有指定 spot_name，正常使用检索结果
        prompt = KNOWLEDGE_QA_PROMPT.format(context=context, question=question)

    answer = await call_llm(
        messages=[{"role": "user", "content": question}],
        system_prompt=prompt,
        temperature=0.7,
        max_tokens=800,
    )
    return answer
```

**改造成果**：

| 场景 | 改造前 | 改造后 |
|------|--------|--------|
| 知识库中有该景点 | ✅ 检索到匹配段落 → 高质量导游回答 | ✅ 同左，不受影响 |
| 知识库中无该景点（检索为空） | ❌ "暂时没有找到" | ✅ LLM 通用知识回答 + 诚实标注信息来源 |
| 知识库中无该景点（误匹配到其他城市） | ⚠️ 不相关 Context 注入 → LLM 自行忽略 | ✅ 低置信度标记 → LLM 明确知道可以忽略 Context |
| 所有场景 | — | ✅ 内容质量分级：有知识库 > LLM 通用知识（标注） > 无回复 |

### 10.5 改造涉及文件

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/app/services/rag_service.py` | 改造 | 增加双层兜底逻辑（检索为空 + 相关性初筛） |

### 10.6 知识库自动调研与自进化（核心）

与其手动写攻略文档，不如建一条**"AI 自动搜索 → 整理 → 入库 → 即时生效"**的全自动管道。

#### 10.6.1 整体流程

```
用户或系统触发："扩充杭州知识库"
  ↓
① 搜索层：DuckDuckGo 多维度搜索
  ├── "杭州 必去景点 攻略"        → attractions[]
  ├── "杭州 历史文化 典故"        → history[]
  ├── "杭州 特色美食 推荐"        → food[]
  └── "杭州 旅游注意事项 交通"    → tips[]
  ↓
② 整理层：LLM 精炼为标准 .md 攻略
  ├── 去除广告/重复/低质内容
  ├── 按已有文档模板格式化
  └── 输出 data/knowledge/杭州.md
  ↓
③ 存储层：调用已有 load_knowledge_base()
  ├── 分块（按 \n\n 分割）
  ├── 向量化（ChromaDB ONNX 嵌入）
  └── 写入 spot_knowledge 集合
  ↓
④ 即时生效，用户问"西湖有什么故事" → 命中新入库的知识段落
```

#### 10.6.2 搜索层实现

依赖 `duckduckgo-search`（免费，无需 API Key）：

```python
# backend/app/services/knowledge_expander.py

from duckduckgo_search import DDGS

SEARCH_TEMPLATES = {
    "attractions": lambda d: f"{d} 必去景点 旅游攻略",
    "history": lambda d: f"{d} 历史文化 典故 名胜古迹",
    "food": lambda d: f"{d} 特色美食 推荐 必吃",
    "tips": lambda d: f"{d} 旅游注意事项 交通 最佳季节",
}

def search_destination(destination: str) -> dict[str, list[str]]:
    """多维度搜索目的地旅游信息"""
    results: dict[str, list[str]] = {}
    with DDGS() as ddgs:
        for category, query_fn in SEARCH_TEMPLATES.items():
            query = query_fn(destination)
            snippets = []
            for r in ddgs.text(query, max_results=5):
                body = (r.get("body") or "").strip()
                if body and len(body) > 30:
                    snippets.append(body)
            results[category] = snippets
    return results
```

#### 10.6.3 整理层实现（LLM 精炼 Prompt）

```python
AUTO_EXPAND_PROMPT = """你是一位专业的旅行攻略编辑。请根据以下网络搜索结果，为「{destination}」编写一份攻略文档。

## 景点搜索结果
{attractions}

## 历史文化搜索结果
{history}

## 美食搜索结果
{food}

## 实用贴士搜索结果
{tips}

## 输出要求

严格按以下 Markdown 格式输出，不要输出任何额外内容：

# {destination}

## 基本信息
（2-3句话介绍城市概况、地理特点、为何值得旅游）

## 历史文化
（核心历史事件、文化特色、名人典故、非遗等，300-400字。基于搜索结果，不要编造）

## 经典景观
（5-8个核心景点，每个1-2句话描述。格式：
- 景点名：简要描述，有什么看点
）

## 美食推荐
（5-6种当地特色美食。格式：
- 美食名：简要说明风味特点，推荐去处
）

## 游玩建议
- 建议游览时间：（几天合适）
- 最佳季节：（哪个季节最推荐，为什么）
- 交通建议：（如何到达、市内交通方式）
- 注意事项：（天气、海拔、文化禁忌等）

要求：
1. 语言简洁准确，基于搜索结果而非编造
2. 不要包含网址、广告、评分等网络痕迹
3. 保持客观，不要用"必去""最美"等绝对化用语
4. 信息不完整时宁缺毋滥
"""


async def expand_knowledge(destination: str) -> dict:
    """完整的自动调研 → 整理 → 入库流程"""
    # 1. 搜索
    search_results = search_destination(destination)

    # 2. 检查搜索结果质量
    total_snippets = sum(len(v) for v in search_results.values())
    if total_snippets < 5:
        return {"status": "insufficient", "message": f"关于{destination}的搜索结果太少({total_snippets}条)，建议换个关键词或稍后重试"}

    # 3. LLM 整理
    prompt = AUTO_EXPAND_PROMPT.format(
        destination=destination,
        attractions="\n".join(f"- {s}" for s in search_results["attractions"]),
        history="\n".join(f"- {s}" for s in search_results["history"]),
        food="\n".join(f"- {s}" for s in search_results["food"]),
        tips="\n".join(f"- {s}" for s in search_results["tips"]),
    )

    md_content = await call_llm(
        messages=[{"role": "user", "content": f"请为{destination}编写旅行攻略"}],
        system_prompt=prompt,
        temperature=0.3,
        max_tokens=1500,
    )

    # 4. 写入文件
    filepath = KNOWLEDGE_DIR / f"{destination}.md"
    filepath.write_text(md_content, encoding="utf-8")

    # 5. 向量化入库（用已有逻辑）
    from app.services.rag_service import load_knowledge_base
    chunk_count = load_knowledge_base()

    return {
        "status": "success",
        "destination": destination,
        "file": str(filepath.name),
        "chunks": chunk_count,
    }
```

#### 10.6.4 API 端点

**单个目的地**：

```
POST /knowledge/auto-expand
{
  "destination": "杭州"
}

→ 返回:
{
  "status": "success",
  "destination": "杭州",
  "file": "杭州.md",
  "message": "杭州知识库已自动扩充"
}
```

**批量扩充**（异步后台执行，WebSocket 推送进度）：

```
POST /knowledge/auto-expand-batch
{
  "destinations": ["北京", "上海", "桂林", "丽江", "张家界", "九寨沟", "黄山"]
}

→ WebSocket 逐条推送进度:
  {"type": "expand_progress", "current": "北京", "index": 1, "total": 7, "status": "searching"}
  {"type": "expand_progress", "current": "北京", "index": 1, "total": 7, "status": "generating"}
  {"type": "expand_progress", "current": "北京", "index": 1, "total": 7, "status": "done", "chunks": 8}
  ...
  {"type": "expand_complete", "total": 7, "success": 7, "failed": 0}
```

#### 10.6.5 自进化闭环：用户反馈纠正

自动调研的质量不如手动编写，但可以加纠正机制：

```
用户使用景点问答 → 发现回答有误 → 直接在聊天中纠正
  ↓ 例如："不对，灵隐寺不是唐朝建的，是东晋建的"
系统检测到纠正意图 → 记录纠正信息
  ↓
更新对应 data/knowledge/杭州.md 的相关段落
  ↓
重新分块向量化该文档
  ↓
下次问答质量提升
```

**实现方式**：在意图识别中新增 `CORRECTION` 子意图，当检测到用户纠正信息时：
1. 调用 LLM 定位需要修正的知识段落
2. 更新对应的 .md 文件
3. 重新加载该文件的向量

```python
# intent_router.py 中新增
CORRECTION_RE = re.compile(r"(不对|错了|更正|纠正|应该是|其实是|不是.*是)")

if intent == "CHAT" and CORRECTION_RE.search(user_message):
    # 判断是否涉及知识库内容的纠正
    # 如果是，触发知识修正流程
    from app.services.knowledge_expander import correct_knowledge
    await correct_knowledge(user_message, device_id)
```

#### 10.6.6 需要安装的依赖

```bash
pip install duckduckgo-search --break-system-packages
```

#### 10.6.7 新增/改造涉及文件

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/app/services/knowledge_expander.py` | **新增** | 搜索层 + 整理层 + 批量扩展 + 反馈纠正 |
| `backend/app/api/knowledge.py` | **新增** | `/auto-expand` + `/auto-expand-batch` 端点 |
| `backend/app/services/rag_service.py` | 小改 | 导入 knowledge_expander 的 reindex 函数 |
| `backend/app/services/intent_router.py` | 小改 | 新增 CORRECTION 检测 + 触发纠正流程 |
| `backend/requirements.txt` | 小改 | 新增 duckduckgo-search |
| `frontend/src/components/chat/ChatContainer.vue` | 小改 | 展示批量扩充的 WebSocket 进度条 |

#### 10.6.8 优先级说明

| 子项 | 优先级 | 理由 |
|------|--------|------|
| KNOWLEDGE 兜底逻辑（10.4） | P0 | 修 Bug：非知识库目的地直接失败 |
| 知识库自动调研（10.6.2-10.6.4） | P2 | 功能增强：减轻手动维护负担 |
| 批量扩充 + 进度推送（10.6.4） | P2 | 体验增强：一次触发覆盖 15+ 城市 |
| 用户反馈纠正闭环（10.6.5） | P3 | 锦上添花：依赖自动调研先上线，有了基础数据纠正才有意义 |

> **一句话总结**：兜底逻辑让系统"什么都能回答"，自动调研让系统"越回答越好"，反馈纠正让系统"越用越准"。三条线各自独立，可以按优先级分步上线。

---

## 十一、行程风格对比

### 11.1 方案

对同一目的地生成 2-3 种不同风格的行程，让用户选择。

**后端改造**：
- `trip_service.py` 中 `generate_trip_plan` 增加 `style` 参数
- 三种预设风格：
  - `compact` — 紧凑打卡型（景点密集，早出晚归）
  - `leisure` — 悠闲度假型（每天 2-3 个景点，留足休息时间）
  - `culture` — 文化深度型（重点博物馆、古迹、民俗体验）

**前端改造**：
- 行程生成前，在输入框上方显示三个风格选项按钮
- 用户选择后带 `style` 参数发请求
- 或以默认风格生成后提供"换一种风格"按钮

---

## 十二、首页天气显示

### 12.1 设计目标

在聊天界面 header 右侧，TravelMate 标题旁边，显示用户当前所在地的实时天气。效果类似：

```
┌─────────────────────────────────────────────────────────┐
│  TravelMate  AI 智游伴                    ☀️ 深圳 26°C │
└─────────────────────────────────────────────────────────┘
```

让用户一打开 App 就有"它在关注我所处的环境"的亲切感，也为后续主动天气提醒埋下伏笔。

### 12.2 定位策略（三层回退）

```
① 用户是否在偏好中设置了"常住城市"？
  → 是 → 直接用该城市查询天气（最准确，零延迟）
  ↓ 否
② 浏览器 Geolocation API 是否可用？
  → 是 → 获取 lat/lng → 后端逆地理编码 → 得到城市名
  ↓ 否/用户拒绝
③ 后端 IP 定位（请求来源 IP → 城市）
  → 精度较低（通常到城市级），但作为兜底
```

### 12.3 后端实现

新增 `GET /weather/current` 端点：

```python
# backend/app/api/weather.py 中新增

@router.get("/weather/current")
async def current_weather(
    device_id: str,
    lat: float | None = None,
    lng: float | None = None,
    request: Request = None,
):
    """获取用户当前所在地天气。定位优先级：偏好城市 > 浏览器坐标 > IP"""
    city = None

    # ① 检查用户偏好中是否有常住城市
    from app.services.memory_service import get_all_preferences
    prefs = get_all_preferences(device_id)
    for p in prefs:
        if p["category"] == "location" and p["key"] == "home_city":
            city = p["value"]
            break

    # ② 浏览器坐标 → 逆地理编码
    if not city and lat and lng:
        from app.services.map_service import reverse_geocode
        geo = reverse_geocode(f"{lng},{lat}")
        city = geo.get("city") if geo else None

    # ③ IP 定位（兜底）
    if not city and request:
        client_ip = request.client.host if request.client else None
        if client_ip:
            city = _ip_to_city(client_ip)

    if not city:
        return {"status": "unknown", "message": "无法确定你的位置"}

    # 查询天气
    from app.services.weather_service import get_weather_forecast
    weather = get_weather_forecast(city)

    today = weather.get("days", [{}])[0] if weather.get("days") else {}
    return {
        "status": "ok",
        "city": city,
        "weather": today.get("day_weather", ""),
        "temp": today.get("day_temp", ""),
        "wind": today.get("day_wind", ""),
        "report_time": weather.get("report_time", ""),
    }
```

**IP 定位**使用免费服务（无需额外 API Key）：

```python
import httpx

async def _ip_to_city(ip: str) -> str | None:
    """通过 IP 获取城市（使用 ip-api.com 免费服务）"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}")
            data = resp.json()
            if data.get("status") == "success":
                return data.get("city")
    except Exception:
        pass
    return None
```

**反向地理编码**复用高德 API（已有 `map_service.py`）：

```python
# 在 map_service.py 中新增
async def reverse_geocode(location: str) -> dict | None:
    """经纬度 → 城市名（location 格式："lng,lat"）"""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://restapi.amap.com/v3/geocode/regeo", params={
            "key": settings.AMAP_API_KEY,
            "location": location,
        })
        data = resp.json()
        if data.get("status") == "1":
            comp = data["regeocode"]["addressComponent"]
            return {"city": comp.get("city") or comp.get("province", "")}
    return None
```

### 12.4 前端实现

在 `ChatContainer.vue` header 中新增天气组件：

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

const weather = ref<{ city: string; weather: string; temp: string } | null>(null)

async function fetchWeather() {
  // ① 尝试获取浏览器坐标
  let lat: number | undefined, lng: number | undefined
  if (navigator.geolocation) {
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 })
      })
      lat = pos.coords.latitude
      lng = pos.coords.longitude
    } catch { /* 用户拒绝或超时，走 IP 兜底 */ }
  }

  // ② 请求后端
  const params: Record<string, any> = { device_id: getDeviceId() }
  if (lat !== undefined) { params.lat = lat; params.lng = lng }
  const res = await api.get('/weather/current', { params })
  if (res.data.status === 'ok') weather.value = res.data
}

onMounted(fetchWeather)
</script>
```

**Header 模板改造**（在现有 header 中新增右侧天气区域）：

```vue
<header class="flex items-center justify-between border-b bg-white px-4 py-3 shadow-sm">
  <div class="flex items-center">
    <h1 class="text-base font-semibold text-gray-800">TravelMate</h1>
    <span class="ml-2 text-xs text-gray-400">AI 智游伴</span>
  </div>

  <!-- 新增：天气显示 -->
  <div v-if="weather" class="flex items-center gap-1.5 text-sm text-gray-600">
    <span>{{ weatherEmoji(weather.weather) }}</span>
    <span class="hidden sm:inline">{{ weather.city }}</span>
    <span class="font-medium">{{ weather.temp }}°C</span>
  </div>
  <div v-else class="text-xs text-gray-300">定位中...</div>
</header>
```

**天气图标映射**：

```typescript
function weatherEmoji(weather: string): string {
  if (/晴/.test(weather)) return '☀️'
  if (/多云|阴/.test(weather)) return '⛅'
  if (/雨|雷/.test(weather)) return '🌧️'
  if (/雪/.test(weather)) return '❄️'
  if (/风/.test(weather)) return '💨'
  return '🌤️'
}
```

### 12.5 定时刷新

前端每 30 分钟自动刷新一次天气（天气变化不快，不需要高频轮询）：

```typescript
onMounted(() => {
  fetchWeather()
  // 每 30 分钟刷新
  const timer = setInterval(fetchWeather, 30 * 60 * 1000)
  onUnmounted(() => clearInterval(timer))
})
```

### 12.6 与主动天气提醒的联动

这个天气组件是阶段八"主动服务"的自然延伸。当 header 显示用户所在地天气后，可以进一步增强：

- 检测到用户所在地即将下雨 → 通过 WebSocket 推送提醒
- 用户搜索其他城市天气时 → header 短暂切换显示目标城市天气，然后恢复
- 用户规划行程到某城市 → header 同时显示"本地天气"和"目的地天气"

### 12.7 改造涉及文件

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/app/api/` 新增 `weather.py` 或扩展现有路由 | 新增端点 | `GET /weather/current` |
| `backend/app/services/map_service.py` | 小改 | 新增 `reverse_geocode()` |
| `frontend/src/components/chat/ChatContainer.vue` | 小改 | header 新增天气组件 + 定位逻辑 |

### 12.8 优先级

**P2** — 属于体验优化，实现简单（前后端加起来约 100 行代码），不依赖其他模块。建议在 P0 （TripCard + KNOWLEDGE 兜底 + 会话管理）完成后顺手做掉。

---

## 十三、会话启动主动问候

### 13.1 设计目标

用户打开聊天界面或新建会话时，不等用户先发消息，AI 主动送上一条个性化开场白。格式：

> 👋 下午好！你目前在深圳，今天晴转多云 26°C，挺适合出门走走的。
> 我注意到你不吃辣，之前还规划过大理的行程，需要帮你继续完善吗？
> 或者你有什么新的旅行计划？我可以帮你规划行程、查天气、推荐景点～

用一句话概括：**打招呼 + 所在地天气 + 回忆偏好/行程 + 开放式邀请**。

### 13.2 触发时机

| 场景 | 触发条件 | 行为 |
|------|----------|------|
| 首次打开（新设备） | messages 为空，无任何历史对话 | 送新用户欢迎语 |
| 新建会话 | 用户点击"新建会话" | 生成新开场白（不重复上次的） |
| 打开空会话 | 切换到一条 messages 为空的已有会话 | 如果是今天内已问候过，不重复发送 |
| 每日首次打开 | 距离上次问候超过 6 小时 | 重新生成当日问候（天气已更新） |

**核心原则**：不骚扰用户。用 `localStorage` 记录最近一次问候的时间戳和 session_id，避免频繁重复。

### 13.3 后端实现

新增 `GET /proactive/greet` 端点，与已有的 `proactive_service.py` 放在一起：

```python
# backend/app/api/proactive.py 中新增

@router.get("/proactive/greet")
async def generate_greeting(device_id: str):
    """生成个性化开场问候"""

    # 1. 收集上下文信息
    from app.services.memory_service import get_all_preferences
    from app.services.trip_service import query_trip_plans as _query_trips
    from app.services.weather_service import get_weather_forecast

    prefs = get_all_preferences(device_id)
    recent_trips = _query_trips(device_id, limit=2)
    weather_data = _get_current_city_weather(device_id)  # 复用十二节的三层定位

    # 2. 判断用户类型
    is_new_user = (len(prefs) == 0 and len(recent_trips) == 0 and _get_total_messages(device_id) < 3)
    is_returning = (len(prefs) > 0 or len(recent_trips) > 0)

    # 3. 组装 Prompt → LLM 生成个性化问候
    prompt = GREETING_PROMPT.format(
        time_of_day=_time_greeting(),
        weather=weather_data,
        preferences=_format_prefs(prefs),
        recent_trips=_format_trips(recent_trips),
        is_new_user=is_new_user,
    )

    greeting = await call_llm(
        messages=[{"role": "user", "content": "生成一条个性化开场问候"}],
        system_prompt=prompt,
        temperature=0.8,  # 稍高温度，让问候语每次略有变化
        max_tokens=300,
    )

    return {"greeting": greeting, "is_new_user": is_new_user}


def _time_greeting() -> str:
    """根据当前时间返回问候语"""
    h = datetime.now().hour
    if h < 6:  return "深夜好"
    if h < 12: return "早上好"
    if h < 14: return "中午好"
    if h < 18: return "下午好"
    return "晚上好"
```

**Prompt 设计**（多场景自适应）：

```python
GREETING_PROMPT = """你是「AI智游伴」的个性化问候生成器。根据以下上下文生成一条温暖的主动开场白。

## 基础信息
- 时间：{time_of_day}
- 天气：{weather}

## 用户画像
- 是新用户：{is_new_user}
- 旅行偏好：{preferences}
- 最近行程：{recent_trips}

## 问候模板（按用户类型选择）

### 如果是新用户（无偏好、无行程）：
1. 时间问候 + 所在地天气
2. 一句话介绍自己能做什么（规划行程、查天气、推荐景点、讲解故事）
3. 一个引导性问题，例如"最近有想去的地方吗？"

### 如果是回访用户（有偏好或行程）：
1. 时间问候 + 所在地天气
2. 提到 1-2 条用户偏好（自然融入，不要生硬列举）
3. 如果有未完成的行程规划，询问是否继续
4. 一个开放式的服务邀请

## 要求
- 语气温暖自然，像老朋友在聊天，不要像机器人客服
- 总长度 2-4 句话，不要太长
- 每次生成的问候语要有变化，不要每次一样
- 不要用"尊贵的用户""您好"等客服腔
- 天气信息自然地融入，不要单独报天气数据
- 直接输出问候语，不要加前缀如"问候：""""
```

### 13.4 新用户 vs 回访用户的差异化

**新用户**（首次打开，无任何数据）：
> 👋 早上好！你目前在杭州，今天小雨 22°C，出门记得带伞哦。
> 我是你的旅行助手，可以帮你规划行程、查天气、推荐美食和景点。
> 最近有想去的地方吗？告诉我目的地和天数，我来帮你安排～

**回访用户**（有偏好"不吃辣"、有行程"大理3天"）：
> 👋 下午好！深圳今天晴 28°C，挺适合出门的。
> 上次你规划的大理行程还没做完呢，要接着完善吗？我知道你不吃辣，到时候帮你留意清淡的餐厅～
> 或者有新的旅行计划也可以告诉我！

**沉默回访用户**（有历史但 7 天以上没来过）：
> 👋 好久不见！最近过得怎么样？
> 你之前的杭州行程还没出发吧？那边这几天降温了，记得多带件外套。要不要帮你看看最新的天气和攻略？

### 13.5 前端实现

在 `ChatContainer.vue` 的 `onMounted` 中新增检测逻辑：

```typescript
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

const GREETING_COOLDOWN_MS = 6 * 60 * 60 * 1000  // 6 小时内不重复问候

onMounted(async () => {
  // 只有消息列表为空时才触发问候
  if (store.messages.length > 0) return

  // 检查冷却时间
  const lastGreeting = localStorage.getItem('travelmate_last_greeting')
  if (lastGreeting) {
    const elapsed = Date.now() - parseInt(lastGreeting)
    if (elapsed < GREETING_COOLDOWN_MS) return
  }

  try {
    const res = await api.get('/proactive/greet', {
      params: { device_id: getDeviceId() }
    })
    // 作为第一条 assistant 消息插入
    store.addMessage({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: res.data.greeting,
      timestamp: Date.now(),
      type: 'proactive',
      metadata: { proactive_type: 'greeting' },
    })
    // 记录时间戳
    localStorage.setItem('travelmate_last_greeting', String(Date.now()))
  } catch {
    // 问候失败不阻塞正常使用，静默跳过
  }
})
```

**给问候消息一个特殊的视觉样式**：在 `MessageBubble.vue` 中，`proactive_type === 'greeting'` 的消息使用渐变背景 + 小星星图标，与普通 AI 回复区分开。

### 13.6 补充建议：快速操作卡片

除了纯文本问候，可以在问候消息下方附上 **2-3 个可点击的快速操作按钮**，降低用户输入门槛：

```
┌──────────────────────────────────────────────┐
│  👋 下午好！深圳今天晴 28°C...              │
│  最近有想去的地方吗？                        │
│                                              │
│  [🗺️ 规划行程] [🌤️ 查天气] [🏯 景点推荐]   │
└──────────────────────────────────────────────┘
```

点击按钮 → 自动填充消息内容并发送，例如：
- 点击"规划行程" → 发送"帮我规划行程"
- 点击"查天气" → 发送"今天天气怎么样"
- 点击"景点推荐" → 发送"推荐一些热门景点"

这样用户连打字都不用，点一下就启动了对话。

**实现方式**：问候消息的 `metadata` 中附带 `quick_actions` 数组，`MessageBubble` 检测到后渲染为底部的一排小按钮。

```json
{
  "greeting": "...",
  "quick_actions": [
    {"label": "规划行程", "message": "帮我规划行程"},
    {"label": "查天气", "message": "今天天气怎么样"},
    {"label": "景点推荐", "message": "推荐一些热门景点"}
  ]
}
```

### 13.7 改造涉及文件

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/app/api/proactive.py` | 改造 | 新增 `GET /proactive/greet` 端点 |
| `backend/app/services/proactive_service.py` | 小改 | 新增 `_get_current_city_weather()` 辅助函数 |
| `frontend/src/components/chat/ChatContainer.vue` | 小改 | onMounted 空会话检测 + 请求问候 |
| `frontend/src/components/chat/MessageBubble.vue` | 小改 | 问候消息特殊样式 + 快速操作按钮渲染 |
| `frontend/src/stores/chat.ts` | 小改 | addMessage 支持 metadata 中的 quick_actions |

### 13.8 优先级

**P2** — 属于体验亮点型功能。实现成本小（后端约 80 行 Prompt + 端点，前端约 60 行），但用户感知极强——"这个 App 是活的"。建议在 P0 和首页天气（十二节）完成后再做，因为需要依赖天气定位功能。

---

## 附录A：数据结构对照

### A.1 已有 Schema（schemas.py）与 TripCard 渲染映射

| Schema 字段 | TripCard 渲染位置 | 图片来源参考 |
|-------------|-------------------|-------------|
| `Itinerary.summary` | 行程总览 Tab 顶部 | - |
| `Itinerary.days[].theme` | Day N Tab 标题 | - |
| `DayPlan.spots[].start_time / end_time` | 活动卡片时间标签 | "09:00-11:00" |
| `DayPlan.spots[].name` | 活动卡片标题 | "西湖风景区" |
| `DayPlan.spots[].description` | 活动卡片正文 | 描述段落 |
| `DayPlan.spots[].tips` | 高亮提示框 | 黄色背景框 |
| `DayPlan.spots[].address` | 位置信息行 | 图钉图标 + 地址 |
| `DayPlan.transport[].mode + duration + estimated_cost` | 交通行 | "打车约15分钟，费用约20元" |
| `DayPlan.meals[].meal_type + name + notes + estimated_cost` | 餐饮推荐卡片 | "午餐推荐" |
| `DayPlan.hotel.name + level + location` | 住宿信息 | - |
| `Itinerary.budget_breakdown` | 行程总览预算区 | - |
| `Itinerary.tips` | 行程总览 Tips 列表 | - |

### A.2 改造前后数据流对比

```
【改造前】
LLM → Markdown 字符串 → reply → TripCard(markdown-it 渲染)

【改造后】
LLM → JSON 字符串 → Pydantic Itinerary → {
    reply: itinerary.summary (文本气泡),
    metadata.trip_plan: itinerary.model_dump() (结构化数据)
} → TripCard 多标签结构化卡片
```

---

> **下一步**：确认此方案后，按优先级 P0 → P1 → P2 → P3 逐项实施。每个模块改造完成后启动前后端验证。
