from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MySQL
    mysql_host: str = "141.94.31.144"
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = "indicator"

    # InfluxDB BOX
    influx_host: str = "tsdbe.nidec-asi-online.com"
    influx_port: int = 443
    influx_user: str = ""
    influx_password: str = ""
    influx_database: str = "Elto"
    influx_ssl: bool = True
    influx_verify_ssl: bool = True
    influx_measurement: str = "elto1sec_box"

    # InfluxDB BORNE
    influx_borne_host: str = "tsdbe.nidec-asi-online.com"
    influx_borne_port: int = 443
    influx_borne_user: str = ""
    influx_borne_password: str = ""
    influx_borne_database: str = "Elto"
    influx_borne_ssl: bool = True
    influx_borne_verify_ssl: bool = True
    influx_borne_measurement: str = "elto1sec_borne"

    # App
    app_timezone: str = "Europe/Zurich"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env"}


settings = Settings()
