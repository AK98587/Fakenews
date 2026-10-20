"""
Synthetic Multimodal Fake News Pipeline Orchestrator
Coordinates Modules 1-7 through the complete 11-step pipeline.
Implements sequential model execution, checkpointing/resume, anti-data-leakage splitting,
and full dry_run support without GPU/heavy models.
"""

import os
import gc
import json
import random
import logging
from typing import List, Dict, Any, Optional

import numpy as np

from src.schemas import (
    ArticleInput, CleanedArticle, Claim, ImageVisualInfo,
    ExportSample, FakeSampleMetadata, RealSampleMetadata
)
from src.data_loader import DataLoader
from src.text_cleaner import TextCleaner
from src.claim_extractor import ClaimExtractor
from src.image_analyzer import ImageAnalyzer
from src.image_selector import ImageSelector
from src.text_generator import TextGenerator
from src.contradiction_checker import ContradictionChecker
from src.quality_filter import QualityFilter
from src.dataset_exporter import DatasetExporter

logger = logging.getLogger(__name__)


def set_seed(seed: int):
    """Sets random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


class ModelManager:
    """Manages sequential loading and freeing of LLM and VLM to optimize VRAM on GPUs/Colab."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dry_run = config.get("general", {}).get("dry_run", False)
        self.device = config.get("general", {}).get("device", "cuda")
        self.llm_cfg = config.get("models", {}).get("llm", {})
        self.vlm_cfg = config.get("models", {}).get("vlm", {})

    def load_llm(self):
        """Loads Qwen2.5-7B-Instruct with 4-bit quantization if on GPU."""
        if self.dry_run:
            logger.info("Dry run mode: Skipping LLM weights download/load.")
            return None

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

            model_name = self.llm_cfg.get("name", "Qwen/Qwen2.5-7B-Instruct")
            logger.info(f"Loading LLM: {model_name}...")

            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            quant_config = None
            if self.llm_cfg.get("load_in_4bit", True) and torch.cuda.is_available():
                quant_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True
                )

            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quant_config,
                device_map="auto" if torch.cuda.is_available() else "cpu",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                trust_remote_code=True
            )

            temperature = self.llm_cfg.get("temperature", 0.7)
            max_new_tokens = self.llm_cfg.get("max_new_tokens", 1024)

            def llm_generate(prompt: str) -> str:
                messages = [{"role": "user", "content": prompt}]
                input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer([input_text], return_tensors="pt").to(model.device)
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id
                    )
                response = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
                return response.strip()

            return llm_generate
        except Exception as e:
            logger.error(f"Failed to load LLM ({e}). Falling back to dry-run mode.")
            return None

    def load_vlm(self):
        """Loads VLM (e.g. google/gemma-3-4b-it or vision pipeline)."""
        if self.dry_run:
            logger.info("Dry run mode: Skipping VLM weights download/load.")
            return None

        try:
            import torch
            from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

            model_name = self.vlm_cfg.get("name", "google/gemma-3-4b-it")
            logger.info(f"Loading VLM: {model_name}...")

            processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
            quant_config = None
            if self.vlm_cfg.get("load_in_4bit", True) and torch.cuda.is_available():
                quant_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True
                )

            model = AutoModelForImageTextToText.from_pretrained(
                model_name,
                quantization_config=quant_config,
                device_map="auto" if torch.cuda.is_available() else "cpu",
                trust_remote_code=True
            )

            def vlm_generate(image_path: str, prompt: str) -> str:
                from PIL import Image
                img = Image.open(image_path).convert("RGB")
                inputs = processor(text=prompt, images=img, return_tensors="pt").to(model.device)
                with torch.no_grad():
                    outputs = model.generate(**inputs, max_new_tokens=256)
                res = processor.decode(outputs[0], skip_special_tokens=True)
                return res.strip()

            return vlm_generate
        except Exception as e:
            logger.error(f"Failed to load VLM ({e}). Falling back to dry-run image analyzer.")
            return None

    def free_vram(self):
        """Frees GPU memory cache between sequential model executions."""
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


