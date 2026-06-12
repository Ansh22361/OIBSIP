# SkyCast Weather

A graphical weather application built with **Tkinter** — no API key required.

## Features

- **Location search** — type any city name (e.g. `London`, `Tokyo`, `New York`)
- **Auto-detect location** — uses your public IP to approximate GPS (desktop-friendly)
- **Current conditions** — temperature, feels-like, weather icon & description
- **Detail metrics** — wind speed & direction, humidity, precipitation, pressure
- **Hourly forecast** — next 24 hours with icons, wind, and rain probability
- **7-day forecast** — daily high/low, conditions, wind, and precipitation

## Requirements

- Python 3.8+
- Tkinter (included with standard Python on Windows)
- Internet connection

No third-party packages required — uses only the Python standard library.

## Run

```bash
cd weather_app
python weather_app.py
```

Or double-click `run.bat` on Windows.

## Data sources

- [Open-Meteo](https://open-meteo.com/) — weather forecasts (free, no API key)
- [ip-api.com](http://ip-api.com/) — IP-based geolocation for "My Location"

## Notes

- True device GPS is not available in standard Tkinter on desktop; **📍 My Location** uses IP geolocation, which is accurate to city level.
- Weather icons use Unicode emoji mapped from WMO weather codes.
