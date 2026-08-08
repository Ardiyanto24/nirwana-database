-- Custom business rule test (Milestone 2.3 KK#2/#3): total_amount tidak
-- boleh negatif. dbt singular test -- FAIL kalau query ini mengembalikan
-- baris apa pun.
select *
from {{ ref('mart_cleaned__bookings') }}
where total_amount < 0
