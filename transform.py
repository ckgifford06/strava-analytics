import csv
import json
from pathlib import Path

DETAIL_DIR = Path("data/raw/details")
OUTPUT_PATH = Path("data/runs.csv")
METERS_PER_MILE = 1609.344
WORKOUT_TYPES = {0: "default", 1: "race", 2: "long_run", 3: "workout"}


def pace(moving_time, distance_m, unit_m):
    if not distance_m or not moving_time:
        return None
    return round(moving_time / 60 / (distance_m / unit_m), 3)


def to_row(a):
    distance = a.get("distance") or 0
    moving_time = a.get("moving_time")
    return {
        "id": a["id"],
        "name": a.get("name"),
        "sport_type": a.get("sport_type", a.get("type")),
        "workout_type": WORKOUT_TYPES.get(a.get("workout_type"), "default"),
        "start_date_local": a["start_date_local"].replace("Z", ""),
        "start_date_utc": a.get("start_date"),
        "timezone": a.get("timezone"),
        "distance_km": round(distance / 1000, 3),
        "distance_mi": round(distance / METERS_PER_MILE, 3),
        "moving_time_s": moving_time,
        "elapsed_time_s": a.get("elapsed_time"),
        "pace_min_per_km": pace(moving_time, distance, 1000),
        "pace_min_per_mi": pace(moving_time, distance, METERS_PER_MILE),
        "average_speed_mps": a.get("average_speed"),
        "max_speed_mps": a.get("max_speed"),
        "elevation_gain_m": a.get("total_elevation_gain"),
        "elev_high_m": a.get("elev_high"),
        "elev_low_m": a.get("elev_low"),
        "calories": a.get("calories"),
        "gear": (a.get("gear") or {}).get("name"),
        "device": a.get("device_name"),
        "trainer": a.get("trainer"),
        "commute": a.get("commute"),
        "manual": a.get("manual"),
        "pr_count": a.get("pr_count"),
        "achievement_count": a.get("achievement_count"),
        "kudos_count": a.get("kudos_count"),
    }


def main():
    rows = [to_row(json.loads(p.read_text())) for p in DETAIL_DIR.glob("*.json")]
    rows.sort(key=lambda r: r["start_date_local"])

    with OUTPUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} runs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
