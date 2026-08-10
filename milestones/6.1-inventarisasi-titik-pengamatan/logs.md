# Milestone 6.1 — Execution Log

## 2026-08-10 — Mulai kerja, klarifikasi workflow project
Did: User meminta cek progress project secara umum sebelum memulai Milestone 6.x. Ringkasan status seluruh Fase 1 (Completed, kecuali 1.5/1.7 Partially Completed) dan Fase 2 (Completed s.d. Milestone 5.7, termasuk 3.6 Partially Completed) disampaikan. User lalu meminta pemahaman workflow project (skill `milestone-execution`) dipastikan dulu sebelum eksekusi dimulai.
Result: worked. Workflow 3-file (`decisions.md`/`logs.md`/`report.md`) per milestone dikonfirmasi dipahami.

## 2026-08-10 — Percobaan breakdown pertama, dikoreksi user
Did: Skill `milestone-execution` dan `planning-and-task-breakdown` dipanggil untuk breakdown Milestone 6.1 langsung dari dokumen sumber (`06-monitoring-warehouse-serving-fase2.md`) + 1 Explore agent + 1 Plan agent, tanpa membaca histori milestone sebelumnya secara mendalam.
Result: Dikoreksi user — ditolak lewat `ExitPlanMode` rejection. User menekankan Milestone 6.1 "butuh pengamatan yang jeli dan mendetail" dan bahwa milestone-milestone sebelumnya "tidak semua sesuai rancangan, beberapa berubah karena harus menyesuaikan kondisi ketika pengerjaan" — meminta pembacaan seluruh `report.md` milestone + dokumen `docs/` yang dihasilkan sepanjang project, dilakukan **bertahap per layer**, bukan sekaligus atau lewat delegasi Explore agent.

## 2026-08-10 — Eksplorasi Layer 1: Fondasi Monitoring Production (Fase 1)
Did: Baca `report.md` Milestone 1.1-1.6 + status `logs.md` 1.7 (belum ada `report.md`, deploy web publik masih tertunda) + `docs/04-monitoring/baseline-inventaris-produksi.md` penuh.
Result: worked. Pola arsitektur `monitoring.*` (snapshot append-only + tabel `alerts`, isolasi `_simulation`) dikonfirmasi sebagai fondasi yang diwarisi Fase 2. Pola deviasi berulang ditemukan (tipe kolom meleset dari `Metadata.md`, 1 business rule dihapus total karena keterbatasan skema). Gap terbuka: kanal notifikasi eksternal (M1.5).

## 2026-08-10 — Eksplorasi Layer 2: Orchestrator + Extraction
Did: Baca `report.md` Milestone 2.0-2.1 + `docs/05-orchestrator/konvensi-job-dependency.md` penuh.
Result: worked. M2.0 membuktikan mekanisme `workflow_run` chaining nyata (run ID GitHub Actions asli) dan memprediksi gap "tidak ada sensor native" yang terbukti benar di M5.4. M2.1 Partially Completed — insiden kehilangan data nyata di 11 tabel saat percobaan partitioning BigQuery Sandbox (dipulihkan sebelum verifikasi akhir), cursor tracking cuma tangkap INSERT bukan UPDATE.

## 2026-08-10 — Eksplorasi Layer 3: Staging + Mart Cleaned + Reverse ETL
Did: Baca `report.md` Milestone 2.2-2.4.
Result: worked. M2.3 Partially Completed — BigQuery Sandbox memblokir DML total (bukan cuma partitioning), `mart_cleaned` full refresh permanen sampai billing aktif. Gap "renewal expiration belum terjadwal untuk mart_cleaned" yang dicatat di M2.3 dicross-check dan dikonfirmasi **sudah ditutup** oleh M2.4 (`transform-mart-cleaned.yml`) — bukti pentingnya cross-check ke milestone berikutnya, bukan percaya laporan satu titik waktu saja. M2.4 membuktikan zero-downtime swap empiris (274 query konkuren, 0 error).

## 2026-08-10 — Eksplorasi Layer 4: Akses Data Scientist + Kredensial
Did: Baca `report.md` Milestone 2.5-2.6 + `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` penuh (registry 22 kredensial project-wide saat itu).
Result: worked. Kontribusi kecil untuk peta 10 titik M6.1 (murni RBAC Lapis 2, bukan soal proses pipeline) — dicatat sebagai konteks pendukung, bukan sumber sinyal baru.

## 2026-08-10 — Eksplorasi Layer 5: Mart Aggregated + Feedback Loop ML + Reverse ETL
Did: Baca `report.md` Milestone 5.1-5.7 + `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` penuh. Verifikasi live tambahan: `grep renew_expiration` ke seluruh `.github/workflows/*.yml` untuk konfirmasi `mart_aggregated`/`mart_aggregated_staging` benar terjadwal (baris 114 `transform-mart-aggregated.yml`) meski tidak disebut eksplisit di deliverables `report.md` M5.4.
Result: worked. Layer paling kaya temuan: M5.4 (sensor `ml_output`, fault-injection nyata membuktikan isolasi kegagalan), M5.5 (76/77 tabel tersinkron, ML table sengaja dikecualikan), M5.7 (bug sistemik ditemukan — swap RENAME-based crash-turned-warning karena `analyst_views` terikat OID, menghasilkan WARNING berulang "expected" di hampir tiap run terjadwal berikutnya). M5.2's mandat "property_id wajib di semua tabel" dikonfirmasi dilanggar `dim_employee` selama 2 milestone tanpa terdeteksi gate DQ — kelas gap yang secara struktural tidak bisa ditangkap dbt test (kolom hilang, bukan nilai salah).

