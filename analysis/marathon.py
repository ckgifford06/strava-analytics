import matplotlib.ticker as mticker
import pandas as pd

from analysis.common import (
    MUTED, PRIMARY, SECONDARY, format_hm, format_hms, legend, new_chart, query, save_chart, save_table,
)
from config import BQ_TARGET_SECONDS, GOAL_RACE_DATE, PREDICTION_WINDOW_DAYS

MARATHON_M = 42195
RIEGEL_EXPONENT = 1.06
MIN_EFFORT_M = 5000

EFFORTS_SQL = """
    SELECT activity_id, effort_name, distance_m, elapsed_time_s, start_date_local::date AS effort_date
    FROM best_efforts
    WHERE distance_m >= %s
    ORDER BY start_date_local
"""

FIRST_RUN_SQL = "SELECT min(local_date) AS first_day, current_date AS today FROM v_runs"


def riegel(time_s, distance_m):
    return time_s * (MARATHON_M / distance_m) ** RIEGEL_EXPONENT


def load_efforts():
    efforts = query(EFFORTS_SQL, (MIN_EFFORT_M,))
    efforts["effort_date"] = pd.to_datetime(efforts["effort_date"])
    efforts["projected_s"] = riegel(efforts["elapsed_time_s"], efforts["distance_m"])
    return efforts


def week_starts():
    bounds = query(FIRST_RUN_SQL).iloc[0]
    first = pd.Timestamp(bounds["first_day"])
    today = pd.Timestamp(bounds["today"])
    return pd.date_range(first - pd.Timedelta(days=first.weekday()), today, freq="W-MON")


def weekly_predictions(efforts):
    window = pd.Timedelta(days=PREDICTION_WINDOW_DAYS)
    rows = []
    for week_start in week_starts():
        week_end = week_start + pd.Timedelta(days=6)
        in_window = efforts[(efforts["effort_date"] > week_end - window) & (efforts["effort_date"] <= week_end)]
        row = {"week_start": week_start.date(), "week_end": week_end.date()}
        if not in_window.empty:
            best = in_window.loc[in_window["projected_s"].idxmin()]
            row.update({
                "predicted_seconds": round(best["projected_s"]),
                "predicted_time": format_hms(best["projected_s"]),
                "gap_to_bq_seconds": round(best["projected_s"] - BQ_TARGET_SECONDS),
                "source_effort": best["effort_name"],
                "source_time": format_hms(best["elapsed_time_s"]),
                "source_date": best["effort_date"].date(),
                "source_activity_id": best["activity_id"],
            })
        rows.append(row)
    predictions = pd.DataFrame(rows)
    for column in ("predicted_seconds", "gap_to_bq_seconds", "source_activity_id"):
        predictions[column] = predictions[column].astype("Int64")
    return predictions


def plot(predictions):
    fig, ax = new_chart(
        "Projected marathon time vs Boston qualifying target",
        "Week",
        "Projected marathon time (h:mm)",
    )
    x = pd.to_datetime(predictions["week_end"])
    ax.plot(x, predictions["predicted_seconds"], color=PRIMARY, linewidth=2, label="Projected marathon (Riegel)")
    ax.axhline(BQ_TARGET_SECONDS, color=SECONDARY, linewidth=2, linestyle="--",
               label=f"BQ target {format_hms(BQ_TARGET_SECONDS)}")
    latest = predictions.dropna(subset=["predicted_seconds"]).iloc[-1]
    ax.annotate(f"Latest {latest['predicted_time']}", xy=(pd.Timestamp(latest["week_end"]), latest["predicted_seconds"]),
                xytext=(6, 6), textcoords="offset points", color=MUTED, fontsize=9)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1800))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: format_hm(v)))
    ax.set_ylim(min(BQ_TARGET_SECONDS, predictions["predicted_seconds"].min()) - 600,
                predictions["predicted_seconds"].max() + 600)
    ax.text(0, -0.14, f"Fastest Riegel projection from 5K+ best efforts in the trailing {PREDICTION_WINDOW_DAYS} days. "
                      f"Goal race: {GOAL_RACE_DATE}.",
            transform=ax.transAxes, color=MUTED, fontsize=8)
    legend(ax, loc="upper right")
    return save_chart(fig, "marathon_prediction.png")


def main():
    predictions = weekly_predictions(load_efforts())
    table_path = save_table(predictions, "marathon_predictions.csv")
    chart_path = plot(predictions)

    valid = predictions.dropna(subset=["predicted_seconds"])
    latest = valid.iloc[-1]
    best = valid.loc[valid["predicted_seconds"].idxmin()]
    gap = latest["gap_to_bq_seconds"]
    print(f"Weeks with a prediction: {len(valid)} of {len(predictions)}")
    print(f"Latest prediction (week ending {latest['week_end']}): {latest['predicted_time']} "
          f"from a {latest['source_effort']} of {latest['source_time']}")
    print(f"Gap to BQ target {format_hms(BQ_TARGET_SECONDS)}: "
          f"{format_hms(abs(gap))} {'slower' if gap > 0 else 'faster'}")
    print(f"Best weekly prediction: {best['predicted_time']} (week ending {best['week_end']})")
    print(f"Wrote {table_path} and {chart_path}")


if __name__ == "__main__":
    main()
