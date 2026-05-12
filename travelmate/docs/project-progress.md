# TravelMate 项目进展 2026-05-11

## 今日完成

### 阶段零：搭建项目骨架，迁移核心服务（`5843d94`）

**目标**：从零搭建前后端项目结构，把已有参考项目的核心服务迁移过来。

**新增文件（37个，+6348行）**：

| 层级 | 文件 | 作用 |
|------|------|------|
| 前端 | `frontend/` 完整目录 | Vue 3 + Vite + TypeScript + Tailwind CSS + Pinia + Axios |
| 前端 | `src/api/client.ts` | Axios 实例，预留 X-Device-ID 拦截器 |
| 前端 | `src/App.vue` | 应用入口组件 |
| 后端 | `app/main.py` | FastAPI 入口，CORS 配置 |
| 后端 | `app/core/config.py` | 环境变量统一管理（API Key、数据库路径等） |
| 后端 | `app/models/schemas.py` | Pydantic 数据模型（行程、天气、地图等） |
| 后端 | `app/services/map_service.py` | 高德地图 API 封装（景点搜索、路线规划） |
| 后端 | `app/services/weather_service.py` | 天气 API 封装 |
| 后端 | `app/services/cache_service.py` | Redis 缓存服务封装 |
| 后端 | `app/services/export_service.py` | 行程导出为 PDF（ReportLab） |
| 后端 | `data/` | 5 份目的地攻略文档（成都/大理/三亚/厦门/西安） |
| 后端 | `requirements.txt` | Python 依赖清单 |
| 配置 | `.gitignore` | 排除 node_modules、__pycache__、.env、*.db、venv |
| 配置 | `.env.example` | 环境变量模板 |
| 文档 | `AI智游伴-完整实现方案.md` | 12 阶段完整实现方案（含目录结构、里程碑验收表） |

**关键决策**：
- 配置管理用 `os.getenv()` 而非 pydantic-settings，避免引入额外依赖
- 地图/天气/缓存/导出四个服务从参考项目迁移，接口不变，只调整导入路径

---

### 阶段一：前端对话界面基础（`573a8a4`）

**目标**：实现可用的聊天界面，前后端能收发消息。

**新增文件（7个，+375行）**：

| 文件 | 作用 |
|------|------|
| `frontend/src/types/chat.ts` | 消息数据模型（Message 接口定义） |
| `frontend/src/stores/chat.ts` | Pinia 聊天状态管理（消息列表、发送逻辑） |
| `frontend/src/components/chat/ChatContainer.vue` | 聊天主容器（消息列表 + 滚动） |
| `frontend/src/components/chat/MessageBubble.vue` | 消息气泡（支持 Markdown 渲染） |
| `frontend/src/components/chat/ChatInput.vue` | 输入框组件（回车发送） |
| `frontend/src/components/chat/TripCard.vue` | 行程卡片组件（预留，阶段六启用） |
| `frontend/src/utils/device.ts` | 设备 ID 生成与 localStorage 持久化 |

**修改文件**：
- `backend/app/api/chat.py` — 新增 `/chat` POST 端点（回显消息）
- `frontend/src/api/client.ts` — 添加 X-Device-ID 请求拦截器

**关键决策**：
- 设备识别用 localStorage 存储 UUID，每次请求通过 X-Device-ID Header 传给后端
- MessageBubble 使用 markdown-it 渲染 AI 回复中的 Markdown 格式

---

### 阶段二：后端 API 网关与数据库初始化（`0d9219e`）

**目标**：建立后端路由体系和 SQLite 数据库，为后续功能提供数据基础。

**新增文件（4个，+165行）**：

| 文件 | 作用 |
|------|------|
| `backend/app/models/database.py` | SQLite 初始化（创建 4 张表） |
| `backend/app/api/memory.py` | `/memory` 路由占位 |
| `backend/app/api/trip.py` | `/trip` 路由占位 |
| `backend/app/api/proactive.py` | `/proactive` 路由占位 |

**修改文件**：
- `backend/app/main.py` — 新增 lifespan 管理、路由注册、启动时 `init_db()`
- `backend/app/models/schemas.py` — 新增 ChatRequest/ChatResponse/IntentType 模型
- `backend/app/api/chat.py` — 使用统一 schema，device_id 移入请求体
- `frontend/src/stores/chat.ts` — device_id 通过请求体传递

**数据库结构（4张表）**：

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `devices` | 设备注册信息 | device_id, created_at |
| `conversations` | 对话历史 | device_id, message, reply, intent, timestamp |
| `user_preferences` | 用户偏好（记忆系统） | device_id, category, key, value, confidence |
| `trip_plans` | 行程计划 | device_id, destination, days, itinerary JSON |

**关键决策**：
- 数据库文件路径：`backend/data/travelmate.db`（与 chroma_memory 同级）
- `init_db()` 在 FastAPI lifespan 启动时自动调用，无需手动执行
- 占位路由先注册但不实现，保证前端调用不会 404

---

### 阶段三：三层意图识别管道（`14a38be`，完成并修复）

**新增文件（4个）**：
- `backend/app/services/regex_matcher.py` — 第一层正则快速匹配（问候/告别/感谢/确认，>50字自动跳过）
- `backend/app/services/llm_client.py` — DeepSeek API 异步调用封装，含错误响应处理
- `backend/app/utils/safety.py` — 输入/输出安全检查（BLOCK/WARN/URGENT 三级）
- `backend/app/services/intent_router.py` — 完整意图管道（安全→正则→AI→安全）

**修改文件**：
- `backend/app/api/chat.py` — 集成 intent_router，返回意图+元数据
- `backend/app/core/config.py` — 新增 DEEPSEEK_API_KEY/BASE_URL/MODEL 配置

### 阶段三 Bug 修复（`4c316a4`，4个运行时错误）

| Bug | 原因 | 修复方式 |
|-----|------|----------|
| `KeyError: '\n  "intent"'` | Prompt 模板中 JSON 示例的 `{}` 被 `.format()` 误解析 | `.format()` → `.replace()` |
| `KeyError: 'reply'` | AI 路径返回的 dict 缺少 reply 字段 | AI 返回路径补充 reply 字段 |
| DeepSeek 错误响应 KeyError | 直接取 `choices[0]` 未检查 error 字段 | 增加 error/choices 字段检查 |
| chat.py 崩溃 | `result["reply"]` 硬访问 | 改为 `result.get("reply", fallback)` |

## 当前项目状态

### Git 提交记录

