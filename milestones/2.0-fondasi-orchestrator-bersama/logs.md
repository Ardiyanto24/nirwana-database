# Milestone 2.0 -- Execution Log

## 2026-08-08 (start)
Did: Breakdown Milestone 2.0 lewat `planning-and-task-breakdown`, menemukan 4 keputusan scope/pendekatan yang harus diambil dulu sebelum `decisions.md` bisa ditulis (scope repo, tool orchestrator, provisioning GCP/BigQuery, cara verifikasi kriteria "pemilik lain"). Dikonfirmasi user via `AskUserQuestion` (dua putaran -- putaran kedua user minta penjelasan detail 3 opsi orchestrator sebelum memutuskan). Hasil: dikerjakan di repo ini (bukan repo baru), orchestrator = GitHub Actions extended (Opsi A, alasan biaya, didesain dekat standar industri, catatan revisit ke self-hosted), provisioning GCP/BigQuery ternyata di luar lingkup M2.0 (dikoreksi ke Milestone 2.1 setelah re-baca source doc), kriteria "pemilik lain" divalidasi lewat simulasi job ketiga.
Result: worked. `decisions.md` ditulis lengkap dengan Task Breakdown + 4 Technical Decisions.

## 2026-08-08 -- Update dokumen scope + konvensi (Task 1, 2, 5)
Did: Update `CLAUDE.md` (Project Scope, Documentation Map, Fase 2 status baru) untuk mencerminkan Fase 2 kini dikerjakan di repo ini. Tambah entri baru di `docs/keputusan-tertunda.md` ("Orchestrator sungguhan untuk Fase 2") mencatat keputusan GitHub Actions-karena-biaya dan rencana revisit ke self-hosted. Tulis `docs/05-orchestrator/konvensi-job-dependency.md` -- konvensi penamaan file/job workflow, dua mekanisme dependency (`needs` dalam satu file vs `workflow_run` lintas file), cara pemilik pekerjaan lain menambah job tanpa mengedit file existing, dan batasan eksplisit (tidak ada sensor native, tidak ada UI dependency graph) sebagai warisan keputusan Opsi A.
Result: worked. (Catatan: `CLAUDE.md` di-gitignore di repo ini -- perubahan tetap tersimpan lokal, tidak akan muncul di `git status`/histori commit, sesuai konvensi repo yang sudah ada sebelum milestone ini.)

## 2026-08-08 -- Workflow demo (Task 3, 4)
Did: Buat 3 file workflow GitHub Actions mengikuti konvensi yang baru ditulis: `orchestrator-demo-extract.yml` (scheduled + `workflow_dispatch`, self-contained/tanpa koneksi GCP -- sengaja, karena provisioning GCP bukan lingkup M2.0), `orchestrator-demo-transform.yml` (trigger via `workflow_run` menunggu "Orchestrator Demo - Extract" selesai, cek `conclusion == 'success'` eksplisit sebelum lanjut), `orchestrator-demo-monitoring.yml` (job KETIGA, mensimulasikan pemilik pekerjaan lain -- ditambahkan murni dengan file baru + `workflow_run` ke workflow transform, tanpa menyentuh 2 file sebelumnya sama sekali, untuk membuktikan Kriteria Keberhasilan #2).
Result: ditulis, belum diverifikasi jalan sungguhan -- workflow_dispatch/workflow_run GitHub Actions hanya aktif untuk workflow file yang ada di branch default, jadi perlu commit+push dulu sebelum bisa diuji lewat run history.

## 2026-08-08 -- Commit, push, verifikasi run history (Task 6)
Did: Commit seluruh perubahan (`5530a4a`) & push ke `main` (workflow_dispatch/workflow_run GitHub Actions hanya aktif untuk file di branch default). Trigger `orchestrator-demo-extract.yml` manual via `gh workflow run`, lalu tunggu & cek `gh run list` untuk ketiga workflow.
Result: worked, urutan run membuktikan seluruh rantai dependency:
- `Orchestrator Demo - Extract` (run 31226809039) -- trigger manual, sukses, mulai 2026-08-07T23:20:12Z.
- `Orchestrator Demo - Transform` (run 31226817633) -- ter-trigger OTOMATIS via `workflow_run` 9 detik setelah extract sukses (23:20:21Z), tanpa aksi manual tambahan. Sukses.
- `Orchestrator Demo - Monitoring (Simulated Other Owner)` (run 31226825790) -- ter-trigger OTOMATIS via `workflow_run` 9 detik setelah transform sukses (23:20:30Z). Sukses. File ini ditambahkan sebagai commit yang sama tapi TANPA mengubah 2 file workflow sebelumnya sama sekali -- membuktikan Kriteria Keberhasilan #2 (pemilik lain bisa menambah job tanpa instance/setup terpisah, dan tanpa mengedit job yang sudah ada).

## Status akhir: Completed
Seluruh 6 task selesai & terverifikasi lewat run history sungguhan (bukan asumsi). Lihat `report.md` untuk pengecekan formal terhadap Kriteria Keberhasilan sumber.
