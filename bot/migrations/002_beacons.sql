CREATE TABLE IF NOT EXISTS beacons (
    beacon_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    chat_id BIGINT NOT NULL,
    message_id BIGINT,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    radius INTEGER NOT NULL DEFAULT 1000,
    state TEXT NOT NULL DEFAULT 'searching',
    current_car_id TEXT,
    current_car_model TEXT,
    current_car_distance DOUBLE PRECISION,
    current_car_lat DOUBLE PRECISION,
    current_car_lon DOUBLE PRECISION,
    skipped_cars TEXT NOT NULL DEFAULT '',
    model_filter TEXT NOT NULL DEFAULT '',
    cars_found_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '60 minutes'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_beacons_active
    ON beacons(state) WHERE state NOT IN ('stopped');
