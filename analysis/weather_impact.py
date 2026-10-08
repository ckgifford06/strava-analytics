import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from analysis.common import (
    MUTED, PRIMARY, SECONDARY, TABLE_DIR, format_ms, legend, new_chart, query, save_chart,
)

MIN_MILES = 1
FASTEST_PACE_S = 5 * 60
SLOWEST_PACE_S = 16 * 60
FORMULA = "pace_s_per_mile ~ temperature_f + dew_point_f + wind_speed_mph + miles + days_since_first_run"

RUNS_SQL = """
    SELECT activity_id, local_date, miles, pace_s_per_mile, temperature_f, dew_point_f, wind_speed_mph,
           local_date - min(local_date) OVER () AS days_since_first_run
    FROM v_runs
"""

EFFECTS = (
    ("dew_point_f", 10, "Each 10°F of dew point"),
    ("temperature_f", 10, "Each 10°F of temperature"),
    ("wind_speed_mph", 5, "Each 5 mph of wind"),
    ("miles", 1, "Each additional mile of run distance"),
    ("days_since_first_run", 365, "Each year of training history"),
)


def model_data():
    runs = query(RUNS_SQL)
    numeric = ["miles", "pace_s_per_mile", "temperature_f", "dew_point_f", "wind_speed_mph", "days_since_first_run"]
    runs[numeric] = runs[numeric].apply(pd.to_numeric)
    total = len(runs)
    runs = runs.dropna(subset=numeric)
    with_weather = len(runs)
    runs = runs[(runs["miles"] >= MIN_MILES)
                & runs["pace_s_per_mile"].between(FASTEST_PACE_S, SLOWEST_PACE_S)]
    return runs, total, with_weather


def interpret(model, runs):
    ci = model.conf_int()
    print(f"OLS on {int(model.nobs)} runs, R² = {model.rsquared:.3f} (adjusted {model.rsquared_adj:.3f})")
    for variable, step, label in EFFECTS:
        effect = model.params[variable] * step
        low, high = ci.loc[variable] * step
        direction = "slower" if effect > 0 else "faster"
        p_value = model.pvalues[variable]
        p_text = "p < 0.001" if p_value < 0.001 else f"p = {p_value:.3f}"
        print(f"  {label} is associated with {abs(effect):.1f} s/mile {direction} "
              f"(95% CI {low:+.1f} to {high:+.1f}, {p_text}), holding the other terms constant.")
    corr = runs["temperature_f"].corr(runs["dew_point_f"])
    print(f"  Temperature and dew point are correlated (r = {corr:.2f}), so their separate effects are imprecise.")


def plot(model, runs):
    fig, ax = new_chart("Pace vs dew point", "Dew point (°F)", "Pace (min:sec per mile, higher is slower)")
    ax.scatter(runs["dew_point_f"], runs["pace_s_per_mile"], s=22, color=PRIMARY, alpha=0.6,
               edgecolors="white", linewidths=0.8, label="Runs")
    grid = pd.DataFrame({"dew_point_f": np.linspace(runs["dew_point_f"].min(), runs["dew_point_f"].max(), 50)})
    for column in ("temperature_f", "wind_speed_mph", "miles", "days_since_first_run"):
        grid[column] = runs[column].mean()
    ax.plot(grid["dew_point_f"], model.predict(grid), color=SECONDARY, linewidth=2,
            label="Model fit, other terms at their means")
    ax.yaxis.set_major_locator(mticker.MultipleLocator(30))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: format_ms(v)))
    ax.text(0, -0.14, f"n = {int(model.nobs)} runs of at least {MIN_MILES} mile, pace between "
                      f"{format_ms(FASTEST_PACE_S)} and {format_ms(SLOWEST_PACE_S)} per mile. Correlational, not causal.",
            transform=ax.transAxes, color=MUTED, fontsize=8)
    legend(ax, loc="upper left")
    return save_chart(fig, "pace_vs_dew_point.png")


def main():
    runs, total, with_weather = model_data()
    model = smf.ols(FORMULA, data=runs).fit()

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = TABLE_DIR / "weather_regression.txt"
    summary_path.write_text(str(model.summary()))
    chart_path = plot(model, runs)

    print(f"Runs: {total} total, {with_weather} with weather, {len(runs)} after distance and pace filters")
    interpret(model, runs)
    print(f"Wrote {summary_path} and {chart_path}")


if __name__ == "__main__":
    main()
