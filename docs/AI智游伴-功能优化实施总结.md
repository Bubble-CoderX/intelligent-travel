# AI智游伴 — 功能优化实施总结

> 本文档记录 AI智游伴（TravelMate）从基础版本到全面优化的完整实施过程。
> 涵盖 32 项优化点的实现状态、分阶段推进记录、关键技术决策和遇到的问题。

---

## 一、优化总览

共规划 32 项优化（O1-O32），实际实现 27 项，跳过 5 项。全部在 7 个阶段内完成。

| 状态 | 数量 | 说明 |
|------|------|------|
| 已实现 | 27 | 功能完整、已集成到主流程 |
| 跳过 | 5 | O3(Coze)、O10(轻量模型)、O15(情绪感知)、O24.3(局部修改)、O25(完整反馈闭环) |

### 已实现的优化项

| 编号 | 优化项 | 优先级 | 核心成果 |
|------|--------|--------|---------|
| O1 | 偏好系统重构（对话式偏好 + 出行档案） | P0 | 对话中自然表达自动提取16项旅行档案 |
| O2 | 行程规划质量升级 | P0 | RAG知识库接通 + 预算精确计算 + 交通推荐 + 健康信息联动 |
| O4 | 天气数据持久化 + 四级降级 | P0 | 缓存→SQLite→API→LLM四级容错，天气永不缺失 |
| O5 | 天气异常检测引擎 | P0 | 4条规则（降雨/高温/骤降/强风），异常主动推送 |
| O6 | TCI旅行体感指数 | P0 | 天气×人群×行程×时段四维融合评估，五档评级 |
| O7 | 天气异常 + TCI + 行程重排联动链 | P0 | 检测→TCI重算→推送预警→行程调整建议 全链路 |
| O8 | 图片上传（部分实现） | P1 | 千问VL图片识别，图片持久化到服务端 |
| O9 | 流式输出（SSE） | P1 | 普通对话逐字流式，天气/行程等走全量生成 |
| O11 | 旅行清单系统升级 | P1 | 规则引擎（天气/人数/过敏）+ LLM补充，结构化清单 |
| O12 | 餐饮推荐权重调整 | P2 | 高温→清凉消暑，低温→暖身热食，嵌入行程Prompt |
| O13 | 天气日报/周报生成 | P2 | LLM分析7天趋势，生成日报/周报 |
| O16 | 数据展示页：行程历史记录 | P1 | 行程列表 + 详情页 + 状态管理（计划/进行中/完成） |
| O17 | 数据展示页：偏好档案页 | P1 | 出行档案 + 手动设置 + 系统信息三区展示 |
| O18 | 数据展示页：知识库浏览页 | P1 | 分类标签筛选 + Markdown内容展示 |
| O19 | 数据展示页：对话历史页 | P2 | 完整对话记录回溯 |
| O20 | 数据展示页：天气记录页 | P2 | 天气采集数据 + 城市筛选 + 湿度/温度/风力展示 |
| O21 | 数据展示页：出行统计页 | P2 | 概览卡片 + 城市排行 + 人员构成分布 |
| O22 | 行程卡片配图 + 导出增强 | P1 | 高德POI照片自动补充 + PDF含清单/照片 |
| O23 | 项目定位升级 | P0 | 定位文档：面向家庭出行的AI旅行助手 |
| O26 | Prompt注入防护 | P3 | 18种注入模式检测 + 输入/输出双重过滤 |
| O27 | WebSocket心跳机制 | P1 | 30秒ping/pong防静默断连 |
| O28 | 知识库内容升级 | P2 | 避坑提示 + 紧急联系方式，知识库子目录分类 |
| O29 | 数据清理机制 | P2 | 每周日凌晨自动清理过期会话/消息/天气记录 |
| O31 | 暗色模式全页面统一适配 | P2 | 新增页面全部适配暗色模式 |
| O32 | 导出PDF排版优化 | P2 | 图文混排 + 清单渲染 + 中文字体 + RFC5987文件名 |

### 跳过的优化项

