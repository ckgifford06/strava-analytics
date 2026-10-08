import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import requests

from config import DATABASE_URL
from load import upsert

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
CACHE_DIR = Path("data/raw/weather")
ARCHIVE_LAG_DAYS = 7
REQUEST_DELAY_SECONDS = 0.5
HOURLY_FIELDS = (
    "temperature_2m", "dew_point_2m", "relative_humidity_2m",
    "wind_speed_10m", "precipitation",
)
WEATHER_COLUMNS = (
    "activity_id", "temperature_f", "dew_point_f", "relative_humidity_pct",
    "wind_speed_mph", "precipitation_in", "observation_hour",
)

ELIGIBLE_RUNS_SQL = """
    SELECT a.activity_id, a.start_lat, a.start_lng,
           a.start_date_utc + make_interval(secs => a.elapsed_time_s / 2.0) AS midpoint
    FROM activities a
    LEFT JOIN weather w USING (activity_id)
    WHERE w.activity_id IS NULL
      AND a.sport_type <> 'VirtualRun'
      AND a.start_lat IS NOT NULL
      AND a.start_lng IS NOT NULL
      AND a.start_date_utc < now() - make_interval(days => %s)
    ORDER BY a.start_date_utc
"""

SKIPPED_RUNS_SQL = """
    SELECT
        count(*) FILTER (WHERE sport_type = 'VirtualRun'),
        count(*) FILTER (WHERE sport_type <> 'VirtualRun' AND (start_lat IS NULL OR start_lng IS NULL)),
        count(*) FILTER (WHERE sport_type <> 'VirtualRun' AND start_lat IS NOT NULL AND start_lng IS NOT NULL
                         AND start_date_utc >= now() - make_interval(days => %s))
    FROM activities
"""


def fetch_archive(lat, lng, midpoint):
    resp = requests.get(ARCHIVE_URL, params={
        "latitude": round(lat, 4),
        "longitude": round(lng, 4),
        "start_date": midpoint.date().isoformat(),
        "end_date": (midpoint + timedelta(days=1)).date().isoformat(),
        "hourly": ",".join(HOURLY_FIELDS),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "UTC",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()


def cached_archive(activity_id, lat, lng, midpoint):
    path = CACHE_DIR / f"{activity_id}.json"
    if path.exists():
        return json.loads(path.read_text()), False
    data = fetch_archive(lat, lng, midpoint)
    path.write_text(json.dumps(data, indent=2))
    return data, True


def nearest_hour_index(times, midpoint):
    hours = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in times]
    return min(range(len(hours)), key=lambda i: abs(hours[i] - midpoint)), hours


def weather_row(activity_id, data, midpoint):
    hourly = data["hourly"]
    i, hours = nearest_hour_index(hourly["time"], midpoint)
    return (
        activity_id,
        hourly["temperature_2m"][i],
        hourly["dew_point_2m"][i],
        hourly["relative_humidity_2m"][i],
        hourly["wind_speed_10m"][i],
        hourly["precipitation"][i],
        hours[i],
    )


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        runs = cur.execute(ELIGIBLE_RUNS_SQL, (ARCHIVE_LAG_DAYS,)).fetchall()
        print(f"{len(runs)} runs need weather")

        rows = []
        requests_made = 0
        for activity_id, lat, lng, midpoint in runs:
            data, fetched = cached_archive(activity_id, lat, lng, midpoint)
            if fetched:
                requests_made += 1
                time.sleep(REQUEST_DELAY_SECONDS)
            rows.append(weather_row(activity_id, data, midpoint))

        changed = upsert(cur, "weather", WEATHER_COLUMNS, ("activity_id",), rows)
        virtual, no_coords, too_recent = cur.execute(SKIPPED_RUNS_SQL, (ARCHIVE_LAG_DAYS,)).fetchone()
        total = cur.execute("SELECT count(*) FROM weather").fetchone()[0]

    print(f"API requests: {requests_made}")
    print(f"weather: {total} rows, {changed} inserted or updated")
    print(f"Skipped: {virtual} virtual, {no_coords} without coordinates, "
          f"{too_recent} within {ARCHIVE_LAG_DAYS} days (archive not yet available)")


if __name__ == "__main__":
    main()
