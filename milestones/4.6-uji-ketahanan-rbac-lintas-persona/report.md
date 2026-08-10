# Milestone 4.6: Uji Ketahanan RBAC Lintas Persona — Report

**Status:** Completed
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [x] **Seluruh 20 persona, saat diuji lewat API, menghasilkan cakupan akses yang persis cocok dengan `role_permissions` — tidak lebih, tidak kurang.** — Layer A: matriks **exhaustive** 20 role × 10 domain (200 sel, bukan sampel) dijalankan lewat `scripts/chatbot_rbac_test/run_access_matrix.py` terhadap API live, dibandingkan terhadap ground truth yang ditarik langsung dari `mart_cleaned.role_permissions` (77 baris) saat runtime. **Hasil: 200/200 sel cocok ekspektasi, 0 mismatch** — tidak ada satu pun kebocoran akses (sel yang seharusnya DENY ternyata ALLOW) maupun akses hilang (sel yang seharusnya ALLOW ternyata DENY). Bukti lengkap: `hasil-layer-a-matriks-akses.txt`. Kedalaman lebih lanjut (Layer B): 15 persona `own_property` diuji ulang mekanisme override property — 15/15 OK, membuktikan bukan cuma keputusan ya/tidak yang benar tapi penegakan batas properti sungguhan juga benar.
- [x] **Prinsip superset (Director superset Manager, Manager superset Staff, CEO superset semua) terverifikasi ulang di level implementasi.** — Layer C: 4 rantai superset (Staff→Manager 7 pasang, Manager→Corporate Director 7 pasang, Manager→General Manager 7 pasang, seluruh peran→CEO 19 pasang, total 40 pasang) dihitung sebagai *set-containment* murni dari hasil Layer A **nyata** (`scripts/chatbot_rbac_test/analyze_superset.py`, parsing HTTP status aktual — bukan re-derivasi dari `role_permissions`). **Hasil: 40/40 pasang valid.** Bukti lengkap: `hasil-layer-c-superset.txt`.

## Deliverables

- `docs/09-serving-ai-chatbot/rancangan-pengujian-rbac-chatbot.md` — dokumen rancangan pengujian komprehensif (ditulis dan disetujui user SEBELUM eksekusi), memuat matriks ekspektasi 200 sel lengkap.
- `scripts/chatbot_rbac_test/{connections.py,ground_truth.py,run_access_matrix.py,run_property_override_sample.py,analyze_superset.py}` — tooling pengujian otomatis, reusable untuk regresi RBAC di masa depan (mis. kalau `role_permissions` berubah, tinggal jalankan ulang seluruh 3 skrip).
- `milestones/4.6-.../hasil-layer-a-matriks-akses.txt`, `hasil-layer-c-superset.txt` — bukti mentah lengkap.
- `requirements.txt` — tambah `requests==2.33.1` (kebutuhan HTTP client terprogram, sebelumnya seluruh verifikasi M3.4-4.5 manual `curl`).

## Deviations from decisions.md

Tidak ada deviasi dari 7 keputusan teknis. Satu **kesalahan tulis murni aritmatika** ditemukan dan diperbaiki di tengah jalan (bukan deviasi keputusan): draft awal rancangan pengujian (Checkpoint 0) menulis total pasang Layer C sebagai "1+7+7+19 = 34", padahal rantai #1 (Staff→Manager) sendiri berisi 7 pasang (bukan 1) — total sebenarnya 7+7+7+19 = **40**. Ditemukan saat `analyze_superset.py` mencetak "40/40" yang tidak cocok ekspektasi tertulis; diinvestigasi dan dipastikan itu salah tulis di dokumen, bukan bug skrip. Kedua dokumen (`rancangan-pengujian-rbac-chatbot.md`, `decisions.md`) dikoreksi.

## Temuan (KK Output #2: "Daftar temuan dan status perbaikannya")

