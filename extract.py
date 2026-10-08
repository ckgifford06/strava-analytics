import json
from pathlib import Path

from strava_client import DailyLimitReached, get

RAW_DIR = Path("data/raw")
SUMMARY_PATH = RAW_DIR / "activities.json"
DETAIL_DIR = RAW_DIR / "details"
RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


def fetch_summaries():
    activities = []
    page = 1
    while True:
        batch = get("/athlete/activities", {"per_page": 200, "page": page})
        if not batch:
            return activities
        activities.extend(batch)
        page += 1


def main():
    DETAIL_DIR.mkdir(parents=True, exist_ok=True)

    summaries = fetch_summaries()
    SUMMARY_PATH.write_text(json.dumps(summaries, indent=2))

    runs = [a for a in summaries if a.get("sport_type", a.get("type")) in RUN_TYPES]
    pending = [a for a in runs if not (DETAIL_DIR / f"{a['id']}.json").exists()]
    print(f"{len(summaries)} activities, {len(runs)} runs, {len(pending)} run details to fetch")

    try:
        for i, activity in enumerate(pending, 1):
            detail = get(f"/activities/{activity['id']}")
            (DETAIL_DIR / f"{activity['id']}.json").write_text(json.dumps(detail, indent=2))
            print(f"[{i}/{len(pending)}] {detail['start_date_local'][:10]}  {detail['name']}")
    except DailyLimitReached:
        print("Daily rate limit reached. Run extract.py again tomorrow and it will resume.")
        return

    print("Extraction complete.")


if __name__ == "__main__":
    main()