-- Milestone 2.3 -- model percobaan pertama untuk pola incremental TANPA
-- partitioning BigQuery (lihat decisions.md "Billing GCP belum diaktifkan").
-- Strategi merge (default dbt-bigquery untuk incremental tanpa partition_by)
-- berbasis unique_key booking_id -- baris yang sudah ada di-update, baris
-- baru di-insert, tidak ada overwrite-per-partition sama sekali.
{{ config(unique_key='booking_id') }}

select *
from {{ ref('stg_reservation_revenue__bookings') }}

{% if is_incremental() %}
where booking_date > (select max(booking_date) from {{ this }})
{% endif %}
