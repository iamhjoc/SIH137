"""
Central application configuration, loaded from environment variables (.env).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://sih_user:sih_pass@localhost:5432/sih26137"
    database_url_sync: str = "postgresql+psycopg2://sih_user:sih_pass@localhost:5432/sih26137"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    object_storage_backend: str = "filesystem"  # "filesystem" | "s3"
    object_storage_path: str = "/data/object-storage"
    s3_endpoint_url: str = ""
    s3_region: str = "ap-south-1"
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    default_seed: int = 20260909
    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"

    # --- Public deployment ---------------------------------------------
    # Comma-separated list of allowed browser origins for CORS, e.g.
    # "https://app.yourdomain.com,https://yourdomain.com". Leave as "*"
    # only for local development -- never in production.
    cors_allowed_origins: str = "*"

    # --- OpenStreetMap / graph import ------------------------------------
    # OSMnx talks to the public Overpass API by default and needs no key.
    # If you've set up a self-hosted/paid Overpass mirror, put its URL here;
    # otherwise leave blank to use the public endpoint.
    osm_overpass_url: str = ""

    # --- Geocoding --------------------------------------------------------
    # PUT YOUR GEOCODING API KEY HERE (via your real .env file, not this
    # source file). provider: "nominatim" | "google" | "mappls"
    geocoding_provider: str = "nominatim"
    geocoding_api_key: str = ""
    geocoding_api_base_url: str = ""  # optional override, e.g. self-hosted Nominatim

    # --- Traffic provider ---------------------------------------------
    # PUT YOUR TRAFFIC PROVIDER API KEY HERE (via your real .env file).
    # provider: "tomtom" | "here" | "mappls" | "simulated"
    traffic_provider: str = "simulated"
    traffic_api_key: str = ""
    traffic_api_base_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cors_origin_list(settings: "Settings") -> list[str]:
    if settings.cors_allowed_origins.strip() == "*":
        return ["*"]
    return [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
