"""Tests for external tool integrations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestWeatherTool:
    def test_is_disabled_without_api_key(self):
        from app.tools.weather import WeatherTool

        with patch("app.tools.weather.get_settings") as mock_settings:
            mock_settings.return_value.tool_weather_enabled = True
            mock_settings.return_value.openweathermap_api_key = None
            assert WeatherTool.is_enabled() is False

    @patch("app.tools.weather.httpx.get")
    def test_returns_formatted_weather(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "main": {"temp": 22.5, "feels_like": 21.0, "humidity": 65},
            "weather": [{"description": "clear sky"}],
            "wind": {"speed": 3.5},
            "name": "London",
            "sys": {"country": "GB"},
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from app.tools.weather import WeatherTool

        tool = WeatherTool()
        result = tool._run("London")

        assert "London" in result
        assert "22.5" in result
        assert "clear sky" in result.lower()

    @patch("app.tools.weather.httpx.get")
    def test_city_not_found(self, mock_get):
        import httpx

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_resp
        )

        from app.tools.weather import WeatherTool

        tool = WeatherTool()
        result = tool._run("NonExistentCityXYZ")
        assert "not found" in result.lower()


class TestCustomAPITool:
    @patch("app.tools.custom_api.httpx.request")
    def test_get_request_returns_response(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "value", "status": "ok"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        with patch("app.tools.custom_api.get_settings") as mock_settings:
            mock_settings.return_value.tool_custom_api_enabled = True
            mock_settings.return_value.custom_api_endpoint = "https://api.example.com"
            mock_settings.return_value.custom_api_header_name = None
            mock_settings.return_value.custom_api_header_value = None

            from app.tools.custom_api import CustomAPITool

            tool = CustomAPITool()
            result = tool._run()

        assert "200" in result
        assert "data" in result

    def test_disabled_tool_returns_message(self):
        with patch("app.tools.custom_api.get_settings") as mock_settings:
            mock_settings.return_value.tool_custom_api_enabled = False
            mock_settings.return_value.custom_api_endpoint = "https://api.example.com"

            from app.tools.custom_api import CustomAPITool

            tool = CustomAPITool()
            result = tool._run()

        assert "disabled" in result.lower()


class TestToolBase:
    def test_tool_has_name_and_description(self):
        from app.tools.weather import WeatherTool

        tool = WeatherTool()
        assert isinstance(tool.name, str) and len(tool.name) > 0
        assert isinstance(tool.description, str) and len(tool.description) > 0

    def test_tool_is_langchain_base_tool(self):
        from langchain_core.tools import BaseTool

        from app.tools.weather import WeatherTool

        tool = WeatherTool()
        assert isinstance(tool, BaseTool)