| 编号 | 优化项 | 跳过原因 |
|------|--------|---------|
| O3 | 接入Coze智能体 | 架构变更过大，当前自有LLM方案已满足需求 |
| O10 | 行程生成换轻量模型 | 需要额外API接入，当前模型速度可接受 |
| O15 | 旅途情绪感知与陪伴 | 已实现代码但未集成到主流程，检测准确率有限、误判风险高 |
| O24.3 | 行程局部修改（单天重生成） | trip_history/trip_plans表ID不匹配，改动风险大 |
| O25 | 完整反馈闭环（用户评价→推荐优化） | 仅实现基础标记完成功能，完整评价回流暂不实现 |

---

## 二、分阶段实施记录

### 第一阶段：项目定位 + 偏好系统重构（O23 + O1）

**目标：** 明确项目定位，从"通用旅行助手"升级为"面向家庭出行的AI旅行伴游"。

**关键实现：**
- 创建项目定位文档，明确目标用户（家庭出行、带娃/老人场景）
- `profile_extractor.py`：从对话中正则提取16项旅行档案（出行人数、人员构成、儿童年龄、老人数量、旅行风格、兴趣标签、饮食忌口、住宿偏好、过敏史、特殊需求、日均预算等）
- `transport_service.py`：基于距离的交通方式推荐（≤50km自驾、50-500km高铁、>500km飞机）
- `PreferencesDrawer.vue` 重写：出行档案展示 + 精确设置区（预算/过敏/特殊需求/出行方式）+ 系统信息区

**遇到的问题：**
- 预算计算错误：系统按"总预算=日均×天数"计算，漏乘人数。修复为"日均×人数×天数"，并增加儿童票政策（6岁以下免票、6-14岁半价）
- 出发地固定问题：IP定位结果存入profile后不再更新。改为每次重新IP定位，profile仅作兜底

---

### 第二阶段：天气系统优化（O4-O7）

**目标：** 建立天气数据基础设施，实现从"被动查询"到"主动预警"的升级。

**关键实现：**
- `weather_records` 表：SQLite持久化天气快照，含humidity实时补充
- 四级降级策略：Redis缓存 → SQLite最近记录（30分钟内） → 高德API → LLM通用知识估算
- `weather_anomaly_detector.py`：4条规则（降雨预报/极端高温/温度骤降/强风），返回AnomalyReport
- `comfort_index_service.py`：TCI五档评级（极佳≥80/舒适≥60/一般≥40/较差≥20/<20），四维融合计算
- `weather_linkage_engine.py`：天气→异常检测→TCI重算→推送预警→行程调整建议 全链路

**遇到的问题：**
- 异常检测漏检：`_check_extreme_heat` 检查的是今天温度而非明天。修复为检查次日温度
- 风力误判：仅匹配"大风""强风"等文字，漏掉数字等级≥6。增加数字风级判断
- TCI阈值不合理：原先85/70/55/35分四档过于宽松。调整为80/60/40/20五档

---

### 第三阶段：天气联动 + 知识库升级（O12 + O20 + O28）

**目标：** 打通天气数据到餐饮推荐的链路，升级知识库内容。

**关键实现：**
- 天气联动餐饮推荐：根据温度返回推荐偏好标签（高温→清凉消暑、低温→暖身热食），注入到行程Prompt的`dining_text`
- 天气记录页（`WeatherRecord.vue`）：展示SQLite中的天气采集数据，支持城市筛选
- 知识库子目录分类：`data/knowledge/` 从平铺结构重组为 cities/ spots/ food/ culture/ 等子目录
- 知识库自动调研：当RAG检索无结果时，自动调用LLM生成知识并入库
- 知识库内容升级：17个城市知识文件重建，增加避坑提示和紧急联系方式

**遇到的问题：**
- 知识库中文目录名导致路径问题。统一改为英文目录名（cities/ spots/ food/），增加`CATEGORY_DIR_MAP`中文→英文映射
- 知识库自动调研超时：默认30秒不够，增大到120秒+
- 上海、西安因内容量大调研失败，需要更长timeout

