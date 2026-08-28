-- =============================================================================
-- 00_init.sql
-- Riksdag ETL — database bootstrap
--
-- Creates the schemas and shared operational objects that every team member
-- needs before running any DDL or ETL code.
--
-- Owner:   P6 (platform / CI-CD)
-- Source:  Sveriges riksdag open data (data.riksdagen.se)
--
-- USAGE
--   Run once against a fresh local database, before any table DDL:
--
--     createdb riksdag
--     psql -d riksdag -f sql/00_init.sql
--
-- This script is IDEMPOTENT. Running it twice is safe and changes nothing.
-- It contains no DROP statements and never touches table data.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Schemas
-- -----------------------------------------------------------------------------
-- stg  = bronze layer. Raw landing zone, mirrors the source. Owned by P1 + P2.
-- dw   = silver layer. Conformed star schema. Owned by P3.
-- ops  = operational metadata for pipeline runs. Owned by P6.

CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS ops;

COMMENT ON SCHEMA stg IS 'Bronze layer. Raw extracts from data.riksdagen.se. Source-faithful column names, permissive types, no business logic. Written by ingest jobs only.';

COMMENT ON SCHEMA dw IS 'Silver layer. Star schema (dim_* / fakta_*) built from stg. The only schema that reports are allowed to read.';

COMMENT ON SCHEMA ops IS 'Pipeline operational metadata. Load logging and run bookkeeping.';


-- -----------------------------------------------------------------------------
-- 2. Operational metadata
-- -----------------------------------------------------------------------------
-- Every ingest and transform step writes one row here. This is what makes the
-- nightly run auditable and gives the reports a "data as of" timestamp.
--
-- NOTE: this table is a proposal from P6, not something the team has agreed on
-- yet. It costs nothing to have and nothing to ignore, but if the team does not
-- want it, delete this section rather than leaving it half-used.

CREATE TABLE IF NOT EXISTS ops.load_log (
    load_id         BIGSERIAL       PRIMARY KEY,
    kalla           TEXT            NOT NULL,   -- e.g. 'personlista', 'voteringlista'
    mallager        TEXT            NOT NULL,   -- target schema: 'stg' or 'dw'
    malltabell      TEXT            NOT NULL,   -- target table name
    riksmote        TEXT            NULL,       -- e.g. '2024/25', NULL if not applicable
    startad         TIMESTAMPTZ     NOT NULL DEFAULT now(),
    avslutad        TIMESTAMPTZ     NULL,
    status          TEXT            NOT NULL DEFAULT 'RUNNING'
                                    CHECK (status IN ('RUNNING', 'OK', 'FAILED')),
    antal_rader     BIGINT          NULL,
    korning_id      TEXT            NULL,       -- CI run id / uuid for one full pipeline run
    meddelande      TEXT            NULL        -- error text or notes
);

COMMENT ON TABLE ops.load_log IS 'One row per load step per run. Written by ingest and transform jobs.';

CREATE INDEX IF NOT EXISTS ix_load_log_startad
    ON ops.load_log (startad DESC);

CREATE INDEX IF NOT EXISTS ix_load_log_korning
    ON ops.load_log (korning_id);


-- -----------------------------------------------------------------------------
-- 3. Sanity check
-- -----------------------------------------------------------------------------
-- Prints the schemas that now exist. If you do not see stg, dw and ops here,
-- something went wrong and you should not proceed to table DDL.

SELECT nspname AS schema_name
FROM   pg_namespace
WHERE  nspname IN ('stg', 'dw', 'ops')
ORDER  BY nspname;
