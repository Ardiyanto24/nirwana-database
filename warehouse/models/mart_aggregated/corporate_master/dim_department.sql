-- dim_department: unit organisasi karyawan (BUKAN dim_business_line/USALI -- lihat
-- disambiguasi di desain-skema-mart-aggregated.md, bagian Corporate/Financial).
-- Sudah dinormalisasi penuh di staging (seeds/department_mapping.csv), 8 nilai baku.
select
    row_number() over (order by department) as department_id,
    department as department_name
from (
    select distinct department
    from {{ ref('mart_cleaned__employees') }}
    where department is not null
)
