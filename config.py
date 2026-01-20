import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""

    # API配置
    siliconflow_api_key: str = Field(..., env="SILICONFLOW_API_KEY")
    siliconflow_base_url: str = Field("https://api.siliconflow.cn/v1", env="SILICONFLOW_BASE_URL")
    siliconflow_model: str = Field("deepseek-ai/DeepSeek-V3.2-Exp", env="SILICONFLOW_MODEL")

    # 应用配置
    api_port: int = Field(8010, env="API_PORT")  # 添加这个配置
    debug: bool = Field(True, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    upload_folder: str = Field("uploads", env="UPLOAD_FOLDER")
    max_upload_size: int = Field(100 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 100MB
    allowed_extensions: List[str] = Field(["pptx", "ppt", "pdf"], env="ALLOWED_EXTENSIONS")

    # 数据库配置
    chroma_host: str = Field("localhost", env="CHROMA_HOST")
    chroma_port: int = Field(8000, env="CHROMA_PORT")
    chroma_collection: str = Field("ppt_content", env="CHROMA_COLLECTION")

    # 外部API
    wikipedia_api_url: str = Field("https://en.wikipedia.org/w/api.php", env="WIKIPEDIA_API_URL")

    # 安全配置
    secret_key: str = Field("your-secret-key-change-this", env="SECRET_KEY")
    cors_origins: List[str] = Field(["http://localhost:8501", "http://localhost:8000","http://localhost:8010"], env="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()