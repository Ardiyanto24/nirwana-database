"""
Milestone 5.5 -- ⚠️ PROVISIONAL/CONTOH index, bukan desain index final.

Desain index sungguhan untuk pola akses Data Analyst adalah scope Milestone
3.3 (`docs/03-implementation-plans/04-serving-data-analyst.md`), BELUM
dibangun. Index di bawah ini SEMATA-MATA untuk membuktikan mekanisme
REINDEX/ANALYZE pasca-swap (decisions.md Keputusan #3) bekerja nyata --
kolom dipilih mengikuti contoh di `rancangan-arsitektur-data-platform-elt.md`
Bagian 9.3.2 (property/date untuk pola akses chatbot), bukan hasil analisis
query pattern sungguhan. Jangan dianggap sebagai desain index M3.3.
"""

EXAMPLE_INDEXES = [
    {
        "table": "fact_revenue_property_daily",
        "index_name": "idx_fact_revenue_property_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
]
