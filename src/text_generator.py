"""
Module 5 — Controlled Text Manipulation
Generates synthetic fake variants using four controlled manipulation groups:
  - G1: Numerical & Temporal Manipulation
  - G2: Entity & Relation Manipulation
  - G3: Event & Outcome Manipulation
  - G4: Multi-claim Manipulation
Adheres to strict constraints: Vietnamese journalistic tone, no meta-text, no hallucinated additions.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional

from src.schemas import CleanedArticle, Claim, ManipulationResult

logger = logging.getLogger(__name__)


class TextGenerator:
    """Orchestrates controlled text manipulation across G1, G2, G3, G4."""

    def __init__(self, config: Dict[str, Any], llm_pipeline=None):
        self.config = config
        self.dry_run = config.get("general", {}).get("dry_run", False)
        self.retry_count = config.get("models", {}).get("llm", {}).get("retry_count", 3)
        self.llm_pipeline = llm_pipeline

        # Load prompts
        prompts_dir = config.get("prompts", {}).get("dir", "prompts")
        self.prompts = {
            "G1": self._load_prompt(os.path.join(prompts_dir, config.get("prompts", {}).get("g1_numerical", "g1_numerical.txt"))),
            "G2": self._load_prompt(os.path.join(prompts_dir, config.get("prompts", {}).get("g2_relation", "g2_relation.txt"))),
            "G3": self._load_prompt(os.path.join(prompts_dir, config.get("prompts", {}).get("g3_event", "g3_event.txt"))),
            "G4": self._load_prompt(os.path.join(prompts_dir, config.get("prompts", {}).get("g4_multiclaim", "g4_multiclaim.txt"))),
        }

    def _load_prompt(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return "Tạo biến thể {manipulation_type}: {title} {content}"

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

    def _clean_forbidden_patterns(self, text: str) -> str:
        """Removes accidental leaks of forbidden phrases and entity duplication artifacts."""
        forbidden = [
            r"đây là tin giả[:,\.]?",
            r"đây là thông tin sai lệch[:,\.]?",
            r"tin tức giả mạo[:,\.]?",
            r"nội dung được tạo bởi ai[:,\.]?",
            r"lưu ý:\s*nội dung trên.*?(?=(\n|$))",
        ]
        cleaned = text
        for pat in forbidden:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # Clean duplicate organization prefixes caused by entity replacements
        cleaned = re.sub(r"(?:Trường\s+)?(?:Cao\s+đẳng|Đại\s+học)\s+Trường\s+Đại\s+học", "Trường Đại học", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"(?:Trường\s+)?Cao\s+đẳng\s+Đại\s+học", "Trường Đại học", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Trường\s+Trường\s+Đại\s+học", "Trường Đại học", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    # =========================================================================
    # DRY RUN / HEURISTIC MANIPULATION METHODS
    # =========================================================================

    def _dry_run_g1(self, article: CleanedArticle, claim: Claim) -> ManipulationResult:
        """Alters numbers, percentages, or dates."""
        text = article.content if len(article.content.split()) > 10 else article.title
        orig_claim = claim.to_summary_text()

        # Modify quantities or dates
        modified_text = text
        mod_claim = orig_claim
        change_summary = ""

        if claim.time and ("2026" in claim.time or "2024" in claim.time or "2025" in claim.time):
            mod_time = "2020" if "2026" in claim.time else "2019"
            modified_text = re.sub(r"\b202[456]\b", mod_time, modified_text)
            mod_claim = orig_claim.replace(claim.time, mod_time)
            change_summary = f"Đổi thời gian từ {claim.time} thành {mod_time} (không vượt quá năm 2026)"
        elif claim.quantity:
            mod_qty = "1.500 chỉ tiêu" if "100" in claim.quantity else "05 chỉ tiêu"
            modified_text = modified_text.replace(claim.quantity, mod_qty)
            mod_claim = orig_claim.replace(claim.quantity, mod_qty)
            change_summary = f"Đổi số liệu từ {claim.quantity} thành {mod_qty}"
        else:
            # Fallback date shift (never exceed 2026)
            modified_text = re.sub(r"\b(202\d)\b", "2018", modified_text)
            mod_claim = orig_claim + " (dời mốc sự kiện về năm 2018)"
            change_summary = "Đổi các mốc năm về năm 2018"

        # If original was a short headline, keep headline length
        mod_title = None
        if len(article.title.split()) > 3:
            mod_title = re.sub(r"\b202[456]\b", "2020", article.title)

        return ManipulationResult(
            manipulation_type="G1",
            original_claim=orig_claim,
            modified_claim=mod_claim,
            modified_title=mod_title,
            modified_text=self._clean_forbidden_patterns(modified_text),
            change_summary=change_summary
        )

    def _dry_run_g2(self, article: CleanedArticle, claim: Claim) -> ManipulationResult:
        """Alters entities, partners, or organizational roles."""
        text = article.content if len(article.content.split()) > 10 else article.title
        orig_claim = claim.to_summary_text()

        entity_replacements = [
            ("Trường Cao đẳng Kỹ thuật Công nghệ Bà Rịa – Vũng Tàu (BCTech)", "Trường Đại học Bách Khoa TP.HCM"),
            ("Trường Cao đẳng Kỹ thuật Công nghệ Bà Rịa - Vũng Tàu", "Trường Đại học Bách Khoa TP.HCM"),
            ("Trường Cao đẳng BCTech", "Trường Đại học Bách Khoa TP.HCM"),
            ("Cao đẳng BCTech", "Trường Đại học Bách Khoa TP.HCM"),
            ("FPT Telecom", "Tập đoàn Bưu chính Viễn thông VNPT"),
            ("BCTech", "Trường Đại học Bách Khoa TP.HCM"),
            ("Công đoàn Ngành Y tế", "Hiệp hội Doanh nghiệp Độc lập"),
            ("Bộ GD-ĐT", "Sở Giao thông Vận tải"),
            ("Bộ GD&ĐT", "Sở Giao thông Vận tải"),
            ("Công ty Cổ phần", "Tổ chức phi chính phủ quốc tế"),
        ]

        modified_text = text
        mod_claim = orig_claim
        change_summary = ""

        for src_ent, tgt_ent in entity_replacements:
            if src_ent.lower() in modified_text.lower():
                modified_text = re.sub(re.escape(src_ent), tgt_ent, modified_text, flags=re.IGNORECASE)
                mod_claim = re.sub(re.escape(src_ent), tgt_ent, mod_claim, flags=re.IGNORECASE)
                change_summary = f"Thay đổi thực thể/đối tác từ '{src_ent}' thành '{tgt_ent}'"
                break

        if not change_summary:
            # Generic entity replacement
            modified_text = modified_text.replace("Trường", "Tập đoàn Đầu tư")
            mod_claim = "Tập đoàn Đầu tư thực hiện liên kết thay cho đơn vị giáo dục"
            change_summary = "Thay thế vai trò đơn vị bằng Tập đoàn Đầu tư"

        # Sanitize entity prefix collisions in mod_claim and text
        mod_claim = self._clean_forbidden_patterns(mod_claim)
        modified_text = self._clean_forbidden_patterns(modified_text)

        mod_title = None
        if len(article.title.split()) > 3:
            mod_title = article.title
            for src_ent, tgt_ent in entity_replacements:
                if src_ent.lower() in mod_title.lower():
                    mod_title = re.sub(re.escape(src_ent), tgt_ent, mod_title, flags=re.IGNORECASE)
            if mod_title:
                mod_title = self._clean_forbidden_patterns(mod_title)

        return ManipulationResult(
            manipulation_type="G2",
            original_claim=orig_claim,
            modified_claim=mod_claim,
            modified_title=mod_title,
            modified_text=modified_text,
            change_summary=change_summary
        )

    def _dry_run_g3(self, article: CleanedArticle, claim: Claim) -> ManipulationResult:
        """Alters event status, outcome, decisions (inverts fact)."""
        text = article.content if len(article.content.split()) > 10 else article.title
        orig_claim = claim.to_summary_text()

        outcome_inversions = [
            ("ký kết", "tuyên bố hủy bỏ kế hoạch ký kết và chấm dứt hợp tác"),
            ("công nhận", "bị từ chối công nhận và buộc đình chỉ"),
            ("tuyển sinh", "thông báo dừng toàn bộ hoạt động tuyển sinh"),
            ("bàn giao", "tạm hoãn vô thời hạn lễ bàn giao"),
            ("tổ chức", "quyết định hủy bỏ sự kiện"),
            ("tiếp nhận", "từ chối tiếp nhận"),
        ]

        modified_text = text
        mod_claim = orig_claim
        change_summary = ""

        for src_act, tgt_act in outcome_inversions:
            if src_act in modified_text.lower():
                # Replace the first occurrence with inverted outcome
                modified_text = re.sub(re.escape(src_act), tgt_act, modified_text, count=2, flags=re.IGNORECASE)
                mod_claim = mod_claim.replace(src_act, tgt_act)
                change_summary = f"Đảo ngược kết quả sự kiện: '{src_act}' -> '{tgt_act}'"
                break

        if not change_summary:
            modified_text = f"Sự việc đã bị đình chỉ: {modified_text}"
            mod_claim = f"Bị đình chỉ: {orig_claim}"
            change_summary = "Đảo ngược trạng thái thực hiện sang bị đình chỉ"

        mod_title = None
        if len(article.title.split()) > 3:
            mod_title = article.title
            for src_act, tgt_act in outcome_inversions:
                if src_act in mod_title.lower():
                    mod_title = re.sub(re.escape(src_act), tgt_act, mod_title, count=1, flags=re.IGNORECASE)
                    break

        return ManipulationResult(
            manipulation_type="G3",
            original_claim=orig_claim,
            modified_claim=mod_claim,
            modified_title=mod_title,
            modified_text=self._clean_forbidden_patterns(modified_text),
            change_summary=change_summary
        )

    def _dry_run_g4(self, article: CleanedArticle, claims: List[Claim]) -> ManipulationResult:
        """
        Multi-attribute manipulation (G4):
        Alters multiple attributes (Entity and Time/Quantity) on the primary claim
        within the article, producing a SINGLE, unified modified claim and consistent fake text.
        """
        primary_claim = claims[0]

        # 1. Apply Entity change
        res_g2 = self._dry_run_g2(article, primary_claim)

        # 2. On the article modified with new entity, apply Numerical/Temporal change
        temp_art = CleanedArticle(
            id=article.id,
            title=res_g2.modified_title or article.title,
            content=res_g2.modified_text,
            image_paths=article.image_paths,
            num_images=article.num_images
        )
        res_g1 = self._dry_run_g1(temp_art, primary_claim)

        # 3. Build ONE unified modified claim that incorporates BOTH changes
        unified_mod_claim = res_g2.modified_claim

        if primary_claim.time and ("2026" in primary_claim.time or "2024" in primary_claim.time or "2025" in primary_claim.time):
            mod_time = "2020" if "2026" in primary_claim.time else "2019"
            unified_mod_claim = unified_mod_claim.replace(primary_claim.time, mod_time)
        elif primary_claim.quantity:
            mod_qty = "1.500 chỉ tiêu" if "100" in primary_claim.quantity else "05 chỉ tiêu"
            unified_mod_claim = unified_mod_claim.replace(primary_claim.quantity, mod_qty)
        else:
            unified_mod_claim = re.sub(r"\b202[456]\b", "2020", unified_mod_claim)

        # Clean any accidental double prefix in claim
        unified_mod_claim = self._clean_forbidden_patterns(unified_mod_claim)

        return ManipulationResult(
            manipulation_type="G4",
            original_claim=primary_claim.to_summary_text(),
            modified_claim=unified_mod_claim,
            modified_title=res_g1.modified_title or res_g2.modified_title,
            modified_text=self._clean_forbidden_patterns(res_g1.modified_text),
            change_summary=f"G4 - Đa thuộc tính: {res_g2.change_summary}; {res_g1.change_summary}"
        )

    # =========================================================================
    # LLM INFERENCE METHOD
    # =========================================================================

    def _generate_with_llm(
        self,
        group: str,
        article: CleanedArticle,
        claim: Claim,
        all_claims: Optional[List[Claim]] = None
    ) -> ManipulationResult:
        prompt_tmpl = self.prompts.get(group, "")

        if group == "G1":
            prompt = prompt_tmpl.format(
                title=article.title,
                content=article.content[:2500],
                original_claim=claim.to_summary_text(),
                evidence=claim.evidence,
                target_quantity_or_time=f"{claim.quantity or ''} {claim.time or ''}".strip() or "Các con số/năm trong bài"
            )
        elif group == "G2":
            prompt = prompt_tmpl.format(
                title=article.title,
                content=article.content[:2500],
                target_entity=f"{claim.subject} / {claim.object}",
                original_claim=claim.to_summary_text(),
                evidence=claim.evidence
            )
        elif group == "G3":
            prompt = prompt_tmpl.format(
                title=article.title,
                content=article.content[:2500],
                original_claim=claim.to_summary_text(),
                target_outcome_or_action=f"{claim.predicate} -> {claim.outcome or ''}",
                evidence=claim.evidence
            )
        elif group == "G4":
            attrs_desc = f"1. Thực thể liên quan: {claim.subject} / {claim.object}\n2. Mốc thời gian/số lượng: {claim.time or '2026'} / {claim.quantity or 'số liệu'}"
            if "{content}" in prompt_tmpl and "{selected_claims_formatted}" in prompt_tmpl:
                prompt = prompt_tmpl.format(
                    title=article.title,
                    content=article.content[:2500],
                    original_claim=claim.to_summary_text(),
                    evidence=claim.evidence,
                    selected_claims_formatted=attrs_desc
                )
            else:
                prompt = (
                    f"{prompt_tmpl}\n\n"
                    f"---\n"
                    f"BÀI BÁO GỐC (GOOD TEXT):\n"
                    f"Tiêu đề: {article.title}\n"
                    f"Nội dung: {article.content[:2500]}\n\n"
                    f"PHÁT BIỂU MỤC TIÊU CẦN BIẾN ĐỔI ĐỒNG THỜI:\n"
                    f"- Phát biểu gốc: {claim.to_summary_text()}\n"
                    f"- Bằng chứng gốc: {claim.evidence}\n"
                    f"- Các thuộc tính cần biến đổi:\n{attrs_desc}\n"
                )
        else:
            prompt = f"Biến đổi nội dung theo {group}: {article.title} {article.content[:1500]}"

        for attempt in range(self.retry_count):
            try:
                response = self.llm_pipeline(prompt)
                parsed = self._extract_json(response)
                if parsed and ("modified_text" in parsed or "text" in parsed):
                    mod_text = self._clean_forbidden_patterns(parsed.get("modified_text") or parsed.get("text", ""))
                    orig_len = len(article.content.split())
                    mod_len = len(mod_text.split())
                    if orig_len < 20 and mod_len > 60:
                        mod_text = parsed.get("modified_title", mod_text[:150])

                    # Extract changes list or single modified_claim
                    if parsed.get("modified_claim"):
                        mod_claim = self._clean_forbidden_patterns(parsed.get("modified_claim"))
                    elif parsed.get("changes"):
                        changes = parsed.get("changes")
                        mod_claim = "; ".join([f"{c.get('attribute', 'thuộc tính')}: {c.get('original')} -> {c.get('replacement')}" for c in changes])
                    else:
                        mod_claim = ""
                    change_sum = parsed.get("change_summary", f"Sinh thành công nhóm {group}")

                    return ManipulationResult(
                        manipulation_type=group,
                        original_claim=parsed.get("original_claim", claim.to_summary_text()),
                        modified_claim=mod_claim,
                        modified_title=parsed.get("modified_title", article.title),
                        modified_text=mod_text,
                        change_summary=change_sum
                    )
            except Exception as e:
                logger.warning(f"LLM generation failed for {group} attempt {attempt+1}: {e}")

        # Fallback to dry run heuristic if LLM failed
        logger.warning(f"Falling back to dry-run heuristic for group {group}.")
        if group == "G1":
            return self._dry_run_g1(article, claim)
        elif group == "G2":
            return self._dry_run_g2(article, claim)
        elif group == "G3":
            return self._dry_run_g3(article, claim)
        else:
            return self._dry_run_g4(article, all_claims or [claim])

    def generate_manipulation(
        self,
        group: str,
        article: CleanedArticle,
        claim: Claim,
        all_claims: Optional[List[Claim]] = None
    ) -> ManipulationResult:
        """Main entry point to generate a synthetic fake variant under group G1/G2/G3/G4."""
        if self.dry_run or self.llm_pipeline is None:
            if group == "G1":
                return self._dry_run_g1(article, claim)
            elif group == "G2":
                return self._dry_run_g2(article, claim)
            elif group == "G3":
                return self._dry_run_g3(article, claim)
            elif group == "G4":
                return self._dry_run_g4(article, all_claims or [claim])
            else:
                return self._dry_run_g3(article, claim)

        return self._generate_with_llm(group, article, claim, all_claims)
