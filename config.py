from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_key_size: int
    postgres_string: str

    model_config = SettingsConfigDict(env_file=".env")