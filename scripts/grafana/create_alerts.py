"""
Milestone 1.5 - Task 5: alert rules Grafana, baca dari monitoring.alerts &
monitoring.schema_drift_events (bukan hitung ulang logic anomali -- lihat decisions.md).

Kanal notifikasi eksternal SENGAJA belum dikonfigurasi (keputusan tertunda,
docs/keputusan-tertunda.md) -- rule ini akan membuat status alert terlihat di
Grafana (Alerting > Alert rules), tapi tidak push ke Discord/Slack/Email mana pun.
"""
from grafana_client import api_request

FOLDER_TITLE = "Nirwana Monitoring"
RULE_GROUP = "data-production-monitoring"


def _get_or_create_folder():
    status, folders = api_request("GET", "/api/folders")
    for f in folders or []:
        if f["title"] == FOLDER_TITLE:
            return f["uid"]
    status, result = api_request("POST", "/api/folders", {"title": FOLDER_TITLE})
    if status not in (200, 201):
        raise RuntimeError(f"Gagal buat folder: {result}")
    return result["uid"]


def _alert_rule_body(uid, title, folder_uid, ds_uid, sql, for_duration="0s"):
    return {
        "uid": uid,
        "title": title,
        "ruleGroup": RULE_GROUP,
        "folderUID": folder_uid,
        "condition": "B",
        "data": [
            {
                "refId": "A",
                "queryType": "",
                "relativeTimeRange": {"from": 86400, "to": 0},
                "datasourceUid": ds_uid,
                "model": {"rawSql": sql, "format": "table", "refId": "A"},
            },
            {
                "refId": "B",
                "queryType": "",
                "relativeTimeRange": {"from": 0, "to": 0},
                "datasourceUid": "__expr__",
                "model": {
                    "type": "threshold",
                    "expression": "A",
                    "conditions": [{
                        "evaluator": {"type": "gt", "params": [0]},
                        "operator": {"type": "and"},
                        "query": {"params": ["A"]},
                        "reducer": {"type": "last"},
                        "type": "query",
                    }],
                    "refId": "B",
                },
            },
        ],
        "noDataState": "OK",
        "execErrState": "Error",
        "for": for_duration,
        "labels": {"source": "nirwana-monitoring"},
        "annotations": {
            "summary": f"{title}: ada baris baru yang perlu direview",
        },
    }


def upsert_rule(folder_uid, ds_uid, uid, title, sql):
    status, existing = api_request("GET", f"/api/v1/provisioning/alert-rules/{uid}")
    body = _alert_rule_body(uid, title, folder_uid, ds_uid, sql)
    if status == 200:
        status, result = api_request("PUT", f"/api/v1/provisioning/alert-rules/{uid}", body)
    else:
        status, result = api_request("POST", "/api/v1/provisioning/alert-rules", body)
    return status, result


def main():
    from create_datasource import upsert_datasource
    status, ds_result = upsert_datasource()
    ds_uid = ds_result["datasource"]["uid"] if "datasource" in ds_result else ds_result["uid"]

    folder_uid = _get_or_create_folder()

    rules = [
        (
            "nirwana-alert-m12-m13",
            "Alert Volume/Freshness/Kualitas Data (M1.2 + M1.3)",
            """SELECT COUNT(*) AS value FROM monitoring.alerts
               WHERE is_simulated = false AND triggered_at > now() - interval '1 day';""",
        ),
        (
            "nirwana-alert-m14-schema-drift",
            "Schema Drift Menunggu Review (M1.4)",
            """SELECT COUNT(*) AS value FROM monitoring.schema_drift_events
               WHERE status = 'pending' AND schema_name != '_simulation';""",
        ),
    ]

    for uid, title, sql in rules:
        status, result = upsert_rule(folder_uid, ds_uid, uid, title, sql)
        print(f"[{status}] {title}")
        if status not in (200, 201):
            print("   ", result)


if __name__ == "__main__":
    main()
