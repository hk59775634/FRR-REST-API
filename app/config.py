from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = "change-me"
    host: str = "0.0.0.0"
    port: int = 8080

    frr_reload_script: str = "/usr/lib/frr/frr-reload.py"
    frr_conf_path: str = "/etc/frr/frr.conf"
    frr_bindir: str = "/usr/bin"
    frr_conf_dir: str = "/etc/frr"
    frr_run_dir: str = "/var/run/frr"
    frr_daemons_path: str = "/etc/frr/daemons"


settings = Settings()
