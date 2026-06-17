# AI智游伴（TravelMate）

> 面向带娃/带老人出行的家庭旅行者的智能旅行助手

一个会看天气、懂你需求、能帮你改行程的旅行伴侣——不只是告诉你去哪玩，而是告诉你现在该不该出去、出去了该怎么调整。

---

## 核心特色

### 天气智能联动
- **四级降级**：Redis缓存 → SQLite → 高德API → LLM估算，天气永不缺失
- **异常检测**：自动检测暴雨/高温/骤降/大风，主动推送预警
- **TCI体感指数**：天气×人群×行程×时段四维融合，五档评级(0-100)
- **行程自动调整**：TCI低于60分时，LLM生成"室内优先"重排建议

### 对话式出行档案
- 对话中自然表达即可自动提取：出行人数、人员构成、儿童年龄、老人数量、旅行风格、兴趣标签、口味偏好、饮食忌口、住宿偏好、过敏史、特殊需求、预算等
- 偏好越用越准：SQLite结构化检索 + ChromaDB语义检索双引擎

### 智能行程规划
- 整合：高德POI + 天气预报 + 用户偏好 + 知识库RAG + 交通推荐 + 餐饮联动
- 预算精确计算：人均日预算 × 人数 × 天数，儿童票政策（6岁以下免/6-14岁半价）
- 出发地智能识别：用户消息 > IP定位 > profile兜底

### 结构化旅行清单
- 6大维度动态生成：天气 + 人群 + 健康状况 + 过敏史 + 饮食忌口 + 目的地特色
- 特殊需求联动：高血压→降压药，糖尿病→血糖仪，哮喘→喷雾剂
- LLM智能补充：根据用户画像推荐目的地特色物品

### 知识库系统
- 9大分类：城市/景点/美食/文化/民俗/历史/自然/古城/博物馆
- 自动调研：用户询问未收录目的地时，LLM自动生成知识并入库
- 避坑提示 + 紧急信息：每个城市知识包含游客常踩的坑和紧急联系方式

---

## 技术架构

```
前端 Vue 3 + TypeScript          后端 FastAPI + Python
├── 聊天界面（流式输出）           ├── 三层意图识别管道
├── TripCard 行程卡片             │   ├── 正则快速匹配
├── 偏好设置面板                  │   ├── AI意图识别（DeepSeek）
├── 数据展示页（7个）             │   └── 安全检查 + Prompt注入防护
└── Pinia 状态管理                ├── 行程规划引擎
                                  ├── 天气智能系统（四级降级+异常检测+TCI）
SQLite + ChromaDB                 ├── 知识库（RAG + 自动调研）
DeepSeek LLM + 千问VL             ├── 主动服务（WebSocket推送+定时巡检）
高德地图 API                      └── 记忆系统（双引擎）
```

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- 高德地图 API Key
- DeepSeek API Key

### 启动后端

```bash
cd travelmate/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 启动前端

```bash
cd travelmate/frontend
npm install
npm run dev
```

访问 http://localhost:5173

### 环境变量

```bash
# .env
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
AMAP_API_KEY=your_amap_key
QWEN_VL_API_KEY=your_qwen_key
```

---

## 项目结构

```
intelligent-travel/
├── travelmate/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/          # API路由
│   │   │   ├── services/     # 核心业务逻辑
│   │   │   ├── models/       # 数据模型
│   │   │   └── utils/        # 工具函数
│   │   ├── data/             # SQLite数据库 + 知识库
│   │   └── requirements.txt
│   └── frontend/
│       ├── src/
│       │   ├── components/   # Vue组件
│       │   ├── views/        # 页面视图
│       │   ├── stores/       # Pinia状态
│       │   └── api/          # API客户端
│       └── package.json
└── docs/                     # 项目文档
```

---

## 功能模块

| 模块 | 说明 |
|------|------|
| 意图识别 | 三层管道：正则→AI→安全，支持5种意图 |
| 行程规划 | LLM生成结构化JSON，含景点/餐饮/交通/住宿/清单 |
| 天气服务 | 四级降级 + 异常检测 + TCI体感指数 + 联动链 |
| 知识库 | RAG检索 + 自动调研 + 9大分类子目录 |
| 记忆系统 | SQLite + ChromaDB双引擎，偏好越用越准 |
| 主动服务 | WebSocket推送 + 天气播报 + 定时巡检 |
| 安全体系 | 三级拦截 + Prompt注入防护 + 输出过滤 + 频率限制 |
| 对话上下文 | 多轮对话 + 智能摘要压缩 + 代词消解 |
| 出行档案 | 对话式提取 + 固定字段展示 + 精确设置编辑 |
| 清单系统 | 天气/人群/健康/过敏/饮食多维度动态生成 |
| 数据展示 | 行程历史/偏好档案/知识库/天气记录/出行统计/对话历史 |
| 导出功能 | PDF行程导出（含清单/照片/中文字体） |

---

## 文档

- [项目完整技术文档](docs/AI智游伴-项目完整技术文档.md) — 架构图、功能详解、UML设计图、问题排查记录
- [功能优化与联动设计](docs/AI智游伴-功能优化与联动设计.md) — 32项优化的详细设计
- [完整实现方案](docs/AI智游伴-完整实现方案.md) — 从零到一的13阶段实现
- [项目书](docs/AI智游伴项目书.md) — 项目定位、架构、原型图、技术方案

---

## License

MIT
