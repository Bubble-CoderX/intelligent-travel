# TravelMate 项目进展 2026-05-11

## 今日完成

### 阶段三：三层意图识别管道（完成并修复）

**新增文件（4个）**：
- `backend/app/services/regex_matcher.py` — 第一层正则快速匹配（问候/告别/感谢/确认，>50字自动跳过）
- `backend/app/services/llm_client.py` — DeepSeek API 异步调用封装，含错误响应处理
- `backend/app/utils/safety.py` — 输入/输出安全检查（BLOCK/WARN/URGENT 三级）
- `backend/app/services/intent_router.py` — 完整意图管道（安全→正则→AI→安全）

**修改文件**：
- `backend/app/api/chat.py` — 集成 intent_router，返回意图+元数据
- `backend/app/core/config.py` — 新增 DEEPSEEK_API_KEY/BASE_URL/MODEL 配置

### 阶段三 Bug 修复（4个运行时错误）

| Bug | 原因 | 修复方式 |
|-----|------|----------|
| `KeyError: '\n  "intent"'` | Prompt 模板中 JSON 示例的 `{}` 被 `.format()` 误解析 | `.format()` → `.replace()` |
| `KeyError: 'reply'` | AI 路径返回的 dict 缺少 reply 字段 | AI 返回路径补充 reply 字段 |
| DeepSeek 错误响应 KeyError | 直接取 `choices[0]` 未检查 error 字段 | 增加 error/choices 字段检查 |
| chat.py 崩溃 | `result["reply"]` 硬访问 | 改为 `result.get("reply", fallback)` |

## 当前项目状态

### Git 提交记录

```
23d33d9  阶段四：记忆系统升级为 ChromaDB + SQLite 双写
c7633da  修复 requirements.txt 中文注释导致 pip GBK 解码失败
3fb08d6  阶段四：Hermes 记忆系统（纯 SQLite 实现）
4c316a4  修复阶段三意图识别管道三个运行时错误
14a38be  阶段三：三层意图识别管道
0d9219e  阶段二：后端 API 网关与数据库初始化
573a8a4  阶段一：前端对话界面基础
5843d94  阶段零：搭建项目骨架，迁移核心服务
```

### 已完成模块

| 层级 | 模块 | 状态 |
|------|------|------|
| 前端 | Vue 3 + Vite + TypeScript + Tailwind CSS + Pinia + Axios | ✅ |
| 前端 | 聊天界面（ChatContainer / MessageBubble / ChatInput / TripCard） | ✅ |
| 前端 | 设备识别（localStorage 持久化 Device ID） | ✅ |
| 后端 | FastAPI + CORS + 路由体系（/chat /memory /trip /proactive） | ✅ |
| 后端 | SQLite 数据库（devices / conversations / user_preferences / trip_plans 四表） | ✅ |
| 后端 | 正则快速匹配层（问候/告别/感谢/确认） | ✅ |
| 后端 | AI 意图识别（DeepSeek API，支持5种意图） | ✅ |
| 后端 | 输入/输出安全检查（BLOCK/WARN/URGENT 三级） | ✅ |
| 后端 | 迁移服务（地图/天气/缓存/导出/行程数据模型） | ✅ |
| 后端 | 记忆系统：SQLite + ChromaDB 双写（语义检索 + 回退） | ✅ |
| 后端 | 记忆 API：GET/POST/DELETE /memory/{device_id}/preferences | ✅ |
| 后端 | 意图管道集成：PREFERENCE 意图自动写入记忆 | ✅ |

### 已验证的功能

- 输入"你好" → 正则层秒回，不调用 LLM ✅
- 输入"我想去杭州玩3天" → AI 识别为 TRIP_PLAN，提取 destination=杭州, days=3 ✅
- 输入"我不吃辣" → AI 识别为 PREFERENCE → 自动写入记忆 → 回复"已记住你的偏好" ✅
- 重复说偏好 → 更新已有记录 + confidence 递增 ✅
- GET /memory/{id}/preferences → 返回全部偏好列表 ✅
- GET /memory/{id}/query?q=spicy → ChromaDB 语义检索 ✅
- DELETE /memory/{id}/preferences?category=diet → 双删（SQLite + ChromaDB） ✅
- Swagger 文档 `http://localhost:8000/docs` 中 /chat 在 chat 标签下 ✅

### 待完成：ChromaDB 向量模型下载

ChromaDB 的 ONNX 嵌入模型（all-MiniLM-L6-v2, ~79MB）首次使用需下载。因 VPN 网络限制，下载极慢。解决方案：

