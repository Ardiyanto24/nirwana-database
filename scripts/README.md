# Katalog Implementasi Operasional

Folder `scripts/` berisi implementasi yang menjalankan, menguji, atau mengamati Nirwana Data Platform. Halaman ini adalah indeks Level 3; setiap folder tetap mempertahankan tanggung jawabnya sendiri agar logic lintas concern tidak tercampur.

## Sebelum menjalankan script

- Gunakan [.env.example](../.env.example) sebagai daftar variabel lingkungan. Jangan menyimpan connection string atau key pada source code.
- Baca [referensi teknis](../docs/README.md) dan [laporan milestone](../milestones/README.md) yang terkait sebelum mengubah script.
- Untuk perubahan pipeline, periksa [konvensi orchestrator](../docs/05-orchestrator/konvensi-job-dependency.md) serta workflow pemanggilnya.
- Setiap script yang menyentuh data atau infrastruktur harus menggunakan kredensial scoped yang sudah ada, bukan memperluas kredensial admin.

## Pipeline data

| Folder | Tanggung jawab | Artefak penting |
| --- | --- | --- |
| [extract/](extract/) | extraction 23 tabel PostgreSQL ke BigQuery `raw_production` | `extract.py`, `tables_config.py`, `renew_expiration.py` |
| [mart_cleaned/](mart_cleaned/) | promotion `mart_cleaned` dengan build → test → swap | `promote.py` |
| [mart_aggregated/](mart_aggregated/) | promotion `mart_aggregated` dengan gate terpisah | `promote.py` |
| [reverse_etl/](reverse_etl/) | sinkronisasi `mart_cleaned` ke PostgreSQL serving | `sync.py`, `test_no_downtime_swap.py` |
| [reverse_etl_mart_aggregated/](reverse_etl_mart_aggregated/) | sinkronisasi `mart_aggregated` ke PostgreSQL serving | `sync.py`, `reindex_analyze.py`, `test_no_downtime_swap.py` |
| [ml_scoring/](ml_scoring/) | mock scoring dan sensor `ml_output` | `mock_score.py`, `wait_for_ml_output.py` |

Transformasi dbt sendiri berada di [warehouse/](../warehouse/), bukan `scripts/`. Script promotion mengorkestrasi gate transformasi tersebut; ia bukan tempat mendefinisikan business logic model.

## Serving dan consumer access

| Folder | Tanggung jawab | Boundary utama |
| --- | --- | --- |
| [data_scientist_access/](data_scientist_access/) | contoh koneksi dan verifikasi reader BigQuery | hanya `mart_cleaned` |
| [data_analyst_views/](data_analyst_views/) | DDL dan deploy `analyst_views` | views per domain |
| [data_analyst_api/](data_analyst_api/) | API internal query Data Analyst | whitelist dan parameterized SQL |
| [data_analyst_credentials/](data_analyst_credentials/) | setup dan verifier role analyst | domain-scoped PostgreSQL roles |
| [analyst_bi_access/](analyst_bi_access/) | contoh akses BigQuery untuk BI | dataset-scoped reader |
| [chatbot_views/](chatbot_views/) | DDL `chatbot_views` | split domain dan granularitas view |
| [chatbot_credentials/](chatbot_credentials/) | setup dan verifier reader Chatbot | 10 reader per domain |
| [chatbot_api/](chatbot_api/) | authorization dan query interface Chatbot | `role_permissions` + credential domain |
| [chatbot_audit/](chatbot_audit/) | koneksi writer audit Chatbot | INSERT-only ke audit log |
| [chatbot_rbac_test/](chatbot_rbac_test/) | matriks verifikasi akses lintas persona | ground truth `role_permissions` |

## Monitoring dan observability

| Folder | Tanggung jawab | Sinyal utama |
| --- | --- | --- |
| [monitoring/](monitoring/) | snapshot volume/freshness dan alert Fase 1 | baseline operasi produksi |
| [dq/](dq/) | Great Expectations dan quality check produksi | rule tetap dan anomaly data |
| [schema_drift/](schema_drift/) | snapshot/diff schema serta acknowledgement | perubahan kolom sumber |
| [monitoring_warehouse/](monitoring_warehouse/) | run log, DQ artifact, volume, ML health, dan root cause | warehouse pipeline |
| [serving_layer_monitor/](serving_layer_monitor/) | storage, vacuum, orphan table, dan durasi swap | kesehatan PostgreSQL serving |
| [chatbot_perf_monitor/](chatbot_perf_monitor/) | latency, query plan, dan connection pool | performa interaktif Chatbot |
| [grafana/](grafana/) | datasource, dashboard, dan alert provisioning | visualisasi dan alert grouping |

## Utilitas dan fondasi bersama

| Folder | Peran |
| --- | --- |
| [bigquery_common/](bigquery_common/) | helper serta verifier isolasi BigQuery yang dipakai lintas credential |
| [api_reader/](api_reader/) | reader yang mendukung API monitoring read-only |
| [profiling/](profiling/) | profiling sumber data sebelum cleaning/modeling |

## Peta verifikasi

| Risiko | Script atau artefak verifikasi |
| --- | --- |
| data buruk menggantikan mart live | `mart_cleaned/promote.py`, `mart_aggregated/promote.py`, dbt tests |
| salinan serving tidak lengkap | `reverse_etl/*/sync.py` dan parity log |
| swap mengganggu pembaca | `reverse_etl/*/test_no_downtime_swap.py` |
| credential membuka data di luar scope | verifier pada folder credential dan `bigquery_common/` |
| RBAC Chatbot berbeda dari ground truth | `chatbot_rbac_test/` |
| anomaly atau health signal tidak terdeteksi | `simulate_test.py` pada folder monitoring terkait |

## Hubungan dengan dokumentasi

- [docs/README.md](../docs/README.md) — kontrak, requirement, dan sumber desain.
- [milestones/README.md](../milestones/README.md) — keputusan serta bukti hasil implementasi.
- [warehouse/README.md](../warehouse/README.md) — setup dbt dan data yang sengaja tidak dibersihkan.
- [.github/workflows/README.md](../.github/workflows/README.md) — jadwal dan dependency yang menjalankan script ini.
