select
    outlet_id,
    date(transaction_datetime) as period_date,
    extract(hour from transaction_datetime) as hour_of_day,
    count(distinct transaction_id) as transaction_count
from {{ ref('mart_cleaned__fnb_transactions') }}
group by 1, 2, 3