```
e4fbfc2  阶段四文档：项目进展记录与 ChromaDB 环境问题排查全过程
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
| 后端 | 记忆系统：SQLite + ChromaDB 双写（语义检索 + 回退） | ✅ 已验证 |
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

### 阶段四：Hermes 记忆系统（`3fb08d6` + `23d33d9`，环境验证完成）

**代码变更**：

| 提交 | 内容 | 文件 |
|------|------|------|
| `3fb08d6` | 纯 SQLite 记忆实现（写入/读取/删除/模糊检索） | `memory_service.py`（新增）、`memory.py`（实现端点）、`intent_router.py`（PREFERENCE 自动写入） |
| `c7633da` | 修复 requirements.txt 中文注释导致 pip GBK 解码失败 | `requirements.txt` |
| `23d33d9` | 升级为 ChromaDB + SQLite 双写，语义检索替代 LIKE | `memory_service.py`（重写）、`requirements.txt`（加 chromadb） |

> Phase 4 代码在上次会话中已提交（`23d33d9`），但 ChromaDB 的 ONNX 向量模型尚未下载，
> 语义检索实际回退到 SQLite LIKE。本次会话的核心任务是让 ChromaDB 真正生效。

**遇到的三个环境问题及解决方案：**

| # | 问题 | 现象 | 原因 | 解决方案 |
|---|------|------|------|----------|
| 1 | onnxruntime DLL 加载失败 | `ImportError: DLL load failed while importing onnxruntime_pybind11_state` | 项目 venv 由 Anaconda Python 3.12 创建，onnxruntime 编译时的 VC++ 运行时与 Anaconda 不匹配 | 用 `D:\Python\python.exe`（3.11.8）重建 venv，重新安装依赖 |
| 2 | ONNX 模型下载极慢 | S3 源下载速度仅 ~20KB/s，79MB 预计 1 小时+ | `chroma-onnx-models.s3.amazonaws.com` 在国内延迟高，与 VPN 无关 | 用 HuggingFace 国内镜像（hf-mirror.com）下载，手动放入 `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/` |
| 3 | 新 venv 中 SQLite 表不存在 | `sqlite3.OperationalError: no such table` | 重建环境后数据库文件为空，未自动初始化 | 正常启动 uvicorn 即可，`app.main` 的 lifespan 自动调用 `init_db()` |

**验证结果（ChromaDB 语义检索 vs SQLite LIKE）：**

```
搜索 "price"         → ChromaDB 找到「每日预算: 500元」 ✅  |  SQLite LIKE 返回 [] ❌
搜索 "accommodation"  → ChromaDB 找到「类型: 喜欢民宿」   ✅  |  SQLite LIKE 返回 [] ❌
搜索 "辣"            → 两者均找到「忌口: 不吃辣」         ✅  |  （字面匹配，两者等价）
```

结论：ChromaDB 能跨语言理解语义（英文 price 匹配中文"每日预算"），SQLite LIKE 只做子串匹配。

**端到端功能验证清单（全部通过）：**

| 测试内容 | 输入 | 预期行为 | 结果 |
|----------|------|----------|------|
| 正则秒回 | `你好` | 不调用 LLM，瞬间返回问候语 | ✅ |
| 安全拦截 | `怎么偷东西` | 拒绝请求，返回安全话术 | ✅ |
| 偏好写入 | `我不吃辣` | AI 识别 PREFERENCE → 写入记忆 → 回复"已记住" | ✅ |
| 重复偏好更新 | 再次说`我不吃辣` | 更新已有记录，confidence 递增 | ✅ |
| 意图识别 | `我想去杭州玩3天` | AI 识别为 TRIP_PLAN | ✅ |
| 语义检索 | `GET /memory/{id}/query?q=price` | ChromaDB 命中"每日预算" | ✅ |
| 记忆上下文 | 存入偏好后规划行程 | AI 的 reasoning 参考了历史偏好 | ✅ |

---

## 关键决策记录

- **DEC-001**: 配置管理用 `os.getenv()` 而非 pydantic-settings，避免引入额外依赖
- **DEC-002**: LLM 客户端使用 httpx 异步，温度 0.1（意图识别需稳定输出）
- **DEC-003**: 意图识别 Prompt 中的 JSON 示例使用 `{user_message}` 占位符 + `.replace()` 替换，避免 `.format()` 与 JSON 花括号冲突
- **DEC-004**: 大于 50 字符的消息跳过正则层直接进 AI 层
- **DEC-005**: 项目 venv 使用 `D:\Python`（3.11.8）而非 Anaconda，确保 onnxruntime DLL 兼容
- **DEC-006**: ONNX 模型通过 HuggingFace 国内镜像下载，手动放置到 ChromaDB 缓存目录，避免 S3 慢速问题
- **DEC-007**: ChromaDB 缓存目录统一放在 `~/.cache/chroma/onnx_models/`，不在项目内，便于跨项目复用

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

---

# 第二次会话协同经验（Phase 4 环境验证）

> 本次会话的核心不是写新代码，而是"让已有代码在真实环境中跑通"——这恰恰是初学者最容易卡住的环节。

## 一、本次会话做了什么

上次会话完成了 ChromaDB + SQLite 双写代码并提交，但 ONNX 向量模型未下载，语义检索实际是假的（回退到 SQLite LIKE）。本次会话用全部时间解决了三个环境问题，最终让 ChromaDB 余弦相似度检索真正生效，并完成了端到端验证。

**没有一行业务代码变更**，但这是项目从"能跑"到"跑对了"的关键一步。

## 二、本次协同与上次的关键区别

### 上次会话（Phase 0-3）：从零写代码

| 特征 | 具体表现 |
|------|----------|
| 工作内容 | 按方案文档逐阶段实现新功能 |
| Agent 输出 | 大量新文件、新代码 |
| 用户指令风格 | "继续下一阶段"（宏观指令） |
| 验证方式 | 功能是否能用（黑盒） |

### 本次会话（Phase 4 验证）：排查环境问题

| 特征 | 具体表现 |
|------|----------|
| 工作内容 | 诊断、调试、验证已有代码 |
| Agent 输出 | 少量配置变更，大量排查过程 |
| 用户指令风格 | "怎么验证区别"（精确问题） |
| 验证方式 | 对比测试 + 数据对比（白盒） |

**启示**：写代码和调代码是两种完全不同的技能，初学者往往低估后者的工作量。

## 三、踩过的坑（给初学者的环境问题清单）

### 坑 1：Python 环境不等于"装了 Python"

**现象**：`onnxruntime DLL load failed`，代码本身没有任何问题。

**根因**：电脑上有两个 Python——Anaconda 自带的 3.12 和独立安装的 3.11。`pip install onnxruntime` 安装的是针对当前 Python 编译的版本，换一个 Python 运行就会 DLL 不兼容。

**教训**：
- Python 环境不是"全局的"，每个 venv 绑定一个特定的 Python 解释器
- 同一台电脑装多个 Python 时，务必确认 venv 用的是哪一个
- 验证方法：`venv/Scripts/python --version` 和 `venv/Scripts/python -c "import sys; print(sys.executable)"`

**给 Agent 的指令技巧**：
- 不要说"报错了"，贴完整的错误信息（截图或复制文本）
- 错误信息中的关键行（如 `ImportError: DLL load failed`）比上下文更重要

### 坑 2：第三方库的"首次运行下载"陷阱

**现象**：ChromaDB 代码能跑，但语义检索结果和 SQLite LIKE 一样——因为模型没下载。

**根因**：ChromaDB 使用 ONNX 嵌入模型生成向量，这个模型（79MB）不在 pip 包里，首次运行时才从 S3 下载。在国内，S3 下载极慢，用户很容易以为"卡死了"而中断。

**教训**：
- 很多 AI/ML 库有"首次运行下载"行为（ChromaDB、Transformers、sentence-transformers 都有）
- 遇到下载慢，先排除 VPN 问题，再考虑镜像源
- HuggingFace 国内镜像 `hf-mirror.com` 是可靠的备选

**给 Agent 的指令技巧**：
- 不要说"下不下来"，告诉 Agent 当前速度和已等待时间
- 可以主动提出"能不能手动下载放到对应目录"——这往往是最快的解法

### 坑 3：环境重建后"之前能跑的不能跑了"

**现象**：重建 venv 后，`save_memory` 报 `no such table`。

**根因**：新 venv 没有自动初始化数据库（表不存在）。但正常启动 uvicorn 后，`app.main` 的 lifespan 会自动调用 `init_db()`。

**教训**：
- 重建环境 ≠ 只装依赖，数据库、缓存等持久化状态也需要确认
- 框架的启动钩子（如 FastAPI lifespan）往往承担初始化职责，别手动重复

## 四、验证阶段的协同方法论

### 4.1 如何向 Agent 描述"我想验证什么"

| 好的描述 | 不好的描述 |
|----------|-----------|
| "怎么验证 ChromaDB 和之前 SQLite 的区别" | "测试一下" |
| "我想看到具体的数据对比" | "看看对不对" |
| "输入 price 能不能找到每日预算" | "语义检索能用吗" |

**核心原则**：告诉 Agent 你想看到什么**具体结果**，而不是问它"对不对"。

### 4.2 验证时 Agent 应该提供什么

一个好的验证方案应该包含：

1. **明确的输入**：用户应该输入什么（精确到每个字符）
2. **明确的预期**：正确的输出长什么样（不能只说"成功"）
3. **判断标准**：怎么区分"通过"和"失败"
4. **对比基线**：和什么比（新旧行为对比最有说服力）

### 4.3 本次会话中有效的协同模式

```
用户：怎么验证区别？
Agent：写对比测试脚本 → 运行 → 展示结果
用户：（看到结果后）提交 git，详细说明问题和解决方案
Agent：写详细 commit message → 提交
用户：整理会话记录，给小白学习
Agent：写文档
```

**模式**：`提出精确问题 → Agent 执行 → 用户确认 → 记录沉淀`

这比上次的"继续下一阶段"更高效，因为每一步的目标都是明确的。

## 五、给初学者的环境问题排查清单

遇到"代码没错但跑不起来"时，按以下顺序排查：

```
1. Python 版本对不对？
   → venv/Scripts/python --version
   → venv/Scripts/python -c "import sys; print(sys.executable)"

