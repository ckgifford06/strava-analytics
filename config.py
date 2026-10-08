import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

BQ_TARGET_SECONDS = 2 * 3600 + 55 * 60
GOAL_RACE_DATE = "2028-04-17"
PREDICTION_WINDOW_DAYS = 56
ACWR_HIGH = 1.5
ACWR_LOW = 0.8
