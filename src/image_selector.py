"""
Module 4b — Image Selector
Selects exactly one representative original image for each generated output sample (both Real and Fake),
prioritizing the image with the highest relevance to the claim being manipulated.
Never edits or modifies the original image files.
"""

import logging
from typing import List, Optional

from src.schemas import ImageVisualInfo, Claim

logger = logging.getLogger(__name__)


class ImageSelector:
    """Selects one representative image from 1-19 candidate images for an article."""

    def __init__(self, config=None):
        self.config = config or {}

    def select_best_image(
        self,
        image_infos: List[ImageVisualInfo],
        target_claim: Optional[Claim] = None,
        target_claim_idx: Optional[int] = None
    ) -> Optional[ImageVisualInfo]:
        """
        Picks the best single image from the list of analyzed images.
        Prioritizes existing images that best match the target claim.
        """
        if not image_infos:
            return None

        # Filter to only existing images on disk
        existing_images = [img for img in image_infos if img.exists]
        candidates = existing_images if existing_images else image_infos

        if not candidates:
            return None

        # 1. Look for image specifically matched with target_claim_idx
        if target_claim_idx is not None:
            for img in candidates:
                if img.matched_claim_idx == target_claim_idx:
                    return img

        # 2. Look for highest relevance score
        sorted_candidates = sorted(candidates, key=lambda x: x.relevance_score, reverse=True)
        return sorted_candidates[0]
