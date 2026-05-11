"""RAGAS metric computation for RAG quality."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def evaluate_ragas(
    scenario_results: list[dict[str, Any]],
    ground_truth_path: Path,
) -> list[dict]:
    """Compute RAGAS metrics for scenario results.

    Args:
        scenario_results: List of dicts from run_assistant with
            question, answer, retrieved_contexts.
        ground_truth_path: Path to ground_truth.json.

    Returns:
        List of per-scenario RAGAS metric dicts.
    """
    try:
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import (
            Faithfulness,
            ResponseRelevancy,
            LLMContextPrecisionWithoutReference,
            LLMContextRecall,
        )
        from ragas import EvaluationDataset, SingleTurnSample
    except ImportError:
        logger.warning("ragas not installed, skipping RAGAS evaluation")
        return []

    gt = json.loads(ground_truth_path.read_text())
    gt_by_id = {s["id"]: s for s in gt["scenarios"]}

    samples = []
    for i, result in enumerate(scenario_results):
        scenario_id = f"scenario_{i + 1}"
        gt_scenario = gt_by_id.get(scenario_id, {})

        sample = SingleTurnSample(
            user_input=result["question"],
            response=result["answer"],
            retrieved_contexts=result.get("retrieved_contexts", []),
            reference=gt_scenario.get("ground_truth_answer", ""),
        )
        samples.append(sample)

    dataset = EvaluationDataset(samples=samples)

    try:
        from langchain_openai import OpenAIEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from connectors.llm import get_llm
        import config

        llm = get_llm()
        embeddings = LangchainEmbeddingsWrapper(
            OpenAIEmbeddings(
                model=config.EMBEDDING_MODEL,
                openai_api_key=config.LLM_API_KEY,
                openai_api_base=config.LLM_BASE_URL,
            )
        )
        ragas_result = ragas_evaluate(
            dataset=dataset,
            metrics=[
                Faithfulness(llm=llm),
                ResponseRelevancy(llm=llm, embeddings=embeddings),
                LLMContextPrecisionWithoutReference(llm=llm),
                LLMContextRecall(llm=llm),
            ],
        )
        df = ragas_result.to_pandas()
        metrics = []
        for i, row in df.iterrows():
            scenario_id = f"scenario_{i + 1}"
            m = {
                "scenario_id": scenario_id,
                "faithfulness": round(float(row.get("faithfulness", 0)), 3),
                "answer_relevancy": round(float(row.get("answer_relevancy", 0)), 3),
                "context_precision": round(float(row.get("context_precision", 0)), 3),
                "context_recall": round(float(row.get("context_recall", 0)), 3),
            }
            metrics.append(m)
            logger.info("RAGAS [%s]: %s", scenario_id, m)
        return metrics
    except Exception as e:
        logger.error("RAGAS evaluation failed: %s", e)
        return []


if __name__ == "__main__":
    print("ragas_metrics module loaded OK")
    print("Full test requires scenario_results from Assistant Agent run")