---

### 第四阶段：数据展示 + 行程配图 + 清单升级（O16 + O17 + O18 + O22 + O11）

**目标：** 构建完整的数据可视化体系，提升行程卡片的视觉呈现。

**关键实现：**
- 行程历史页（`TripHistory.vue`）：行程列表 + 详情页 + 状态管理（planned/in_progress/completed）
- 偏好档案页（`ProfilePage.vue`）：三区展示 + 统计数据
- 知识库浏览页（`KnowledgeBrowser.vue`）：分类标签筛选 + Markdown内容渲染
- 行程卡片配图：`photo_service.py` 从高德POI API自动补充景点照片，TripCard/TripDetail渲染64×64缩略图
- 清单系统升级：`checklist_service.py` 重写为规则引擎（天气联动/人数联动/过敏联动/常见药品），支持LLM补充目的地特色清单

**遇到的问题：**
- Checklist字段缺失：Itinerary模型中没有`checklist`字段。在schemas.py中新增`checklist: dict | None`
- 照片不显示：photo_url保存后刷新丢失。改为服务端URL持久化，前端统一渲染
- PDF导出无清单：export_service读取trip_plans（不含清单）。改为优先读取trip_history（含清单+照片）

---

### 第五阶段：出行统计 + 反馈闭环 + 数据清理 + 暗色模式（O21 + O25 + O29 + O31）

**目标：** 完善数据展示体系，增加自动化运维能力。

**关键实现：**
- 出行统计页（`TravelStats.vue`）：概览卡片（总行程/城市/天数/预算） + 城市排行 + 人员构成分布
- 基础反馈闭环：行程详情页"✓完成"按钮，标记行程为completed状态
- 数据清理机制（`data_cleanup.py`）：清理30天前会话、60天前消息、90天前天气记录，APScheduler每周日凌晨3点执行
- 暗色模式适配：所有新增页面（TripHistory/TripDetail/ProfilePage/KnowledgeBrowser/WeatherRecord/TravelStats）统一适配暗色模式

---

### 第六阶段：安全系统 + 图片上传 + UI统一（O26 + O8 + O24）

**目标：** 增强系统安全性，实现多模态交互。

**关键实现：**
- Prompt注入防护（`safety.py`）：18种注入模式检测，在意图识别前拦截，输出端二次过滤
- 图片上传（`chat.py` + `qwen_vl_client.py`）：前端读取图片→Base64编码→千问VL识别→结果返回，图片持久化到`data/uploads/`
- 流式输出（`llm_client.py` + `chat.py`）：`call_llm_stream()` 函数，前端SSE逐字渲染；WEATHER/KNOWLEDGE/TRIP_PLAN走非流式路径
- WebSocket心跳（`chat.py`）：30秒ping/pong机制防静默断连

**遇到的问题：**
- 千问VL API不稳定：先后尝试qwen-vl-max、qwen-vl-plus、qwen3.5-omni-plus，最终需要在百炼控制台开通qwen-vl-max
- 流式端点天气/知识异常：WEATHER意图走了streaming路径但使用CHAT的prompt。修复为WEATHER/KNOWLEDGE走full_gen非流式路径

---

### 第七阶段：收尾 + 测试 + 清理 + UI统一

**目标：** 修复所有遗留问题，统一时间标准，完善UI细节。

**关键实现：**
- UTC+8时间标准化：sessions/trip_history/weather_records/memory/proactive 全部INSERT/UPDATE使用`datetime.now(timezone(timedelta(hours=8)))`
- 出发地优先级修复：从"profile > IP"改为"IP > profile"，每次重新获取当前位置
- 预算提示增强：Prompt中增加"每人每天×人数×天数"详细拆解，含住宿间数计算和儿童票政策
- 偏好UI修复：编辑/关闭按钮切换、空输入禁用保存、预算显示"元/人/天"
- 主动问候天气修复：IP定位结果英文→中文翻译，确保天气API能正确查询