```bash
# 方法：断开 VPN 后在终端运行
cd "C:/Users/21041/Desktop/intelligent travel/travelmate/backend"
python -c "from app.services.memory_service import save_memory, query_memory; save_memory('test','food','spicy','no'); print(query_memory('test','辣'))"
# 模型会自动下载到 ~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/
```

> 注：未下载模型时系统自动回退到 SQLite LIKE 查询，功能不受影响。

## 关键决策记录

- **DEC-001**: 配置管理用 `os.getenv()` 而非 pydantic-settings，避免引入额外依赖
- **DEC-002**: LLM 客户端使用 httpx 异步，温度 0.1（意图识别需稳定输出）
- **DEC-003**: 意图识别 Prompt 中的 JSON 示例使用 `{user_message}` 占位符 + `.replace()` 替换，避免 `.format()` 与 JSON 花括号冲突
- **DEC-004**: 大于 50 字符的消息跳过正则层直接进 AI 层

## 关键文件索引

### 后端核心
| 文件 | 作用 |
|------|------|
| `travelmate/backend/app/main.py` | FastAPI 入口，CORS，lifespan |
| `travelmate/backend/app/core/config.py` | 环境变量配置 |
| `travelmate/backend/app/api/chat.py` | `/chat` 端点 |
| `travelmate/backend/app/api/memory.py` | `/memory` 端点（偏好 CRUD + 语义检索） |
| `travelmate/backend/app/services/intent_router.py` | 意图管道主逻辑 |
| `travelmate/backend/app/services/regex_matcher.py` | 正则匹配层 |
| `travelmate/backend/app/services/llm_client.py` | DeepSeek API 封装 |
| `travelmate/backend/app/services/memory_service.py` | 记忆系统（SQLite + ChromaDB 双写） |
| `travelmate/backend/app/utils/safety.py` | 安全检查 |
| `travelmate/backend/app/models/database.py` | SQLite 初始化 |
| `travelmate/backend/app/models/schemas.py` | Pydantic 数据模型 |

### 前端核心
| 文件 | 作用 |
|------|------|
| `travelmate/frontend/src/stores/chat.ts` | Pinia 聊天状态管理 |
| `travelmate/frontend/src/components/chat/ChatContainer.vue` | 聊天主容器 |
| `travelmate/frontend/src/components/chat/MessageBubble.vue` | 消息气泡（Markdown 渲染） |
| `travelmate/frontend/src/components/chat/ChatInput.vue` | 输入框 |
| `travelmate/frontend/src/api/client.ts` | Axios 实例 + X-Device-ID 拦截器 |
| `travelmate/frontend/src/utils/device.ts` | 设备 ID 管理 |

## 下一步：阶段五 — 外部 API 集成

按实现方案，下一阶段需要：

1. 集成高德地图 API（景点搜索、路线规划）
2. 集成天气 API（实时天气查询、天气预报）
3. 实现 WEATHER 意图 → 调用天气 API → 返回结构化天气信息
4. 实现 KNOWLEDGE 意图 → 调用地图 API → 返回景点信息
5. 验证："杭州明天天气怎么样" → 识别 WEATHER → 调用 API → 返回天气

## 恢复命令

```bash
# 终端1：启动后端
cd "C:/Users/21041/Desktop/intelligent travel/travelmate/backend"
source venv/bin/activate   # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# 终端2：启动前端
cd "C:/Users/21041/Desktop/intelligent travel/travelmate/frontend"
npm run dev
```

验证地址：
- 前端：http://localhost:5173
- 后端 Swagger：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

# 人-Agent 协同经验总结

> 以下内容基于本次 TravelMate 项目 Phase 0-3 的实际交互过程，结合 SPORTS-ASSISTANT 项目的协同方法论，提炼给初学者的参考经验。

## 一、本次协同的几个关键特征

### 1. 按照完整的实现方案文档逐阶段推进

用户提前准备好了《AI智游伴-完整实现方案.md》（12个阶段、附录含完整目录结构和里程碑验收表），Agent 只需按方案执行即可。这验证了一个核心原则：

> **好的方案文档 = 人与 Agent 之间的"接口契约"。方案越清晰，Agent 执行越准确，返工越少。**

### 2. 每阶段验证、提交 Git，形成可回退的里程碑

本项目严格执行了"做完 → 验证 → 提交 → 继续"的节奏。5个 commit 对应5个可回退的检查点。

