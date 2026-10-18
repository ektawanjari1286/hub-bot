
def is_weather_question(message):
    text = message.lower()

    keywords = [
        "weather",
        "temperature",
        "humidity",
        "rain forecast",
        "will it rain",
        "mausam",
        "kitna temperature",
        "बारिश",
        "मौसम",
    ]

    return any(word in text for word in keywords)


def get_nagpur_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=21.1458"
        "&longitude=79.0882"
        "&current=temperature_2m,relative_humidity_2m,"
        "apparent_temperature,is_day,precipitation,"
        "weather_code,wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max"
        "&timezone=Asia%2FKolkata"
        "&forecast_days=1"
    )

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Hub-Bot/1.0"},
        )

        with urllib.request.urlopen(request, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))

        current = data["current"]
        daily = data.get("daily", {})

        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snowfall",
            73: "Moderate snowfall",
            75: "Heavy snowfall",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail",
        }

        code = current.get("weather_code")
        condition = weather_codes.get(code, "Conditions unavailable")

        temperature = current.get("temperature_2m")
        feels_like = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        precipitation = current.get("precipitation")

        lines = [
            "Current weather in Nagpur, Maharashtra:",
            f"Condition: {condition}.",
        ]

        if temperature is not None:
            lines.append(f"Temperature: {temperature}°C.")

        if feels_like is not None:
            lines.append(f"Feels like: {feels_like}°C.")

        if humidity is not None:
            lines.append(f"Humidity: {humidity}%.")

        if wind is not None:
            lines.append(f"Wind speed: {wind} km/h.")

        if precipitation is not None:
            lines.append(f"Current precipitation: {precipitation} mm.")

        maximum = daily.get("temperature_2m_max", [None])[0]
        minimum = daily.get("temperature_2m_min", [None])[0]
        rain_chance = daily.get(
            "precipitation_probability_max", [None]
        )[0]

        if maximum is not None and minimum is not None:
            lines.append(
                f"Today's forecast: {minimum}°C to {maximum}°C."
            )

        if rain_chance is not None:
            lines.append(
                f"Maximum forecast precipitation probability: "
                f"{rain_chance}%."
            )

        lines.append(
            "Source: Open-Meteo (https://open-meteo.com/)"
        )

        return "\n".join(lines)

    except Exception:
        return None
