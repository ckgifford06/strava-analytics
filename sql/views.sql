CREATE OR REPLACE VIEW v_runs AS
SELECT
    a.activity_id,
    a.name,
    a.sport_type,
    a.workout_type,
    a.start_date_utc,
    a.start_date_local,
    a.start_date_local::date AS local_date,
    a.distance_m,
    a.distance_m / 1609.344 AS miles,
    a.moving_time_s,
    a.elapsed_time_s,
    CASE WHEN a.distance_m > 0 THEN a.moving_time_s / (a.distance_m / 1609.344) END AS pace_s_per_mile,
    w.temperature_f,
    w.dew_point_f,
    w.relative_humidity_pct,
    w.wind_speed_mph,
    w.precipitation_in
FROM activities a
LEFT JOIN weather w USING (activity_id);

CREATE OR REPLACE VIEW v_daily_load AS
WITH days AS (
    SELECT generate_series(
        (SELECT min(local_date) FROM v_runs),
        current_date,
        interval '1 day'
    )::date AS day
)
SELECT
    d.day,
    coalesce(sum(r.miles), 0)::double precision AS miles,
    (coalesce(sum(r.moving_time_s), 0) / 60.0)::double precision AS minutes
FROM days d
LEFT JOIN v_runs r ON r.local_date = d.day
GROUP BY d.day;

CREATE OR REPLACE VIEW v_acwr AS
WITH rolling AS (
    SELECT
        day,
        miles,
        sum(miles) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS acute_miles,
        sum(miles) OVER (ORDER BY day ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) / 4.0 AS chronic_miles,
        row_number() OVER (ORDER BY day) AS day_number
    FROM v_daily_load
),
ratios AS (
    SELECT
        day,
        miles,
        acute_miles,
        chronic_miles,
        CASE WHEN day_number >= 28 AND chronic_miles > 0 THEN acute_miles / chronic_miles END AS acwr
    FROM rolling
)
SELECT
    day,
    miles,
    acute_miles,
    chronic_miles,
    acwr,
    CASE
        WHEN acwr IS NULL THEN NULL
        WHEN acwr > {acwr_high} THEN 'high'
        WHEN acwr < {acwr_low} THEN 'low'
        ELSE 'optimal'
    END AS risk_band
FROM ratios;

CREATE OR REPLACE VIEW v_weekly_mileage AS
WITH weeks AS (
    SELECT date_trunc('week', day)::date AS week_start, sum(miles) AS total_miles
    FROM v_daily_load
    GROUP BY 1
),
runs AS (
    SELECT date_trunc('week', local_date)::date AS week_start, count(*) AS run_count, max(miles) AS longest_run_miles
    FROM v_runs
    GROUP BY 1
)
SELECT
    w.week_start,
    to_char(w.week_start, 'IYYY-"W"IW') AS iso_week,
    w.total_miles,
    coalesce(r.run_count, 0) AS run_count,
    coalesce(r.longest_run_miles, 0) AS longest_run_miles,
    100.0 * (w.total_miles - lag(w.total_miles) OVER (ORDER BY w.week_start))
        / nullif(lag(w.total_miles) OVER (ORDER BY w.week_start), 0) AS pct_change
FROM weeks w
LEFT JOIN runs r USING (week_start);
