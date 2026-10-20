"""
Module 7 — Dataset Exporter
Exports balanced Real and Synthetic Fake multimodal dataset conforming strictly to Section 9 of doc/plan.md.
Ensures Anti-Data-Leakage splits (Train / Val / Test) and outputs dataset summary statistics.
"""

import os
import json
import logging
from typing import List, Dict, Any
from collections import Counter

from src.schemas import ExportSample

logger = logging.getLogger(__name__)


class DatasetExporter:
    """Exports generated samples to JSON and JSONL datasets partitioned by split."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        out_cfg = config.get("outputs", {})
        self.final_dir = out_cfg.get("final_dataset_dir", "outputs/final_dataset")
        self.rejected_dir = out_cfg.get("rejected_dir", "outputs/rejected")
        os.makedirs(self.final_dir, exist_ok=True)
        os.makedirs(self.rejected_dir, exist_ok=True)

    def export_dataset(
        self,
        samples: List[ExportSample],
        rejected_records: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exports all valid samples into train.jsonl, val.jsonl, test.jsonl, and full_dataset.json.
        Also exports rejected records to outputs/rejected/ for auditing.
        """
        rejected_records = rejected_records or []

        # Group by split
        splits_data: Dict[str, List[Dict[str, Any]]] = {
            "train": [],
            "val": [],
            "test": [],
            "unassigned": []
        }

        all_records = []
        for s in samples:
            rec = s.model_dump()
            split = rec.get("metadata", {}).get("split", "train")
            if split in splits_data:
                splits_data[split].append(rec)
            else:
                splits_data["unassigned"].append(rec)
            all_records.append(rec)

        # 1. Write split JSONL files
        for split_name, recs in splits_data.items():
            if recs:
                split_file = os.path.join(self.final_dir, f"{split_name}.jsonl")
                with open(split_file, "w", encoding="utf-8") as f:
                    for r in recs:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                logger.info(f"Exported {len(recs)} samples to {split_file}")

        # 2. Write full dataset JSON
        full_json_path = os.path.join(self.final_dir, "dataset.json")
        with open(full_json_path, "w", encoding="utf-8") as f:
            json.dump(all_records, f, ensure_ascii=False, indent=2)
        logger.info(f"Exported full dataset ({len(all_records)} samples) to {full_json_path}")

        # 3. Write rejected records for auditing
        if rejected_records:
            rejected_file = os.path.join(self.rejected_dir, "rejected_samples.jsonl")
            with open(rejected_file, "w", encoding="utf-8") as f:
                for r in rejected_records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            logger.info(f"Saved {len(rejected_records)} rejected records to {rejected_file}")

        # 4. Generate statistics summary
        real_count = sum(1 for s in samples if s.label == 1)
        fake_count = sum(1 for s in samples if s.label == 0)
        manipulation_counts = Counter(
            s.metadata.get("manipulation_type", "unknown") for s in samples if s.label == 0
        )
        verif_status_counts = Counter(
            s.metadata.get("verification_status", "unknown") for s in samples if s.label == 0
        )
        rejection_reasons = Counter(
            r.get("reason", "unknown") for r in rejected_records
        )

        summary = {
            "total_samples": len(samples),
            "real_samples": real_count,
            "fake_samples": fake_count,
            "balance_ratio_real_vs_fake": f"{real_count}:{fake_count}",
            "splits": {k: len(v) for k, v in splits_data.items() if len(v) > 0},
            "manipulation_distribution": dict(manipulation_counts),
            "verification_status_distribution": dict(verif_status_counts),
            "total_rejected": len(rejected_records),
            "rejection_reasons": dict(rejection_reasons)
        }

        summary_file = os.path.join(self.final_dir, "dataset_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"Dataset generation complete! Summary saved to {summary_file}")
        return summary