## 2026-08-10 — Eksplorasi Layer 6: Serving Data Analyst
Did: Baca `report.md` Milestone 3.2-3.6 (3.1 sudah dibaca lengkap di sesi sebelumnya sebagai template breakdown).
Result: worked. Kontribusi kecil untuk peta 10 titik M6.1 (murni layer konsumsi, sama seperti titik 11 out-of-scope) — tapi kaya temuan untuk M6.6 nanti (cache-cold anomaly pasca-reindex, selektivitas filter > ukuran tabel untuk keputusan planner, admin bukan superuser jadi GRANT bisa silent no-op).

## 2026-08-10 — Eksplorasi Layer 7: Serving AI Chatbot
Did: Baca `report.md` Milestone 4.1-4.6 + bagian "Cara Query untuk M6.5" di `docs/09-serving-ai-chatbot/audit-log-chatbot.md`.
Result: worked. Layer paling relevan untuk Milestone 6.5 — 2 query contoh sudah disiapkan M4.5 untuk M6.5 langsung dipakai. Temuan penting: `chatbot_query_log` tidak punya kolom latency (perlu join `pg_stat_statements` terpisah untuk M6.5), dan FastAPI `BackgroundTasks` sempat diam-diam terbuang di jalur `raise` exception (jalur ditolak awalnya tidak tercatat, diperbaiki M4.5).

## 2026-08-10 — Sintesis peta 10 titik + diskusi 2 temuan risiko dengan user
Did: Menyusun tabel peta 10 titik (skema kolom Titik/Tahap/Sumber Sinyal/Gap/Dependency/Prioritas) dari seluruh 7 layer, disajikan ke user di chat. User bertanya apakah 2 temuan (titik 1→2 tidak digate; titik 3/7 DQ gate tidak queryable) adalah masalah, lalu apakah mengancam kesuksesan seluruh Milestone 6.x, lalu milestone mana (6.2 dst) yang bertanggung jawab menutupnya.
Result: worked. Disepakati: temuan 1 = risiko berdiri sendiri, tidak dimiliki milestone monitoring manapun untuk diperbaiki (perlu kewenangan terpisah mengedit workflow pipeline), M6.2/6.7 cuma bisa mendeteksinya. Temuan 2 = prasyarat langsung Milestone 6.3 (Output #1-nya literal), berisiko menjalar ke M6.7 sebagai titik buta kalau under-scoped. Keduanya tidak mengancam kesuksesan 6.x secara keseluruhan (preseden project: gap serupa selalu diserap sebagai "Partially Completed" atau "koreksi ditemukan & diperbaiki", tidak pernah gagal total), tapi layak dicatat eksplisit supaya M6.3 tidak under-scope breakdown-nya sendiri.

## 2026-08-10 — Checkpoint 1: decisions.md
Did: Tulis `milestones/6.1-inventarisasi-titik-pengamatan/decisions.md` — kontrak, ringkasan 7 layer, 2 temuan risiko, 7 keputusan teknis (segmentasi eksplorasi, resolusi diskrepansi 10-vs-11, 2 temuan ke keputusan-tertunda, report.md ditunda, lokasi dokumen folder vs file tunggal, skema kolom tabel, klasifikasi prioritas 3 level).
Result: worked. Commit `246a9a6`.

## 2026-08-10 — Checkpoint 2: docs/keputusan-tertunda.md
Did: Append 2 entri baru ke `docs/keputusan-tertunda.md` mengikuti format standar file (What was deferred/Why deferred/Revisit when/Status) — entri "Dependency gate ekstraksi→transformasi mart_cleaned belum ditegakkan" dan "Hasil data quality gate `mart_cleaned`/`mart_aggregated` tidak tercatat di manapun yang queryable" (dengan penekanan eksplisit "wajib direvisit di awal breakdown Milestone 6.3" sesuai instruksi user).
Result: worked. Commit `7b33201`.

## 2026-08-10 — Checkpoint 3: docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md
Did: Tulis dokumen peta utama — header metadata, catatan diskrepansi 10-vs-11 + ringkasan 2 temuan risiko, tabel 10 titik lengkap dengan evidence per sel, klasifikasi prioritas ringkasan, titik 11 out-of-scope (termasuk gap `chatbot_query_log` tanpa latency dan Data Analyst API tanpa audit log), cross-check Kriteria Keberhasilan M6.1.
Result: worked. Commit `7b17973`. Folder baru `docs/10-monitoring-warehouse-serving/` dibuat mengikuti preseden `07`/`08`/`09` (bukan file tunggal seperti awalnya diketik user — dikoreksi dengan alasan eksplisit di `decisions.md` Keputusan #5, dikomunikasikan ke user).

## 2026-08-10 — Checkpoint 4: logs.md ini + status milestone
Did: Tulis `logs.md` ini (jurnal retroaktif, sesi kerja tunggal panjang). `report.md` **belum ditulis** sesuai Keputusan #4 `decisions.md` — menunggu user membaca `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` dan mengonfirmasi akurat sebelum milestone dinyatakan Completed.
Result: in progress — menunggu review user.
