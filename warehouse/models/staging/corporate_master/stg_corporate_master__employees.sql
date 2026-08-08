-- Cleaning per pemetaan-kebutuhan-konsumen-data-mart.md baris 45:
--   full_name  : trim whitespace berlebih
--   department : normalisasi 19 variasi -> 8 nilai baku (lihat seeds/department_mapping.csv --
--                seluruh 19 variasi ternyata murni beda kapitalisasi/whitespace, dikonfirmasi
--                lewat query langsung ke raw_production, bukan diasumsikan)
--   hire_date  : standarkan ke DATE (dari campuran ISO dan DD/MM/YYYY)
--   role_title : kosong (~2%) DIPERTAHANKAN -- missing value bermakna, tidak diisi paksa
with source as (
    select * from {{ source('raw_production', 'corporate_master__employees') }}
),

department_mapped as (
    select
        source.*,
        dept_map.department_canonical
    from source
    left join {{ ref('department_mapping') }} as dept_map
        on lower(trim(source.department)) = dept_map.department_key
)

select
    employee_id,
    property_id,
    trim(full_name) as full_name,
    role_title,
    department_canonical as department,
    access_level,
    -- hire_date raw tersimpan sebagai text, campuran ISO 'YYYY-MM-DD' dan 'DD/MM/YYYY'.
    -- Format DD/MM/YYYY dibedakan dari ISO karena mengandung '/', ISO selalu pakai '-'.
    case
        when hire_date like '%/%' then parse_date('%d/%m/%Y', hire_date)
        else parse_date('%Y-%m-%d', hire_date)
    end as hire_date,
    status,
    _synced_at
from department_mapped
