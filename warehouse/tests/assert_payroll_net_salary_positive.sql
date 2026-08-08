-- Custom business rule: net_salary harus positif (tidak ada karyawan digaji <= 0).
select *
from {{ ref('mart_cleaned__payroll') }}
where net_salary <= 0
