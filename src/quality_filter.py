"""
Module 6b — Quality Filter
Performs quality gate checks:
  1. Text fluency and repetition loop detection
  2. Forbidden token detection ('đây là tin giả', JSON/markdown leaks)
  3. Image-text relevance threshold
  4. Duplicate detection across generated samples
"""

import re
import hashlib
import logging
from typing import Set, Tuple, Dict, Any, Optional

from src.schemas import ManipulationResult, ImageVisualInfo, VerificationResult

logger = logging.getLogger(__name__)

FORBIDDEN_PHRASES = [
    "đây là tin giả",
    "đây là thông tin sai lệch",
    "tin tức giả mạo",
    "nội dung được tạo bởi ai",
    "bản dịch tự động",
    "lưu ý: nội dung",
    "```json",
    "```",
]


class QualityFilter:
    """Quality filter and deduplication gate."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.verif_cfg = config.get("verification", {})
        self.min_relevance = self.verif_cfg.get("clip_relevance_threshold", 0.20)
        self.seen_fake_hashes: Set[str] = set()

    def _has_forbidden_tokens(self, text: str) -> Tuple[bool, Optional[str]]:
        lower_text = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lower_text:
                return True, f"contains_forbidden_phrase: '{phrase}'"
        return False, None

    def _has_repetition_loops(self, text: str) -> Tuple[bool, Optional[str]]:
        """Detects LLM degeneration loop (e.g. repeated sentences or severe n-gram loops)."""
        words = text.split()
        if len(words) < 20:
            return False, None

        # Check consecutive identical sentences
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if len(s.strip()) > 15]
        for i in range(len(sentences) - 1):
            if sentences[i].lower() == sentences[i + 1].lower():
                return True, f"consecutive_identical_sentences: '{sentences[i][:40]}...'"

        # Severe n-gram repetition loop (> 7 times or > 8% of total tokens)
        ngram_size = 5
        seen_ngrams = {}
        max_repeats = max(7, int(len(words) * 0.08))
        for i in range(len(words) - ngram_size + 1):
            ngram = " ".join(words[i:i + ngram_size]).lower()
            seen_ngrams[ngram] = seen_ngrams.get(ngram, 0) + 1
            if seen_ngrams[ngram] > max_repeats:
                return True, f"repetition_loop_detected: '{ngram}' ({seen_ngrams[ngram]} times)"
        return False, None

    def filter_sample(
        self,
        manipulation: ManipulationResult,
        image_info: Optional[ImageVisualInfo],
        verification: VerificationResult
    ) -> Tuple[bool, Optional[str]]:
        """
        Runs quality gate on a candidate fake sample.
        Returns (passed, rejection_reason).
        """
        # 1. Verification status check
        if not verification.quality_passed or verification.verification_status == "rejected":
            return False, verification.rejection_reason or "failed_contradiction_verification"

        text = manipulation.modified_text.strip()

        # 2. Minimum length check
        if len(text.split()) < 5:
            return False, "text_too_short"

        # 3. Forbidden tokens
        has_forbidden, forbidden_reason = self._has_forbidden_tokens(text)
        if has_forbidden:
            return False, forbidden_reason

        # 4. Repetition loop check
        has_loop, loop_reason = self._has_repetition_loops(text)
        if has_loop:
            return False, loop_reason

        # 5. Image relevance check (only if valid image exists)
        if image_info and image_info.exists and image_info.relevance_score < self.min_relevance:
            return False, f"image_text_relevance_too_low: {image_info.relevance_score:.2f} < {self.min_relevance}"

        # 6. Deduplication check
        norm_text = re.sub(r"\s+", " ", text.lower().strip())
        text_hash = hashlib.md5(norm_text.encode("utf-8")).hexdigest()
        if text_hash in self.seen_fake_hashes:
            return False, "duplicate_fake_sample_detected"
        self.seen_fake_hashes.add(text_hash)

        return True, None
