CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    region_id INTEGER NOT NULL DEFAULT 16,
    notifications_on BOOLEAN NOT NULL DEFAULT TRUE,
    model_filter TEXT NOT NULL DEFAULT '',
    quiet_start INTEGER NOT NULL DEFAULT -1,
    quiet_end INTEGER NOT NULL DEFAULT -1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zones (
    zone_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    name TEXT NOT NULL DEFAULT 'Зона',
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    radius INTEGER NOT NULL DEFAULT 1000,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    schedule TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_zones_user_id ON zones(user_id);

CREATE TABLE IF NOT EXISTS car_plates (
    car_id TEXT PRIMARY KEY,
    plate TEXT NOT NULL,
    reported_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
