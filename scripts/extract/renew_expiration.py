"""
Milestone 2.3 -- mitigation for BigQuery Sandbox mode's hard 60-day table/view
expiration (project has no billing account yet, see docs/keputusan-tertunda.md
"Aktivasi billing GCP..."). Extends every table/view's expirationTime to
~55 days from now, run as a step in scheduled workflows (extract-production.yml
and later the mart_cleaned refresh workflow) so expiration never actually hits
as long as the workflow keeps running on schedule.

NOT a permanent fix -- if the scheduled workflow stops running for more than
~55 days, everything still expires and Fase 2 needs a full rebuild from
Postgres. Revisit once billing is enabled (see decisions.md).

Usage: python scripts/extract/renew_expiration.py <dataset_name> [<dataset_name> ...]
"""
import datetime
import os
import sys

from google.cloud import bigquery

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "monitoring"))
from bq import get_client  # noqa: E402

RENEWAL_DAYS = 55


def main():
    datasets = sys.argv[1:]
    if not datasets:
        print("Usage: python renew_expiration.py <dataset_name> [<dataset_name> ...]")
        sys.exit(1)

    client, _ = get_client()
    new_expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=RENEWAL_DAYS)

    for dataset_id in datasets:
        tables = list(client.list_tables(f"{client.project}.{dataset_id}"))
        for table_ref in tables:
            table = client.get_table(table_ref)
            table.expires = new_expiration
            client.update_table(table, ["expires"])
            print(f"{dataset_id}.{table_ref.table_id}: expiration renewed to {new_expiration.isoformat()}")

    print(f"\n{sum(len(list(client.list_tables(f'{client.project}.{d}'))) for d in datasets)} tables/views renewed.")


if __name__ == "__main__":
    main()
