import httpx
from .database import get_device_coordinates
from ..models.models import Temperature
from datetime import datetime, timedelta, timezone

def get_current_temperature(device_id: int):
    device = get_device_coordinates(device_id)

    if not device:
        return None

    lat, lon = device[0]["lat"], device[0]["lon"]

    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:00")
    end_time = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:00")

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m"
        f"&start={start_time}&end={end_time}"
        f"&timezone=UTC"
    )

    try:
        response = httpx.get(url, timeout=5.0)
        data = response.json()

        times = data.get("hourly", {}).get("time", [])
        temps = data.get("hourly", {}).get("temperature_2m", [])

        if not times or not temps:
            return None

        # Parse timestamps and pair with temps
        parsed_data = [
            (datetime.fromisoformat(t).replace(tzinfo=timezone.utc), temp)
            for t, temp in zip(times, temps)
        ]

        # Sort by time just in case
        parsed_data.sort(key=lambda x: x[0])

        past = None
        future = None

        for t, temp in parsed_data:
            if t <= now:
                past = (t, temp)
            elif t > now and future is None:
                future = (t, temp)
                break

        return Temperature(
            last_temp=round(past[1], 1) if past else None,
            next_temp=round(future[1], 1) if future else None,
            current_time=now.isoformat()
        )

    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None