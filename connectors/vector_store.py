"""LanceDB connector for semantic layer."""

import logging
from pathlib import Path
from typing import Optional

import lancedb
from langchain_openai import OpenAIEmbeddings

import config

logger = logging.getLogger(__name__)


class VectorStoreConnector:
    """Provides connection, upsert, and search for the semantic layer."""

    def __init__(
        self,
        db_path: Path = config.VECTOR_STORE_DIR,
    ) -> None:
        self._db_path = db_path
        self._db: Optional[lancedb.DBConnection] = None
        self._embedder: Optional[OpenAIEmbeddings] = None
        self._table_name = "metadata"

    def _get_embedder(self) -> OpenAIEmbeddings:
        if self._embedder is None:
            self._embedder = OpenAIEmbeddings(
                model=config.EMBEDDING_MODEL,
                openai_api_key=config.LLM_API_KEY,
                openai_api_base=config.LLM_BASE_URL,
            )
            logger.info("Loaded embedding model: %s", config.EMBEDDING_MODEL)
        return self._embedder

    def _get_db(self) -> lancedb.DBConnection:
        if self._db is None:
            self._db_path.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self._db_path))
            logger.info("Connected to LanceDB at %s", self._db_path)
        return self._db

    def _embed(self, text: str) -> list[float]:
        embedder = self._get_embedder()
        return embedder.embed_query(text)

    def upsert(self, table_name: str, description: str, metadata: dict) -> None:
        """Add or update a table description in the vector store."""
        db = self._get_db()
        vector = self._embed(description)
        record = {
            "table_name": table_name,
            "description": description,
            "vector": vector,
            **metadata,
        }

        if self._table_name in db.list_tables().tables:
            tbl = db.open_table(self._table_name)
            try:
                tbl.delete(f'table_name = "{table_name}"')
            except Exception:
                pass
            tbl.add([record])
        else:
            db.create_table(self._table_name, [record])

        logger.info("Upserted description for table: %s", table_name)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Search for tables by semantic similarity to query."""
        db = self._get_db()
        if self._table_name not in db.list_tables().tables:
            logger.warning("Vector store is empty")
            return []

        query_vector = self._embed(query)
        tbl = db.open_table(self._table_name)
        results = (
            tbl.search(query_vector)
            .limit(top_k)
            .to_list()
        )
        return [
            {
                "table_name": r["table_name"],
                "description": r["description"],
                "score": r.get("_distance", 0.0),
            }
            for r in results
        ]

    def count(self) -> int:
        """Return number of records in vector store."""
        db = self._get_db()
        if self._table_name not in db.list_tables().tables:
            return 0
        return db.open_table(self._table_name).count_rows()


if __name__ == "__main__":
    import shutil
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp()) / "test_vs"
    try:
        vs = VectorStoreConnector(db_path=tmp_dir)
        vs.upsert("dim_contract", "Dimension table for contracts with status and manager info", {})
        vs.upsert("fact_revenue", "Fact table with revenue amounts by contract and date", {})
        print(f"Count: {vs.count()}")

        results = vs.search("contract information", top_k=2)
        print(f"Search 'contract information': {[r['table_name'] for r in results]}")

        results = vs.search("revenue data", top_k=2)
        print(f"Search 'revenue data': {[r['table_name'] for r in results]}")

        print("VectorStoreConnector OK")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
