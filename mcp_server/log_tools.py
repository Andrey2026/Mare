"""Execution logs and data metrics tools."""

import logging

from connectors.dwh import DWHConnector

logger = logging.getLogger(__name__)


def fetch_recent_logs(
    dwh: DWHConnector, process_name: str, limit: int = 50
) -> list[dict]:
    """Extract recent text log entries of an ETL process.

    Contains level (INFO/WARNING/ERROR) and messages.
    Used for finding errors and warnings during incident diagnosis.

    Args:
        dwh: DWH connector instance.
        process_name: ETL process name.
        limit: Maximum number of log entries.

    Returns:
        List of log records, most recent first.
    """
    return dwh.execute(
        "SELECT log_id, process_name, timestamp, level, message "
        "FROM etl_process_logs WHERE process_name = ? "
        "ORDER BY timestamp DESC LIMIT ?",
        (process_name, limit),
    )


def get_table_increment_stats(dwh: DWHConnector, table_name: str) -> dict:
    """Estimate data volume in the last table increment vs average.

    Reveals anomalous data growth that may cause ETL slowdowns.

    Args:
        dwh: DWH connector instance.
        table_name: Target table name of ETL process.

    Returns:
        Dict with last_rows, avg_rows, ratio, process_name.
    """
    processes = dwh.execute(
        "SELECT process_name FROM etl_processes WHERE target_table = ?",
        (table_name,),
    )
    if not processes:
        return {"error": f"No ETL process found for table '{table_name}'"}

    process_name = processes[0]["process_name"]

    stats = dwh.execute(
        "SELECT "
        "  (SELECT rows_affected FROM etl_execution_log "
        "   WHERE process_name = ? ORDER BY started_at DESC LIMIT 1) as last_rows, "
        "  (SELECT AVG(rows_affected) FROM etl_execution_log "
        "   WHERE process_name = ?) as avg_rows",
        (process_name, process_name),
    )

    if not stats or stats[0]["last_rows"] is None:
        return {"error": f"No execution history for '{process_name}'"}

    row = stats[0]
    avg = row["avg_rows"] or 1
    return {
        "process_name": process_name,
        "table_name": table_name,
        "last_rows": row["last_rows"],
        "avg_rows": round(avg, 0),
        "ratio": round(row["last_rows"] / avg, 2),
    }


if __name__ == "__main__":
    dwh = DWHConnector()
    dwh.init_from_files()

    print("=== fetch_recent_logs('etl_refresh_dm_contract_report') ===")
    logs = fetch_recent_logs(dwh, "etl_refresh_dm_contract_report", limit=3)
    for log_entry in logs:
        print(f"  [{log_entry['level']}] {log_entry['message']}")

    print("\n=== get_table_increment_stats('stg_contract_events') ===")
    stats = get_table_increment_stats(dwh, "stg_contract_events")
    print(f"  last_rows={stats.get('last_rows')}, avg={stats.get('avg_rows')}, ratio={stats.get('ratio')}")

    print("\n=== get_table_increment_stats('nonexistent') ===")
    print(f"  {get_table_increment_stats(dwh, 'nonexistent')}")

    dwh.close()
    import os
    os.remove(str(dwh._db_path))
    print("\nlog_tools OK")
