import pandas as pd

from analysis.common import (
    CRITICAL, GOOD, MUTED, PRIMARY, SECONDARY, WARNING, legend, new_chart, query, save_chart, save_table,
)
from config import ACWR_HIGH, ACWR_LOW

ACWR_PLOT_CAP = 3.0
MILEAGE_INCREASE_PCT = 10
ROLLING_WEEKS = 4

ACWR_SQL = "SELECT day, miles, acute_miles, chronic_miles, acwr, risk_band FROM v_acwr ORDER BY day"
WEEKLY_SQL = """
    SELECT week_start, iso_week, total_miles, run_count, longest_run_miles, pct_change
    FROM v_weekly_mileage
    ORDER BY week_start
"""


def plot_acwr(acwr):
    fig, ax = new_chart("Acute to chronic workload ratio (mileage)", "Date", "ACWR (7-day miles / 28-day weekly average)")
    x = pd.to_datetime(acwr["day"])
    ax.axhspan(0, ACWR_LOW, color=WARNING, alpha=0.12, linewidth=0)
    ax.axhspan(ACWR_LOW, ACWR_HIGH, color=GOOD, alpha=0.08, linewidth=0)
    ax.axhspan(ACWR_HIGH, ACWR_PLOT_CAP, color=CRITICAL, alpha=0.10, linewidth=0)
    ax.plot(x, acwr["acwr"].clip(upper=ACWR_PLOT_CAP), color=PRIMARY, linewidth=1.2)
    for y, label in (
        (ACWR_PLOT_CAP - 0.12, f"High risk (above {ACWR_HIGH})"),
        ((ACWR_LOW + ACWR_HIGH) / 2, f"Optimal ({ACWR_LOW} to {ACWR_HIGH})"),
        (ACWR_LOW / 2, f"Low (below {ACWR_LOW})"),
    ):
        ax.text(1.01, y, label, transform=ax.get_yaxis_transform(), color=MUTED, fontsize=9, va="center")
    ax.set_ylim(0, ACWR_PLOT_CAP)
    ax.text(0, -0.14, f"Values above {ACWR_PLOT_CAP} are drawn at {ACWR_PLOT_CAP}. "
                      "The first 27 days and periods with no running in the past 28 days have no ratio.",
            transform=ax.transAxes, color=MUTED, fontsize=8)
    return save_chart(fig, "acwr.png")


def plot_weekly(weekly):
    fig, ax = new_chart("Weekly mileage", "Week starting", "Miles")
    x = pd.to_datetime(weekly["week_start"])
    ax.bar(x, weekly["total_miles"], width=5, color=PRIMARY, label="Weekly miles")
    rolling = weekly["total_miles"].rolling(ROLLING_WEEKS, min_periods=1).mean()
    ax.plot(x, rolling, color=SECONDARY, linewidth=2, label=f"{ROLLING_WEEKS}-week average")
    legend(ax, loc="upper left")
    return save_chart(fig, "weekly_mileage.png")


def print_band_counts(acwr):
    counts = acwr["risk_band"].value_counts()
    total = int(counts.sum())
    print(f"Days in each ACWR risk band ({total} days with a ratio):")
    for band in ("low", "optimal", "high"):
        days = int(counts.get(band, 0))
        print(f"  {band:<8} {days:>5} days  {100 * days / total:5.1f}%")
    print(f"  no ratio {len(acwr) - total:>5} days")


def print_mileage_jumps(weekly):
    jumps = weekly[weekly["pct_change"] > MILEAGE_INCREASE_PCT].copy()
    jumps["previous_miles"] = weekly["total_miles"].shift(1).loc[jumps.index]
    print(f"Weeks with more than {MILEAGE_INCREASE_PCT}% mileage increase: {len(jumps)} of {len(weekly)}")
    for _, row in jumps.iterrows():
        print(f"  {row['iso_week']}  {row['previous_miles']:5.1f} to {row['total_miles']:5.1f} mi  "
              f"(+{row['pct_change']:.0f}%)")


def main():
    acwr = query(ACWR_SQL)
    weekly = query(WEEKLY_SQL)
    for column in ("miles", "acute_miles", "chronic_miles", "acwr"):
        acwr[column] = pd.to_numeric(acwr[column])
    for column in ("total_miles", "longest_run_miles", "pct_change"):
        weekly[column] = pd.to_numeric(weekly[column])

    table_path = save_table(acwr.round(3), "acwr.csv")
    chart_paths = [plot_acwr(acwr), plot_weekly(weekly)]

    print_band_counts(acwr)
    print()
    print_mileage_jumps(weekly)
    print()
    print(f"Wrote {table_path}, {', '.join(str(p) for p in chart_paths)}")


if __name__ == "__main__":
    main()
