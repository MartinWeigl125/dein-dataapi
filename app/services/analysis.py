from datetime import datetime
from typing import Optional
from fastapi.responses import JSONResponse
from ..db.database import get_readings_for_device
from ..db.weatherdata import get_current_temperature
from ..models.models import Temperature
import numpy as np
from scipy.stats import linregress


def analyze_device_status(device_id: int):
    readings = get_readings_for_device(device_id)
    temperature: Optional[Temperature] = get_current_temperature(device_id)

    if isinstance(readings, str) and readings.startswith("Error"):
        return JSONResponse(
            status_code=404,
            content=f"No data for device with ID={device_id}."
        )

    if not temperature:
        return JSONResponse(
            status_code=502,
            content=f"Failed to fetch weather data for device ID={device_id}."
        )

    if len(readings) < 5:
        return JSONResponse(
            status_code=400,
            content=f"Not enough data for device with ID={device_id}."
        )

    set_temps = [r["set_temperature"] for r in readings]
    actual_temps = [r["actual_temperature"] for r in readings]
    # timestamps = [datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) for r in readings]

    latest_set = set_temps[-1]
    latest_actual = actual_temps[-1]

    # mit Linearer Regression herausfinden, ob sich die aktuelle Temperatur der eingestellten annähert
    slope, _, _, _, _ = linregress(range(len(actual_temps)), actual_temps)
    trend_positive = bool(slope > 0) if latest_set > latest_actual else bool(slope < 0)

    # Wurde die eingestellte Temperatur geändert? Wann?
    setpoint_changed = len(set(set_temps)) > 1
    change_index = next((i for i in range(1, len(set_temps)) if set_temps[i] != set_temps[i-1]), None)

    # Hat sich die aktuelle Temperatur nach dem Umstellen in die richtige Richtung entwickelt?
    if setpoint_changed and change_index:
        t_before = actual_temps[change_index - 1]
        t_after = actual_temps[-1]
        set_before = set_temps[change_index - 1]
        set_after = set_temps[change_index]
        responded = abs(t_after - t_before) > 0.3 and (set_after - t_before) * (t_after - t_before) > 0
    else:
        responded = None

    # === Stabilität und Heizarbeitsabschätzung ===
    temp_diffs = [abs(s - a) for s, a in zip(set_temps, actual_temps)]
    max_deviation = max(temp_diffs)
    avg_deviation = sum(temp_diffs) / len(temp_diffs)

    heating_effort = sum(
        max(0, s - a) for s, a in zip(set_temps, actual_temps)
    ) / len(readings)

    # Außentemperatur einbeziehen
    outside_now = temperature.last_temp
    temp_diff_outside = latest_actual - outside_now

    tips = []

    # Verhältnis Außen-/Innenklima bewerten
    if latest_actual > latest_set + 1 and temp_diff_outside > 2:
        tips.append("Fenster öffnen - Raum überheizt, draußen ist es kühler.")
    elif latest_actual < latest_set - 1 and outside_now > latest_set:
        tips.append("Rollläden schließen - starker Wärmeeintrag von außen.")
    elif abs(temp_diff_outside) < 0.5:
        tips.append("Außen- und Innentemperatur sind ähnlich - natürliche Lüftung möglich.")
    elif latest_actual < 20 and outside_now < 15:
        tips.append("Fenster besser geschlossen halten - es ist draußen deutlich kälter.")

    # Überprüfe, ob die eingestellte Temperatur zu warm oder zu kalt ist
    if latest_set > 24 or latest_set < 18:
        tips.append("Zieltemperatur außerhalb der gängigen Raumtemperatur (18-24 °C).")

    # Ausreißer erkennen mit Standardabweichung
    if np.std(actual_temps) > 1.5:
        tips.append("Starke Temperaturschwankungen - prüfen Sie Fenster oder Thermostat.")

    # === Bewertung ===
    if max_deviation > 2 and not setpoint_changed:
        status = "warning"
        message = "Starke Abweichung zwischen Soll- und Ist-Temperatur."
    elif not trend_positive and max_deviation > 1.0:
        status = "warning"
        message = "Temperatur nähert sich dem Zielwert nicht an."
    elif responded is False:
        status = "warning"
        message = "Temperatur reagiert nicht auf neue Zielvorgabe."
    elif avg_deviation < 1:
        status = "ok"
        message = "Temperatur stabil im Zielbereich."
    elif trend_positive:
        status = "info"
        message = "Temperatur nähert sich dem Zielwert an."
    else:
        status = "info"
        message = "Analyse nicht eindeutig, aber keine Auffälligkeit."

    return {
        "status": status,
        "message": message,
        "meta": {
            "avg_deviation": round(avg_deviation, 2),
            "max_deviation": round(max_deviation, 2),
            "setpoint_changed": setpoint_changed,
            "trend_positive": trend_positive,
            "heating_effort_estimate": round(heating_effort, 2),
            "outside_temperature": round(outside_now, 1),
            "temp_diff_outside": round(temp_diff_outside, 1),
        },
        "tips": tips
    }

