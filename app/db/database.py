import os
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL und SUPABASE_KEY müssen als Umgebungsvariablen gesetzt sein!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_device_coordinates(device_id: int):
    response = supabase.table("devices").select("device_id, lat, lon").eq("device_id", device_id).execute()

    if not response.data:
        return None
    
    return response.data

def get_readings_for_device(device_id: int):
    now = datetime.now(timezone.utc)
    time_limit = (now - timedelta(hours=1)).isoformat()

    response = supabase.table("thermostat_readings") \
        .select("device_id, timestamp, actual_temperature, set_temperature") \
        .eq("device_id", device_id) \
        .gte("timestamp", time_limit) \
        .lte("timestamp", now) \
        .order("timestamp", desc=False) \
        .execute()

    if not response.data:
        return "Error. No data found."
    
    return response.data
