# Milestone 4.6: Uji Ketahanan RBAC Lintas Persona — Decisions

**Sumber:** `docs/03-implementation-plans/05-serving-ai-chatbot.md`, Milestone 4.6 (baris 146-161).
**Prasyarat:** Milestone 4.1-4.5 (pemetaan, view, kredensial, API, audit log — semua Completed).
**Status:** Completed
**Date started:** 2026-08-10

## Lingkup Sumber / Contract

- **Lingkup:** Pengujian menyeluruh dan sistematis 20 persona untuk memastikan tidak ada kebocoran akses (baik akses yang seharusnya diberikan tapi tidak muncul, maupun sebaliknya). Termasuk re-verifikasi prinsip *superset* di level implementasi.
- **Output:** Hasil pengujian sistematis 20 persona (akses didapat vs seharusnya) + daftar temuan dan status perbaikan.
- **Kriteria Keberhasilan:**
  1. Seluruh 20 persona, diuji lewat API, cakupan akses persis cocok `role_permissions` — tidak lebih, tidak kurang.
  2. Prinsip superset (Staff→Manager, Manager→Corporate Director, Manager→General Manager, seluruh peran→CEO) terverifikasi ulang di level implementasi.

## Temuan Eksplorasi

- Ground truth ditarik langsung dari `mart_cleaned.role_permissions`: 77 baris, 20 `role_title`, 10 `data_domain` — 29 baris `all_properties` (5 role Korporat), 48 baris `own_property` (15 role Staff+Manager).
- KK1 secara harfiah minta "tidak lebih, tidak kurang" — matriks lengkap 20×10 = 200 kombinasi harus diuji (77 ALLOW + 123 DENY), bukan cuma yang granted, supaya kebocoran di sel yang seharusnya DENY tidak luput. 200 kombinasi terlalu banyak untuk pola manual `curl` M4.1-4.5 — dibutuhkan script data-driven.
- `authorize(role_title, domain)` adalah keputusan level-domain, bukan level-view — 1 view representatif per domain cukup untuk KK M4.6 (kolom/isi view + filter own_property per view sendiri sudah dibuktikan M4.2/M4.4).
- **Temuan arsitektural**: `role_title` (dipakai `authorize()`) dan `employee_id` (dipakai `resolve_property_id()`) adalah dua klaim independen — API tidak pernah memverifikasi `employee_id` yang dikirim benar-benar berjabatan `role_title` yang diklaim. Diperkuat temuan data: `mart_cleaned.employees.role_title` NULL by design, `department`+`access_level` cuma 8×2 bucket kasar (tidak cukup granular memetakan 20 `role_title` `role_permissions` satu-satu). Konsisten Lapis 1/Lapis 2 (M4.5 Keputusan #7) — pengikatan identitas pegawai↔role adalah tanggung jawab Lapis 1. Konsekuensi: 1 `employee_id` tetap per property cukup untuk seluruh sel `OP` Layer A, apa pun `role_title` yang diklaim.
- Superset (KK2) bisa diverifikasi tanpa panggilan HTTP tambahan — 4 rantai adalah pernyataan set-containment atas hasil Layer A yang sudah terkumpul.

## Keputusan Teknis

1. **Matriks lengkap 20×10, via script bukan curl manual** — `scripts/chatbot_rbac_test/run_access_matrix.py`, 200 panggilan, 1 view representatif per domain (lihat `docs/09-serving-ai-chatbot/rancangan-pengujian-rbac-chatbot.md`).
2. **Ground truth: query langsung `mart_cleaned.role_permissions`** via `scripts/chatbot_credentials/connections.py::get_serving_connection` (admin, read-only) — bukan lewat `chatbot_authz_reader` (kredensial itu murni untuk API produksi, M4.5 menegaskan "tidak pernah diteruskan sebagai response endpoint apa pun"; tooling uji eksternal beda konteks, boleh baca langsung).
3. **`employee_id` tetap per property untuk seluruh uji `own_property`** — lihat Temuan Eksplorasi di atas.
4. **Layer B spot-check (~15), bukan exhaustive 48** — mekanisme override domain-agnostic, sudah terbukti berulang M4.4/M4.5.
5. **Layer C dihitung dari hasil Layer A nyata, tanpa panggilan tambahan** — 4 rantai, 40 pasang set-containment total (7+7+7+19, dikoreksi dari draft awal "34" — salah hitung, lihat Temuan Implementasi Checkpoint 3).
6. **Dokumen rancangan pengujian terpisah, ditulis sebelum eksekusi** — `docs/09-serving-ai-chatbot/rancangan-pengujian-rbac-chatbot.md` (diminta eksplisit user), memuat matriks 200 sel lengkap, pemetaan view, data uji, definisi superset, prosedur, kriteria lulus.
7. **Temuan ditangani seperti pola M4.4** — mismatch nyata = bug RBAC, diperbaiki sebelum ditutup. Independensi `role_title`/`employee_id` didokumentasikan sebagai fakta desain (bukan gap), mengikuti pola investigasi M4.4 (`guests_pii`/`guests_profile`).

## Task Breakdown

5 checkpoint.

### Checkpoint 0 — Rancangan Pengujian
1. `docs/09-serving-ai-chatbot/rancangan-pengujian-rbac-chatbot.md`. — **Selesai**
2. `decisions.md` (dokumen ini). — **Selesai**

### Checkpoint 1 — Tooling
3. `scripts/chatbot_rbac_test/{connections.py,ground_truth.py,run_access_matrix.py}` — dry-run kombinasi dikenal sebelum full run. — **Selesai**. `load_role_permissions()` mengembalikan 77 baris (cocok jumlah `role_permissions`). Dry-run 3 kombinasi: CEO/reservation -> 200 (expect 200), HR Staff/financial -> 403 (expect 403), General Manager/spa_event -> 200 (expect 200) — 3/3 cocok.

**✅ Checkpoint 1** — mekanika tooling tervalidasi, siap full run Layer A.

### Checkpoint 2 — Layer A: Matriks Akses Penuh (KK1)
4. Full run 200 kombinasi terhadap `uvicorn` live. Investigasi + perbaiki mismatch (kalau ada). — **Selesai**. **200/200 cocok, 0 mismatch** — tidak perlu perbaikan. Hasil lengkap di `hasil-layer-a-matriks-akses.txt`.

**✅ Checkpoint 2** — KK1 (lapisan keputusan akses) terpenuhi penuh untuk seluruh 20 persona.

### Checkpoint 3 — Layer B + C (KK1 kedalaman + KK2)
5. `run_property_override_sample.py` — 15×2 kombinasi. — **Selesai**, 15/15 OK (0 inconclusive).
6. Analisis superset 40 pasang dari hasil Layer A. — **Selesai**, 40/40 valid.

**✅ Checkpoint 3** — KK1 (kedalaman mekanisme) dan KK2 (superset) sama-sama terpenuhi.

## Temuan Implementasi (Checkpoint 3)

- **Salah hitung jumlah pasang Layer C di draft rancangan** (`decisions.md`/`rancangan-pengujian-rbac-chatbot.md` versi Checkpoint 0): ditulis "1+7+7+19 = 34 pasang", padahal rantai #1 (Staff→Manager) sendiri berisi 7 pasang, bukan 1 — total sebenarnya 7+7+7+19 = **40**. Ditemukan saat `analyze_superset.py` mencetak "40/40 pasang superset valid" (tidak cocok ekspektasi tertulis 34) — bukan bug logic, murni typo aritmatika saat menulis rancangan. Kedua dokumen dikoreksi ke 40.

### Checkpoint 4 (final) — Temuan + Penutupan
7. Dokumentasikan temuan independensi `role_title`/`employee_id`. — **Selesai**. Dikonfirmasi definitif lewat uji langsung: `employee_id=E0001` (pegawai Corporate manager sungguhan) + klaim `role_title=Housekeeping Staff` (Staff-tier, facility) tetap 200 OK, data P01 (properti asli E0001) — membuktikan API sungguhan tidak pernah mencocokkan keduanya.
8. `report.md` — verifikasi ulang KK1-KK2, daftar temuan + status perbaikan. Commit; tanya user sebelum push. — **Selesai**.

**✅ Checkpoint 4 (final)** — Status: Completed. 0 temuan bug RBAC di 240 panggilan HTTP (200 Layer A + 30 Layer B).
