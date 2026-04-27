CREATE TABLE IF NOT EXISTS organizations (
    id                serial PRIMARY KEY,
    inn               varchar(12) UNIQUE NOT NULL,
    organization_name text NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_users (
    id            serial PRIMARY KEY,
    telegram_id   bigint UNIQUE NOT NULL,
    inn           varchar(12) REFERENCES organizations(inn),
    registered_at timestamp DEFAULT now(),
    is_active     bool DEFAULT true
);

CREATE TABLE IF NOT EXISTS admin_filters (
    id          serial PRIMARY KEY,
    field_name  varchar(50) NOT NULL,
    field_value text NOT NULL,
    is_active   bool DEFAULT true
);

CREATE TABLE IF NOT EXISTS report_state (
    id                  serial PRIMARY KEY,
    last_processed_date date
);

INSERT INTO report_state (last_processed_date)
SELECT NULL WHERE NOT EXISTS (SELECT 1 FROM report_state);
