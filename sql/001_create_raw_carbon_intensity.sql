CREATE TABLE IF NOT EXISTS raw_carbon_intensity (
    from_time TIMESTAMPTZ NOT NULL,
    to_time TIMESTAMPTZ NOT NULL,
    forecast_intensity INTEGER,
    actual_intensity INTEGER,
    intensity_index TEXT,
    raw_payload JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (from_time, to_time)
);