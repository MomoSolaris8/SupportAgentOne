import pytest

from supportagent.mcp_servers.http import ToolConfigurationError
from supportagent.mcp_servers.weather_mcp import tools


def test_weather_falls_back_to_open_meteo_without_google_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_WEATHER_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    def fake_request_json(method, url, **kwargs):
        if url == tools.OPEN_METEO_GEOCODING_URL:
            return {
                "results": [
                    {
                        "name": "Zurich",
                        "country": "Switzerland",
                        "latitude": 47.3769,
                        "longitude": 8.5417,
                        "timezone": "Europe/Zurich",
                    }
                ]
            }
        if url == tools.OPEN_METEO_FORECAST_URL:
            return {"current": {"temperature_2m": 20}, "daily": {}}
        raise AssertionError(url)

    monkeypatch.setattr(tools, "request_json", fake_request_json)
    result = tools.get_weather(location="Zurich")

    assert result["provider"] == "open_meteo"
    assert result["resolved_location"]["label"] == "Zurich, Switzerland"


def test_weather_geocodes_and_calls_google_weather(monkeypatch):
    calls = []

    def fake_request_json(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url == tools.GEOCODING_URL:
            return {
                "results": [
                    {
                        "formatted_address": "Zurich, Switzerland",
                        "geometry": {"location": {"lat": 47.3769, "lng": 8.5417}},
                    }
                ]
            }
        if url.endswith("/currentConditions:lookup"):
            return {"temperature": {"degrees": 20}}
        if url.endswith("/forecast/days:lookup"):
            return {"forecastDays": []}
        raise AssertionError(url)

    monkeypatch.setattr(tools, "request_json", fake_request_json)
    result = tools.get_weather(location="Zurich", days=2, api_key="key")

    assert result["provider"] == "google_weather"
    assert result["resolved_location"]["label"] == "Zurich, Switzerland"
    assert calls[1][2]["params"]["location.latitude"] == 47.3769
    assert calls[2][2]["params"]["days"] == 2
