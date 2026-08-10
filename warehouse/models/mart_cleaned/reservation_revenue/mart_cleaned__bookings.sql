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

-- TEMPORARY -- Milestone 6.3 Checkpoint 2 Task 6, uji coba terkontrol KK1
-- (fault-injection nyata, pola sama M2.3). Baris ini DIHAPUS setelah
-- diverifikasi capture_dbt_test_results.py menangkap FAIL dengan benar.
union all
select
    CURRENT_TIMESTAMP() as _synced_at,
    'confirmed' as status,
    'G00001' as guest_id,
    1 as nights,
    -500000.0 as total_amount,
    'Direct' as booking_channel,
    DATE('2026-01-01') as check_in_date,
    DATE('2026-01-02') as check_out_date,
    DATE('2026-01-01') as booking_date,
    'Standard' as room_type,
    'P01' as property_id,
    -500000.0 as room_rate,
    'BK_M63_SIMULATION_BAD_ROW' as booking_id
