-- Milestone 2.3 -- full refresh (materialized: table, lihat dbt_project.yml)
-- karena Sandbox mode (belum billing) memblokir semua DML, jadi strategi
-- incremental dbt manapun (merge/append) tidak bisa jalan -- lihat
-- decisions.md "DML diblokir total di Sandbox mode". unique_key + blok
-- is_incremental() DIBIARKAN dormant di bawah (otomatis tidak pernah aktif
-- selama materialized=table) supaya tinggal diaktifkan lagi begitu billing
-- aktif, tidak perlu ditulis ulang.
{{ config(unique_key='booking_id') }}

select *
from {{ ref('stg_reservation_revenue__bookings') }}

{% if is_incremental() %}
where booking_date > (select max(booking_date) from {{ this }})
{% endif %}
