-- Models for staging layer
-- This file defines the staging model for maintenance events

{{ config(
    materialized='table',
    schema='staging',
    tags=['maintenance', 'staging']
) }}

SELECT
    aircraft_msn,
    component_id,
    event_timestamp,
    event_type,
    is_scheduled,
    duration_hours,
    maintenance_action,
    technician_id,
    EXTRACT(HOUR FROM event_timestamp) AS hour_of_day,
    EXTRACT(DOW FROM event_timestamp) AS day_of_week,
    EXTRACT(DAY FROM event_timestamp) AS day_of_month,
    EXTRACT(MONTH FROM event_timestamp) AS month,
    EXTRACT(YEAR FROM event_timestamp) AS year
FROM {{ source('raw', 'maintenance_events') }}
