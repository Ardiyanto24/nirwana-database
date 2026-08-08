-- Kasus Khusus M5.1/M5.2 kategori B: within-entity-over-time. baseline_* = rata-rata
-- seluruh bulan SEBELUM bulan berjalan untuk employee yang sama (expanding window,
-- bukan angka tetap) -- "rate absen 3 bulan terakhir dibanding rate absen individu
-- itu sebelumnya" (M5.1 §5.2).
--
-- Milestone 5.6 -- in_watchlist ditambahkan: threshold yang sebelumnya belum
-- ditentukan (Keputusan #7 M5.2 decisions.md) diputuskan lewat siklus
-- pengajuan-evaluasi-tindak lanjut M5.6 (lihat docs/07-mart-aggregated/
-- pengajuan-perubahan-cakupan.md). Rasio deviasi > 5x baseline individu
-- (absence ATAU late) -- coalesce ke false supaya bulan pertama karyawan
-- (baseline NULL, ratio NULL) dianggap belum bisa dinilai, bukan otomatis
-- ter-flag.
--
-- Angka 5x (BUKAN 1.5x seperti draf keputusan awal) dikalibrasi terhadap
-- distribusi riil: 1.5x ternyata men-flag 47% seluruh baris (P75 absence
-- ratio SUDAH 1.9x -- jelas bukan "di luar kebiasaan"), sama sekali tidak
-- berguna sebagai early warning. 5x mendekati P95 (4.64x) -- proporsi
-- ter-flag turun ke ~4.7%, jauh lebih masuk akal sebagai watchlist
-- (minoritas kecil yang benar-benar menyimpang). Lihat docs/07-mart-aggregated/
-- pengajuan-perubahan-cakupan.md untuk detail kalibrasi.
with monthly as (
    select
        employee_id,
        date_trunc(date, month) as period_date,
        safe_divide(countif(status = 'absent'), count(*)) as absence_rate,
        safe_divide(countif(status = 'late'), count(*)) as late_rate
    from {{ ref('mart_cleaned__staff_shifts') }}
    group by 1, 2
),

with_baseline as (
    select
        employee_id,
        period_date,
        absence_rate as current_absence_rate,
        avg(absence_rate) over (
            partition by employee_id order by period_date
            rows between unbounded preceding and 1 preceding
        ) as baseline_absence_rate,
        late_rate as current_late_rate,
        avg(late_rate) over (
            partition by employee_id order by period_date
            rows between unbounded preceding and 1 preceding
        ) as baseline_late_rate
    from monthly
)

select
    employee_id,
    period_date,
    current_absence_rate,
    baseline_absence_rate,
    current_late_rate,
    baseline_late_rate,
    safe_divide(current_absence_rate, nullif(baseline_absence_rate, 0)) as absence_deviation_ratio,
    safe_divide(current_late_rate, nullif(baseline_late_rate, 0)) as late_deviation_ratio,
    coalesce(safe_divide(current_absence_rate, nullif(baseline_absence_rate, 0)) > 5, false)
        or coalesce(safe_divide(current_late_rate, nullif(baseline_late_rate, 0)) > 5, false) as in_watchlist
from with_baseline
