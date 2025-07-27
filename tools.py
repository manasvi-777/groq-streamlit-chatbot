import requests
import os
from dotenv import load_dotenv

load_dotenv()

FXRATESAPI_API_KEY = os.getenv("FXRATESAPI_API_KEY")
WEATHERAPI_API_KEY = os.getenv("WEATHERAPI_API_KEY")

def calculate(expression: str) -> str:
    """Evaluates a simple mathematical expression."""
    try:
        # Basic and unsafe eval for demonstration. For production, use a safer math parser.
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error calculating: {e}"

def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Converts currency using fxratesapi.com.
    Example: convert_currency(100, 'USD', 'EUR')
    """
    if not FXRATESAPI_API_KEY:
        return "Currency conversion service not configured (API key missing)."
    try:
        url = f"https://api.fxratesapi.com/latest?base={from_currency.upper()}&symbols={to_currency.upper()}&api_key={FXRATESAPI_API_KEY}"
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200 and data.get("rates") and to_currency.upper() in data["rates"]:
            rate = data["rates"][to_currency.upper()]
            converted_amount = amount * rate
            return f"{amount} {from_currency.upper()} is {converted_amount:.2f} {to_currency.upper()}"
        else:
            return f"Could not convert currency. Error: {data.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error during currency conversion: {e}"

def get_weather(location: str) -> str:
    """
    Gets the current weather forecast for a specified location using weatherapi.com.
    Example: get_weather('London')
    """
    if not WEATHERAPI_API_KEY:
        return "Weather service not configured (API key missing)."
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHERAPI_API_KEY}&q={location}"
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            current = data['current']
            location_info = data['location']
            condition = current['condition']['text']
            temp_c = current['temp_c']
            feels_like_c = current['feelslike_c']
            humidity = current['humidity']
            wind_kph = current['wind_kph']
            return (f"The current weather in {location_info['name']}, {location_info['country']} is "
                    f"{condition}. The temperature is {temp_c}°C (feels like {feels_like_c}°C). "
                    f"Humidity: {humidity}%, Wind: {wind_kph} km/h.")
        else:
            return f"Could not get weather for {location}. Error: {data.get('error', {}).get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error fetching weather: {e}"

# Define the tools for Groq API
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluates a mathematical expression and returns the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to evaluate (e.g., '2 + 2', '10 * 5 / 2')."
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Converts an amount from one currency to another using real-time exchange rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The amount of money to convert."
                    },
                    "from_currency": {
                        "type": "string",
                        "description": "The currency code to convert from (e.g., 'USD', 'EUR', 'GBP')."
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "The currency code to convert to (e.g., 'INR', 'JPY', 'AUD')."
                    }
                },
                "required": ["amount", "from_currency", "to_currency"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Gets the current weather conditions for a specified city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city or location to get the weather for (e.g., 'New York', 'Tokyo')."
                    }
                },
                "required": ["location"]
            }
        }
    }
]

# Map tool names to their functions
TOOL_MAP = {
    "calculate": calculate,
    "convert_currency": convert_currency,
    "get_weather": get_weather,
}