- **0 temuan bug RBAC nyata** — di seluruh 240 panggilan HTTP (200 Layer A + 30 Layer B) sepanjang milestone ini, tidak ditemukan satu pun kasus akses yang tidak sesuai `role_permissions`. RBAC Lapis 2 yang dibangun M4.1-4.5 terbukti tepat 100% terhadap ground truth di seluruh 20 persona, bukan cuma sampel yang diuji milestone-milestone sebelumnya.
- **1 temuan arsitektural, diinvestigasi dan didokumentasikan sebagai fakta desain (bukan gap)**: `role_title` (dipakai `authorize()` untuk keputusan domain) dan `employee_id` (dipakai `resolve_property_id()` untuk keputusan properti) adalah **dua klaim yang sepenuhnya independen** di dalam API — tidak pernah saling divalidasi. Dikonfirmasi definitif lewat uji langsung: `employee_id=E0001` (pegawai `department=Corporate`, `access_level=manager` sungguhan) dikirim bersama klaim `role_title=Housekeeping Staff` (Staff-tier, domain `facility`) — API tetap mengembalikan 200 OK, data 100% property P01 (properti asli E0001), bukan ditolak maupun error. Ini **bukan** kebocoran RBAC (`authorize()` tetap benar memutuskan berdasarkan `role_title` yang diklaim, `resolve_property_id()` tetap benar memutuskan berdasarkan `employee_id` yang diklaim — keduanya independen secara sadar) — melainkan konsekuensi langsung dari pemisahan Lapis 1/Lapis 2 (M4.5 Keputusan #7): pengikatan "pegawai X sungguhan memang menjabat role_title Y" adalah tanggung jawab Lapis 1 (sistem chatbot/session, di luar cakupan repo ini), bukan Lapis 2. Status: **tidak perlu perbaikan** — didokumentasikan eksplisit di sini dan di `rancangan-pengujian-rbac-chatbot.md` supaya tim yang membangun Lapis 1 nanti sadar mereka tidak boleh mengasumsikan Lapis 2 melakukan pengecekan ini.
- **1 kesalahan tulis (bukan bug)**: lihat "Deviations" di atas — jumlah pasang Layer C di draft awal.

## Known Gaps / Follow-ups

- **Bukan pengujian lintas semua 67 view** — Layer A sengaja hanya menguji 1 view representatif per domain (keputusan #1), karena `authorize()` adalah keputusan level-domain, bukan level-view. Kolom/isi tiap view individual sudah dibuktikan M4.2, filter `own_property` per view (termasuk 2 kasus koreksi M4.4) sudah dibuktikan M4.4 — tidak diulang di sini.
- **Layer B sampel (15), bukan exhaustive 48** — mekanisme override domain-agnostic, dianggap cukup dibuktikan sekali per persona. Kalau ada perubahan kode `_run_whitelisted_query`/`resolve_property_id` di masa depan, disarankan jalankan ulang `run_property_override_sample.py` sebagai regresi cepat.
- **Tooling reusable untuk regresi** — `scripts/chatbot_rbac_test/` tidak dijadwalkan otomatis (manual-only, sama klasifikasi tooling M4.x lain) — kalau `role_permissions` berubah di masa depan (penambahan role/domain baru), 3 skrip ini bisa dijalankan ulang langsung tanpa perubahan kode untuk re-validasi menyeluruh.

## Handoff Notes

- **Untuk tim yang membangun Lapis 1 (sistem AI Chatbot, di luar repo ini)**: baca bagian temuan independensi `role_title`/`employee_id` di atas — Lapis 1 bertanggung jawab memastikan `employee_id` yang dikirim ke API ini benar-benar milik pengguna yang sedang login dengan `role_title` yang diklaim. Lapis 2 (repo ini) tidak dan tidak akan pernah melakukan pengecekan itu.
- **Untuk audit RBAC berikutnya (kalau `role_permissions` berubah)**: jalankan ulang `python run_access_matrix.py` → `python run_property_override_sample.py` → `python analyze_superset.py` secara berurutan (server `uvicorn` harus hidup untuk 2 yang pertama) — seluruh matriks ekspektasi otomatis ditarik ulang dari database, tidak perlu edit kode kalau cuma isi `role_permissions` yang berubah (cuma perlu edit `ROLES`/`DOMAINS`/`CHAINS` di `ground_truth.py`/`analyze_superset.py` kalau ada role/domain BARU ditambahkan).
- **Milestone 4.x (Serving AI Chatbot) kini selesai penuh** (4.1-4.6, seluruhnya Completed) — pekerjaan yang masih tersisa di dokumen sumber `05-serving-ai-chatbot.md` adalah integrasi nyata dengan sistem AI Chatbot pihak lain (di luar cakupan repo ini) dan Milestone 6.5 (`06-monitoring-warehouse-serving-fase2.md`, belum diberi nomor milestone, belum dimulai) yang akan memanfaatkan audit log M4.5.
