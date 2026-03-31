from influxdb import InfluxDBClient

from backend.config import settings

_client_box: InfluxDBClient | None = None
_client_borne: InfluxDBClient | None = None


def get_influx_client(source: str = "box") -> InfluxDBClient:
    global _client_box, _client_borne
    if source == "borne":
        if _client_borne is None:
            _client_borne = InfluxDBClient(
                host=settings.influx_borne_host,
                port=settings.influx_borne_port,
                username=settings.influx_borne_user,
                password=settings.influx_borne_password,
                database=settings.influx_borne_database,
                ssl=settings.influx_borne_ssl,
                verify_ssl=settings.influx_borne_verify_ssl,
            )
        return _client_borne
    else:
        if _client_box is None:
            _client_box = InfluxDBClient(
                host=settings.influx_host,
                port=settings.influx_port,
                username=settings.influx_user,
                password=settings.influx_password,
                database=settings.influx_database,
                ssl=settings.influx_ssl,
                verify_ssl=settings.influx_verify_ssl,
            )
        return _client_box
