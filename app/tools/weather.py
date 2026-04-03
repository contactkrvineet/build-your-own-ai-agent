"""
Weather tool — fetches current weather via OpenWeatherMap API.
Toggle in config.yaml → tools.weather.enabled
API key in .env → OPENWEATHERMAP_API_KEY
"""

from __future__ import annotations

from typing import Optional, Type

import httpx
from pydantic import BaseModel, Field

from app.config.settings import get_settings
from app.tools.base import AskVineetBaseTool
from app.utils.logger import logger


class WeatherInput(BaseModel):
    city: str = Field(
        description="City name to get weather for, e.g. 'London' or 'New York,US'"
    )
    units: Optional[str] = Field(
        default=None,
        description="Units: 'metric' (Celsius) | 'imperial' (Fahrenheit) | 'standard' (Kelvin)",
    )


class WeatherTool(AskVineetBaseTool):
    name: str = "get_weather"
    description: str = (
        "Get the current weather for a city. "
        "Use this when the user asks about weather, temperature, or conditions in a location."
    )
    args_schema: Type[BaseModel] = WeatherInput

    @classmethod
    def is_enabled(cls) -> bool:
        s = get_settings()
        return s.tool_weather_enabled and bool(s.openweathermap_api_key)

    def _run(self, city: str, units: Optional[str] = None) -> str:
        s = get_settings()
        api_key = s.openweathermap_api_key
        if not api_key:
            return "Weather tool is not configured. Set OPENWEATHERMAP_API_KEY in .env"

        effective_units = units or s.tool_weather_units

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": city,
                "appid": api_key,
                "units": effective_units,
            }
            resp = httpx.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            description = data["weather"][0]["description"].capitalize()
            wind_speed = data["wind"]["speed"]
            city_name = data["name"]
            country = data["sys"]["country"]

            unit_symbol = {"metric": "°C", "imperial": "°F", "standard": "K"}.get(
                effective_units, "°C"
            )

            return (
                f"Weather in {city_name}, {country}:\n"
                f"  Condition: {description}\n"
                f"  Temperature: {temp}{unit_symbol} (feels like {feels_like}{unit_symbol})\n"
                f"  Humidity: {humidity}%\n"
                f"  Wind Speed: {wind_speed} m/s"
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"City '{city}' not found. Try a more specific name, e.g. 'London,GB'."
            logger.error(f"Weather API HTTP error: {e}")
            return f"Weather API error: {e.response.status_code}"
        except Exception as e:
            logger.error(f"Weather tool failed: {e}")
            return f"Failed to fetch weather: {str(e)}"