**遇到的问题：**
- sessions表INSERT缺少updated_at：导致前端显示空时间。补上updated_at字段
- trip_history用CURRENT_TIMESTAMP：SQLite的CURRENT_TIMESTAMP是UTC，导致时间差8小时
- proactive.py UnboundLocalError：datetime在函数内import导致UnboundLocalError。改为模块级import
- 出发地IP定位英文名：ip-api返回英文城市名（如"Guangzhou"），天气API不认。增加`_EN_TO_CN_CITY`翻译

---

## 三、关键技术决策

### 1. 天气四级降级策略
- Level 1: Redis内存缓存（TTL按配置）
- Level 2: SQLite最近记录（30分钟内有效）
- Level 3: 高德天气API实时请求
- Level 4: LLM通用知识估算（最终兜底）
- 每条数据含`_source`字段标识来源

### 2. 对话式偏好提取
- 正则匹配优先（确定性高、无token消耗）
- 16项旅行档案字段，覆盖出行人数/构成/年龄/风格/兴趣/饮食/住宿/过敏/预算等
- 用户在对话中自然表达，系统自动提取并持久化到SQLite

### 3. 知识库RAG + 自动调研
- ChromaDB向量检索 + SQLite元数据
- 检索无结果时自动触发LLM生成知识并入库
- 知识库按类别分目录（cities/ spots/ food/ culture/ 等），支持分类浏览

### 4. TCI旅行体感指数
- 四维融合：天气（温度/湿度/风力/天气状况）× 人群（老人/儿童/普通）× 行程（活动强度）× 时段（早中晚）
- 五档评级：极佳(≥80) / 舒适(≥60) / 一般(≥40) / 较差(≥20) / 极差(<20)
- 纯计算函数，无LLM依赖，支持单元测试

### 5. 流式输出架构
- 普通对话（CHAT）：SSE逐字流式，前端实时渲染
- 功能型意图（WEATHER/KNOWLEDGE/TRIP_PLAN）：全量生成，确保数据完整性和结构化输出
- 图片/文件上传：Base64编码 → 千问VL识别 → 服务端持久化

---

## 四、项目文件变更统计

### 新增文件（主要）

**后端服务：**
- `services/profile_extractor.py` — 对话式偏好提取
- `services/transport_service.py` — 交通方式推荐
- `services/weather_anomaly_detector.py` — 天气异常检测
- `services/comfort_index_service.py` — TCI旅行体感指数
- `services/weather_linkage_engine.py` — 天气联动引擎
- `services/checklist_service.py` — 旅行清单系统
- `services/photo_service.py` — 景点照片补充
- `services/export_service.py` — 行程PDF导出
- `services/weather_report_service.py` — 天气日报/周报
- `services/mood_companion_service.py` — 情绪感知（已实现但未集成）
- `services/data_cleanup.py` — 过期数据清理
- `services/qwen_vl_client.py` — 千问VL图片识别
- `services/knowledge_expander.py` — 知识库自动调研

**后端API：**
- `api/trip_history.py` — 行程历史CRUD
- `api/knowledge_browse.py` — 知识库浏览
- `api/weather_intel.py` — 天气智能（日报/周报/TCI）

**前端页面：**
- `views/TripHistory.vue` — 行程历史页
- `views/TripDetail.vue` — 行程详情页
- `views/ProfilePage.vue` — 偏好档案页
- `views/KnowledgeBrowser.vue` — 知识库浏览页
- `views/WeatherRecord.vue` — 天气记录页
- `views/TravelStats.vue` — 出行统计页
- `views/ChatHistory.vue` — 对话历史页

### 重构/重写文件

- `services/trip_service.py` — 行程规划核心，加入RAG/预算/交通/健康/餐饮联动
- `utils/trip_prompts.py` — Prompt模板全面升级
- `services/proactive_service.py` — 主动服务加入天气巡检+TCI联动
- `services/llm_client.py` — 新增流式输出支持
- `components/PreferencesDrawer.vue` — 三区布局重写
- `components/chat/SessionSidebar.vue` — 三段式侧边栏
- `stores/chat.ts` — 流式输出支持

