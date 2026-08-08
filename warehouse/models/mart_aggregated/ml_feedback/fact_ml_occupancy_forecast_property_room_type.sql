-- Milestone 5.4 -- feedback loop ML, PROVISIONAL/contoh (lihat catatan status
-- di header milestones/5.4-.../decisions.md, bukan kontrak final).
--
-- Grain: 1 baris per prediksi (property_id x room_type_id x target_date x
-- scored_at run). FROM ml_output.predictions sebagai base -- BUKAN LEFT JOIN
-- dari sisi mart_aggregated -- supaya model_version/feature_snapshot_at
-- selalu terisi by construction (KK2), tidak nullable lewat join.
-- entity_id di-split "property_id:room_type_id" (Keputusan #6). LEFT JOIN
-- actual occupancy (fact_revenue_room_type_daily, M5.3) by target_date untuk
-- forecast_error_abs -- nullable, cuma terisi kalau target_date sudah lewat
-- dan data aktual tersedia.
with predictions as (
    select
        prediction_id,
        entity_id,
        split(entity_id, ':')[offset(0)] as property_id,
        cast(split(entity_id, ':')[offset(1)] as int64) as room_type_id,
        model_name,
        model_version,
        prediction_type,
        cast(predicted_value as float64) as predicted_occupancy_rate,
        confidence_score,
        scored_at,
        feature_snapshot_at,
        target_date
    from {{ source('ml_output', 'predictions') }}
    where model_name = 'occupancy_forecast'
),

actuals as (
    select
        property_id,
        room_type_id,
        period_date,
        occupancy_rate as actual_occupancy_rate
    from {{ ref('fact_revenue_room_type_daily') }}
)

select
    p.prediction_id,
    p.property_id,
    p.room_type_id,
    p.target_date,
    p.model_name,
    p.model_version,
    p.prediction_type,
    p.predicted_occupancy_rate,
    p.confidence_score,
    p.scored_at,
    p.feature_snapshot_at,
    a.actual_occupancy_rate,
    abs(p.predicted_occupancy_rate - a.actual_occupancy_rate) as forecast_error_abs
from predictions as p
left join actuals as a
    on p.property_id = a.property_id
    and p.room_type_id = a.room_type_id
    and p.target_date = a.period_date
