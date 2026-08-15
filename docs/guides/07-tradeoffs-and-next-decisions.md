# 07 — Trade-off dan Keputusan Lanjutan

## Ringkasan

Sistem yang dapat dipelajari harus menjelaskan bukan hanya apa yang dibangun, tetapi juga batas keputusan yang diambil. Di project ini, constraint biaya, keterbatasan platform, dan pemisahan ownership memengaruhi implementasi nyata. Status terbuka tidak berarti detail terlupakan; ia berarti perubahan tersebut membutuhkan keputusan atau otorisasi baru.

## Constraint yang membentuk implementasi saat ini

### BigQuery Sandbox

Warehouse berjalan tanpa billing account. Konsekuensinya, BigQuery Sandbox memblokir DML dan memberi masa berlaku 60 hari untuk tabel, view, maupun partition. Implementasi menggunakan materialisasi full refresh berbasis DDL dan workflow memperbarui expiration agar data tidak kedaluwarsa selama workflow tetap berjalan.

Ini adalah mitigasi, bukan pengganti solusi permanen. Ketika billing tersedia, langkah migrasi yang terdokumentasi mencakup penghapusan expiration default, pembaruan tabel existing, dan peninjauan kembali model incremental/partitioning.

### GitHub Actions sebagai orchestrator yang diperluas

GitHub Actions dipilih karena biaya dan kesederhanaan operasional. `workflow_run`, `needs`, dan polling manual cukup untuk jalur yang ada, tetapi tidak menyediakan sensor native, retry granular, maupun graph dependency visual seperti Airflow, Dagster, atau Prefect.

Pilihan ini tidak dilabeli sebagai solusi universal. Ia cocok untuk constraint saat ini dan perlu dievaluasi ulang saat dependency serta kegagalan per-task menjadi lebih kompleks.

### Feedback loop ML masih provisional

`ml_output` dan mock scorer membuktikan contract, urutan orkestrasi, dan observability yang diperlukan untuk integrasi ML. Namun model, cadence retraining, threshold drift, dan skema output final belum ditentukan bersama pemilik sistem ML. Fact ML juga sengaja belum disinkronkan ke serving PostgreSQL.

Pembaca tidak seharusnya menyimpulkan bahwa platform telah memiliki model prediksi produksi hanya karena ada jalur scoring.

## Gap yang sudah diketahui

| Area | Keadaan saat ini | Keputusan/aksi lanjutan |
| --- | --- | --- |
| Source extraction | koneksi langsung ke primary PostgreSQL | tinjau read replica atau CDC saat beban sumber menjadi nyata |
| Extraction → transform | dependency masih memiliki gap wiring; detector dapat memberi sinyal turunan | tambahkan dependency gate setelah ada otorisasi untuk mengubah workflow terkait |
| Reverse ETL dan view | view perlu reapply setelah RENAME swap; orphan dapat terdeteksi | otomasi reapply view, cleanup, dan penanganan nama `__old` perlu diselesaikan bersama pemilik pipeline/view |
| BI tool | credential dan query programatik terbukti, GUI BI belum diverifikasi | lakukan koneksi nyata ke tool BI tanpa mengubah scope credential |
| Alert delivery | alert sudah terlihat dan dikelompokkan di Grafana | pilih serta konfigurasi kanal notifikasi eksternal bila dibutuhkan |
| ML monitoring | staleness informational dan drift availability canary | sepakati contract, cadence retrain, serta threshold bersama tim ML |

## Cara mengambil keputusan lanjutan

Perubahan pada aset bersama—terutama `mart_aggregated`, workflow lintas milestone, credential, atau serving view—tidak dikerjakan sebagai edit lokal yang terisolasi. Project menggunakan tiga mekanisme:

1. **Dokumentasikan kebutuhan dan dampaknya.** Perubahan agregasi masuk melalui pengajuan perubahan cakupan `mart_aggregated`.
2. **Tentukan owner dan boundary.** Consumer layer tidak mengubah model mart bersama secara langsung.
3. **Verifikasi setelah perubahan.** Test, promotion, parity, dan isolasi akses diperiksa lagi pada jalur yang terdampak.

Pola ini membuat scope growth terlihat dan dapat ditinjau, terutama ketika satu perubahan kecil—misalnya kolom baru pada dimension—dapat memengaruhi dbt model, reverse ETL, view, index, role, dan API.

## Prinsip untuk melanjutkan sistem

- Jangan mengganti full refresh dengan incremental hanya karena tampak lebih modern; pastikan constraint DML, partitioning, dan recovery telah berubah.
- Jangan memperluas akses consumer dengan credential admin; tambahkan view dan role scoped sesuai pola yang sudah ada.
- Jangan menutup alert dengan filter visual jika akar masalahnya ada di collector atau workflow; catat mitigasi defensif dan perbaiki di owner yang tepat.
- Jangan menjadikan mock ML sebagai dasar keputusan bisnis tanpa contract dan validasi dari pemilik model.
- Jangan menganggap gap dokumentasi sebagai defect implementasi sebelum memeriksa `docs/keputusan-tertunda.md` dan laporan milestone terkait.

## Referensi lanjutan

- [Backlog keputusan tertunda](../keputusan-tertunda.md)
- [Mekanisme pengajuan perubahan `mart_aggregated`](../07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md)
- [Backlog perubahan cakupan `mart_aggregated`](../07-mart-aggregated/pengajuan-perubahan-cakupan.md)
- [Konvensi dependency orchestrator](../05-orchestrator/konvensi-job-dependency.md)
- [Laporan serving Data Analyst](../../milestones/3.6-akses-bigquery-bi-tool/report.md)
- [Laporan feedback loop ML](../../milestones/5.4-integrasi-feedback-loop-ml/report.md)
- [Laporan reverse ETL serving health](../../milestones/6.6-monitoring-reverse-etl-serving-layer/report.md)
- [Laporan observability terpadu](../../milestones/6.7-dashboard-alerting-terpadu/report.md)