> **每阶段独立可验证，比一口气写完全部代码再测试，效率更高、风险更小。**

### 3. 遇到 Bug 时，用户展示截图而非口头描述

Phase 3 遇到 4 个运行时错误，用户通过浏览器截图展示错误信息。截图比口头描述（"报错了"）提供了更准确的定位信息。

### 4. "先改错再提交"而非"覆盖式提交"

Phase 3 的 bug 修复是独立的一个 commit（`4c316a4`），而不是 squash 到原 commit。这样 commit 历史清晰展示了"做了什么 + 踩了什么坑 + 怎么修复的"。

## 二、协同中踩过的坑与解决方法

### 坑1：Python `.format()` 与 JSON 花括号冲突

**现象**：LLM 返回 `KeyError: '\n  "intent"'`

**原因**：Prompt 模板中嵌入了 JSON 示例（含 `{}`），Python 的 `.format()` 将所有 `{}` 视为格式化占位符。

**教训**：当 Prompt 中包含 JSON 示例时，用 `.replace()` 而非 `.format()` 替换占位符。这个坑在方案文档中其实已埋下伏笔——方案里用了 `.format()`，但实际运行时才发现问题。

### 坑2：API 错误响应格式未处理

**现象**：DeepSeek API 返回错误时，代码直接取 `response.json()["choices"][0]` 导致崩溃。

**教训**：调用第三方 API 时，必须检查响应中是否有 `error` 字段，不能假设每次调用都成功。Agent 写出"正常路径"的代码很容易，但"异常路径"往往被人忽略。

### 坑3：防御性编程的边界

**现象**：`result["reply"]` 在某个代码路径下 dict 缺少 `reply` 键。

**教训**：在管道式架构中，每一层的输出应该被下一层"防御性地消费"——用 `.get()` 而非直接索引。这同样适用于 Agent 写代码的场景：Agent 容易假定上游一定返回某个字段。

## 三、给初学者的建议

### 3.1 开始前必须做的事

- [ ] 准备一份完整的实现方案文档（哪怕只是简单的阶段划分）
- [ ] 初始化 Git 仓库，`.gitignore` 排除 `node_modules`、`.env`、`__pycache__`、`*.db`
- [ ] 前后端都跑通一次"Hello World"再开始写业务代码

### 3.2 每次会话应该做的事

- [ ] 启动前后端，实际验证新功能是否生效
- [ ] 遇到错误时截个图给 Agent（比口头描述更高效）
- [ ] 每完成一个阶段就 Git commit（出问题可以回退）
- [ ] Bug 修复单独 commit（历史可追溯）

### 3.3 每次会话结束前应该做的事

- [ ] 让 Agent 整理工作进展，写入文件
- [ ] 文件包含：做了什么、文件在哪、怎么启动验证、下一步做什么
- [ ] 新会话第一条消息就引用这份进展文件

### 3.4 给 Agent 指令的要点

| 好的指令 | 不好的指令 |
|----------|-----------|
| "继续下一阶段"（在已有方案文档的上下文中） | "帮我做个聊天机器人" |
| 展示带错误信息的截图 | "报错了" |
| "先帮我提交git" | 一直不提交，到最后丢失代码 |
| "这些不应该提交，帮我去掉" | 不管不顾，敏感文件进了 Git |

### 3.5 本项目对应的五大原则

本文档与 SPORTS-ASSISTANT 案例中的五大原则一一对应：

| 原则 | 本项目体现 |
|------|-----------|
| 先上下文 | 用户给了完整实现方案 + 参考项目代码 |
| 先探讨 | 方案文档已做好架构决策，Agent 按方案执行 |
| 拆步骤 | 12个阶段，每次只做一个阶段 |
| 要验证 | 每个阶段做完前后端启动测试 |
| 存上下文 | 每次会话结束写入进展文件（本文档即为此目的） |

## 四、本次协同的指令风格评估

基于本次 Phase 0-3 的交互：

| 做得好 | 可改进 |
|--------|--------|
| 有完整的方案文档作为"北极星" | 遇到 Bug 时可以更早地描述"期望行为 + 实际行为" |
| 每阶段验证 + Git 提交 | 可以事先告知 Agent "做完后自己测试一下" |
| 用截图展示错误，信息准确 | — |
| 关键决策果断（如回退 .gitignore 修改） | — |

> **一句话记住**：方案文档是你的设计图，Agent 是施工队，Git 是你的安全网，阶段验证是你的竣工验收。
