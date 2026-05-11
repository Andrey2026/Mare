"""Precision/Recall metrics for semantic search."""

import json
import logging
from pathlib import Path

from connectors.vector_store import VectorStoreConnector

logger = logging.getLogger(__name__)


def evaluate_search(
    vector_store: VectorStoreConnector,
    ground_truth_path: Path,
) -> list[dict]:
    """Evaluate semantic search quality against ground truth.

    Args:
        vector_store: Vector store connector.
        ground_truth_path: Path to ground_truth.json.

    Returns:
        List of per-query metric dicts.
    """
    gt = json.loads(ground_truth_path.read_text())
    results = []

    for q in gt["search_queries"]:
        query = q["query"]
        expected = set(q["expected_tables"])
        k = q["k"]

        search_results = vector_store.search(query, top_k=k)
        retrieved = [r["table_name"] for r in search_results]
        retrieved_set = set(retrieved)

        relevant_in_topk = retrieved_set & expected
        precision = len(relevant_in_topk) / k if k > 0 else 0
        recall = len(relevant_in_topk) / len(expected) if expected else 0

        results.append({
            "query": query,
            "expected": sorted(expected),
            "retrieved": retrieved,
            "precision_at_k": round(precision, 3),
            "recall_at_k": round(recall, 3),
            "k": k,
        })
        logger.info(
            "Search [%s]: P@%d=%.3f R@%d=%.3f",
            query[:40], k, precision, k, recall,
        )

    return results


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    import config
    from connectors.vector_store import VectorStoreConnector

    descriptions = {
        "stg_contract_events": "Staging table with raw contract events from source systems",
        "dim_contract": "Dimension table for contracts with status and manager info",
        "dim_manager": "Dimension table for managers with names and departments",
        "dim_date": "Calendar dimension with dates, months, quarters, years",
        "fact_revenue": "Fact table with revenue amounts by contract and date",
        "fact_contract_events": "Fact table with contract lifecycle events",
        "dm_contract_report": "Data mart for contract reporting with aggregated revenue",
    }

    vs = VectorStoreConnector()
    for name, desc in descriptions.items():
        vs.upsert(name, desc, {})

    results = evaluate_search(vs, config.GROUND_TRUTH_PATH)
    print(f"\n=== Search Metrics ===")
    for r in results:
        print(f"  {r['query'][:40]:40s} P@{r['k']}={r['precision_at_k']:.3f} R@{r['k']}={r['recall_at_k']:.3f} retrieved={r['retrieved']}")

    avg_p = sum(r["precision_at_k"] for r in results) / len(results)
    avg_r = sum(r["recall_at_k"] for r in results) / len(results)
    print(f"\n  Avg P@k={avg_p:.3f} Avg R@k={avg_r:.3f}")

    import shutil
    shutil.rmtree(config.VECTOR_STORE_DIR, ignore_errors=True)
    print("\nsearch_metrics OK")
