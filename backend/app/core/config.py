from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://agro:agro@localhost:5432/agro_ai"

settings = Settings()