class FakeNewsPipeline:
    """Full 11-Step Pipeline orchestrator for generating Synthetic Multimodal Fake News."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.general_cfg = config.get("general", {})
        self.seed = self.general_cfg.get("seed", 42)
        set_seed(self.seed)

        self.resume = self.general_cfg.get("resume", True)
        self.save_intermediate = self.general_cfg.get("save_intermediate", True)
        self.intermediate_dir = config.get("outputs", {}).get("intermediate_dir", "outputs/intermediate")
        os.makedirs(self.intermediate_dir, exist_ok=True)

        self.model_mgr = ModelManager(config)

        # Initialize Modules
        self.data_loader = DataLoader(config)
        self.text_cleaner = TextCleaner(config)
        self.image_selector = ImageSelector(config)
        self.quality_filter = QualityFilter(config)
        self.dataset_exporter = DatasetExporter(config)

        self.checkpoint_file = os.path.join(self.intermediate_dir, "checkpoint_source_ids.json")
        self.processed_source_ids = self._load_checkpoint()

    def _load_checkpoint(self) -> set:
        if self.resume and os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data)
            except Exception:
                return set()
        return set()

    def _save_checkpoint(self):
        if self.save_intermediate:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(list(self.processed_source_ids), f, ensure_ascii=False)

    def run(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Executes the complete pipeline end-to-end."""
        # Load sufficient raw articles to satisfy limit of valid articles
        raw_limit = max(limit * 3, 40) if limit else None
        raw_articles = self.data_loader.load_raw_articles(limit=raw_limit)

        logger.info("=== STEP 2: TEXT CLEANING & FILTERING ===")
        valid_articles, initial_rejected = self.text_cleaner.process_all(raw_articles)

        # Apply limit to valid articles if requested
        if limit:
            valid_articles = valid_articles[:limit]

        logger.info(f"Proceeding with {len(valid_articles)} valid Good articles.")

        logger.info("=== STEP 3: SPLITTING DATASET (ANTI-DATA LEAKAGE) ===")
        split_dict = self.data_loader.split_dataset_by_source_id(valid_articles)
        # Map source_id to split name
        split_mapping = {}
        for sname, items in split_dict.items():
            for itm in items:
                split_mapping[itm.id] = sname

        # Collect rejection records
        rejected_records: List[Dict[str, Any]] = []
        for r in initial_rejected:
            rejected_records.append({
                "source_id": r.id,
                "title": r.title,
                "reason": r.filter_reason or "cleaning_filter_rejection",
                "stage": "text_cleaning"
            })

        # Save intermediate cleaned articles
        if self.save_intermediate:
            cleaned_path = os.path.join(self.intermediate_dir, "cleaned_articles.json")
            with open(cleaned_path, "w", encoding="utf-8") as f:
                json.dump([a.model_dump() for a in valid_articles], f, ensure_ascii=False, indent=2)

        # Load models sequentially
        logger.info("=== INITIALIZING MODELS ===")
        llm_pipeline = self.model_mgr.load_llm()
        vlm_pipeline = self.model_mgr.load_vlm()

        claim_extractor = ClaimExtractor(self.config, llm_pipeline=llm_pipeline)
        image_analyzer = ImageAnalyzer(self.config, vlm_pipeline=vlm_pipeline)
        text_generator = TextGenerator(self.config, llm_pipeline=llm_pipeline)
        contradiction_checker = ContradictionChecker(self.config, llm_pipeline=llm_pipeline)

        manip_cfg = self.config.get("manipulation", {})
        groups = manip_cfg.get("groups_to_generate", ["G1", "G2", "G3", "G4"])
        max_fakes = manip_cfg.get("max_fakes_per_good", 2)
        preserve_real = manip_cfg.get("preserve_real_sample", True)

        final_samples: List[ExportSample] = []
        fake_counter = 1
        real_counter = 1

        logger.info(f"=== PROCESSING {len(valid_articles)} VALID ARTICLES ===")

        for idx, art in enumerate(valid_articles):
            if self.resume and art.id in self.processed_source_ids:
                logger.info(f"Skipping already processed article {art.id} (Resume mode)")
                continue

            split_name = split_mapping.get(art.id, "train")

            # STEP 4: Claim Extraction
            extraction_res = claim_extractor.extract_claims(art)
            if not extraction_res.is_viable or not extraction_res.claims:
                rejected_records.append({
                    "source_id": art.id,
                    "title": art.title,
                    "reason": extraction_res.rejection_reason or "no_claims_extracted",
                    "stage": "claim_extraction"
                })
                self.processed_source_ids.add(art.id)
                continue

            claims = extraction_res.claims

            # STEP 5: Image Analysis
            image_infos = image_analyzer.analyze_images(art.image_paths, claims)

            # STEP 6: Select Representative Image
            chosen_image_info = self.image_selector.select_best_image(image_infos, claims[0], 0)
            chosen_img_path = chosen_image_info.image_path if chosen_image_info else (
                art.image_paths[0] if art.image_paths else "images/placeholder.jpg"
            )

            # REAL SAMPLE: Add unaltered Good article (Label 1)
            if preserve_real:
                real_id = f"real_{real_counter:06d}"
                real_counter += 1
                real_meta = RealSampleMetadata(
                    original_claim=claims[0].to_summary_text(),
                    split=split_name
                )
                real_text = art.content.strip() if (art.content and art.content.startswith(art.title)) else f"{art.title}. {art.content}".strip()
                final_samples.append(
                    ExportSample(
                        id=real_id,
                        source_id=f"good_{art.id}",
                        image_path=chosen_img_path,
                        text=real_text,
                        label=1,
                        metadata=real_meta.model_dump()
                    )
                )

            # STEP 7-10: Controlled Manipulation & Verification
            fakes_generated_for_art = 0
            # Rotate groups deterministically based on index
            selected_groups = [groups[(idx + g_offset) % len(groups)] for g_offset in range(len(groups))]

            for group in selected_groups:
                if fakes_generated_for_art >= max_fakes:
                    break

                target_claim = claims[0]
                manipulation_res = text_generator.generate_manipulation(
                    group=group,
                    article=art,
                    claim=target_claim,
                    all_claims=claims
                )

                # Re-select best image if group targeted a specific claim
                best_img = self.image_selector.select_best_image(image_infos, target_claim)
                img_path_for_fake = best_img.image_path if best_img else chosen_img_path

                # STEP 8: Factual Contradiction Check
                verif_res = contradiction_checker.verify_contradiction(
                    article=art,
                    claim=target_claim,
                    manipulation=manipulation_res
                )

                # STEP 9 & 10: Quality Gate & Image Consistency
                passed, reject_reason = self.quality_filter.filter_sample(
                    manipulation=manipulation_res,
                    image_info=best_img,
                    verification=verif_res
                )

                if passed:
                    fake_id = f"fake_{fake_counter:06d}"
                    fake_counter += 1
                    fakes_generated_for_art += 1

                    meta = FakeSampleMetadata(
                        generation_model="Qwen2.5-7B-Instruct" if not self.config.get("general", {}).get("dry_run") else "heuristic_rule_engine",
                        generation_method="controlled_manipulation",
                        manipulation_type=group,
                        original_claim=manipulation_res.original_claim,
                        modified_claim=manipulation_res.modified_claim,
                        verification_status=verif_res.verification_status,
                        image_original=True,
                        quality_passed=True,
                        change_summary=manipulation_res.change_summary,
                        image_description=best_img.description if best_img else None,
                        image_contextual_only=best_img.is_contextual_only if best_img else True,
                        split=split_name
                    )

                    sample = ExportSample(
                        id=fake_id,
                        source_id=f"good_{art.id}",
                        image_path=img_path_for_fake,
                        text=manipulation_res.modified_text,
                        label=0,
                        metadata=meta.model_dump()
                    )
                    final_samples.append(sample)
                else:
                    rejected_records.append({
                        "source_id": art.id,
                        "title": art.title,
                        "group": group,
                        "reason": reject_reason,
                        "stage": "quality_verification"
                    })

            self.processed_source_ids.add(art.id)
            self._save_checkpoint()

        logger.info("=== STEP 11: DATASET EXPORT ===")
        summary = self.dataset_exporter.export_dataset(
            samples=final_samples,
            rejected_records=rejected_records
        )

        return summary
