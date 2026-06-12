"""Open-Meteo and IP geolocation client — no API key required."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
import json
from typing import Any, Dict, List, Optional, Tuple


class WeatherAPIError(Exception):
    pass


def _get(url: str, timeout: int = 12) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "SecureWeather/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        raise WeatherAPIError(f"Network error: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise WeatherAPIError("Invalid response from weather service") from exc


def geocode_location(query: str) -> List[Dict[str, Any]]:
    q = urllib.parse.quote(query.strip())
    if not q:
        raise WeatherAPIError("Please enter a city or location name.")
    url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        f"name={q}&count=8&language=en&format=json"
    )
    data = _get(url)
    results = data.get("results") or []
    if not results:
        raise WeatherAPIError(f"No locations found for '{query.strip()}'.")
    return results


def detect_location_by_ip() -> Tuple[float, float, str]:
    """Approximate location from public IP (desktop-friendly GPS alternative)."""
    data = _get("http://ip-api.com/json/?fields=status,message,lat,lon,city,regionName,country")
    if data.get("status") != "success":
        raise WeatherAPIError(data.get("message", "Could not detect your location."))
    lat, lon = data["lat"], data["lon"]
    parts = [data.get("city"), data.get("regionName"), data.get("country")]
    label = ", ".join(p for p in parts if p)
    return lat, lon, label


def fetch_weather(latitude: float, longitude: float) -> dict:
    params = urllib.parse.urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "surface_pressure",
                    "is_day",
                ]
            ),
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "precipitation_probability",
                    "weather_code",
                    "wind_speed_10m",
                    "relative_humidity_2m",
                ]
            ),
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                    "sunrise",
                    "sunset",
                ]
            ),
            "forecast_days": 7,
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    return _get(url)


# WMO Weather interpretation codes (WW) → icon + description
WEATHER_CODES = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Depositing rime fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Moderate drizzle"),
    55: ("🌧️", "Dense drizzle"),
    56: ("🌧️", "Freezing drizzle"),
    57: ("🌧️", "Dense freezing drizzle"),
    61: ("🌧️", "Slight rain"),
    63: ("🌧️", "Moderate rain"),
    65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Freezing rain"),
    67: ("🌧️", "Heavy freezing rain"),
    71: ("🌨️", "Slight snow"),
    73: ("🌨️", "Moderate snow"),
    75: ("❄️", "Heavy snow"),
    77: ("🌨️", "Snow grains"),
    80: ("🌦️", "Slight rain showers"),
    81: ("🌧️", "Moderate rain showers"),
    82: ("⛈️", "Violent rain showers"),
    85: ("🌨️", "Slight snow showers"),
    86: ("❄️", "Heavy snow showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm with hail"),
    99: ("⛈️", "Thunderstorm with heavy hail"),
}


def weather_info(code: Optional[int]) -> Tuple[str, str]:
    if code is None:
        return "🌡️", "Unknown"
    return WEATHER_CODES.get(code, ("🌡️", "Unknown"))


def wind_direction(degrees: Optional[float]) -> str:
    if degrees is None:
        return "—"
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((degrees + 22.5) / 45) % 8
    return dirs[idx]
