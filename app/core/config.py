# app/core/config.py
import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

env = os.environ
class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent Builder"
    DATABASE_URL: str = f"mysql+pymysql://{env.get('DB_USER')}:{env.get('DB_PASSWORD')}@{env.get('DB_HOST')}:{env.get('DB_PORT')}/{env.get('DB_NAME')}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
