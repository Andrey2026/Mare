"""MARE project configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

# --- Paths ---
DATA_DIR = PROJECT_ROOT / "data"
DDL_DIR = DATA_DIR / "ddl"
SEED_DIR = DATA_DIR / "seed"
DWH_DB_PATH = DATA_DIR / "dwh.db"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
RESULTS_DIR = PROJECT_ROOT / "results"
GROUND_TRUTH_PATH = DATA_DIR / "ground_truth.json"

# --- LLM ---
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# --- Embeddings (OpenAI-compatible, same base URL as LLM) ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# --- Manual time estimates (seconds) for comparison ---
MANUAL_TIME_SCENARIO_1 = int(os.getenv("MANUAL_TIME_SCENARIO_1", "900"))
MANUAL_TIME_SCENARIO_2 = int(os.getenv("MANUAL_TIME_SCENARIO_2", "1800"))


if __name__ == "__main__":
    print(f"PROJECT_ROOT:    {PROJECT_ROOT}")
    print(f"DWH_DB_PATH:     {DWH_DB_PATH}")
    print(f"LLM_BASE_URL:    {LLM_BASE_URL}")
    print(f"LLM_MODEL:       {LLM_MODEL}")
    print(f"EMBEDDING_MODEL: {EMBEDDING_MODEL}")
    print(f"DDL_DIR exists:  {DDL_DIR.exists()}")
