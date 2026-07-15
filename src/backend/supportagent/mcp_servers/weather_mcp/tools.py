import os
from typing import Any

from pydantic import Field
from pydantic.fields import FieldInfo

from supportagent.mcp_servers.http import ToolConfigurationError, request_json

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_WEATHER_BASE_URL = os.environ.get("GOOGLE_WEATHER_BASE_URL", "https://weather.googleapis.com/v1")
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _api_key(api_key: str | None) -> str:
    if isinstance(api_key, FieldInfo):
        api_key = None
    key = api_key or os.environ.get("GOOGLE_WEATHER_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        raise ToolConfigurationError(
            "Missing Google Weather API key. Pass api_key or set GOOGLE_WEATHER_API_KEY."
        )
    return key


def _optional_api_key(api_key: str | None) -> str | None:
    if isinstance(api_key, FieldInfo):
        api_key = None
    return api_key or os.environ.get("GOOGLE_WEATHER_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")


def _resolve_location(location: str | None, latitude: float | None, longitude: float | None, key: str) -> dict[str, Any]:
    if latitude is not None and longitude is not None:
        return {"latitude": latitude, "longitude": longitude, "label": location}
    if not location:
        raise ToolConfigurationError("Pass either location or latitude plus longitude.")

    geocode = request_json("GET", GEOCODING_URL, api_key=key, params={"address": location})
    results = geocode.get("results", []) if isinstance(geocode, dict) else []
    if not results:
        return {"ok": False, "error": f"Could not geocode location: {location}"}

    first = results[0]
    lat_lng = first["geometry"]["location"]
    return {
        "latitude": lat_lng["lat"],
        "longitude": lat_lng["lng"],
        "label": first.get("formatted_address", location),
    }


def _resolve_location_open_meteo(
    location: str | None,
    latitude: float | None,
    longitude: float | None,
) -> dict[str, Any]:
    if latitude is not None and longitude is not None:
        return {"latitude": latitude, "longitude": longitude, "label": location}
    if not location:
        raise ToolConfigurationError("Pass either location or latitude plus longitude.")

    geocode = request_json(
        "GET",
        OPEN_METEO_GEOCODING_URL,
        params={"name": location, "count": 1, "language": "de", "format": "json"},
    )
    results = geocode.get("results", []) if isinstance(geocode, dict) else []
    if not results:
        return {"ok": False, "error": f"Could not geocode location: {location}"}

    first = results[0]
    label_parts = [
        first.get("name"),
        first.get("admin1"),
        first.get("country"),
    ]
    return {
        "latitude": first["latitude"],
        "longitude": first["longitude"],
        "label": ", ".join(part for part in label_parts if part),
        "timezone": first.get("timezone", "auto"),
    }


def _get_weather_open_meteo(
    location: str | None,
    latitude: float | None,
    longitude: float | None,
    days: int,
) -> dict[str, Any]:
    resolved = _resolve_location_open_meteo(location, latitude, longitude)
    if resolved.get("ok") is False:
        return resolved

    forecast = request_json(
        "GET",
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": resolved["latitude"],
            "longitude": resolved["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "forecast_days": days,
            "timezone": resolved.get("timezone", "auto"),
        },
    )
    return {
        "provider": "open_meteo",
        "resolved_location": resolved,
        "current": forecast.get("current", {}) if isinstance(forecast, dict) else {},
        "daily": forecast.get("daily", {}) if isinstance(forecast, dict) else {},
        "raw": forecast,
    }


def get_weather(
    location: str | None = Field(default=None, description="Location text, e.g. Zurich or Berlin."),
    latitude: float | None = Field(default=None, description="Latitude. Provide with longitude to skip geocoding."),
    longitude: float | None = Field(default=None, description="Longitude. Provide with latitude to skip geocoding."),
    days: int = Field(default=3, ge=1, le=10, description="Forecast days to request."),
    api_key: str | None = Field(default=None, description="Google Weather API key."),
) -> dict[str, Any]:
    """Get current weather and daily forecast from Google Weather."""
    location = None if isinstance(location, FieldInfo) else location
    latitude = None if isinstance(latitude, FieldInfo) else latitude
    longitude = None if isinstance(longitude, FieldInfo) else longitude
    days = 3 if isinstance(days, FieldInfo) else days
    key = _optional_api_key(api_key)
    if not key:
        return _get_weather_open_meteo(location, latitude, longitude, days)

    resolved = _resolve_location(location, latitude, longitude, key)
    if resolved.get("ok") is False:
        return _get_weather_open_meteo(location, latitude, longitude, days)

    params = {
        "location.latitude": resolved["latitude"],
        "location.longitude": resolved["longitude"],
    }
    current = request_json(
        "GET",
        f"{GOOGLE_WEATHER_BASE_URL}/currentConditions:lookup",
        api_key=key,
        params=params,
    )
    forecast = request_json(
        "GET",
        f"{GOOGLE_WEATHER_BASE_URL}/forecast/days:lookup",
        api_key=key,
        params={**params, "days": days},
    )
    if isinstance(current, dict) and current.get("ok") is False:
        return _get_weather_open_meteo(location, latitude, longitude, days)
    if isinstance(forecast, dict) and forecast.get("ok") is False:
        return _get_weather_open_meteo(location, latitude, longitude, days)
    return {
        "provider": "google_weather",
        "resolved_location": resolved,
        "current": current,
        "forecast": forecast,
    }


WEATHER_TOOLS = [get_weather]
