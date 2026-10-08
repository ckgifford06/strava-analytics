CREATE TABLE IF NOT EXISTS activities (
    activity_id BIGINT PRIMARY KEY,
    name TEXT,
    sport_type TEXT,
    workout_type INT,
    start_date_utc TIMESTAMPTZ,
    start_date_local TIMESTAMP,
    timezone TEXT,
    distance_m DOUBLE PRECISION,
    moving_time_s INT,
    elapsed_time_s INT,
    average_speed_mps DOUBLE PRECISION,
    max_speed_mps DOUBLE PRECISION,
    start_lat DOUBLE PRECISION,
    start_lng DOUBLE PRECISION,
    is_private BOOLEAN,
    raw JSONB
);

CREATE TABLE IF NOT EXISTS splits (
    activity_id BIGINT REFERENCES activities ON DELETE CASCADE,
    split_index INT,
    distance_m DOUBLE PRECISION,
    moving_time_s INT,
    elapsed_time_s INT,
    average_speed_mps DOUBLE PRECISION,
    PRIMARY KEY (activity_id, split_index)
);

CREATE TABLE IF NOT EXISTS best_efforts (
    activity_id BIGINT REFERENCES activities ON DELETE CASCADE,
    effort_name TEXT,
    distance_m DOUBLE PRECISION,
    moving_time_s INT,
    elapsed_time_s INT,
    start_date_local TIMESTAMP,
    pr_rank INT,
    PRIMARY KEY (activity_id, effort_name)
);

CREATE TABLE IF NOT EXISTS weather (
    activity_id BIGINT PRIMARY KEY REFERENCES activities ON DELETE CASCADE,
    temperature_f DOUBLE PRECISION,
    dew_point_f DOUBLE PRECISION,
    relative_humidity_pct DOUBLE PRECISION,
    wind_speed_mph DOUBLE PRECISION,
    precipitation_in DOUBLE PRECISION,
    observation_hour TIMESTAMPTZ
);
