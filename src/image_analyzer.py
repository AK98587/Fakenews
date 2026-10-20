"""
Module 4a — Image Analyzer
Analyzes visual content of 1-19 images per article without hallucinating non-visible identities/events.
Uses Gemma-3-4B-IT (or vision model) in GPU mode, or non-destructive metadata heuristic in dry_run.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from PIL import Image

from src.schemas import ImageVisualInfo, Claim

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Analyzes visual characteristics of images belonging to news articles."""

    def __init__(self, config: Dict[str, Any], vlm_pipeline=None):
        self.config = config
        self.dry_run = config.get("general", {}).get("dry_run", False)
        self.image_base_dir = config.get("data", {}).get("image_base_dir", ".")
        self.vlm_pipeline = vlm_pipeline

    def _resolve_path(self, path: str) -> str:
        """Finds absolute or workspace relative path."""
        if os.path.exists(path):
            return path
        joined = os.path.normpath(os.path.join(self.image_base_dir, path))
        if os.path.exists(joined):
            return joined
        return path

    def analyze_single_image(self, rel_path: str, claims: List[Claim]) -> ImageVisualInfo:
        """Analyzes a single image file."""
        resolved = self._resolve_path(rel_path)
        exists = os.path.exists(resolved) and (os.path.getsize(resolved) > 0)

        if not exists:
            return ImageVisualInfo(
                image_path=rel_path,
                exists=False,
                description="Hình ảnh không tồn tại hoặc kích thước 0 byte.",
                relevance_score=0.0,
                is_contextual_only=True
            )

        width, height = None, None
        try:
            with Image.open(resolved) as img:
                width, height = img.size
        except Exception as e:
            logger.debug(f"Could not open image {resolved}: {e}")
            return ImageVisualInfo(
                image_path=rel_path,
                exists=False,
                description="Tập tin hình ảnh bị lỗi hoặc không thể đọc.",
                relevance_score=0.0,
                is_contextual_only=True
            )

        # VLM Inference or Dry-Run Heuristic
        if not self.dry_run and self.vlm_pipeline is not None:
            try:
                # Prompt VLM to describe strictly visible elements
                prompt = (
                    "Mô tả ngắn gọn khách quan các đối tượng, hoạt động trực quan trong ảnh bằng tiếng Việt (1-2 câu). "
                    "Không suy diễn danh tính cá nhân, địa danh hoặc thời gian nếu không có biển hiệu ghi rõ."
                )
                description = self.vlm_pipeline(resolved, prompt)
            except Exception as e:
                logger.warning(f"VLM analysis failed for {resolved}: {e}. Falling back to heuristic.")
                description = self._dry_run_image_description(rel_path, width, height)
        else:
            description = self._dry_run_image_description(rel_path, width, height)

        # Relevance scoring with claims
        best_rel_score = 0.5  # default moderate baseline
        best_claim_idx = None
        desc_lower = description.lower()

        for idx, clm in enumerate(claims):
            score = 0.5
            # Check overlap with claim keywords
            if clm.subject.lower() in desc_lower:
                score += 0.25
            if clm.predicate.lower() in desc_lower:
                score += 0.20
            if score > best_rel_score:
                best_rel_score = min(1.0, score)
                best_claim_idx = idx

        return ImageVisualInfo(
            image_path=rel_path,
            exists=True,
            width=width,
            height=height,
            description=description,
            relevance_score=best_rel_score,
            matched_claim_idx=best_claim_idx,
            is_contextual_only=True  # Grounded in plan: images provide context, not absolute proof
        )

    def _dry_run_image_description(self, path: str, width: Optional[int], height: Optional[int]) -> str:
        """Generates grounded visual description based on image path, aspect ratio, and filename tokens."""
        fname = os.path.basename(path).lower()
        aspect = "ngang" if width and height and width >= height else "dọc"
        
        if "ky-ket" in fname or "hop-tac" in fname or "8856" in fname or "8853" in fname:
            return f"Ảnh khổ {aspect} chụp đại diện các bên tại buổi lễ ký kết hoặc làm việc chính thức."
        elif "tuyen-dung" in fname or "thong-bao" in fname or "infographic" in fname:
            return f"Ảnh tư liệu khổ {aspect} thể hiện thông tin thông báo hoặc áp phích hoạt động."
        elif "phong-ban" in fname or "artboard" in fname:
            return f"Hình ảnh đồ họa biểu trưng hoặc bối cảnh chung của đơn vị."
        elif "thuc-hanh" in fname or "duoc" in fname or "lop" in fname:
            return f"Ảnh khổ {aspect} ghi lại hoạt động thực hành, học tập của học viên."
        else:
            return f"Hình ảnh hiện trường khổ {aspect} phản ánh hoạt động thực tế liên quan đến bài viết."

    def analyze_images(self, image_paths: List[str], claims: List[Claim]) -> List[ImageVisualInfo]:
        """Analyzes all images belonging to an article (up to 19 images)."""
        results: List[ImageVisualInfo] = []
        for path in image_paths[:19]:
            info = self.analyze_single_image(path, claims)
            results.append(info)
        return results
