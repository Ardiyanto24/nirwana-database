-- dim_employee: employee_id natural key. full_name diteruskan apa adanya
-- (Audit PII M5.2: domain employees_directory, akses granular diatur RBAC layer M4.x,
-- bukan masking di data layer -- lihat desain-skema-mart-aggregated.md Audit PII).
--
-- Milestone 5.7 -- property_id ditambahkan: kolom ini sudah ada penuh di
-- mart_cleaned.employees sejak M2.1-2.3 tapi terlewat di-select saat desain
-- M5.2, meski M5.2 KK#2 mewajibkan property_id sebagai kolom filter wajib di
-- seluruh skema. Ditemukan & diajukan lewat mekanisme M5.6 oleh Data Analyst
-- Serving (M3.2, non-simulasi) -- lihat docs/07-mart-aggregated/
-- pengajuan-perubahan-cakupan.md.
select
    e.employee_id,
    e.property_id,
    trim(e.full_name) as full_name,
    d.department_id,
    a.access_level_id
from {{ ref('mart_cleaned__employees') }} as e
left join {{ ref('dim_department') }} as d
    on e.department = d.department_name
left join {{ ref('dim_access_level') }} as a
    on e.access_level = a.access_level_name
