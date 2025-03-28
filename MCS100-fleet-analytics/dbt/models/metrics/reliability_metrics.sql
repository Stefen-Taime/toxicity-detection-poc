-- Models for metrics layer
-- This file defines the reliability metrics model

{{ config(
    materialized='table',
    schema='metrics',
    tags=['reliability', 'metrics']
) }}

WITH component_failures AS (
    SELECT
        me.component_id,
        COUNT(*) AS total_failures,
        COUNT(*) FILTER (WHERE me.is_scheduled = false) AS unscheduled_failures
    FROM {{ ref('stg_maintenance_events') }} me
    WHERE me.event_type = 'FAILURE'
    GROUP BY me.component_id
),

component_alerts AS (
    SELECT
        a.component_id,
        COUNT(*) AS total_alerts,
        COUNT(*) FILTER (WHERE a.severity = 'CRITICAL') AS critical_alerts
    FROM {{ ref('stg_alerts') }} a
    GROUP BY a.component_id
),

component_usage AS (
    SELECT
        c.aircraft_msn,
        c.component_id,
        SUM(u.flight_hours) AS total_flight_hours,
        SUM(u.takeoffs) AS total_cycles
    FROM {{ source('raw', 'components') }} c
    JOIN {{ ref('stg_usage_cycles') }} u ON c.aircraft_msn = u.aircraft_msn
    GROUP BY c.aircraft_msn, c.component_id
)

SELECT
    cu.component_id,
    cu.aircraft_msn,
    COALESCE(cf.total_failures, 0) AS total_failures,
    COALESCE(cf.unscheduled_failures, 0) AS unscheduled_failures,
    COALESCE(ca.total_alerts, 0) AS total_alerts,
    COALESCE(ca.critical_alerts, 0) AS critical_alerts,
    cu.total_flight_hours,
    cu.total_cycles,
    CASE 
        WHEN COALESCE(cf.total_failures, 0) > 0 THEN cu.total_flight_hours / COALESCE(cf.total_failures, 1)
        ELSE NULL
    END AS mtbf_hours,
    CASE 
        WHEN cu.total_flight_hours > 0 THEN COALESCE(cf.total_failures, 0) * 1000.0 / cu.total_flight_hours
        ELSE NULL
    END AS failure_rate_per_1000_hours,
    CURRENT_TIMESTAMP AS calculation_timestamp
FROM component_usage cu
LEFT JOIN component_failures cf ON cu.component_id = cf.component_id
LEFT JOIN component_alerts ca ON cu.component_id = ca.component_id
