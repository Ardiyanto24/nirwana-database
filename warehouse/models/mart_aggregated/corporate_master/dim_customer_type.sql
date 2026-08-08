-- dim_customer_type: inhouse/walk-in, dipakai lintas domain F&B dan Spa & Event.
select
    row_number() over (order by customer_type) as customer_type_id,
    customer_type as customer_type_name
from (
    select distinct customer_type
    from {{ ref('mart_cleaned__fnb_transactions') }}
    where customer_type is not null

    union distinct

    select distinct customer_type
    from {{ ref('mart_cleaned__spa_bookings') }}
    where customer_type is not null
)
