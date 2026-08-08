-- dim_property: passthrough dari mart_cleaned__properties (property_id natural key stabil).
select
    property_id,
    property_name,
    region,
    opening_date
from {{ ref('mart_cleaned__properties') }}
