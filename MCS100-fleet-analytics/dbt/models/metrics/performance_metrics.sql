-- Models for metrics layer
-- This file defines the performance metrics model

{{ config(
    materialized='table',
    schema='metrics',
    tags=['performance', 'metrics']
) }}

WITH aircraft_usage AS (
    SELECT
        aircraft_msn,
        SUM(flight_hours) AS total_flight_hours,
        SUM(takeoffs) AS total_takeoffs,
        SUM(landings) AS total_landings,
        AVG(flight_hours) AS avg_daily_flight_hours,
        MAX(date) AS last_usage_date,
        MIN(date) AS first_usage_date
    FROM {{ ref('stg_usage_cycles') }}
    GROUP BY aircraft_msn
),

aircraft_maintenance AS (
    SELECT
        aircraft_msn,
        COUNT(*) AS total_maintenance_events,
        COUNT(*) FILTER (WHERE is_scheduled = false) AS unscheduled_maintenance_events,
        SUM(duration_hours) AS total_maintenance_hours
    FROM {{ ref('stg_maintenance_events') }}
    GROUP BY aircraft_msn
),

aircraft_alerts AS (
    SELECT
        aircraft_msn,
        COUNT(*) AS total_alerts,
        COUNT(*) FILTER (WHERE severity = 'CRITICAL') AS critical_alerts,
        COUNT(*) FILTER (WHERE severity = 'WARNING') AS warning_alerts
    FROM {{ ref('stg_alerts') }}
    GROUP BY aircraft_msn
),

aircraft_flight_data AS (
    SELECT
        aircraft_msn,
        AVG(engine_1_temp) AS avg_engine_1_temp,
        AVG(engine_2_temp) AS avg_engine_2_temp,
        AVG(fuel_flow_rate) AS avg_fuel_flow_rate,
        STDDEV(engine_1_vibration) AS stddev_engine_1_vibration,
        STDDEV(engine_2_vibration) AS stddev_engine_2_vibration
    FROM {{ ref('stg_flight_data') }}
    GROUP BY aircraft_msn
)

SELECT
    au.aircraft_msn,
    am.airline_code,
    au.total_flight_hours,
    au.total_takeoffs,
    au.total_landings,
    au.avg_daily_flight_hours,
    COALESCE(ama.total_maintenance_events, 0) AS total_maintenance_events,
    COALESCE(ama.unscheduled_maintenance_events, 0) AS unscheduled_maintenance_events,
    COALESCE(ama.total_maintenance_hours, 0) AS total_maintenance_hours,
    COALESCE(aa.total_alerts, 0) AS total_alerts,
    COALESCE(aa.critical_alerts, 0) AS critical_alerts,
    COALESCE(aa.warning_alerts, 0) AS warning_alerts,
    afd.avg_engine_1_temp,
    afd.avg_engine_2_temp,
    afd.avg_fuel_flow_rate,
    afd.stddev_engine_1_vibration,
    afd.stddev_engine_2_vibration,
    CASE 
        WHEN au.total_flight_hours > 0 THEN COALESCE(ama.total_maintenance_events, 0) / au.total_flight_hours
        ELSE NULL
    END AS maintenance_events_per_flight_hour,
    CASE 
        WHEN au.total_flight_hours > 0 THEN COALESCE(aa.total_alerts, 0) / au.total_flight_hours
        ELSE NULL
    END AS alerts_per_flight_hour,
    CASE 
        WHEN COALESCE(ama.total_maintenance_events, 0) > 0 THEN COALESCE(ama.unscheduled_maintenance_events, 0)::float / COALESCE(ama.total_maintenance_events, 1)
        ELSE NULL
    END AS unscheduled_maintenance_ratio,
    CURRENT_TIMESTAMP AS calculation_timestamp
FROM aircraft_usage au
JOIN {{ source('raw', 'aircraft_metadata') }} am ON au.aircraft_msn = am.aircraft_msn
LEFT JOIN aircraft_maintenance ama ON au.aircraft_msn = ama.aircraft_msn
LEFT JOIN aircraft_alerts aa ON au.aircraft_msn = aa.aircraft_msn
LEFT JOIN aircraft_flight_data afd ON au.aircraft_msn = afd.aircraft_msn
