# Milestone 5.2: Desain Struktur Tabel Mart Aggregated — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Skema mencakup seluruh metrik prioritas Milestone 5.1 tanpa ambiguitas granularitas — tiap tabel punya definisi grain yang jelas.** — Terpenuhi. 45 fact table dirancang di `docs/07-mart-aggregated/desain-skema-mart-aggregated.md`, tiap tabel dengan grain eksplisit satu baris ("1 baris per ..."). Seluruh 77 baris Cakupan Awal + 3 Kebutuhan Khusus dari M5.1 tercakup (dicek per checkpoint domain: Revenue 15/15, F&B 15/15 Cakupan Awal+Khusus, Facility/Ops 14/14, Spa & Event 13/13, HR 10/10 termasuk watchlist di Task 8, Corporate/Financial 13/13). 2 kasus khusus (pace booking, watchlist HR) dapat fact table tersendiri sesuai karakternya. Ditemukan & didokumentasikan 1 gap M5.1 (booking per loyalty_tier) dan 2 disambiguasi konsep penting ("department" HR vs "department" USALI; payroll pakai `dim_department` bukan `dim_business_line`) yang mencegah ambiguitas di implementasi M5.3.
- [x] **Skema mempertimbangkan filter wajib konsumen (`property_id`, `department`, rentang waktu) sebagai kolom mudah difilter/di-cluster, bukan tersembunyi di dalam kalkulasi.** — Terpenuhi. Seluruh 45 fact table punya `property_id` (atau FK yang menurunkannya, mis. `outlet_id`→`dim_outlet.property_id`) sebagai kolom cluster eksplisit, kolom `department_id`/`business_line_id`/`priority_id` dst sebagai cluster sekunder sesuai relevansi domain, dan kolom `DATE` native (`period_date`/`snapshot_date`) sebagai partition key BigQuery — bukan disembunyikan di ekspresi kalkulasi.
- [x] **Setiap kolom yang berpotensi PII di `mart_aggregated` punya keputusan eksplisit (diteruskan apa adanya dengan alasan, atau di-mask dengan metode jelas) — tidak ada kolom PII masuk skema tanpa keputusan sadar.** — Terpenuhi. Bagian "Audit PII" mendata 3 kolom yang tersentuh domain RBAC personal (`dim_employee.full_name` — `employees_directory`; `dim_loyalty_tier.loyalty_tier_name` dan `dim_nationality_group.group_name` — `guests_profile`), masing-masing dengan keputusan eksplisit "diteruskan apa adanya" beserta alasannya. Ditelusuri ulang seluruh 45 fact + 27 dimension table dan dikonfirmasi **tidak ada kolom `guests_pii`** (email/phone/guest_id individual) masuk skema sama sekali — seluruh kebutuhan kontak tamu tetap dilayani row-level dari `mart_cleaned`.

## Deliverables

- `docs/07-mart-aggregated/desain-skema-mart-aggregated.md` — 27 dimension table, 45 fact table (Revenue 5, F&B 8, Facility/Ops 9, Spa & Event 6, HR 6, Corporate/Financial 9, Kasus Khusus 2), bagian Audit PII.
- `milestones/5.2-desain-struktur-tabel-mart-aggregated/{decisions,logs}.md`.
- 1 entri baru di `docs/keputusan-tertunda.md` (data dictionary penuh ditunda ke M5.3).

## Deviations from decisions.md

Tidak ada deviasi pada 10 keputusan inti. Satu penambahan wajar muncul selama eksekusi (bukan deviasi keputusan, murni cakupan): saat mendesain fact table ditemukan 4 dimension table yang terlewat di Task 1 inventarisasi awal (`dim_pricing_reason`, `dim_waste_reason`, `dim_ingredient`, `dim_employee_status`) — ditambahkan sebagai amendemen terdokumentasi di bagian Dimension Tables, bukan disisipkan diam-diam.

## Known Gaps / Follow-ups

- **Tension append-only vs Sandbox mode belum terpecahkan** — `fact_revenue_pace_booking_snapshot` butuh perilaku append-only (baris snapshot historis tidak pernah diupdate), sementara BigQuery Sandbox mode saat ini memblokir seluruh DML dan seluruh tabel lain di skema ini didesain full-refresh. Dicatat eksplisit sebagai pertanyaan implementasi terbuka untuk M5.3 — di luar scope M5.2 yang hanya menjamin struktur benar.
- **Threshold SLA breach dan watchlist HR masih belum diputuskan** — skema sudah mengakomodasi (kolom nilai mentah tersedia, tanpa flag), tapi nilai ambang batas aktualnya tetap perlu keputusan bisnis terpisah sebelum M5.3 bisa menghasilkan kolom klasifikasi (breach/tidak, watchlist/tidak).
- **Data dictionary penuh belum ditulis** — sesuai Keputusan #10, sengaja ditunda ke M5.3 setelah SQL transformasi selesai dan teruji (dicatat di `docs/keputusan-tertunda.md`).
- **Aturan kategorisasi `nationality` → `dim_nationality_group`** (Domestik vs Mancanegara) belum diformalkan jadi aturan eksplisit (mis. daftar kode negara) — perlu diputuskan sebelum implementasi M5.3, diwariskan dari catatan M5.1.

## Handoff Notes

- **`docs/07-mart-aggregated/desain-skema-mart-aggregated.md` adalah input utama Milestone 5.3** (implementasi transformasi SQL). 3 hal yang perlu ditindaklanjuti eksplisit di sana: (1) selesaikan tension append-only pace booking vs Sandbox mode DML block, (2) tulis data dictionary lengkap (cara hitung, unit, contoh nilai) mengikuti pola `Metadata.md`, (3) tentukan aturan kategorisasi nationality.
- **2 disambiguasi konsep wajib dipahami implementer M5.3**: (a) `dim_department` (unit organisasi karyawan, dipakai HR & `fact_payroll_*`) BUKAN `dim_business_line` (baris USALI Room/F&B/Spa&Event/Overall/Corporate Overhead, dipakai `fact_financial_*` dari `financial_summary`) — keduanya sama-sama disebut "department" di dokumen requirement tapi taksonomi berbeda; (b) filter `business_line_id` ke `Room`/`F&B`/`Spa&Event` saja wajib diterapkan untuk metrik "departmental margin", tidak boleh menyertakan `Overall`/`Corporate Overhead` (risiko double counting, sama seperti aturan asli di `financial_summary`).
- **Untuk Milestone 04/05 (serving Data Analyst & AI Chatbot)**: skema ini sudah PII-safe by design (tidak ada `guests_pii` sama sekali) — kedua pekerjaan konsumen tidak perlu menambah lapisan masking sendiri untuk domain tamu, tapi tetap perlu RBAC layer untuk `dim_employee.full_name` (`employees_directory`) sesuai peta akses masing-masing persona/peran.
- Metrik cross-domain (`capture_rate`, `delayed_rate_vs_occupancy`, `service_charge_pool`'s korelasi occupancy, `gop_pricing_impact`) sudah ditandai eksplisit di tiap fact table terkait — implementer M5.3 tinggal ikuti anotasi "cross-domain, precompute" di kolom yang relevan.
