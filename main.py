"""
Main entry point for the Synthetic Multimodal Fake News Generation System.
Supports dry-run testing, full GPU inference, checkpoint resumption, and sample limits.
"""

import os
import sys
import argparse
import logging
import yaml
from typing import Dict, Any

# Ensure stdout handles UTF-8 on Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add current workspace to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.pipeline import FakeNewsPipeline


def setup_logging(log_dir: str, level_str: str = "INFO"):
    """Sets up formatted logging to console and file."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "pipeline_run.log")

    level = getattr(logging, level_str.upper(), logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Synthetic Multimodal Fake News Generation System (from Good Dataset)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.yaml",
        help="Path to YAML configuration file (default: configs/config.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (heuristics/mock, no large LLM/VLM download or GPU required)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of raw articles to process (e.g. --limit 5)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume mode and reprocess from scratch"
    )

    args = parser.parse_args()

    # Load configuration
    config = load_yaml_config(args.config)

    # CLI Overrides
    if args.dry_run:
        config.setdefault("general", {})["dry_run"] = True
    if args.no_resume:
        config.setdefault("general", {})["resume"] = False

    # Setup Logging
    log_dir = config.get("outputs", {}).get("logs_dir", "outputs/logs")
    log_level = config.get("general", {}).get("log_level", "INFO")
    setup_logging(log_dir, log_level)

    logger = logging.getLogger("main")
    logger.info("================================================================")
    logger.info("STARTING SYNTHETIC MULTIMODAL FAKE NEWS PIPELINE")
    logger.info(f"Config: {args.config}")
    logger.info(f"Dry Run: {config.get('general', {}).get('dry_run', False)}")
    logger.info(f"Limit: {args.limit if args.limit else 'All'}")
    logger.info(f"Resume: {config.get('general', {}).get('resume', True)}")
    logger.info("================================================================")

    # Instantiate and run pipeline
    pipeline = FakeNewsPipeline(config)
    summary = pipeline.run(limit=args.limit)

    # Print summary
    logger.info("================================================================")
    logger.info("PIPELINE EXECUTION FINISHED SUCCESSFULLY")
    logger.info(f"Total Samples Generated: {summary.get('total_samples', 0)}")
    logger.info(f"Real Samples (Label 0): {summary.get('real_samples', 0)}")
    logger.info(f"Fake Samples (Label 1): {summary.get('fake_samples', 0)}")
    logger.info(f"Balance Ratio (Real:Fake): {summary.get('balance_ratio_real_vs_fake', 'N/A')}")
    logger.info(f"Splits Distribution: {summary.get('splits', {})}")
    logger.info(f"Manipulation Groups: {summary.get('manipulation_distribution', {})}")
    logger.info(f"Total Rejected Samples: {summary.get('total_rejected', 0)}")
    logger.info("================================================================")

    # Automatically regenerate Human Check HTML
    try:
        from generate_human_check_html import build_human_check_html
        build_human_check_html()
        logger.info("Human check HTML interfaces updated: human_check.html and outputs/human_check.html")
    except Exception as e:
        logger.warning(f"Could not generate human check HTML automatically: {e}")

if __name__ == "__main__":
    main()
