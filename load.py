import json
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from config import DATABASE_URL

DETAIL_DIR = Path("data/raw/details")
SCHEMA_PATH = Path("sql/schema.sql")
TABLES = ("activities", "splits", "best_efforts", "weather")

ACTIVITY_COLUMNS = (
    "activity_id", "name", "sport_type", "workout_type",
    "start_date_utc", "start_date_local", "timezone",
    "distance_m", "moving_time_s", "elapsed_time_s",
    "average_speed_mps", "max_speed_mps",
    "start_lat", "start_lng", "is_private", "raw",
)
SPLIT_COLUMNS = (
    "activity_id", "split_index", "distance_m",
    "moving_time_s", "elapsed_time_s", "average_speed_mps",
)
BEST_EFFORT_COLUMNS = (
    "activity_id", "effort_name", "distance_m",
    "moving_time_s", "elapsed_time_s", "start_date_local", "pr_rank",
)


def local_timestamp(value):
    return value.rstrip("Z") if value else None


def activity_row(a):
    latlng = a.get("start_latlng") or [None, None]
    return (
        a["id"], a.get("name"), a.get("sport_type", a.get("type")), a.get("workout_type"),
        a.get("start_date"), local_timestamp(a.get("start_date_local")), a.get("timezone"),
        a.get("distance"), a.get("moving_time"), a.get("elapsed_time"),
        a.get("average_speed"), a.get("max_speed"),
        latlng[0], latlng[1], a.get("private"), Jsonb(a),
    )


def split_rows(a):
    return [
        (a["id"], s["split"], s.get("distance"),
         s.get("moving_time"), s.get("elapsed_time"), s.get("average_speed"))
        for s in a.get("splits_standard") or []
    ]


def best_effort_rows(a):
    return [
        (a["id"], e["name"], e.get("distance"),
         e.get("moving_time"), e.get("elapsed_time"),
         local_timestamp(e.get("start_date_local")), e.get("pr_rank"))
        for e in a.get("best_efforts") or []
    ]


def upsert_sql(table, columns, key):
    updates = [c for c in columns if c not in key]
    return (
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join(['%s'] * len(columns))}) "
        f"ON CONFLICT ({', '.join(key)}) DO UPDATE SET "
        + ", ".join(f"{c} = EXCLUDED.{c}" for c in updates)
        + f" WHERE ({', '.join(f'{table}.{c}' for c in updates)}) "
        f"IS DISTINCT FROM ({', '.join(f'EXCLUDED.{c}' for c in updates)})"
    )


def upsert(cur, table, columns, key, rows):
    if not rows:
        return 0
    cur.executemany(upsert_sql(table, columns, key), rows)
    return cur.rowcount


def read_details():
    return [json.loads(p.read_text()) for p in sorted(DETAIL_DIR.glob("*.json"))]


def main():
    details = read_details()
    activities = [activity_row(a) for a in details]
    splits = [row for a in details for row in split_rows(a)]
    best_efforts = [row for a in details for row in best_effort_rows(a)]

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_PATH.read_text())
        changed = {
            "activities": upsert(cur, "activities", ACTIVITY_COLUMNS, ("activity_id",), activities),
            "splits": upsert(cur, "splits", SPLIT_COLUMNS, ("activity_id", "split_index"), splits),
            "best_efforts": upsert(
                cur, "best_efforts", BEST_EFFORT_COLUMNS, ("activity_id", "effort_name"), best_efforts
            ),
        }
        for table in TABLES:
            cur.execute(f"SELECT count(*) FROM {table}")
            total = cur.fetchone()[0]
            print(f"{table}: {total} rows, {changed.get(table, 0)} inserted or updated")


if __name__ == "__main__":
    main()
