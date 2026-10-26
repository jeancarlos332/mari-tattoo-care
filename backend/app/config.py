from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mari Tattoo Care API"
    environment: str = "development"
    frontend_origins: str = "http://localhost:4200"
    frontend_base_url: str = "http://localhost:4200"
    database_url: str
    token_encryption_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()