-- dim_loyalty_tier: label kategori agregat (Audit PII M5.2: domain guests_profile,
-- diteruskan apa adanya -- bukan atribut individual, lihat desain-skema-mart-aggregated.md).
select
    row_number() over (order by loyalty_tier) as loyalty_tier_id,
    loyalty_tier as loyalty_tier_name
from (
    select distinct loyalty_tier
    from {{ ref('mart_cleaned__guests') }}
    where loyalty_tier is not null
)
