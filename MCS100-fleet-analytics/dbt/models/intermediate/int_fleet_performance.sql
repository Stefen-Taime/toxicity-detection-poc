-- Models for intermediate layer
-- These models join and transform staging data

-- Intermediate model for fleet performance metrics
{{ config(
    materialized='table',
    schema='intermediate'
) }}

WITH flight_data AS (
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
        speed
    FROM {{ ref('stg_flight_data') }}
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

-- Agrégation des données de vol par avion et par jour
daily_flight_metrics AS (
    SELECT
        aircraft_msn,
        DATE(event_timestamp) AS flight_date,
        COUNT(DISTINCT flight_id) AS flights_count,
        AVG(engine_1_temp) AS avg_engine_1_temp,
        AVG(engine_2_temp) AS avg_engine_2_temp,
        AVG(engine_1_pressure) AS avg_engine_1_pressure,
        AVG(engine_2_pressure) AS avg_engine_2_pressure,
        AVG(engine_1_vibration) AS avg_engine_1_vibration,
        AVG(engine_2_vibration) AS avg_engine_2_vibration,
        AVG(fuel_flow_rate) AS avg_fuel_flow_rate,
        AVG(altitude) AS avg_altitude,
        AVG(speed) AS avg_speed,
        MAX(altitude) AS max_altitude,
        MAX(speed) AS max_speed
    FROM flight_data
    GROUP BY aircraft_msn, DATE(event_timestamp)
),

-- Jointure avec les données d'utilisation
daily_performance AS (
    SELECT
        f.aircraft_msn,
        f.flight_date,
        f.flights_count,
        f.avg_engine_1_temp,
        f.avg_engine_2_temp,
        f.avg_engine_1_pressure,
        f.avg_engine_2_pressure,
        f.avg_engine_1_vibration,
        f.avg_engine_2_vibration,
        f.avg_fuel_flow_rate,
        f.avg_altitude,
        f.avg_speed,
        f.max_altitude,
        f.max_speed,
        u.flight_hours,
        u.takeoffs,
        u.landings,
        -- Calcul des métriques de performance
        CASE 
            WHEN u.flight_hours > 0 
            THEN f.avg_fuel_flow_rate * u.flight_hours 
            ELSE NULL 
        END AS estimated_fuel_consumption,
        CASE 
            WHEN u.takeoffs > 0 
            THEN u.flight_hours / u.takeoffs 
            ELSE NULL 
        END AS avg_flight_duration
    FROM daily_flight_metrics f
    LEFT JOIN usage_data u ON f.aircraft_msn = u.aircraft_msn AND f.flight_date = u.date
)

-- Agrégation mensuelle pour les métriques de performance de la flotte
SELECT
    aircraft_msn,
    DATE_TRUNC('month', flight_date) AS month,
    COUNT(flight_date) AS days_with_flights,
    SUM(flights_count) AS total_flights,
    SUM(flight_hours) AS total_flight_hours,
    SUM(takeoffs) AS total_takeoffs,
    SUM(landings) AS total_landings,
    AVG(avg_engine_1_temp) AS monthly_avg_engine_1_temp,
    AVG(avg_engine_2_temp) AS monthly_avg_engine_2_temp,
    AVG(avg_engine_1_pressure) AS monthly_avg_engine_1_pressure,
    AVG(avg_engine_2_pressure) AS monthly_avg_engine_2_pressure,
    AVG(avg_engine_1_vibration) AS monthly_avg_engine_1_vibration,
    AVG(avg_engine_2_vibration) AS monthly_avg_engine_2_vibration,
    AVG(avg_fuel_flow_rate) AS monthly_avg_fuel_flow_rate,
    SUM(estimated_fuel_consumption) AS monthly_fuel_consumption,
    AVG(avg_flight_duration) AS monthly_avg_flight_duration,
    MAX(max_altitude) AS monthly_max_altitude,
    MAX(max_speed) AS monthly_max_speed,
    -- Métriques d'efficacité
    CASE 
        WHEN SUM(flight_hours) > 0 
        THEN SUM(estimated_fuel_consumption) / SUM(flight_hours) 
        ELSE NULL 
    END AS fuel_efficiency,
    CASE 
        WHEN SUM(takeoffs) > 0 
        THEN SUM(flight_hours) / SUM(takeoffs) 
        ELSE NULL 
    END AS utilization_efficiency,
    current_timestamp as calculated_at
FROM daily_performance
GROUP BY aircraft_msn, DATE_TRUNC('month', flight_date)
