"""
Milestone 1.3 - Task 3 & 5: bangun expectation suite per tabel dari rules_config.py,
jalankan validasi, tulis hasil ke monitoring.dq_test_results.

Satu asset/batch-definition per tabel dibuat sekali (idempotent -- get-or-create),
suite dibangun ulang tiap run supaya selalu mencerminkan rules_config.py terkini
(bukan suite lama yang basi).
"""
import sys
import os
import datetime
import great_expectations as gx
import great_expectations.expectations as gxe

from ge_context import get_context
from rules_config import RULES

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402


def _get_or_create_batch_definition(ds, schema, table):
    asset_name = f"{schema}__{table}__asset"
    batch_def_name = f"{schema}__{table}__whole"
    try:
        asset = ds.add_table_asset(name=asset_name, table_name=table, schema_name=schema)
    except Exception:
        asset = ds.get_asset(asset_name)
    try:
        batch_def = asset.add_batch_definition_whole_table(batch_def_name)
    except Exception:
        batch_def = asset.get_batch_definition(batch_def_name)
    return batch_def


def build_suite(ctx, schema, table, config):
    suite_name = f"{schema}.{table}"
    # Bangun objek suite baru tiap run (bukan reuse suite lama dari store) supaya
    # tidak menumpuk expectation yang sudah dihapus dari rules_config.py.
    suite = gx.ExpectationSuite(name=suite_name)

    for col in config.get("not_null", []):
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))
    for col in config.get("unique", []):
        suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column=col))
    for col, values in config.get("accepted_values", {}).items():
        suite.add_expectation(gxe.ExpectColumnValuesToBeInSet(column=col, value_set=values))
    for rule_name, predicate in config.get("custom", []):
        # {batch} sudah tersubstitusi jadi "(SELECT ...) AS subselect" -- JANGAN tambah alias
        # sendiri (mis. "AS t"), itu bikin double-alias syntax error. Predikat yang perlu
        # merujuk balik ke baris batch (bukan ke tabel lain di subquery) pakai prefix
        # "subselect." -- lihat rules_config.py.
        suite.add_expectation(gxe.UnexpectedRowsExpectation(
            unexpected_rows_query=f"SELECT * FROM {{batch}} WHERE {predicate}",
            meta={"rule_name": rule_name},
        ))

    suite = ctx.suites.add_or_update(suite)
    return suite


def _describe_expectation(exp_config):
    etype = exp_config.type
    kwargs = exp_config.kwargs
    if etype == "unexpected_rows_expectation":
        return exp_config.meta.get("rule_name", "custom_rule") if exp_config.meta else "custom_rule"
    if "column" in kwargs:
        detail = kwargs["column"]
        if "value_set" in kwargs:
            detail += f" in {kwargs['value_set']}"
        return detail
    return str(kwargs)


def run_all(persist=True, run_date=None):
    run_date = run_date or datetime.date.today()
    ctx, ds = get_context()
    conn = get_connection(readonly=False) if persist else None
    cur = conn.cursor() if conn else None

    summary = []
    for (schema, table), config in RULES.items():
        batch_def = _get_or_create_batch_definition(ds, schema, table)
        suite = build_suite(ctx, schema, table, config)
        batch = batch_def.get_batch()
        result = batch.validate(suite)

        for r in result.results:
            etype = r.expectation_config.type
            detail = _describe_expectation(r.expectation_config)
            success = r.success
            unexpected_count = None
            unexpected_percent = None
            if r.result:
                # UnexpectedRowsExpectation melaporkan jumlah baris lewat "observed_value",
                # bukan "unexpected_count" (yang dipakai expectation berbasis kolom).
                unexpected_count = r.result.get("unexpected_count", r.result.get("observed_value"))
                unexpected_percent = r.result.get("unexpected_percent")

            if cur is not None:
                cur.execute(
                    """
                    INSERT INTO monitoring.dq_test_results
                        (schema_name, table_name, suite_name, expectation_type, expectation_detail,
                         success, unexpected_count, unexpected_percent, run_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (schema, table, suite.name, etype, detail, success,
                     unexpected_count, unexpected_percent, run_date),
                )
            summary.append((schema, table, etype, detail, success, unexpected_count))

    if conn:
        conn.commit()
        cur.close()
        conn.close()
    return summary


if __name__ == "__main__":
    results = run_all(persist=True)
    total = len(results)
    passed = sum(1 for r in results if r[4])
    print(f"=== DQ run selesai: {passed}/{total} expectation lolos ({len(RULES)} tabel) ===\n")
    for schema, table, etype, detail, success, unexpected_count in results:
        if not success:
            print(f"[FAIL] {schema}.{table} :: {detail} (unexpected={unexpected_count})")