2. 依赖装全了没？
   → pip list | grep <包名>
   → pip install -r requirements.txt

3. 数据库/缓存初始化了没？
   → 检查 data/ 目录下有没有 .db 文件
   → 检查 ~/.cache/chroma/ 下有没有模型文件

4. 第三方服务连得上没？
   → DeepSeek API：curl 测试
   → ChromaDB 模型：首次运行会自动下载，看日志有没有报错

5. 端口被占用没？
   → netstat -ano | grep 8000
```

## 六、本次会话的指令风格评估

| 做得好 | 可改进 |
|--------|--------|
| "怎么验证区别" — 精确的验证目标 | 一开始没有明确说"我想看数据对比"，Agent 需要追问 |
| "提交 git，详细说明问题和解决方案" — 明确的交付要求 | — |
| "整理会话记录给小白学习" — 明确的受众和目的 | — |
| 遇到问题时提供了完整的错误信息（截图/文本） | — |

> **一句话记住**：写完代码只是完成了一半，让代码在真实环境跑通才是另一半——而后者往往花更多时间。

---

# 第三次会话协同记录（Phase 5-12 + 对话上下文）

> 本次会话从阶段五一路推进到阶段十二（最终交付），并在交付后继续实现了对话上下文与记忆连贯性功能。过程中遇到了大量实际 Bug，调试过程极具学习价值。

## 一、Phase 5-12 完成概览

| 阶段 | 提交 | 核心内容 | 关键技术 |
|------|------|----------|----------|
| 阶段五 | — | 天气 API + 景点知识集成 | 和风天气 API、RAG 知识检索 |
| 阶段六 | — | 行程规划服务 | LLM 生成行程、结构化输出 |
| 阶段七 | `ae19d38` | RAG 景点知识服务 | ChromaDB 向量检索 + LLM 导游式回答 |
| 阶段八 | `b8bf6b0` | 主动服务推送 | WebSocket 实时连接、APScheduler 定时提醒 |
| 阶段九 | `d76a46d` | 前端-后端业务大串联 | 消息类型分支（card/weather/knowledge）、卡片渲染 |
| 阶段十 | `a092fd0` | 安全系统完善 | 三级拦截（BLOCK/WARN/URGENT）、输出过滤、频率限制 |
| 阶段十一 | `f38fd1c` | 语音交互 | Web Speech API 语音输入、SpeechSynthesis TTS 播报 |
| 阶段十二 | `2dd44b9` | 联调优化、测试与部署 | E2E 测试、移动端适配、性能优化、UX 打磨 |
| 对话上下文 | `89cf729` | 多轮对话 + 智能摘要 | 历史上下文加载、摘要压缩、正则预拦截 |

---

## 二、重点 Bug 调试记录

### Bug 1：APScheduler 环境问题（阶段八）

**现象**：启动 uvicorn 后报 `ModuleNotFoundError: No module named 'apscheduler'`

**原因**：终端处于 conda base 环境，但 uvicorn 使用的是 `D:\Python` 下的独立 Python，两个环境的包不互通。

**解决**：
```bash
D:\Python\python.exe -m pip install apscheduler
```

**教训**：多 Python 环境时，安装依赖必须用实际运行 uvicorn 的那个 Python。

---

### Bug 2：WARN/URGENT 安全提醒不显示（阶段十）

**现象**：输入"我想一个人去偏远地区旅行"，应该显示安全警告，但回复中没有任何提醒。

**排查过程**：

1. 截图显示回复是 AI 的 raw reasoning（"意图分析..."），不是正常回复 → CHAT 分支返回了 `reasoning` 而非 `reply`
2. 修复后回复正常了，但安全提醒仍然不显示

**三个根因逐一修复**：

| # | 根因 | 修复 |
|---|------|------|
| 1 | CHAT else 分支直接返回 `reasoning` 字段作为 reply | 改为调用 LLM 生成自然回复 |
| 2 | return dict 中 `safety` 使用了 `output_safety`（每次都是 SAFE），覆盖了输入安全检查的结果 | 改为使用输入阶段的 `safety` |
| 3 | 前端 TripCard 组件没有 `safetyWarning` prop | 新增 prop 并在卡片顶部显示警告横幅 |

**教训**：
- 管道式架构中，每个阶段的状态（如 safety level）必须完整传递到最终输出，不能被中间步骤覆盖
- 前端组件的 prop 设计要和后端 metadata 字段一一对应

---

### Bug 3：语音识别有时能用有时不能（阶段十一）

**现象**：点击麦克风按钮，有时正常识别，有时无反应。

**排查过程**：

用户报告"我把微信后台关了，他就正常了"。

**原因**：微信桌面版占用了麦克风资源，Web Speech API 无法获取音频输入。

**教训**：Web Speech API 依赖系统麦克风，其他应用占用麦克风时会静默失败。测试语音功能时确保没有其他录音应用在运行。

---

### Bug 4：对话上下文重复保存（对话上下文功能）

**现象**：用户说"你好"后，对话历史里出现两条相同的用户消息。

**排查过程**：

查看 `chat.py` 代码，发现 `save_message` 在 `route_intent` 之前调用，而 `route_intent` 内部的某些分支（如 PREFERENCE）也会保存消息，导致重复。

**修复**：将 `save_message` 移到 `route_intent` 之后，只在处理完成后保存一次。

**教训**：消息保存应该遵循"处理后写入"原则，在意图管道完成后再保存，避免管道内部的副作用导致数据不一致。

---

### Bug 5："我叫小明"被误存为旅行偏好（对话上下文功能）

**现象**：用户说"你好，我叫小明"，AI 把"小明"识别为 PREFERENCE，回复"已记住你的偏好：小明"。

**排查过程**：

1. **第一轮修复**：添加 `personal_keys` 排除列表（名字、年龄、职业等），在 PREFERENCE 保存前检查 key 是否在列表中
2. **第二轮修复**：`elif` 分支陷阱——把 `intent = "CHAT"` 写在 elif 里，导致 else（CHAT 处理器）被完全跳过，reply 未赋值
3. **第三轮修复**：DeepSeek 对"我叫小明"和"你还记得我吗"都过度分类为 PREFERENCE，personal_keys 无法穷举所有提取词
4. **最终修复**：在 AI 调用前用正则预拦截（`我(叫|是|的名字)`、`你还?记得`），完全绕过 AI 意图识别

**关键代码**：
```python
# 模块级别预编译
_INTRO_RE = re.compile(r"我(叫|是|的名字)")
_RECALL_RE = re.compile(r"(你还?记得|之前.*说过|刚才.*说过|上回.*说过)")

