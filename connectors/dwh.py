"""SQLite connector for DWH emulation."""

import logging
import sqlite3
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class DWHConnector:
    """Provides connection and query execution for the emulated DWH."""

    def __init__(self, db_path: Path = config.DWH_DB_PATH) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Return existing connection or create a new one."""
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            logger.info("Connected to DWH at %s", self._db_path)
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute SQL and return results as list of dicts."""
        conn = self.connect()
        cursor = conn.execute(sql, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def execute_script(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script."""
        conn = self.connect()
        conn.executescript(sql_script)
        conn.commit()

    def init_from_files(self) -> None:
        """Initialize DWH from DDL and seed SQL files."""
        for sql_file in sorted(config.DDL_DIR.glob("*.sql")):
            logger.info("Executing DDL: %s", sql_file.name)
            self.execute_script(sql_file.read_text())
        for sql_file in sorted(config.SEED_DIR.glob("*.sql")):
            logger.info("Executing seed: %s", sql_file.name)
            self.execute_script(sql_file.read_text())

    def close(self) -> None:
        """Close the connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


if __name__ == "__main__":
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        dwh = DWHConnector(db_path=Path(f.name))
        dwh.execute_script("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);")
        dwh.execute_script("INSERT INTO test VALUES (1, 'hello');")
        rows = dwh.execute("SELECT * FROM test")
        print("Test query result:", rows)
        dwh.close()
        print("DWH connector OK")
