-- Models for intermediate layer
-- These models join and transform staging data

-- Intermediate model for aircraft reliability metrics
{{ config(
    materialized='table',
    schema='intermediate'
) }}

WITH maintenance_data AS (
    SELECT
        aircraft_msn,
        component_id,
        event_timestamp,
        event_type,
        is_scheduled
    FROM {{ ref('stg_maintenance_events') }}
),

alerts_data AS (
    SELECT
        aircraft_msn,
        component_id,
        alert_timestamp,
        alert_code,
        severity
    FROM {{ ref('stg_alerts') }}
),

usage_data AS (
    SELECT
        aircraft_msn,
        date,
        flight_hours,
        takeoffs,
        landings
    FROM {{ ref('stg_usage_cycles') }}
),

-- Agrégation des heures de vol par avion
aircraft_usage AS (
    SELECT
        aircraft_msn,
        SUM(flight_hours) AS total_flight_hours,
        SUM(takeoffs) AS total_takeoffs,
        SUM(landings) AS total_landings,
        MIN(date) AS first_date,
        MAX(date) AS last_date
    FROM usage_data
    GROUP BY aircraft_msn
),

-- Agrégation des événements de maintenance par avion et composant
component_maintenance AS (
    SELECT
        aircraft_msn,
        component_id,
        COUNT(*) AS total_maintenance_events,
        SUM(CASE WHEN event_type = 'REPAIR' THEN 1 ELSE 0 END) AS total_repairs,
        SUM(CASE WHEN event_type = 'INSPECTION' THEN 1 ELSE 0 END) AS total_inspections,
        SUM(CASE WHEN is_scheduled = false THEN 1 ELSE 0 END) AS total_unscheduled
    FROM maintenance_data
    GROUP BY aircraft_msn, component_id
),

-- Agrégation des alertes par avion et composant
component_alerts AS (
    SELECT
        aircraft_msn,
        component_id,
        COUNT(*) AS total_alerts,
        SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_alerts,
        SUM(CASE WHEN severity = 'WARNING' THEN 1 ELSE 0 END) AS warning_alerts
    FROM alerts_data
    GROUP BY aircraft_msn, component_id
)

-- Jointure finale pour créer les métriques de fiabilité
SELECT
    a.aircraft_msn,
    COALESCE(m.component_id, al.component_id) AS component_id,
    a.total_flight_hours,
    a.total_takeoffs,
    a.total_landings,
    a.first_date,
    a.last_date,
    COALESCE(m.total_maintenance_events, 0) AS total_maintenance_events,
    COALESCE(m.total_repairs, 0) AS total_repairs,
    COALESCE(m.total_inspections, 0) AS total_inspections,
    COALESCE(m.total_unscheduled, 0) AS total_unscheduled,
    COALESCE(al.total_alerts, 0) AS total_alerts,
    COALESCE(al.critical_alerts, 0) AS critical_alerts,
    COALESCE(al.warning_alerts, 0) AS warning_alerts,
    -- Calcul des métriques de fiabilité
    CASE 
        WHEN a.total_flight_hours > 0 AND COALESCE(m.total_repairs, 0) > 0 
        THEN a.total_flight_hours / COALESCE(m.total_repairs, 1) 
        ELSE NULL 
    END AS mtbf_hours,
    CASE 
        WHEN a.total_takeoffs > 0 AND COALESCE(m.total_repairs, 0) > 0 
        THEN a.total_takeoffs / COALESCE(m.total_repairs, 1) 
        ELSE NULL 
    END AS mtbf_cycles,
    CASE 
        WHEN a.total_flight_hours > 0 
        THEN COALESCE(m.total_unscheduled, 0) / a.total_flight_hours * 1000 
        ELSE NULL 
    END AS unscheduled_removal_rate,
    current_timestamp as calculated_at
FROM aircraft_usage a
LEFT JOIN component_maintenance m ON a.aircraft_msn = m.aircraft_msn
LEFT JOIN component_alerts al ON a.aircraft_msn = al.aircraft_msn AND 
    (m.component_id IS NULL OR m.component_id = al.component_id)
WHERE m.component_id IS NOT NULL OR al.component_id IS NOT NULL