# 在 AI 调用前拦截
if _INTRO_RE.search(user_message) or _RECALL_RE.search(user_message):
    intent = "CHAT"  # 直接走闲聊，不调 AI
else:
    # 才进入 AI 意图识别
```

**教训**：
- **elif 分支陷阱**：在条件分支中修改变量后跳转，必须确保目标分支能被执行。如果用 elif 连接，修改 intent 后不能 fall through 到 else
- **正则预拦截比修补 AI 分类更可靠**：对于明确的模式（自我介绍、回忆问题），用正则 100% 拦截，比依赖 AI 分类更稳定

---

### Bug 6：LLM 复读历史脏数据（对话上下文功能）

**现象**：Edge 浏览器中，用户说"你好，我叫小明"，LLM 回复"好的，已记住你的偏好：小明"——和之前错误回复一模一样。

**排查过程**（最精彩的一个）：

1. **加日志验证**：在 `intent_router.py` 中加 `print()` 调试输出（`logger.info` 被 logging 配置过滤了，看不到）
2. **日志结果**：
   ```
   [DEBUG] intro=True recall=False
   [DEBUG] 模式拦截触发 → CHAT
   [DEBUG] CHAT handler: history_len=10
   [DEBUG] LLM 原始回复: '好的，已记住你的偏好：小明。之后的推荐会参考它～'
   ```
3. **关键发现**：拦截成功了（`intro=True`），intent 确实是 CHAT，但 **LLM 看到历史里有旧的错误回复就直接复读了**

**根因**：Edge 浏览器的设备 ID 累积了 54 条旧对话记录（含之前的错误 PREFERENCE 回复），LLM 上下文里有这条回复就直接照搬。

**修复**：
1. 清除 Edge 设备的旧对话数据
2. 实现摘要压缩机制：超过 30 条自动摘要旧消息，避免脏数据长期污染

**教训**：
- **LLM 是"鹦鹉"**：它会参考上下文中的回复模式，如果历史里有错误回复，它可能会复读
- **数据清理是调试的一部分**：代码修好了不代表问题解决了，数据库里的脏数据仍在影响行为
- **logger.info 不一定能看到**：Python logging 配置可能过滤 INFO 级别，调试时优先用 `print(flush=True)`

---

### Bug 7：代词消解——"那附近有什么好吃的"（对话上下文功能）

**现象**：用户先问"西湖有什么好玩的"，然后问"那附近有什么好吃的"，AI 回复"请问你想了解哪个景点"——没有理解"那"指代西湖。

**修复**：在 KNOWLEDGE 分支中，当没有提取到关键词时，从对话历史中用 LLM 提取最近提到的景点/城市名称：

```python
if not keyword:
    history = await get_recent_history(device_id)
    resolve_prompt = "从以下对话历史中提取最近提到的景点或城市名称，只返回名称。"
    hist_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    resolved = await call_llm(
        messages=[{"role": "user", "content": f"历史：{hist_text}\n当前：{user_message}"}],
        system_prompt=resolve_prompt,
        temperature=0.0, max_tokens=50,
    )
    keyword = resolved.strip() if resolved.strip() != "无" else ""
```

**教训**：代词消解（"那"、"那里"、"它"）是多轮对话的核心难题，最实用的方案是用 LLM 从历史中提取指代对象，而非维护复杂的规则引擎。

---

## 三、多浏览器设备 ID 问题

**现象**：VSCode 内置浏览器测试正常，复制链接到 Edge 浏览器测试就出错。

**排查**：

1. 两个浏览器各有独立的 `localStorage`，生成不同的 `device_id`
2. Edge 浏览器的设备 ID 有旧的脏数据（54 条），VSCode 浏览器是干净的
3. 后端是同一个，但不同设备 ID 的对话历史完全不同

**关键代码**（`frontend/src/utils/device.ts`）：
```typescript
export function getDeviceId(): string {
  let deviceId = localStorage.getItem('travelmate_device_id')
  if (!deviceId) {
    deviceId = 'dev_' + crypto.randomUUID()
    localStorage.setItem('travelmate_device_id', deviceId)
  }
  return deviceId
}
```

**教训**：
- 每个浏览器的 localStorage 是独立的，测试多浏览器时要注意 device_id 不同
- 调试时如果怀疑设备 ID 问题，可以在后端日志中查看 `device=` 字段确认

---

## 四、对话历史摘要压缩机制

### 设计原理

| 阈值 | 行为 |
|------|------|
| 消息 ≤ 30 条 | 全部原文返回 |
| 消息 > 30 条 | 旧消息自动摘要 + 最近 20 条原文 |
| 摘要缓存 | 消息数变化 < 5 条时复用旧摘要，避免重复调用 LLM |

### 关键文件

`backend/app/services/context_service.py`：
- `save_message()` — 保存单条消息（同步）
- `get_recent_history()` — 异步获取对话历史，支持自动摘要

### 摘要流程

```
用户发消息
  ↓
get_recent_history() 被调用
  ↓
消息数 ≤ 30？ → 是 → 返回全部原文
  ↓ 否
取最近 20 条原文
  ↓
摘要缓存有效？ → 是 → 用缓存摘要
  ↓ 否
从数据库取旧消息 → 发给 LLM 生成摘要 → 缓存
  ↓
返回 [摘要消息] + [最近 20 条原文]
```

### MAX_HISTORY 选择

| 值 | 约对话轮数 | 占用 tokens | 适用场景 |
|----|-----------|-------------|----------|
| 10 | 5 轮 | ~500 | 极简场景 |
| 20 | 10 轮 | ~1,000 | 轻量对话 |
| **50** | **25 轮** | **~2,500** | **本项目选用** |
| 100 | 50 轮 | ~5,000 | 深度对话 |

DeepSeek 上下文窗口 128K tokens，50 条消息约 2500 tokens，占比 2%，留有充足空间给系统 prompt 和回复。

---

## 五、本次会话踩坑总结（给初学者）

### 坑1：elif 分支修改变量后不能 fall through

```python
# ❌ 错误写法
if intent == "PREFERENCE" and key in personal_keys:
    intent = "CHAT"  # 改了 intent
elif intent == "TRIP_PLAN":
    ...
else:
    # 这里不会执行！因为上面的 elif 已经匹配了
    # 虽然 intent 改成了 CHAT，但 else 是和 elif 平级的
```

```python
# ✅ 正确写法：预处理 + 主链
if intent == "PREFERENCE" and key in personal_keys:
    intent = "CHAT"  # 先改

if intent == "PREFERENCE":      # 用 if 而非 elif
    ...
elif intent == "TRIP_PLAN":
    ...
else:                           # intent="CHAT" 能正确走到这里
    ...
