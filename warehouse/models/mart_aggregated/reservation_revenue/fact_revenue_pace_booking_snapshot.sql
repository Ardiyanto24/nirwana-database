-- Kasus Khusus M5.1/M5.2: pace booking. Self-union CREATE OR REPLACE (Keputusan #1
-- decisions.md M5.3) -- murni DDL (CTAS), kompatibel BigQuery Sandbox mode yang
-- blokir semua DML, efeknya seperti append. Full history, tanpa retention window.
--
-- Idempoten untuk re-run di hari yang sama: baris snapshot_date=hari ini di tabel
-- lama dibuang sebelum digabung ulang dengan hasil hitung baru, supaya tidak
-- terduplikasi kalau job dijalankan >1x per hari.
{% set target_relation = adapter.get_relation(database=this.database, schema=this.schema, identifier=this.identifier) %}

with room_capacity as (
    select
        property_id,
        room_type_id,
        count(*) as total_rooms_available
    from {{ ref('dim_room') }}
    group by 1, 2
),

new_snapshot as (
    select
        b.property_id,
        rt.room_type_id,
        b.check_in_date as stay_date,
        current_date() as snapshot_date,
        count(*) as rooms_sold_asof,
        any_value(rc.total_rooms_available) as rooms_available_asof
    from {{ ref('mart_cleaned__bookings') }} as b
    left join {{ ref('dim_room_type') }} as rt
        on b.room_type = rt.room_type_name
    left join room_capacity as rc
        on b.property_id = rc.property_id and rt.room_type_id = rc.room_type_id
    where b.status in ('completed', 'confirmed')
        and b.check_in_date > current_date()
        and b.check_in_date <= date_add(current_date(), interval 14 day)
    group by 1, 2, 3, 4
)

{% if target_relation is not none %}
select * from {{ this }} where snapshot_date != current_date()
union all
select * from new_snapshot
{% else %}
select * from new_snapshot
{% endif %}
