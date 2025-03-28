-- Models for staging layer
-- This file defines the staging model for usage cycles

{{ config(
    materialized='table',
    schema='staging',
    tags=['usage', 'staging']
) }}

SELECT
    aircraft_msn,
    date,
    flight_hours,
    takeoffs,
    landings,
    apu_cycles,
    apu_hours,
    EXTRACT(DOW FROM date) AS day_of_week,
    EXTRACT(DAY FROM date) AS day_of_month,
    EXTRACT(MONTH FROM date) AS month,
    EXTRACT(YEAR FROM date) AS year
FROM {{ source('raw', 'usage_cycles') }}
