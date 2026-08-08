-- dim_business_line: baris USALI dari financial_summary.department (Room/F&B/Spa&Event/
-- Overall/Corporate Overhead). BUKAN dim_department (unit organisasi karyawan) -- lihat
-- disambiguasi eksplisit di desain-skema-mart-aggregated.md, bagian Corporate/Financial.
select
    row_number() over (order by department) as business_line_id,
    department as line_name
from (
    select distinct department
    from {{ ref('mart_cleaned__financial_summary') }}
    where department is not null
)
