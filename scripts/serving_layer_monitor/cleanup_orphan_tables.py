"""
Milestone 6.6 -- Keputusan B: pembersihan SEKALI tabel orphan `__old` yang
sudah ada (73 tabel, 112.1MB, ditemukan saat riset milestone ini). BUKAN
solusi permanen/otomasi untuk siklus berikutnya -- itu tetap keputusan
terpisah, lihat docs/keputusan-tertunda.md entri M5.7 (Status tetap Open).

Prasyarat WAJIB dijalankan manual SEBELUM script ini (tidak dipanggil dari
sini -- reapply view adalah operasi terpisah milik M3.2/M4.2, bukan
tanggung jawab folder ini):
  python scripts/data_analyst_views/apply_views.py --all
  python scripts/chatbot_views/apply_views.py --all

Setelah itu, DROP TABLE langsung tiap `__old` yang masih ada -- TIDAK perlu
rerun sync.py penuh (dependency OID sudah lepas lewat CREATE OR REPLACE
VIEW di atas, drop langsung cukup, tidak perlu re-fetch data dari BigQuery
lagi).

Usage: python cleanup_orphan_tables.py [--dry-run]
"""
import argparse
import sys

from connections import get_serving_connection

SCHEMAS = ("mart_cleaned", "mart_aggregated")


def find_orphans(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT schemaname, relname FROM pg_stat_user_tables WHERE schemaname = ANY(%s) AND relname LIKE '%%__old' ORDER BY 1, 2",
        (list(SCHEMAS),),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="cuma list, tidak DROP apa pun")
    args = parser.parse_args()

    conn = get_serving_connection(readonly=False)
    conn.autocommit = True
    try:
        orphans = find_orphans(conn)
        print(f"Ditemukan {len(orphans)} tabel orphan.")
        if not orphans:
            return

        if args.dry_run:
            for schema, table in orphans:
                print(f"  [DRY-RUN] would DROP {schema}.{table}")
            return

        dropped, failed = [], []
        cur = conn.cursor()
        for schema, table in orphans:
            try:
                cur.execute(f'DROP TABLE {schema}."{table}"')
                dropped.append(f"{schema}.{table}")
                print(f"  dropped {schema}.{table}")
            except Exception as e:
                failed.append((f"{schema}.{table}", str(e)))
                print(f"  FAILED {schema}.{table}: {e}")
        cur.close()

        print(f"\n{len(dropped)}/{len(orphans)} tabel orphan berhasil di-DROP.")
        if failed:
            print(f"{len(failed)} GAGAL -- kemungkinan masih ada view yang belum di-reapply:")
            for name, err in failed:
                print(f"  {name}: {err}")
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
