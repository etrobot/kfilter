"""Utility script to exercise the ZAI deepsearch streaming client.

Run with `uv run python backend/scripts/test_deepsearch.py --sector-code BK0893 --sector-name 光刻机`.
Requires valid ZAI credentials in backend/config.json or environment variables.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from datetime import datetime

from config import get_zai_credentials, is_zai_configured
from data_management.deepsearch import ZAIChatClient


def build_messages(sector_name: str) -> list[dict[str, str]]:
    current_year = datetime.now().year
    prompt = (
        f"{current_year}A股{sector_name}概念投资机会分析，搜集的材料要涵盖"
        f"{sector_name}概念的起源到最新消息"
    )
    return [{"role": "user", "content": prompt}]


def run_stream(client: ZAIChatClient, messages: list[dict[str, str]], *, model: Optional[str]) -> str:
    full_response = ""
    for chunk in client.stream_chat_completion(messages, model=model or "GLM-4-6-API-V1"):
        if chunk:
            full_response += chunk
            print(chunk, end="", flush=True)
    print()  # newline after stream
    return full_response


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Exercise ZAI deepsearch streaming client")
    parser.add_argument("--sector-name", required=True, help="Concept or sector name to query")
    parser.add_argument("--sector-code", default="", help="Optional concept code for logging")
    parser.add_argument(
        "--model",
        default=None,
        help="Override model identifier (default: GLM-4-6-API-V1)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    if not is_zai_configured():
        logging.error("ZAI credentials are not configured. Please run the config dialog first.")
        return 1

    bearer, cookie, user_id = get_zai_credentials()
    if not bearer or not user_id:
        logging.error("Missing bearer token or user id in configuration.")
        return 1

    logging.info("Creating ZAI client for %s (%s)", args.sector_name, args.sector_code or "no-code")
    config = {
        'bearer_token': bearer,
        'user_id': user_id
    }
    client = ZAIChatClient(config=config)
    messages = build_messages(args.sector_name)

    try:
        response = run_stream(client, messages, model=args.model)
    except Exception as exc:  # pylint: disable=broad-except
        logging.exception("Deepsearch streaming failed: %s", exc)
        return 2

    logging.info("Received %s characters from deepsearch", len(response))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
