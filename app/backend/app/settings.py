from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_prefix: str = "/api"
    cors_origins: list[str] = [
        "http://localhost:8083",
        "http://127.0.0.1:8083",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    data_source: str = "mock"

    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = ""
    database_user: str = ""
    database_password: str = ""
    products_table: str = "products"
    formats_table: str = "label_formats"
    history_table: str = "print_history"
    inventory_table: str = "inventory"
    inventory_entries_table: str = "inventory_entries"

    external_database_host: str = ""
    external_database_port: int = Field(default=1433, ge=1, le=65535)
    external_database_name: str = ""
    external_database_user: str = ""
    external_database_password: str = ""
    external_database_timeout_seconds: int = Field(default=60, ge=1)
    external_sync_enabled: bool = True
    external_sync_interval_minutes: int = Field(default=60, ge=1)
    external_sync_lookback_days: int = Field(default=1, ge=0)
    inventory_entries_retention_months: int = Field(default=2, ge=1, le=2)
    sync_query_dir: str = "../../scripts"

    warehouse_app_ssh_host: str = ""
    warehouse_app_ssh_port: int = Field(default=22, ge=1, le=65535)
    warehouse_app_ssh_user: str = ""
    warehouse_app_ssh_password: str = ""
    warehouse_app_database_host: str = ""
    warehouse_app_database_port: int = Field(default=5432, ge=1, le=65535)
    warehouse_app_database_name: str = ""
    warehouse_app_database_user: str = ""
    warehouse_app_database_password: str = ""
    warehouse_app_database_engine: str = "postgres"

    printer_name: str = "Zebra ZD230"
    print_agent_token: str = ""
    print_agent_id: str = "windows-primary"
    print_agent_stale_seconds: int = Field(default=120, ge=30)

    model_config = SettingsConfigDict(
        env_prefix="CLINIC_",
        extra="ignore",
    )

    @property
    def use_postgres(self) -> bool:
        return self.data_source.lower() in {"postgres", "postgresql"}

    @property
    def external_database_configured(self) -> bool:
        return all(
            (
                self.external_database_host,
                self.external_database_name,
                self.external_database_user,
                self.external_database_password,
            )
        )

    @property
    def warehouse_app_database_configured(self) -> bool:
        return all(
            (
                self.warehouse_app_ssh_host,
                self.warehouse_app_ssh_user,
                self.warehouse_app_ssh_password,
                self.warehouse_app_database_host,
                self.warehouse_app_database_name,
                self.warehouse_app_database_user,
                self.warehouse_app_database_password,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
