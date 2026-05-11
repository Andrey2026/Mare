"""Generate evaluation report in JSON and Markdown."""

import json
import logging
from typing import Any

import config

logger = logging.getLogger(__name__)


def generate_report(
    search_metrics: list[dict],
    ragas_metrics: list[dict],
    scenario_results: list[dict[str, Any]],
) -> None:
    """Generate metrics.json and report.md.

    Args:
        search_metrics: Per-query search precision/recall.
        ragas_metrics: Per-scenario RAGAS scores.
        scenario_results: Raw scenario results with timing.
    """
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    all_metrics = {
        "search_metrics": search_metrics,
        "ragas_metrics": ragas_metrics,
        "execution_time": [
            {
                "scenario_id": f"scenario_{i + 1}",
                "agent_seconds": r["duration_seconds"],
                "manual_estimate_seconds": (
                    config.MANUAL_TIME_SCENARIO_1 if i == 0
                    else config.MANUAL_TIME_SCENARIO_2
                ),
            }
            for i, r in enumerate(scenario_results)
        ],
    }

    json_path = config.RESULTS_DIR / "metrics.json"
    json_path.write_text(json.dumps(all_metrics, indent=2, ensure_ascii=False))
    logger.info("Metrics saved to %s", json_path)

    lines = ["# MARE Evaluation Report\n"]

    if ragas_metrics:
        lines.append("## RAGAS Metrics\n")
        lines.append("| Scenario | Faithfulness | Answer Relevance | Context Precision | Context Recall |")
        lines.append("|----------|-------------|-----------------|-------------------|----------------|")
        for m in ragas_metrics:
            lines.append(
                f"| {m['scenario_id']} | {m['faithfulness']:.3f} | "
                f"{m['answer_relevancy']:.3f} | {m['context_precision']:.3f} | "
                f"{m['context_recall']:.3f} |"
            )
        lines.append("")

    if search_metrics:
        lines.append("## Semantic Search Precision/Recall\n")
        lines.append("| Query | P@k | R@k | Retrieved | Expected |")
        lines.append("|-------|-----|-----|-----------|----------|")
        for m in search_metrics:
            lines.append(
                f"| {m['query'][:40]} | {m['precision_at_k']:.3f} | "
                f"{m['recall_at_k']:.3f} | {', '.join(m['retrieved'])} | "
                f"{', '.join(m['expected'])} |"
            )
        lines.append("")

    lines.append("## Execution Time\n")
    lines.append("| Scenario | Agent (sec) | Manual estimate (min) | Speedup |")
    lines.append("|----------|------------|----------------------|---------|")
    for i, r in enumerate(scenario_results):
        manual = config.MANUAL_TIME_SCENARIO_1 if i == 0 else config.MANUAL_TIME_SCENARIO_2
        speedup = round(manual / max(r["duration_seconds"], 0.1), 1)
        lines.append(
            f"| scenario_{i+1} | {r['duration_seconds']:.1f} | "
            f"{manual // 60} | {speedup}x |"
        )

    md_path = config.RESULTS_DIR / "report.md"
    md_path.write_text("\n".join(lines))
    logger.info("Report saved to %s", md_path)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    mock_search = [
        {"query": "test query", "expected": ["t1"], "retrieved": ["t1", "t2", "t3"],
         "precision_at_k": 0.333, "recall_at_k": 1.0, "k": 3},
    ]
    mock_ragas = [
        {"scenario_id": "scenario_1", "faithfulness": 0.9, "answer_relevancy": 0.85,
         "context_precision": 1.0, "context_recall": 1.0},
    ]
    mock_results = [
        {"question": "test?", "answer": "answer", "retrieved_contexts": [],
         "duration_seconds": 5.2, "message_count": 4},
    ]

    generate_report(mock_search, mock_ragas, mock_results)

    report_path = config.RESULTS_DIR / "report.md"
    print(report_path.read_text())
    print("\nreport OK")

    import shutil
    shutil.rmtree(config.RESULTS_DIR)
