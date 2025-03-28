-- Models for staging layer
-- This file defines the staging models for the MCS100 fleet analytics solution

-- Staging model for flight data
{{ config(
    materialized='table',
    schema='staging',
    tags=['flight_data', 'staging']
) }}

SELECT
    aircraft_msn,
    flight_id,
    event_timestamp,
    engine_1_temp,
    engine_2_temp,
    engine_1_pressure,
    engine_2_pressure,
    engine_1_vibration,
    engine_2_vibration,
    fuel_flow_rate,
    altitude,
    speed,
    external_temp,
    EXTRACT(HOUR FROM event_timestamp) AS hour_of_day,
    EXTRACT(DOW FROM event_timestamp) AS day_of_week,
    EXTRACT(DAY FROM event_timestamp) AS day_of_month,
    EXTRACT(MONTH FROM event_timestamp) AS month,
    EXTRACT(YEAR FROM event_timestamp) AS year
FROM {{ source('raw', 'flight_data') }}
