from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    RATE_LIMITING_ENABLE: bool = False
    RATE_LIMITING_FREQUENCY: str = "2/3seconds"
    # Enable only where a trusted proxy overwrites client-supplied Fly-Client-IP headers.
    TRUST_PROXY_HEADERS: bool = False

    TFMKT_BASE_URL: str = "https://tmapi.transfermarkt.technology"
    TFMKT_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0, le=300, allow_inf_nan=False)
    TFMKT_MAX_CONCURRENCY: int = Field(default=10, ge=1, le=100)
    CACHE_TTL_SECONDS: int = Field(default=600, ge=1, le=604_800)
    CACHE_REFERENCE_TTL_SECONDS: int = Field(default=86_400, ge=1, le=604_800)
    CACHE_MAX_ENTRIES: int = Field(default=2_000, ge=1, le=100_000)


settings = Settings()
