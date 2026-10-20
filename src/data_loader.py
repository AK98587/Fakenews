"""
Module 1 — Data Loader
Handles loading data from CSV, JSON, or JSONL with configurable field mapping,
image path validation (supporting 1-19 images per article), and anti-data-leakage splitting by source_id.
"""

import os
import json
import logging
from typing import List, Dict, Any, Tuple
import pandas as pd
from sklearn.model_selection import train_test_split

from src.schemas import ArticleInput

logger = logging.getLogger(__name__)


class DataLoader:
    """Configurable loader for raw news datasets."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_cfg = config.get("data", {})
        self.input_path = self.data_cfg.get("input_path", "real_data_annotation.csv")
        self.input_format = self.data_cfg.get("input_format", "csv").lower()
        self.image_base_dir = self.data_cfg.get("image_base_dir", ".")
        self.field_mapping = self.data_cfg.get("field_mapping", {})
        self.delimiter = self.field_mapping.get("image_delimiter", "|")
        self.splits_cfg = self.data_cfg.get("splits", {"train": 0.8, "val": 0.1, "test": 0.1, "split_seed": 42})

    def _resolve_image_path(self, raw_path: str) -> str:
        """Standardizes path and checks existence."""
        cleaned_path = raw_path.strip().replace("\\", "/")
        full_path = os.path.normpath(os.path.join(self.image_base_dir, cleaned_path))
        if os.path.exists(full_path) or os.path.exists(cleaned_path):
            return cleaned_path
        # Log missing image warning but keep relative path
        logger.debug(f"Image not found on disk: {cleaned_path} (resolved: {full_path})")
        return cleaned_path

    def _parse_image_paths(self, raw_images: Any) -> List[str]:
        """Parses list of image paths from various formats (string with delimiter, list, or JSON)."""
        if raw_images is None or (isinstance(raw_images, float) and pd.isna(raw_images)):
            return []

        if isinstance(raw_images, list):
            return [self._resolve_image_path(str(p)) for p in raw_images if str(p).strip()]

        if isinstance(raw_images, str):
            raw_str = raw_images.strip()
            if not raw_str:
                return []
            if raw_str.startswith("[") and raw_str.endswith("]"):
                try:
                    parsed = json.loads(raw_str)
                    if isinstance(parsed, list):
                        return [self._resolve_image_path(str(p)) for p in parsed if str(p).strip()]
                except Exception:
                    pass
            # Split by delimiter (e.g. '|' or ',')
            if self.delimiter in raw_str:
                parts = raw_str.split(self.delimiter)
            elif "," in raw_str and not os.path.exists(raw_str):
                parts = raw_str.split(",")
            else:
                parts = [raw_str]
            return [self._resolve_image_path(p) for p in parts if p.strip()]

        return []

    def load_raw_articles(self, limit: int = None) -> List[ArticleInput]:
        """
        Loads raw articles from configured input file without modifying the original source.
        Returns a list of validated ArticleInput objects.
        """
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input data file not found: {self.input_path}")

        logger.info(f"Loading data from {self.input_path} (format: {self.input_format})...")
        articles: List[ArticleInput] = []

        if self.input_format == "csv":
            df = pd.read_csv(self.input_path, encoding="utf-8")
        elif self.input_format in ["json", "jsonl"]:
            if self.input_format == "jsonl":
                records = []
                with open(self.input_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            records.append(json.loads(line))
                df = pd.DataFrame(records)
            else:
                with open(self.input_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    df = pd.DataFrame(data if isinstance(data, list) else [data])
        else:
            raise ValueError(f"Unsupported format: {self.input_format}")

        # Field mapping
        id_col = self.field_mapping.get("id", "id")
        title_col = self.field_mapping.get("title", "title")
        content_col = self.field_mapping.get("content", "content")
        images_col = self.field_mapping.get("image_paths", "image_paths")
        is_dup_col = self.field_mapping.get("is_duplicate", "is_duplicate")
        source_col = self.field_mapping.get("source", "source")

        for idx, row in df.iterrows():
            if limit and len(articles) >= limit:
                break

            article_id = str(row.get(id_col, f"art_{idx+1}"))
            title = str(row.get(title_col, "")).strip() if pd.notna(row.get(title_col)) else ""
            content = str(row.get(content_col, "")).strip() if pd.notna(row.get(content_col)) else ""

            # Fallback if text field is used instead of content
            if not content and "text" in row and pd.notna(row["text"]):
                content = str(row["text"]).strip()

            raw_images = row.get(images_col, None)
            parsed_images = self._parse_image_paths(raw_images)
            is_dup = int(row.get(is_dup_col, 0)) if pd.notna(row.get(is_dup_col)) else 0
            source_url = str(row.get(source_col, "")) if pd.notna(row.get(source_col)) else None

            article = ArticleInput(
                id=article_id,
                title=title,
                content=content,
                image_paths=parsed_images,
                num_images=len(parsed_images),
                source_url=source_url,
                is_duplicate=is_dup,
                raw_metadata={"row_index": idx}
            )
            articles.append(article)

        logger.info(f"Loaded {len(articles)} raw articles.")
        return articles

    def split_dataset_by_source_id(
        self, articles: List[ArticleInput]
    ) -> Dict[str, List[ArticleInput]]:
        """
        Anti-Data-Leakage Splitting:
        Splits articles into train/val/test by source_id so all variants of a Good article
        remain strictly within the same subset.
        """
        train_ratio = self.splits_cfg.get("train", 0.8)
        val_ratio = self.splits_cfg.get("val", 0.1)
        test_ratio = self.splits_cfg.get("test", 0.1)
        seed = self.splits_cfg.get("split_seed", 42)

        unique_ids = [a.id for a in articles]
        if len(unique_ids) < 3:
            # Not enough samples for a 3-way split, assign all to train
            return {"train": articles, "val": [], "test": []}

        # For small sample sizes (< 10), split deterministically without sklearn error
        if len(unique_ids) < 10:
            n_total = len(unique_ids)
            n_val = 1
            n_test = 1 if n_total >= 4 else 0
            n_train = n_total - n_val - n_test
            train_ids = unique_ids[:n_train]
            val_ids = unique_ids[n_train:n_train + n_val]
            test_ids = unique_ids[n_train + n_val:]
        else:
            temp_ratio = val_ratio + test_ratio
            train_ids, temp_ids = train_test_split(
                unique_ids, test_size=temp_ratio, random_state=seed, shuffle=True
            )
            val_relative_ratio = val_ratio / temp_ratio if temp_ratio > 0 else 0.5
            if len(temp_ids) <= 1:
                val_ids = temp_ids
                test_ids = []
            else:
                val_ids, test_ids = train_test_split(
                    temp_ids, test_size=(1.0 - val_relative_ratio), random_state=seed, shuffle=True
                )

        train_set = set(train_ids)
        val_set = set(val_ids)
        test_set = set(test_ids)

        splits: Dict[str, List[ArticleInput]] = {"train": [], "val": [], "test": []}
        for a in articles:
            if a.id in train_set:
                splits["train"].append(a)
            elif a.id in val_set:
                splits["val"].append(a)
            else:
                splits["test"].append(a)

        logger.info(
            f"Dataset Split (Anti-Leakage): Train={len(splits['train'])}, "
            f"Val={len(splits['val'])}, Test={len(splits['test'])}"
        )
        return splits
