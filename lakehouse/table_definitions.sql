-- AuthPulse - Complete Table Definitions
-- Detailed schema definitions for all Iceberg tables

-- ============================================================
-- TABLE: auth_events_raw
-- Purpose: Unmodified events from Kinesis (archival)
-- ============================================================
-- TODO: Define raw events table schema

-- ============================================================
-- TABLE: auth_events_curated
-- Purpose: Enriched events with risk scores and flags
-- Partitioned by: event_date
-- ============================================================
-- TODO: Define curated events table schema

-- ============================================================
-- TABLE: user_behavior_hourly
-- Purpose: Hourly user activity aggregations
-- ============================================================
-- TODO: Define user behavior aggregation schema

-- ============================================================
-- TABLE: host_popularity_daily
-- Purpose: Daily host access statistics
-- ============================================================
-- TODO: Define host popularity aggregation schema
