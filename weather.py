import requests
from datetime import datetime

# API Key and Base URL for Visual Crossing API
API_KEY = "AB4UEP2GLGCYG4RVTADXUB2LL"  # Replace with your Visual Crossing API key
BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"

def get_14_day_forecast(latitude, longitude):
    """
    Fetches the 14-day weather forecast for a specific latitude and longitude.
    
    Parameters:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        
    Returns:
        list: 14-day forecast data including temperature, conditions, and other details.
    """
    url = f"{BASE_URL}{latitude},{longitude}"
    params = {
        "unitGroup": "metric",  # Use metric units (Celsius, etc.)
        "key": API_KEY,         # Your API key
        "include": "days",      # Include daily forecast data
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        weather_data = response.json()
        
        forecast = []
        for day in weather_data.get("days", []):
            forecast.append({
                "date": day.get("datetime"),  # The date of the day forecast
                "temperature": day.get("temp"),  # Day temperature
                "conditions": day.get("conditions"),  # Weather conditions (e.g., clear, rain)
                "rain": day.get("precip", 0),  # Precipitation in mm
                "snow": day.get("snow", 0),  # Snowfall in mm
            })
        
        return forecast
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return []


def will_it_rain_or_snow(latitude, longitude, start_datetime, end_datetime):
    """
    Checks if it will rain or snow between two datetime values at a specific location.
    
    Parameters:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        start_datetime (str): Start date and time in ISO format (e.g., '2024-11-16T14:00:00').
        end_datetime (str): End date and time in ISO format (e.g., '2024-11-17T14:00:00').
        
    Returns:
        list: List of times when rain or snow is forecasted.
    """
    url = f"{BASE_URL}{latitude},{longitude}"
    params = {
        "unitGroup": "metric",
        "key": API_KEY,
        "include": "hours",  # Include hourly data
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        weather_data = response.json()
        hourly_data = weather_data.get("days", [])
        
        rain_or_snow_forecast = []
        start_dt = datetime.fromisoformat(start_datetime)
        end_dt = datetime.fromisoformat(end_datetime)
        
        for day in hourly_data:
            day_date = day.get("datetime")  # The date of the day forecast (e.g., '2024-11-16')
            for hour in day.get("hours", []):
                hour_time = f"{day_date}T{hour['datetime']}"  # Combine date and time
                try:
                    hour_time = datetime.fromisoformat(hour_time)
                except ValueError as ve:
                    print(f"Invalid datetime format: {ve}")
                    continue
                
                if start_dt <= hour_time <= end_dt:
                    # Check for rain or snow in the conditions
                    if "rain" in hour.get("conditions", "").lower() or "snow" in hour.get("conditions", "").lower():
                        rain_or_snow_forecast.append({
                            "datetime": hour_time.isoformat(),
                            "temperature": hour.get("temp"),
                            "conditions": hour.get("conditions"),
                            "rain": hour.get("precip", 0),  # Precipitation (rain) in mm
                            "snow": hour.get("snow", 0),  # Snowfall in mm
                        })
        
        return rain_or_snow_forecast
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return []

def check_rain_or_snow_for_day(latitude, longitude, date):
    """
    Checks whether it will rain or snow on a particular day for a given location.
    
    Parameters:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        date (str): The date to check in ISO format (e.g., '2024-11-17').
        
    Returns:
        dict: Contains rain or snow status, or None if no rain or snow is expected.
    """
    # Parse the date to ensure we are looking at a valid day
    target_date = datetime.strptime(date, "%Y-%m-%d").date()  # Parse only the date part

    # Call the API to get hourly data for the given day (same logic as before)
    url = f"{BASE_URL}{latitude},{longitude}/{target_date.year}-{target_date.month:02d}-{target_date.day:02d}"
    params = {
        "unitGroup": "metric", 
        "key": API_KEY,
        "include": "hours"  # We need hourly data to detect rain/snow
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        weather_data = response.json()
        
        # Flag to track if rain or snow is detected
        rain_detected = False
        snow_detected = False
        
        # Loop through the hourly data for the day
        for hour in weather_data.get("days", [])[0].get("hours", []):
            if hour.get('rain', 0) > 0:
                rain_detected = True
            if hour.get('snow', 0) > 0:
                snow_detected = True

        # Return the result indicating if rain or snow is expected
        return {
            "rain": rain_detected,
            "snow": snow_detected
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

# Example usage:
if __name__ == "__main__":
    # Example coordinates and datetime
    latitude = 51.509865  # Latitude for London
    longitude = -0.118092 # Longitude for London
    start_datetime = "2024-11-16T14:00:00"  # Start time
    end_datetime = "2024-11-17T14:00:00"    # End time
    
    # Check for rain or snow
    rain_or_snow_times = will_it_rain_or_snow(latitude, longitude, start_datetime, end_datetime)
    
    if rain_or_snow_times:
        print(f"Rain or Snow is expected between {start_datetime} and {end_datetime} at:")
        for forecast in rain_or_snow_times:
            print(f" - {forecast['datetime']}: {forecast['conditions']} at {forecast['temperature']}°C")
    else:
        print("No rain or snow expected between the specified times.")
