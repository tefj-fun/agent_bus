# Weather Toolkit

A comprehensive skill for fetching, analyzing, and interpreting weather data using the NOAA Weather API.

## Overview

The Weather Toolkit provides capabilities for:
- **Current conditions**: Real-time weather data for any US location
- **Multi-day forecasts**: Extended weather predictions
- **Pattern analysis**: Identify trends and anomalies in weather data

## Capabilities

### 1. weather-query
Fetch current weather conditions including temperature, humidity, wind, and precipitation.

**Usage:**
```python
# Get current weather for a location
weather = await get_current_weather("San Francisco, CA")
# Returns: temperature, conditions, humidity, wind speed/direction
```

### 2. weather-forecast
Retrieve multi-day forecasts with detailed hourly and daily predictions.

**Usage:**
```python
# Get 7-day forecast
forecast = await get_forecast("New York, NY", days=7)
# Returns: daily highs/lows, precipitation probability, conditions
```

### 3. weather-analysis
Analyze weather patterns, detect anomalies, and provide insights.

**Usage:**
```python
# Analyze recent weather trends
analysis = await analyze_weather_pattern("Chicago, IL", days_back=30)
# Returns: trends, anomalies, seasonal comparisons
```

## API Integration

This skill uses the NOAA National Weather Service API (weather.gov):
- **No API key required** - Public access
- **Coverage**: United States locations only
- **Rate limit**: 5 requests per second
- **Data freshness**: Updated hourly

## Required Tools

- `web_fetch` (required) - For API requests to weather.gov
- `exec` (optional) - For advanced data processing with system tools

## Dependencies

Install with:
```bash
pip install requests>=2.28.0 python-dateutil>=2.8.0
```

## Implementation Example

### Basic Weather Query

```python
import requests
from datetime import datetime

async def get_current_weather(location: str) -> dict:
    """
    Fetch current weather conditions for a location.
    
    Args:
        location: City, State format (e.g., "Seattle, WA")
    
    Returns:
        Dictionary with weather data:
        - temperature: Current temp in Fahrenheit
        - conditions: Description (e.g., "Partly Cloudy")
        - humidity: Percentage
        - wind_speed: MPH
        - wind_direction: Cardinal direction
        - timestamp: ISO 8601 timestamp
    """
    # Step 1: Geocode location to lat/lon
    geocode_url = f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
    params = {
        "address": location,
        "benchmark": "Public_AR_Current",
        "format": "json"
    }
    
    geo_response = requests.get(geocode_url, params=params)
    geo_data = geo_response.json()
    
    if not geo_data.get("result", {}).get("addressMatches"):
        raise ValueError(f"Location not found: {location}")
    
    coords = geo_data["result"]["addressMatches"][0]["coordinates"]
    lat, lon = coords["y"], coords["x"]
    
    # Step 2: Get weather station
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    points_response = requests.get(points_url)
    points_data = points_response.json()
    
    # Step 3: Fetch current conditions
    stations_url = points_data["properties"]["observationStations"]
    stations_response = requests.get(stations_url)
    station_id = stations_response.json()["features"][0]["properties"]["stationIdentifier"]
    
    obs_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    obs_response = requests.get(obs_url)
    obs_data = obs_response.json()["properties"]
    
    return {
        "temperature": obs_data["temperature"]["value"],
        "conditions": obs_data["textDescription"],
        "humidity": obs_data["relativeHumidity"]["value"],
        "wind_speed": obs_data["windSpeed"]["value"],
        "wind_direction": obs_data["windDirection"]["value"],
        "timestamp": obs_data["timestamp"]
    }
```

### Forecast Retrieval

```python
async def get_forecast(location: str, days: int = 7) -> list:
    """
    Get multi-day forecast for a location.
    
    Args:
        location: City, State format
        days: Number of days to forecast (1-7)
    
    Returns:
        List of daily forecast dictionaries
    """
    # Geocode and get forecast endpoint (similar to above)
    # ...
    
    forecast_url = points_data["properties"]["forecast"]
    forecast_response = requests.get(forecast_url)
    forecast_data = forecast_response.json()
    
    periods = forecast_data["properties"]["periods"][:days*2]  # Day + night
    
    daily_forecasts = []
    for i in range(0, len(periods), 2):
        day_period = periods[i]
        night_period = periods[i+1] if i+1 < len(periods) else None
        
        daily_forecasts.append({
            "date": day_period["startTime"][:10],
            "high": day_period["temperature"],
            "low": night_period["temperature"] if night_period else None,
            "conditions": day_period["shortForecast"],
            "precipitation_probability": day_period.get("probabilityOfPrecipitation", {}).get("value", 0),
            "wind": f"{day_period['windSpeed']} {day_period['windDirection']}"
        })
    
    return daily_forecasts
```

## Best Practices

1. **Error Handling**: Always wrap API calls in try/except blocks
2. **Rate Limiting**: Respect the 5 req/sec limit with backoff
3. **Caching**: Cache geocoding results to reduce API calls
4. **Validation**: Validate location input before API calls
5. **Logging**: Log API errors for debugging

## Example Use Cases

### Travel Planning
```
"What's the weather forecast for Miami next week?"
→ Use weather-forecast capability for 7-day outlook
```

### Event Planning
```
"Will it rain in Portland this weekend?"
→ Use weather-forecast + precipitation probability
```

### Pattern Analysis
```
"Has this month been warmer than usual in Denver?"
→ Use weather-analysis to compare against historical averages
```

## Limitations

- **Geographic Coverage**: US locations only (NOAA limitation)
- **Historical Data**: Limited to recent observations
- **Update Frequency**: Hourly updates, not real-time
- **Rate Limits**: Max 5 requests/second

## Testing

Run the included test suite:
```bash
pytest tests/test_weather_toolkit.py -v
```

## Contributing

To extend this skill:
1. Add new capabilities to `skill.json`
2. Document in this file
3. Add tests for new functionality
4. Update version number (semantic versioning)

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- GitHub: https://github.com/example/weather-toolkit/issues
- Documentation: https://weather-toolkit.example.com/docs
