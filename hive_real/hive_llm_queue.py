"""hive_llm_queue.py - Simple queue file helpers"""
from pathlib import Path


def requests_path(base_dir: Path) -> Path:
    """Get path to requests queue file"""
    return base_dir / "inbox" / "hive_llm_requests.jsonl"


def responses_path(base_dir: Path) -> Path:
    """Get path to responses queue file"""
    return base_dir / "outbox" / "hive_llm_responses.jsonl"
