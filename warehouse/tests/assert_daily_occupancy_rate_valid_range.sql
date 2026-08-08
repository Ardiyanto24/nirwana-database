-- Custom business rule: occupancy_rate harus di rentang [0, 1] (rasio kamar terjual).
select *
from {{ ref('mart_cleaned__daily_occupancy') }}
where occupancy_rate < 0 or occupancy_rate > 1
