from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.api.routes import projects, pipeline, candidates, exports, settings, irasutoya
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

app = FastAPI(title="KiriNuki API", version="0.1.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    init_db()

# 注册路由
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["candidates"])
app.include_router(exports.router, prefix="/api/exports", tags=["exports"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(irasutoya.router, prefix="/api/irasutoya", tags=["irasutoya"])

@app.get("/")
async def root():
    return {"message": "KiriNuki API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "ok"}
