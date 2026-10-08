import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://www.strava.com/api/v3"
TOKEN_PATH = "token.json"
WINDOW_SECONDS = 900


class DailyLimitReached(Exception):
    pass


def load_token():
    with open(TOKEN_PATH) as f:
        return json.load(f)


def save_token(token):
    with open(TOKEN_PATH, "w") as f:
        json.dump(token, f, indent=2)


def access_token():
    token = load_token()
    if token["expires_at"] - 60 > time.time():
        return token["access_token"]
    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": os.environ["STRAVA_CLIENT_ID"],
        "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    token = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": data["expires_at"],
    }
    save_token(token)
    return token["access_token"]


def seconds_to_next_window():
    return WINDOW_SECONDS - (time.time() % WINDOW_SECONDS) + 5


def check_limits(headers):
    for limit_key, usage_key in (
        ("X-RateLimit-Limit", "X-RateLimit-Usage"),
        ("X-ReadRateLimit-Limit", "X-ReadRateLimit-Usage"),
    ):
        if limit_key not in headers or usage_key not in headers:
            continue
        limits = [int(x) for x in headers[limit_key].split(",")]
        usage = [int(x) for x in headers[usage_key].split(",")]
        if usage[1] >= limits[1] - 1:
            raise DailyLimitReached()
        if usage[0] >= limits[0] - 2:
            return True
    return False


def wait_for_window():
    wait = seconds_to_next_window()
    print(f"Near the 15-minute rate limit, pausing {int(wait)}s")
    time.sleep(wait)


def get(path, params=None):
    while True:
        resp = requests.get(
            f"{API}{path}",
            headers={"Authorization": f"Bearer {access_token()}"},
            params=params,
            timeout=30,
        )
        if resp.status_code == 429:
            check_limits(resp.headers)
            wait_for_window()
            continue
        resp.raise_for_status()
        if check_limits(resp.headers):
            wait_for_window()
        return resp.json()