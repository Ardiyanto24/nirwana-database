"""Milestone 1.5 - Task 3: buat/perbarui datasource Postgres (Supabase) di Grafana."""
from grafana_client import api_request, get_config, parse_supabase_url

DATASOURCE_NAME = "Supabase Postgres (Nirwana)"


def upsert_datasource():
    cfg = get_config()
    conn = parse_supabase_url(cfg["supabase_db_url"])

    payload = {
        "name": DATASOURCE_NAME,
        "type": "grafana-postgresql-datasource",
        "access": "proxy",
        "url": f"{conn['host']}:{conn['port']}",
        "database": conn["database"],
        "user": conn["user"],
        "secureJsonData": {"password": conn["password"]},
        "jsonData": {
            "sslmode": "require",
            "postgresVersion": 1500,
            "timescaledb": False,
        },
        "isDefault": True,
    }

    status, existing = api_request("GET", "/api/datasources/name/" + DATASOURCE_NAME.replace(" ", "%20"))
    if status == 200:
        ds_id = existing["id"]
        status, result = api_request("PUT", f"/api/datasources/{ds_id}", payload)
    else:
        status, result = api_request("POST", "/api/datasources", payload)

    return status, result


if __name__ == "__main__":
    status, result = upsert_datasource()
    print(f"Status: {status}")
    print(result)