```

**关键理解**：Python 的 if/elif/else 是"互斥分支"，一旦某个分支被执行，后面的 elif/else 全部跳过。在分支中修改控制变量不会影响当前的分支选择。

### 坑2：logger.info 看不到输出

```python
# ❌ 调试时
logger.info("[DEBUG] something happened")  # 可能被 logging 配置过滤

# ✅ 调试时
print(f"[DEBUG] something happened", flush=True)  # 一定能看到
```

**原因**：uvicorn 的 logging 配置默认只输出 WARNING 及以上级别，`logger.info` 被静默过滤。

**最佳实践**：开发调试用 `print(flush=True)`，上线前删除。`flush=True` 确保输出立即显示，不被缓冲。

### 坑3：LLM 会复读历史中的错误回复

LLM 处理对话时，会将历史消息作为上下文。如果历史中包含系统之前给出的错误回复，LLM 可能会模仿或复读那个模式。

**应对策略**：
1. 及时清理数据库中的脏数据
2. 实现摘要压缩，让旧消息逐渐"淡出"
3. 在系统 prompt 中明确指示"基于事实回答，不要模仿历史回复格式"

### 坑4：多浏览器测试时 localStorage 独立

每个浏览器实例有独立的 localStorage，生成不同的 device_id。测试时要注意：
- 同一个浏览器的不同标签页共享 device_id
- 不同浏览器的 device_id 不同，对话历史也不同
- 调试时在后端日志中确认 device_id 是否符合预期

### 坑5：正则预拦截优于修补 AI 分类

当 AI 意图分类不准确时，有两个修复方向：

| 方向 | 做法 | 优劣 |
|------|------|------|
| 修补 AI | 调整 prompt、扩大排除列表 | 治标不治本，AI 可能换一种方式误分类 |
| 正则预拦截 | 用正则匹配明确模式，绕过 AI | 100% 确定性，不依赖 AI 理解 |

**结论**：对于模式明确的输入（自我介绍、回忆问题、紧急求助），正则预拦截是最可靠的方案。AI 意图识别留给真正需要理解语义的场景。

---

## 六、完整的调试方法论

本次会话中最精彩的一次调试（Bug 6：LLM 复读脏数据）展示了完整的排查流程：

```
现象：Edge 浏览器回复错误
  ↓
假设1：代码没生效 → 检查代码 ✓ 已修改
  ↓
假设2：后端没重启 → 重启后仍然错误
  ↓
假设3：有多个后端在跑 → netstat 检查，只有一个
  ↓
假设4：拦截没触发 → 加 print 日志验证
  ↓
日志显示：拦截确实触发了，intent=CHAT
  ↓
假设5：CHAT 处理器有问题 → 加 print 看 LLM 返回值
  ↓
关键发现：LLM 原始回复就是错误内容！
  ↓
根因：历史数据中有旧的错误回复，LLM 照搬了
  ↓
修复：清库 + 摘要压缩机制
```

**核心方法**：不要猜，用日志验证。每一层假设都要有实际证据支撑。

---

## 七、项目最终状态

### Git 提交记录（完整）

```
89cf729  对话上下文与记忆连贯性：多轮对话支持 + 智能摘要压缩
2dd44b9  阶段十二：联调优化、测试与部署（最终交付）
f38fd1c  阶段十一：语音交互（Web Speech API 语音输入 + TTS 播报）
a092fd0  阶段十：安全系统完善（三级拦截 + 输出过滤 + 频率限制）
d76a46d  阶段九：前端-后端业务大串联（WebSocket + 消息类型分支 + 卡片渲染）
b8bf6b0  阶段八：主动服务（WebSocket 推送 + APScheduler 定时提醒）
ae19d38  阶段七：RAG 景点知识服务（ChromaDB 向量检索 + LLM 导游式回答）
e4fbfc2  阶段四文档：项目进展记录与 ChromaDB 环境问题排查全过程
23d33d9  阶段四：记忆系统升级为 ChromaDB + SQLite 双写
c7633da  修复 requirements.txt 中文注释导致 pip GBK 解码失败
3fb08d6  阶段四：Hermes 记忆系统（纯 SQLite 实现）
4c316a4  修复阶段三意图识别管道三个运行时错误
14a38be  阶段三：三层意图识别管道
0d9219e  阶段二：后端 API 网关与数据库初始化
573a8a4  阶段一：前端对话界面基础
5843d94  阶段零：搭建项目骨架，迁移核心服务
```

### 已完成模块（更新）

| 层级 | 模块 | 状态 |
|------|------|------|
| 前端 | Vue 3 + Vite + TypeScript + Tailwind CSS + Pinia + Axios | ✅ |
| 前端 | 聊天界面（ChatContainer / MessageBubble / ChatInput / TripCard） | ✅ |
| 前端 | 语音输入（Web Speech API，continuous 模式） | ✅ |
| 前端 | TTS 播报（SpeechSynthesis，Markdown 去除） | ✅ |
| 前端 | WebSocket 实时连接 + 主动消息推送 | ✅ |
| 前端 | 移动端响应式适配 | ✅ |
| 后端 | FastAPI + CORS + 路由体系 | ✅ |
| 后端 | SQLite 数据库（5 张表） | ✅ |
| 后端 | 三层意图识别（安全→正则→AI）+ 正则预拦截 | ✅ |
| 后端 | 天气 API / 地图 API / RAG 知识检索 | ✅ |
| 后端 | 行程规划服务（LLM 生成） | ✅ |
| 后端 | 安全系统（三级拦截 + 输出过滤 + 频率限制） | ✅ |
| 后端 | 记忆系统（SQLite + ChromaDB 双写） | ✅ |
| 后端 | 对话上下文（历史加载 + 摘要压缩） | ✅ |
| 后端 | WebSocket 推送 + APScheduler 定时提醒 | ✅ |

---

## 八、三次会话协同模式对比

| 维度 | 第一次（Phase 0-3） | 第二次（Phase 4 验证） | 第三次（Phase 5-12 + 上下文） |
|------|---------------------|----------------------|-------------------------------|
| 工作类型 | 从零写代码 | 排查环境问题 | 功能开发 + 深度调试 |
| Bug 数量 | 4 个运行时错误 | 3 个环境问题 | 7+ 个逻辑 Bug |
| 调试深度 | 浅（改代码即可） | 中（需理解环境） | 深（需追踪数据流） |
| 关键技能 | 按方案执行 | 环境排查 | 端到端追踪 + 日志验证 |
| 用户参与度 | 低（"继续下一阶段"） | 中（展示截图） | 高（持续反馈 + 验证） |

**最大教训**：随着项目复杂度增加，Bug 的排查难度指数级上升。阶段三的 Bug 改一行代码就好，阶段十的 Bug 需要同时改前后端三个文件，对话上下文的 Bug 需要追踪从正则→AI→LLM→数据库→前端的完整链路。

> **一句话记住**：代码越复杂，调试越需要系统性思维——不是"哪里报错改哪里"，而是"数据从哪里来，经过了什么变换，在哪里出了问题"。

---

# 第四次会话协同记录（P0-P3 优化方案实施 + Bug 修复）

> 本次会话从《AI智游伴-完整实现方案.md》的 13 个优化模块审计开始，逐个实施缺失功能，
> 并在实施和用户测试过程中修复了 7 个真实 Bug。涵盖了从 UI 细节到后端架构的全栈改动。

## 一、优化方案审计与实施概览

### 1.1 审计结果

对完整实现方案的 13 个模块逐个比对代码，确认：
- **13 个核心模块全部到位**（P0-P3 优化方案）
- **3 个 P3 子项缺失**：会话重命名 UI、动态 placeholder 轮播、消息滑入动画
- **4-5 个 UI 细节缺失**：批量扩充弹窗、知识纠正闭环等

### 1.2 实施的 6 个缺失功能（commit `a349483`）

| 功能 | 文件 | 核心实现 |
|------|------|----------|
| 会话重命名 UI | `SessionSidebar.vue`、`chat.ts` | 双击标题进入编辑，Enter 提交/Escape 取消，hover 显示编辑+删除按钮 |
| 动态 placeholder 轮播 | `ChatInput.vue` | 5 条提示语 5 秒间隔轮播，`setInterval` + `onUnmounted` 清理 |
| 消息滑入动画 | `style.css`、`MessageBubble.vue` | `@keyframes msgSlideIn` + `.msg-slide-in` 类 |
| 批量扩充知识库弹窗 | `BatchExpandModal.vue`、`ChatContainer.vue` | 完整 Modal 组件 + SSE 流式进度 + 15 个预设景点 |
| 批量扩充后端 API | `knowledge.py` | `POST /knowledge/auto-expand-batch` + `StreamingResponse` SSE |
| 用户反馈纠正闭环 | `knowledge_expander.py`、`intent_router.py` | 正则检测纠正意图 → LLM 提取纠正信息 → 修改文件 → 重新向量化 |

### 1.3 暗色模式持久化与重启检测（commit `7fcefae`）

| 改动 | 文件 | 内容 |
|------|------|------|
| 暗色模式同步初始化 | `App.vue` | `initDark()` 同步读 localStorage，消除 `onMounted` 异步导致的闪白 |
| 后端重启检测 | `main.py`、`App.vue` | `_STARTUP_TS` 模块级变量 + `GET /startup-ts` 接口，前端 onMounted 比对时间戳 |
| 批量扩充 URL 修复 | `BatchExpandModal.vue` | `/api/knowledge/...` → `http://localhost:8000/knowledge/...`（fetch 不走 axios） |

