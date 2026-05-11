"""DWH structure and query plan tools."""

import logging

from connectors.dwh import DWHConnector

logger = logging.getLogger(__name__)


def get_table_schema(dwh: DWHConnector, table_name: str) -> str:
    """Return DDL definition (CREATE TABLE) of a table.

    Used by Ingestion Agent for analyzing new table structure
    and by Assistant Agent for understanding schema.

    Args:
        dwh: DWH connector instance.
        table_name: Name of the table.

    Returns:
        CREATE TABLE statement as string.
    """
    rows = dwh.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    )
    if not rows:
        return f"Table '{table_name}' not found"
    return rows[0]["sql"]


def analyze_query_plan(dwh: DWHConnector, sql: str) -> str:
    """Validate SQL syntax (SELECT only) and return execution plan.

    Used by Assistant Agent for verification of generated SQL
    and for diagnosing suboptimal queries in ETL.

    Args:
        dwh: DWH connector instance.
        sql: SQL query to analyze.

    Returns:
        EXPLAIN QUERY PLAN output or error message.
    """
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT"):
        return "Error: only SELECT statements are allowed for analysis"

    try:
        rows = dwh.execute(f"EXPLAIN QUERY PLAN {sql}")
        lines = [
            f"id={r['id']} parent={r['parent']} detail={r['detail']}"
            for r in rows
        ]
        return "\n".join(lines) if lines else "Empty query plan"
    except Exception as e:
        return f"SQL error: {e}"


if __name__ == "__main__":
    dwh = DWHConnector()
    dwh.init_from_files()

    print("=== get_table_schema ===")
    schema = get_table_schema(dwh, "dim_contract")
    print(schema)

    print("\n=== analyze_query_plan (valid) ===")
    plan = analyze_query_plan(dwh, "SELECT * FROM dim_contract WHERE contract_status = 'terminated'")
    print(plan)

    print("\n=== analyze_query_plan (invalid SQL) ===")
    plan = analyze_query_plan(dwh, "DELETE FROM dim_contract")
    print(plan)

    print("\n=== analyze_query_plan (syntax error) ===")
    plan = analyze_query_plan(dwh, "SELECT * FORM dim_contract")
    print(plan)

    print("\n=== get_table_schema (missing) ===")
    print(get_table_schema(dwh, "nonexistent_table"))

    dwh.close()
    import os
    os.remove(str(dwh._db_path))
    print("\ndwh_tools OK")