---

## 五、Git提交记录

项目共 58 次提交，优化阶段约 20 次关键提交：

```
60d6d59 fix(O24+UTC修复): 偏好UI编辑切换 + 预算人均提示 + 出发地IP优先 + 时间标准化
00d1525 fix: 流式端点天气/知识查询修复
5cb2627 fix: proactive.py UnboundLocalError修复
cfae10b feat(全面收尾): 时间修复 + 数据展示页 + UI优化 + 总结文档
cc004f7 fix: checklist字段 + 照片补充 + 行程详情页渲染
bc73653 fix: UTC+8本地时间统一 + 主动服务时间修复 + export_service日志
5e7204f feat(O8+知识库重构+UI优化): 千问VL图片识别 + 知识库子目录 + 图片持久化
5ebb71e feat(O8+知识库重构): 千问VL图片识别 + 知识库子目录分类 + 自动调研
89910c4 feat(O26): Prompt注入防护 — 检测并拦截提示词攻击
ca90988 feat(O21+O25+O29+O31+UI修复): 出行统计 + 反馈闭环 + 数据清理 + 侧边栏优化
70703ac feat(O21+O25+O29+O31): 出行统计 + 反馈闭环 + 数据清理 + 暗色模式
37c22b1 feat(O12+O20+O28): 餐饮联动 + 天气记录页 + 知识库重建+避坑紧急
6e2667f feat(O9+O8): 流式输出(SSE) + 图片文件上传 + TRIP_PLAN消息持久化修复
be2b6a5 feat(O22+O27+O19+O11): 行程配图 + 心跳 + 对话历史 + 清单升级
bd04062 feat(O22): 行程卡片配图 + 景点照片自动补充 + 历史详情支持照片
bfccea3 feat(O11): 旅行清单系统升级 — 结构化清单 + 天气/人群/过敏联动
c05c596 feat(O18+UI): 知识库浏览页 + 侧边栏三段式改造 + 消息时间戳
7a5961f feat(O16+O17): 数据展示页系列 — 行程历史 + 偏好档案 + Vue Router搭建
785555e feat(O4-O7): 天气系统优化 — humidity持久化 + 异常检测精确化 + TCI五档 + 联动链
03ff504 feat(O2-Batch3): 知识库全面重建 + 高德校正 + 知识库路线仅作参考
85ac284 feat(O2-Batch2): 出发地处理 + 交通推荐 + ValidationError彻底消除
0a77abc feat(O2-Batch1+hotfix): 行程规划质量升级 — RAG接通+Prompt大升级
c1d8623 feat(O2-Batch1): 行程规划质量升级 — RAG接通 + Prompt大升级
2cec64d feat(O23+O1): 项目定位文档 + 偏好系统重构
```

---

## 六、已知限制与后续建议

### 已知限制
1. **千问VL API不稳定**：图片识别偶尔超时或返回空结果，需要网络环境良好
2. **知识库自动调研超时**：城市级知识生成（内容量大）可能需要120秒以上
3. **O15情绪感知未集成**：代码已实现（`mood_companion_service.py`），但检测准确率有限，未接入主流程
4. **O24.3局部修改未实现**：trip_history/trip_plans表ID不匹配，需要数据库迁移才能支持
5. **SQLite并发限制**：多用户同时写入可能锁表，适合单用户/小团队场景

### 后续建议
1. **数据库迁移**：将trip_plans和trip_history统一为一张表，支持O24.3局部修改
2. **接入更好的VL模型**：等千问VL API稳定后完善图片识别功能
3. **O15情绪感知集成**：在chat.py中增加情绪拦截判断，当置信度>0.4时优先处理情绪
4. **性能优化**：考虑将SQLite迁移到PostgreSQL，支持更高并发
5. **O30回归测试**：编写自动化测试覆盖核心功能链路

---

> 文档生成时间：2026-06-17
> 项目总提交：58 次
> 优化阶段提交：约 20 次
> 优化完成度：27/32（84.4%）
