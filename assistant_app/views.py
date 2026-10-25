from google.genai import types
import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

from google import genai

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import ChatMessage


# ---------------- LOGIN ----------------

def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "assistant_app/login.html")


# ---------------- REGISTER ----------------

def register_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get(
            "confirm_password",
            request.POST.get("password2", ""),
        )

        if not username or not password:
            messages.error(
                request, "Username and password are required."
            )
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            messages.success(
                request, "Account created. Please log in."
            )
            return redirect("login")

    return render(request, "assistant_app/register.html")


# ---------------- DASHBOARD ----------------

@login_required(login_url="login")
def dashboard(request):
    return render(request, "assistant_app/dashboard.html")


# ---------------- LOGOUT ----------------

def logout_page(request):
    logout(request)
    return redirect("login")


# ---------------- CURRENT TIME ----------------



def is_time_question(message):
    text = message.lower().strip()
    text = " ".join(text.split())
    text = text.rstrip("?!., ")

    # Single-word commands
    if text in {
        "time", "date", "today", "day",
        "samay", "tareekh", "tarikh", "aaj"
    }:
        return True

    keywords = [
        "current time",
        "what time",
        "what is the time",
        "time now",
        "current date",
        "today's date",
        "today date",
        "what is today's date",
        "what is the date",
        "what is the date today",
        "what date is it",
        "what day is today",
        "today's day",
        "aaj ki date",
        "aaj ka date",
        "aaj ka din",
        "aaj kaun sa din",
        "aaj kya date hai",
        "kitne baje",
        "abhi time",
        "abhi kitna baj raha hai",
    ]

    return any(word in text for word in keywords)


def get_current_time():
    now = datetime.now(ZoneInfo("Asia/Kolkata"))

    return (
        f"Current date: {now.strftime('%d %B %Y')}\n"
        f"Current time: {now.strftime('%I:%M:%S %p')}\n"
        f"Day: {now.strftime('%A')}\n"
        "Timezone: India Standard Time (IST)"
    )


# ---------------- WEATHER ----------------

def is_weather_question(message):
    text = message.lower().strip()
    text = text.replace("whether", "weather")

    keywords = [
        "weather",
        "temperature",
        "humidity",
        "rain forecast",
        "will it rain",
        "rain today",
        "forecast",
        "mausam",
        "mausam kaisa",
        "kitna temperature",
        "बारिश",
        "मौसम",
    ]

    return any(word in text for word in keywords)


def get_nagpur_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=21.1458&longitude=79.0882"
        "&current=temperature_2m,relative_humidity_2m,"
        "apparent_temperature,precipitation,weather_code,"
        "wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max"
        "&timezone=Asia%2FKolkata&forecast_days=1"
    )

    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Heavy rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail",
    }

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Hub-Bot/1.0"},
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        current = data["current"]
        daily = data.get("daily", {})

        code = current.get("weather_code")
        condition = weather_codes.get(code, "Unavailable")

        lines = [
            "Live weather for Nagpur, Maharashtra:",
            f"Condition: {condition}",
            f"Temperature: {current.get('temperature_2m')}°C",
            f"Feels like: {current.get('apparent_temperature')}°C",
            f"Humidity: {current.get('relative_humidity_2m')}%",
            f"Wind speed: {current.get('wind_speed_10m')} km/h",
        ]

        precipitation = current.get("precipitation")
        if precipitation is not None:
            lines.append(f"Precipitation: {precipitation} mm")

        minimum = daily.get("temperature_2m_min", [None])[0]
        maximum = daily.get("temperature_2m_max", [None])[0]
        rain_chance = daily.get(
            "precipitation_probability_max", [None]
        )[0]

        if minimum is not None and maximum is not None:
            lines.append(
                f"Today's temperature range: {minimum}°C to {maximum}°C"
            )

        if rain_chance is not None:
            lines.append(
                f"Maximum rain probability today: {rain_chance}%"
            )

        lines.append("Source: Open-Meteo (open-meteo.com)")
        return "\n".join(lines)

    except Exception as error:
        # Keep the API key and technical details out of the chat UI.
        print(
            f"Hub-Bot weather error: "
            f"{type(error).__name__}: {error}"
        )
        return None

# ---------------- GEMINI AI ----------------


def ask_gemini(message):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=(
            "You are Hub-Bot, a helpful AI assistant. "
            "Answer in the same language as the user. "
            "For current events, recent news, latest facts, "
            "and other time-sensitive questions, use Google "
            "Search to verify current information. "
            "Do not guess current facts. "
            "Keep answers clear and concise.\n\n"
            f"User: {message}"
        ),
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ]
        ),
    )

    reply = response.text

    if not reply or not reply.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return reply.strip()

# ---------------- SAVE CHAT MESSAGES ----------------

def save_chat_message(user, role, content):
    return ChatMessage.objects.create(
        user=user,
        role=role,
        content=content,
    )


# ---------------- CHAT API ----------------

@login_required(login_url="login")
@require_POST
def chat_api(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        user_message = body.get("message", "").strip()

        if not isinstance(user_message, str) or not user_message:
            return JsonResponse(
                {"error": "Please enter a message."},
                status=400,
            )

        # Save the user's message.
        save_chat_message(request.user, "user", user_message)

        if is_time_question(user_message):
            reply = get_current_time()

        elif is_weather_question(user_message):
            reply = get_nagpur_weather()

            if reply is None:
                reply = (
                    "I couldn't retrieve live weather for Nagpur. "
                    "Please check your internet connection and try again."
                )

        else:
            try:
                reply = ask_gemini(user_message)

            except Exception:
                # Keep technical details and API keys out of the UI.
                return JsonResponse(
                    {
                        "error": (
                            "Gemini se response nahi mil raha. "
                            "API key, model availability aur internet "
                            "connection check karo."
                        )
                    },
                    status=503,
                )

        # Save the assistant's response.
        save_chat_message(request.user, "assistant", reply)

        return JsonResponse({"reply": reply})

    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid request data."},
            status=400,
        )

    except Exception:
        return JsonResponse(
            {"error": "Something went wrong. Please try again."},
            status=500,
        )


# ---------------- CHAT HISTORY API ----------------

@login_required(login_url="login")
def chat_history_api(request):
    messages_list = ChatMessage.objects.filter(
        user=request.user
    ).order_by("created_at")

    return JsonResponse({
        "messages": [
            {
                "role": item.role,
                "content": item.content,
                "created_at": timezone.localtime(
                    item.created_at
                ).strftime("%d %b %Y, %I:%M %p"),
            }
            for item in messages_list
        ]
    })


# ---------------- CLEAR CHAT HISTORY API ----------------

@login_required(login_url="login")
@require_POST
def clear_chat_history_api(request):
    ChatMessage.objects.filter(user=request.user).delete()

    return JsonResponse({
        "success": True,
        "message": "Your chat history has been cleared.",
    })
