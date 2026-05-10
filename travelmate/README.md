# TravelMate - AI 智游伴

AI 驱动的智能旅行规划助手，支持行程生成、地图增强、天气查询、行程导出等功能。

## 技术栈

**前端**
- Vue 3 + Vite + TypeScript
- Tailwind CSS
- Pinia (状态管理)
- Axios (HTTP 客户端)

**后端**
- FastAPI (Python)
- SQLAlchemy + SQLite
- 高德地图 API (地图/天气服务)
- Redis (可选缓存)

## 本地启动

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # 填写你的 API Key
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，后端默认运行在 `http://localhost:8000`。
