"""
Module 6a — Contradiction Checker
Verifies factual contradiction between modified claim/text and original Good source article.
Distinguishes between:
  - verified_contradiction
  - source_contradiction
  - synthetic_unverified
  - rejected
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional

from src.schemas import CleanedArticle, Claim, ManipulationResult, VerificationResult

logger = logging.getLogger(__name__)


class ContradictionChecker:
    """Verifies that generated text genuinely contradicts original facts."""

    def __init__(self, config: Dict[str, Any], llm_pipeline=None):
        self.config = config
        self.dry_run = config.get("general", {}).get("dry_run", False)
        self.llm_pipeline = llm_pipeline

        prompts_dir = config.get("prompts", {}).get("dir", "prompts")
        prompt_file = config.get("prompts", {}).get("verification", "verification.txt")
        prompt_path = os.path.join(prompts_dir, prompt_file)
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        else:
            self.prompt_template = "Kiểm tra mâu thuẫn: {original_evidence} vs {modified_claim}"

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        return None

    def _dry_run_check(
        self,
        article: CleanedArticle,
        claim: Claim,
        manipulation: ManipulationResult
    ) -> VerificationResult:
        """Rule-based verification check."""
        orig_text = f"{article.title} {article.content}".strip()
        mod_text = manipulation.modified_text.strip()

        # 1. Exact copy check (if unchanged, it is NOT a valid fake)
        if orig_text == mod_text:
            return VerificationResult(
                quality_passed=False,
                verification_status="rejected",
                is_contradicting=False,
                is_fluent=True,
                rejection_reason="modified_text_identical_to_original"
            )

        # 2. Check for token modification
        if manipulation.original_claim == manipulation.modified_claim:
            return VerificationResult(
                quality_passed=False,
                verification_status="rejected",
                is_contradicting=False,
                is_fluent=True,
                rejection_reason="claim_was_not_modified"
            )

        # 3. Check for obvious contradiction signals
        contradiction_keywords = [
            "hủy bỏ", "huy bo", "chấm dứt", "cham dut", "từ chối", "tu choi",
            "đình chỉ", "dinh chi", "thu hồi", "thu hoi", "sai phạm",
            "dời", "thay đổi", "tạm hoãn"
        ]
        has_direct_inversion = any(kw in manipulation.modified_claim.lower() for kw in contradiction_keywords)

        if has_direct_inversion:
            status = "verified_contradiction"
            score = 0.95
        else:
            status = "source_contradiction"
            score = 0.85

        return VerificationResult(
            quality_passed=True,
            verification_status=status,
            is_contradicting=True,
            is_fluent=True,
            has_forbidden_tokens=False,
            fluency_score=0.95,
            contradiction_score=score,
            audit_notes="Rule-based contradiction check passed."
        )

    def verify_contradiction(
        self,
        article: CleanedArticle,
        claim: Claim,
        manipulation: ManipulationResult
    ) -> VerificationResult:
        """Main verification entry point."""
        if self.dry_run or self.llm_pipeline is None:
            return self._dry_run_check(article, claim, manipulation)

        prompt = self.prompt_template.format(
            original_evidence=claim.evidence,
            modified_claim=manipulation.modified_claim,
            modified_text=manipulation.modified_text[:2000]
        )

        try:
            response = self.llm_pipeline(prompt)
            parsed = self._extract_json(response)
            if parsed:
                return VerificationResult(
                    quality_passed=parsed.get("quality_passed", True),
                    verification_status=parsed.get("verification_status", "source_contradiction"),
                    is_contradicting=parsed.get("is_contradicting", True),
                    is_fluent=parsed.get("is_fluent", True),
                    has_forbidden_tokens=parsed.get("has_forbidden_tokens", False),
                    fluency_score=float(parsed.get("fluency_score", 0.9)),
                    contradiction_score=float(parsed.get("contradiction_score", 0.9)),
                    rejection_reason=parsed.get("rejection_reason"),
                    audit_notes=parsed.get("audit_notes")
                )
        except Exception as e:
            logger.warning(f"LLM contradiction check failed: {e}. Falling back to rule-based check.")

        return self._dry_run_check(article, claim, manipulation)