### 1.4 行程方案持久化（commit `1698311`）

**问题**：生成 TripCard 后刷新页面，结构化卡片降级为纯文本。

**全链路修复（7 个文件）**：

| 层级 | 文件 | 改动 |
|------|------|------|
| DB schema | `database.py` | `ALTER TABLE conversations ADD COLUMN metadata TEXT`（增量迁移） |
| 存储函数 | `context_service.py` | `save_message()` 新增 `metadata` 参数，dict → JSON |
| API 端点 | `chat.py` | assistant 消息存储时传入 `metadata=metadata` |
| 查询返回 | `sessions.py` | SELECT 加 `metadata` 列，JSON 反序列化返回 |
| 前端加载 | `chat.ts` | `switchSession` 按 intent 映射 type + 传递 metadata |
| 渲染判断 | `ChatContainer.vue` | `isTripCard` 加严为 `type + role + trip_plan` 三重条件 |

### 1.5 会话智能命名 + 意图识别上下文感知（commit `2ea51fd`）

**会话命名**：
- `sessions.py` 新增 `update_session_title()` 公共函数
- `chat.py` 自动命名逻辑：首条消息 → 截取消息内容；行程方案生成 → "目的地·N日游"
- `SessionSidebar.vue` 时间改为 HH:MM 格式，去掉消息条数显示

**意图识别上下文感知**：
- `intent_router.py` 的 `INTENT_RECOGNITION_PROMPT` 新增 `{recent_context}` 占位符
- `route_intent` 调 AI 前取最近 6 条对话历史注入 prompt
- 新增"上下文延续"优先级规则，LLM 看到上文问天气 → 用户回复地名 → 正确返回 WEATHER

---

## 二、7 个 Bug 详细调试记录

### Bug 1：批量扩充弹窗"开始扩充"按钮点击后闪退

**现象**：点击"开始扩充"按钮，弹窗闪了一下就消失了，没有显示进度。

**排查过程**：

1. 用户截图显示弹窗消失，无错误提示
2. 检查 `BatchExpandModal.vue` 的 `startBatchExpand()` 函数
3. 发现 `fetch()` 使用了相对路径 `/api/knowledge/auto-expand-batch`

**根因**：Vue 项目中 `fetch()` 是原生 Web API，不走 axios 实例。axios 配置了 `baseURL: 'http://localhost:8000'`，但 `fetch()` 完全独立，相对路径会请求 `localhost:5173`（前端 dev server），返回 404。

**修复**：
```typescript
// 之前（错误）
const res = await fetch('/api/knowledge/auto-expand-batch', { ... })

// 之后（正确）
const API_BASE = 'http://localhost:8000'
const res = await fetch(`${API_BASE}/knowledge/auto-expand-batch`, { ... })
```

同时增加了 `res.ok` 检查和红色错误横幅 `fetchError`，让连接失败时用户能看到具体原因。

**教训**：`fetch()` vs `axios` 是 Vue 项目中常见的遗漏点——两者是完全独立的网络层，axios 的 `baseURL`、拦截器等配置对 `fetch()` 无效。

---

### Bug 2：暗色模式刷新页面后偏好丢失

**现象**：设置为暗色模式后刷新页面，自动变回浅色。

**排查过程**：

1. 初始实现用 `onMounted` 异步读 localStorage
2. 但 `ref(false)` 初始化后，`watchEffect` 立即执行，把 `false` 写入 localStorage
3. `onMounted` 回调到达时，localStorage 已被覆盖为 `false`

**根因**：Vue 的 `onMounted` 是异步触发的。`ref()` 初始化 → `watchEffect` 立即执行写入 `false` → `onMounted` 读取时已是 `false`。

**修复**：同步函数 `initDark()` 在 `ref()` 初始化时立即读取 localStorage，不依赖任何异步钩子：
```typescript
function initDark(): boolean {
  const stored = localStorage.getItem('travelmate_dark')
  if (stored !== null) return stored === 'true'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}
const dark = ref(initDark())  // 同步读取，无时序问题
```

**教训**：`ref()` 的初始值应该同步确定，不能依赖 `onMounted` 等异步钩子——`watchEffect` 会在 `onMounted` 之前执行。

---

### Bug 3：后端重启后暗色模式未重置为浅色

**现象**：后端重启后刷新页面，暗色模式仍然保持，用户希望重启后回到浅色。

**根因**：localStorage 只区分"页面刷新"，无法区分"后端重启"——两个场景都只是页面重新加载。

**修复**：引入"后端启动时间戳"桥接前后端状态：
- `main.py` 模块级 `_STARTUP_TS = int(time.time())` + `GET /startup-ts` 接口
- `App.vue` onMounted 异步请求 `/startup-ts`，与 localStorage 存储值对比
- 时间戳不同（后端重启了）→ `dark.value = false` 回到浅色

**教训**：状态持久化要区分两个维度——"页面刷新"是客户端状态，"后端重启"是服务端状态，两者需要桥梁（startup-ts）来同步语义。

---

### Bug 4：行程方案刷新后样式丢失

**现象**：生成 TripCard 行程方案后刷新页面，结构化卡片变成纯文本"杭州三日游，融合西湖经典……"

**排查过程**：

1. 诊断发现 metadata（含 trip_plan 结构化数据）只存在于 API 响应中，从未写入数据库
2. 刷新后 `switchSession` 从 DB 加载消息，type 被硬编码为 `'text'`
3. TripCard 渲染条件 `type === 'card'` 不满足，降级为 MessageBubble

