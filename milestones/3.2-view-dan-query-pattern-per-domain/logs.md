# Milestone 3.2: View dan Query Pattern per Domain — Logs

## 2026-08-09 — Mulai kerja

- Plan disetujui via Plan Mode. `decisions.md` ditulis, mengunci 1 keputusan via AskUserQuestion (schema `analyst_views`) + 6 keputusan teknis (cakupan view, dimension resolved ke nama, deployment plain SQL, koneksi admin, SLA threshold, struktur file per domain).
- Folder dibuat: `milestones/3.2-view-dan-query-pattern-per-domain/`, `scripts/data_analyst_views/`.
- Dikonfirmasi `SERVING_DB_URL` tersedia di `.env`.
- Mulai Task 1 (Fase 0 — setup infrastruktur view).

## 2026-08-09 — Checkpoint 1

- `scripts/data_analyst_views/{connections.py,schema.sql,apply_views.py}` dibuat, meniru pola `scripts/monitoring/db.py`+`apply_schema.py` (runner psycopg2, autocommit=False, commit/rollback eksplisit) dan `get_serving_connection` dari `scripts/reverse_etl/connections.py`.
- `apply_views.py schema.sql` dijalankan sukses terhadap `SERVING_DB_URL` sungguhan.
- Verifikasi: `information_schema.schemata` mengonfirmasi `analyst_views` ada berdampingan dengan `mart_aggregated`/`mart_cleaned`.

## 2026-08-09 — Checkpoint 2

- `views_revenue.sql` (8 view: room_type_daily, channel_daily, los_daily, property_daily, gop_impact_monthly, pricing_deviation, loyalty_daily, nationality_daily) dan `views_fnb.sql` (8 view: outlet_daily, category_daily, hourly, customer_type_daily, menu_item_daily, waste_daily, inventory_status, ingredient_price_daily) ditulis dan di-apply ke `analyst_views` sungguhan.
- Kolom fact/dim diambil langsung dari `information_schema.columns` live (bukan asumsi dari dokumen desain) untuk memastikan akurasi.
- Verifikasi KK1: (a) `v_revenue_room_type_daily` — row count identik fact vs view (19.746), sampel `occupancy_rate`/`adr`/`revpar` cocok persis, dimensi ter-resolve benar (P01 → "Nirwana Beach Resort Bali", room_type_id 1 → "Deluxe"). (b) `v_fnb_menu_item_daily` — row count identik (289.938), sampel `food_cost_ratio_actual`/`food_cost_ratio_target` cocok persis, outlet ter-resolve ke property lewat `dim_outlet` (OUT001 → P01/"Sunset Restaurant").
