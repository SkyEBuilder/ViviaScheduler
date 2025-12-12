from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    admin_secret: str = "vivia-admin-secret"
    
    # We will just use simple JSON file for users for now
    users_file: str = "users.json"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