**修复**：7 个文件全链路打通（见 1.4 节），metadata 从 DB → API → 前端完整传递。

**教训**：加一个字段看似简单，实际要改 5 层（DB schema → 存储函数 → API 端点 → 响应序列化 → 前端类型映射），任何一环断裂都会导致数据丢失。

---

### Bug 5：metadata 持久化引发的回归——所有消息变成 TripCard

**现象**：Bug 4 修复后，刷新页面发现所有消息（包括用户消息和普通聊天）都显示"目的地："前缀，样式全变了。

**排查过程**：

1. 用户截图显示：用户说"杭州"、assistant 问"请问计划玩几天？"都渲染成了 TripCard
2. 检查 `switchSession`：`m.intent === 'TRIP_PLAN' ? 'card' : 'text'`
3. 关键发现：**用户消息 "杭州" 也被存为 TRIP_PLAN 意图**（chat.py 中 `save_message(user, ..., intent)` 把用户消息的 intent 设为 TRIP_PLAN）
4. `isTripCard` 只检查 `type === 'card'`，不区分 role 和 metadata
5. TripCard 的 fallback 模板：`<p>目的地：{{ safetyWarning ? '' : '' }}</p>`——当 `tripPlan` 为 null 但 `fallbackSummary` 有值时，显示"目的地："前缀

**根因**：意图（intent）≠ 展示形态（type）。用户说"杭州"触发 TRIP_PLAN 意图，但这条用户消息本身不是行程方案。

**修复**：`isTripCard` 加严为三重条件：
```typescript
// 之前
return msg.type === 'card'
// 现在
return msg.type === 'card' && msg.role === 'assistant' && !!msg.metadata?.trip_plan
```

**教训**：修复功能 X 时要检查对功能 Y 的影响。type 映射逻辑不应仅依赖 intent，应该用数据是否完整（`trip_plan` 存在）作为最终判断标准。条件判断应尽可能严格。

---

### Bug 6：TRIP_PLAN 多轮对话——"三天"没有关联上文的"杭州"

**现象**：用户说"杭州" → AI 问"请问计划玩几天？" → 用户说"三天" → AI 回复"请问你想去哪里旅行呢？"，没有将"三天"与上文的"杭州"关联。

**根因**：TRIP_PLAN 分支在 destination 为空时直接报错询问，没有利用对话历史做上下文补全。与 KNOWLEDGE 意图的代词消解问题完全同构。

**修复**：在 `intent_router.py` 的 TRIP_PLAN 分支中，destination 为空时先读取对话历史，用 LLM 提取最近提到的目的地：
```python
if not destination:
    history = await get_recent_history(device_id, session_id=session_id)
    resolve_prompt = "从以下对话历史中，提取用户最近提到的旅行目的地……"
    resolved = await call_llm(...)
    destination = resolved.strip() if resolved.strip() != "无" else ""
```

**教训**：代词消解（"三天"指"杭州的三天"、"那附近"指"西湖附近"）是多轮对话的核心难题。最实用的方案是用 LLM 从历史中提取指代对象，而非维护复杂的规则引擎。同一个解决方案可以复用在多个意图分支中。

---

### Bug 7：会话标题整坨 JSON + 天气对话中说地名被错误识别为行程规划

**问题 A：会话标题显示整坨行程 JSON**

现象：会话标题显示"哈尔滨·[{'day_index': 1, 'date': None, 'theme': ...}日游"

根因：`trip_plan.get("days", 0)` 取到的是 `days` 数组（包含每天的行程对象），不是天数。`f"{dest}·{days}日游"` 渲染时数组被转成字符串。

修复：改为 `len(trip_plan.get("days", []))`，正确取数组长度。

**问题 B：天气对话中说地名被错误识别为行程规划**

现象：用户在天气对话中说"哈尔滨"，AI 回复"好的，你想去哈尔滨！请问计划玩几天呢？"而不是回复哈尔滨天气。

根因：AI 意图识别是无状态的，LLM 只看当前消息"哈尔滨"，不知道上文在问天气。看到地名就按关键词优先匹配为 TRIP_PLAN。

修复：
- `INTENT_RECOGNITION_PROMPT` 新增"上下文延续"优先级规则
- `route_intent` 调 AI 前取最近 6 条对话历史注入 `{recent_context}` 字段
- LLM 看到"上轮问天气城市 → 用户回复地名"后，正确返回 WEATHER

**教训**：
- API 返回的字段名 ≠ 数据类型：`trip_plan.days` 是 `DayPlan[]` 数组，不是数字，取值前先确认实际类型
- LLM 意图识别需要对话历史：单条消息的意图分类天然存在歧义（"哈尔滨"可以是天气/行程/知识），必须注入上下文

---

## 三、本次会话的完整 Git 提交记录

```
2ea51fd  feat: 会话智能命名 + 意图识别上下文感知
1698311  fix: 行程方案刷新丢失 + TRIP_PLAN 多轮对话上下文补全
7fcefae  fix: 批量扩充URL修复 + 暗色模式持久化与重启检测
a349483  feat: UI 细节补全 + 批量扩充 + 知识纠正闭环
```

---

## 四、本次会话修改的完整文件清单

### 后端

| 文件 | 改动次数 | 改动内容 |
|------|----------|----------|
| `app/main.py` | 1 | 新增 `_STARTUP_TS` + `GET /startup-ts` 接口 |
| `app/api/chat.py` | 3 | metadata 传入 save_message + 会话自动命名 + days 取 len() |
| `app/api/sessions.py` | 2 | 返回 metadata 字段 + 新增 `update_session_title()` |
| `app/api/knowledge.py` | 1 | 新增 `POST /knowledge/auto-expand-batch` SSE 端点 |
| `app/models/database.py` | 1 | conversations 表加 `metadata TEXT` 列 |
| `app/services/context_service.py` | 1 | `save_message()` 支持 metadata 参数 |
| `app/services/intent_router.py` | 3 | TRIP_PLAN 代词消解 + 纠正闭环 + 意图识别上下文注入 |
| `app/services/knowledge_expander.py` | 1 | 新增 `correct_knowledge()` 纠正闭环 |

### 前端

| 文件 | 改动次数 | 改动内容 |
|------|----------|----------|
| `src/App.vue` | 2 | 暗色模式同步初始化 + 后端重启检测 |
| `src/stores/chat.ts` | 2 | 重命名会话 + 加载时还原 type 和 metadata |
| `src/style.css` | 1 | 新增 `@keyframes msgSlideIn` 动画 |
| `src/components/chat/ChatContainer.vue` | 3 | 批量扩充入口 + `isTripCard` 三重条件 |
| `src/components/chat/ChatInput.vue` | 1 | 动态 placeholder 轮播 |
| `src/components/chat/MessageBubble.vue` | 1 | 新增 `msg-slide-in` 类 |
| `src/components/chat/SessionSidebar.vue` | 2 | 重命名 UI + 时间 HH:MM + 去掉条数 |
| `src/components/chat/BatchExpandModal.vue` | 2 | 新建组件 + URL 修复 + 错误横幅 |

---

## 五、本次会话踩坑总结

### 坑1：`fetch()` vs `axios` 是两套独立网络层

Vue 项目中 axios 实例配置的 `baseURL`、拦截器等对原生 `fetch()` 完全无效。用 `fetch()` 时必须写完整 URL。这是最常见的遗漏点。

### 坑2：`onMounted` 是异步的，`ref()` 初始值应同步确定

