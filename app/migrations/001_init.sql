-- Idempotent schema; safe to run on every start.
CREATE TABLE IF NOT EXISTS users (
    sub          TEXT PRIMARY KEY,
    email        TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS items (
    id            BIGSERIAL PRIMARY KEY,
    owner_sub     TEXT NOT NULL REFERENCES users(sub),
    kind          TEXT NOT NULL CHECK (kind IN ('lost', 'found')),
    title         TEXT NOT NULL,
    notes         TEXT NOT NULL DEFAULT '',
    description   TEXT NOT NULL DEFAULT '',
    category      TEXT NOT NULL DEFAULT 'Other',
    ml_category   TEXT,
    ml_confidence REAL,
    location      TEXT NOT NULL DEFAULT '',
    item_date     DATE,
    image_key     TEXT,
    labels        JSONB NOT NULL DEFAULT '[]'::jsonb,
    status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'claimed', 'returned')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS claims (
    id           BIGSERIAL PRIMARY KEY,
    item_id      BIGINT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    claimant_sub TEXT NOT NULL REFERENCES users(sub),
    message      TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_items_created ON items (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_items_kind_status ON items (kind, status);
CREATE INDEX IF NOT EXISTS idx_items_category ON items (category);
CREATE INDEX IF NOT EXISTS idx_claims_item ON claims (item_id);
