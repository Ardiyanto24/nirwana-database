"""
Milestone 6.7 - Checkpoint 4: alert rule + notification policy grouping untuk
KK2 (root-cause grouping). BERBEDA dari create_alerts.py (M1.5, Fase 1) yang
bikin 1 rule per sumber sinyal -- di sini SENGAJA 1 rule saja, bersumber
monitoring.alerts_with_root_cause (Checkpoint 2), supaya banyak alert_type
Fase 2 tidak menghasilkan banyak rule terpisah (itu sendiri akan membanjiri,
bertentangan KK2). Query mengembalikan 1 baris per root_titik_id (bukan 1
angka tunggal) -- pola "multi-dimensional alert" Grafana: tiap baris tabel
jadi 1 alert instance terpisah, kolom non-value (root_titik_id) otomatis
jadi label. Label root_titik_id itulah yang dipakai notification policy
untuk mengelompokkan (Task 15) -- sehingga N alert dengan root_titik_id sama
dibundel jadi 1 notifikasi, bukan N terpisah.

ruleGroup baru ("warehouse-serving-monitoring"), folder Grafana SAMA dengan
Fase 1 ("Nirwana Monitoring", M1.5) -- reuse _get_or_create_folder dari
create_alerts.py supaya tidak duplikat folder. 2 rule Fase 1 TIDAK disentuh.
"""
from create_alerts import _get_or_create_folder
from grafana_client import api_request

RULE_GROUP = "warehouse-serving-monitoring"
ROUTE_LABEL_KEY = "source"
ROUTE_LABEL_VALUE = "nirwana-warehouse-serving"


def _root_cause_rule_body(uid, folder_uid, ds_uid):
    return {
        "uid": uid,
        "title": "Alert Aktif per Titik Akar Masalah (Fase 2, M6.7)",
        "ruleGroup": RULE_GROUP,
        "folderUID": folder_uid,
        "condition": "A",
        "data": [
            {
                "refId": "A",
                "queryType": "",
                "relativeTimeRange": {"from": 86400, "to": 0},
                "datasourceUid": ds_uid,
                "model": {
                    "rawSql": (
                        "SELECT root_titik_id::text AS root_titik_id, "
                        "COUNT(*)::float AS value "
                        "FROM monitoring.alerts_with_root_cause "
                        "WHERE is_simulated = false "
                        "GROUP BY root_titik_id;"
                    ),
                    "format": "table",
                    "refId": "A",
                },
            },
        ],
        "noDataState": "OK",
        "execErrState": "Error",
        "for": "0s",
        "labels": {ROUTE_LABEL_KEY: ROUTE_LABEL_VALUE},
        "annotations": {
            "summary": (
                "Titik {{ $labels.root_titik_id }} adalah akar masalah -- "
                "lihat panel 'Alert Aktif per Akar Masalah' di dashboard "
                "Warehouse & Serving Monitoring untuk daftar lengkap event "
                "yang tergolong di bawahnya."
            ),
        },
    }


def upsert_rule(folder_uid, ds_uid, uid):
    status, existing = api_request("GET", f"/api/v1/provisioning/alert-rules/{uid}")
    body = _root_cause_rule_body(uid, folder_uid, ds_uid)
    if status == 200:
        status, result = api_request("PUT", f"/api/v1/provisioning/alert-rules/{uid}", body)
    else:
        status, result = api_request("POST", "/api/v1/provisioning/alert-rules", body)
    return status, result


def upsert_notification_policy():
    """Tambah 1 nested route (group_by root_titik_id) untuk rule di atas,
    tanpa mengubah route Fase 1 yang sudah ada."""
    status, tree = api_request("GET", "/api/v1/provisioning/policies")
    if status != 200:
        raise RuntimeError(f"Gagal ambil notification policy tree: {tree}")

    routes = tree.get("routes") or []
    matcher = [ROUTE_LABEL_KEY, "=", ROUTE_LABEL_VALUE]
    new_route = {
        "receiver": tree.get("receiver"),
        "object_matchers": [matcher],
        "group_by": ["root_titik_id"],
        "routes": [],
    }
    routes = [r for r in routes if r.get("object_matchers") != [matcher]]
    routes.append(new_route)
    tree["routes"] = routes

    status, result = api_request("PUT", "/api/v1/provisioning/policies", tree)
    return status, result


def main():
    from create_datasource import upsert_datasource

    status, ds_result = upsert_datasource()
    ds_uid = ds_result["datasource"]["uid"] if "datasource" in ds_result else ds_result["uid"]

    folder_uid = _get_or_create_folder()

    status, result = upsert_rule(folder_uid, ds_uid, "nirwana-alert-m67-root-cause")
    print(f"[{status}] Alert Aktif per Titik Akar Masalah (Fase 2)")
    if status not in (200, 201):
        print("   ", result)

    status, result = upsert_notification_policy()
    print(f"[{status}] Notification policy group_by root_titik_id")
    if status not in (200, 201):
        print("   ", result)


if __name__ == "__main__":
    main()
