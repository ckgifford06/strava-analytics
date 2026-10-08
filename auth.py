import json
import os
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from dotenv import load_dotenv

load_dotenv()

PORT = 8000
REDIRECT_URI = f"http://localhost:{PORT}"
SCOPE = "read,activity:read_all"
TOKEN_PATH = "token.json"


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        self.server.result = {k: v[0] for k, v in query.items()}
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Authorized. You can close this tab.")

    def log_message(self, *args):
        pass


def main():
    client_id = os.environ["STRAVA_CLIENT_ID"]
    client_secret = os.environ["STRAVA_CLIENT_SECRET"]

    url = "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "approval_prompt": "force",
        "scope": SCOPE,
    })
    print(f"Opening browser to authorize. If it does not open, visit:\n{url}\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", PORT), CallbackHandler)
    server.result = None
    while server.result is None:
        server.handle_request()
    result = server.result

    if "error" in result or "code" not in result:
        sys.exit(f"Authorization failed: {result.get('error', 'no code returned')}")
    if "activity:read_all" not in result.get("scope", ""):
        sys.exit("The activity:read_all box was unchecked. Run auth.py again and leave it checked.")

    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": result["code"],
        "grant_type": "authorization_code",
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    with open(TOKEN_PATH, "w") as f:
        json.dump({
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data["expires_at"],
        }, f, indent=2)
    print(f"Authorized as {data['athlete']['firstname']} {data['athlete']['lastname']}. Token saved to {TOKEN_PATH}.")


if __name__ == "__main__":
    main()