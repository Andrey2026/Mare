"""ETL process information tools."""

import logging

from connectors.dwh import DWHConnector

logger = logging.getLogger(__name__)


def find_etl_process_by_table(dwh: DWHConnector, table_name: str) -> list[dict]:
    """Find ETL processes that load data into the specified target table.

    Returns process name, schedule, and source tables.
    Used for building data dependency chains.

    Args:
        dwh: DWH connector instance.
        table_name: Target table name.

    Returns:
        List of ETL process records.
    """
    return dwh.execute(
        "SELECT process_name, target_table, source_tables, schedule, description "
        "FROM etl_processes WHERE target_table = ?",
        (table_name,),
    )


def get_process_execution_status(dwh: DWHConnector, process_name: str) -> list[dict]:
    """Return history of last 5 executions of an ETL process.

    Shows start/end time, status, rows affected, duration.
    Reveals anomalies in execution dynamics.

    Args:
        dwh: DWH connector instance.
        process_name: ETL process name.

    Returns:
        List of execution log records, most recent first.
    """
    return dwh.execute(
        "SELECT execution_id, process_name, started_at, finished_at, "
        "status, rows_affected, duration_seconds "
        "FROM etl_execution_log WHERE process_name = ? "
        "ORDER BY started_at DESC LIMIT 5",
        (process_name,),
    )


if __name__ == "__main__":
    dwh = DWHConnector()
    dwh.init_from_files()

    print("=== find_etl_process_by_table('dm_contract_report') ===")
    procs = find_etl_process_by_table(dwh, "dm_contract_report")
    for p in procs:
        print(p)

    print("\n=== get_process_execution_status('etl_refresh_dm_contract_report') ===")
    status = get_process_execution_status(dwh, "etl_refresh_dm_contract_report")
    for s in status:
        print(f"  {s['started_at']} | {s['status']} | rows={s['rows_affected']} | {s['duration_seconds']}s")

    dwh.close()
    import os
    os.remove(str(dwh._db_path))
    print("\netl_tools OK")
