from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Life Assistant"
    debug: bool = False
    
    # 数据库
    database_url: str = "sqlite+aiosqlite:///./life_assistant.db"
    
    # AI配置 - 硅基流动 (默认) 或 Kimi
    llm_provider: str = "siliconflow"  # "siliconflow" 或 "kimi"
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_model: str = "deepseek-ai/DeepSeek-V2.5"
    
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-8k"
    
    # 安全
    secret_key: str = "your-secret-key-change-in-production"
    token_expire_hours: int = 720  # 30天
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
