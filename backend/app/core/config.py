import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用配置
    app_name: str = "KiriNuki"
    debug: bool = True

    # 数据库配置
    # 使用持久化 SQLite 数据库文件
    database_url: str = "sqlite:///./kirinuki.db"

    # 工作目录
    work_dir: Path = Path("./data")

    # FFmpeg 路径
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    # irasutoya 服务
    irasutoya_enabled: bool = True
    irasutoya_port: int = 3000

    class Config:
        env_file = ".env"

settings = Settings()

# 确保工作目录存在
settings.work_dir.mkdir(parents=True, exist_ok=True)
(settings.work_dir / "projects").mkdir(exist_ok=True)
(settings.work_dir / "exports").mkdir(exist_ok=True)