`ref()` 初始化后 `watchEffect` 立即执行，如果初始值依赖 `onMounted` 中的异步操作，`watchEffect` 会在数据就绪前执行，导致状态被覆盖。

### 坑3：持久化要区分"页面刷新"和"后端重启"

localStorage 是客户端状态，只能区分"页面刷新"。后端重启是服务端状态，两者需要桥梁（startup timestamp）来同步语义。

### 坑4：metadata 全链路打通需要改 5 层

加一个字段看似简单：DB schema → 存储函数 → API 端点 → 响应序列化 → 前端类型映射，任何一环断裂都会导致数据丢失。

### 坑5：意图（intent）≠ 展示形态（type）

用户说"杭州"触发 TRIP_PLAN 意图，但这条用户消息本身不是行程方案。不能简单地 `if intent == TRIP_PLAN then type = 'card'`——应该用数据是否完整（trip_plan 存在）作为渲染判断标准。

### 坑6：API 返回字段名 ≠ 数据类型

`trip_plan.days` 在 TripPlan 接口中是 `DayPlan[]` 数组，不是数字。用 `.get("days", 0)` 取值时拿到数组，`f"...{days}..."` 渲染出整个数组。取值前先确认实际类型。

### 坑7：LLM 意图识别需要对话历史

单条消息的意图分类天然存在歧义（"哈尔滨"可以是天气/行程/知识）。必须把最近对话历史注入 prompt，让 LLM 理解"上文在问什么"，才能正确判断当前消息是延续还是新话题。

---

## 六、四次会话协同模式对比

| 维度 | 第一次（Phase 0-3） | 第二次（Phase 4 验证） | 第三次（Phase 5-12） | 第四次（P0-P3 优化） |
|------|---------------------|----------------------|---------------------|---------------------|
| 工作类型 | 从零写代码 | 排查环境问题 | 功能开发+深度调试 | 方案审计+功能补全+Bug修复 |
| Bug 数量 | 4 个运行时错误 | 3 个环境问题 | 7+ 个逻辑 Bug | 7 个真实 Bug |
| 调试深度 | 浅 | 中 | 深（端到端追踪） | 深（全栈+回归） |
| 关键技能 | 按方案执行 | 环境排查 | 数据流追踪 | 架构理解+回归防御 |
| 用户参与度 | 低 | 中 | 高 | 最高（持续测试反馈） |
| 典型指令 | "继续下一阶段" | "怎么验证区别" | 展示截图报 Bug | 截图+逻辑分析+验收 |

**最大教训**：本次会话的 7 个 Bug 中，有 2 个是"修 Bug 引入的新 Bug"（Bug 5 回归、Bug 7-A JSON 溢出）。随着项目复杂度增加，每次修改都要考虑对现有功能的影响——修复 X 时要检查 Y 和 Z 是否被波及。

> **一句话记住**：功能开发是"从无到有"，优化是"从有到好"，而"从好到稳"需要的不是更多代码，而是更严格的条件判断和更全面的回归测试。

---

## 七、项目当前状态

### Git 提交记录（完整）

```
2ea51fd  feat: 会话智能命名 + 意图识别上下文感知
1698311  fix: 行程方案刷新丢失 + TRIP_PLAN 多轮对话上下文补全
7fcefae  fix: 批量扩充URL修复 + 暗色模式持久化与重启检测
a349483  feat: UI 细节补全 + 批量扩充 + 知识纠正闭环
4955de9  feat(P3): 行程风格对比 + 知识库自动调研
7a94288  P2 体验优化：天气 · 问候 · 界面美化 · 预算估算 · 旅行清单
530d77b  P1 可靠性优化：错误恢复 + 消息右键菜单 + 行程导出 + 一键启动脚本
88efabb  P0 核心优化：KNOWLEDGE兜底 + TripCard结构化 + 偏好管理 + 会话系统
328c1a6  文档更新：补充阶段5-12调试记录，重命名去除日期后缀
89cf729  对话上下文与记忆连贯性：多轮对话支持 + 智能摘要压缩
2dd44b9  阶段十二：联调优化、测试与部署（最终交付）
f38fd1c  阶段十一：语音交互（Web Speech API 语音输入 + TTS 播报）
a092fd0  阶段十：安全系统完善（三级拦截 + 输出过滤 + 频率限制）
d76a46d  阶段九：前端-后端业务大串联（WebSocket + 消息类型分支 + 卡片渲染）
b8bf6b0  阶段八：主动服务（WebSocket 推送 + APScheduler 定时提醒）
ae19d38  阶段七：RAG 景点知识服务（ChromaDB 向量检索 + LLM 导游式回答）
b8150bf  阶段六：行程规划服务（LLM 生成 + POI/天气/偏好融合 + SQLite 持久化）
d04b45b  阶段五：外部 API 集成（高德地图 + 天气查询）
e133e10  补充 Phase 0/1/2 详细记录，完善项目全过程文档
e4fbfc2  阶段四文档：项目进展记录与 ChromaDB 环境问题排查全过程
23d33d9  阶段四：记忆系统升级为 ChromaDB + SQLite 双写
c7633da  修复 requirements.txt 中文注释导致 pip GBK 解码失败
3fb08d6  阶段四：Hermes 记忆系统（纯 SQLite 实现）
4c316a4  修复阶段三意图识别管道三个运行时错误
14a38be  阶段三：三层意图识别管道
0d9219e  阶段二：后端 API 网关与数据库初始化
573a8a4  阶段一：前端对话界面基础
5843d94  阶段零：搭建项目骨架，迁移核心服务
```

### 已完成模块（最终）

| 层级 | 模块 | 状态 |
|------|------|------|
| 前端 | Vue 3 + Vite + TypeScript + Tailwind CSS + Pinia + Axios | ✅ |
| 前端 | 聊天界面（ChatContainer / MessageBubble / ChatInput / TripCard / SessionSidebar / BatchExpandModal） | ✅ |
| 前端 | 语音输入 + TTS 播报 | ✅ |
| 前端 | WebSocket 实时连接 + 主动消息推送 | ✅ |
| 前端 | 暗色模式（localStorage 持久化 + 后端重启检测） | ✅ |
| 前端 | 会话管理（创建 / 切换 / 重命名 / 删除 / 智能命名） | ✅ |
| 前端 | 批量扩充知识库（SSE 流式进度） | ✅ |
| 前端 | 行程方案结构化展示 + 风格切换 + 刷新保持 | ✅ |
| 后端 | FastAPI + CORS + 路由体系 | ✅ |
| 后端 | SQLite 数据库（6 张表，含 metadata 列） | ✅ |
| 后端 | 三层意图识别（安全→正则→AI）+ 正则预拦截 + 上下文感知 | ✅ |
| 后端 | 天气 API / 地图 API / RAG 知识检索 | ✅ |
| 后端 | 行程规划服务 + 风格对比 + 多轮上下文补全 | ✅ |
| 后端 | 安全系统（三级拦截 + 输出过滤 + 频率限制） | ✅ |
| 后端 | 记忆系统（SQLite + ChromaDB 双写） | ✅ |
| 后端 | 对话上下文（历史加载 + 摘要压缩） | ✅ |
| 后端 | WebSocket 推送 + APScheduler 定时提醒 | ✅ |
| 后端 | 知识库自动调研 + 批量扩充 + 用户纠正闭环 | ✅ |
| 后端 | 会话智能命名（首次消息命名 + 行程方案更新） | ✅ |
| 后端 | 启动时间戳 API（前端暗色模式重启检测） | ✅ |
