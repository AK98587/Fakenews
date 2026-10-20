"""
Data Schemas and Pydantic Models for the Synthetic Multimodal Fake News Pipeline.
Conforms to specifications in doc/plan.md.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class ArticleInput(BaseModel):
    """Raw article loaded from source dataset."""
    id: str
    title: str = ""
    content: str = ""
    image_paths: List[str] = Field(default_factory=list)
    num_images: int = 0
    source_url: Optional[str] = None
    source_file: Optional[str] = None
    is_duplicate: int = 0
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class CleanedArticle(BaseModel):
    """Article after passing text cleaning & heuristic filtering."""
    id: str
    title: str
    content: str
    image_paths: List[str] = Field(default_factory=list)
    num_images: int = 0
    source_url: Optional[str] = None
    is_valid: bool = True
    filter_reason: Optional[str] = None
    char_count: int = 0
    word_count: int = 0


class Claim(BaseModel):
    """A verifiable factual claim extracted from a Good news article."""
    subject: str = Field(description="Chủ thể chính của phát biểu")
    predicate: str = Field(description="Hành động, quan hệ, hoặc vị ngữ")
    object: str = Field(description="Đối tượng hoặc nội dung chịu tác động")
    time: Optional[str] = Field(default=None, description="Thời gian diễn ra sự kiện")
    location: Optional[str] = Field(default=None, description="Địa điểm")
    quantity: Optional[str] = Field(default=None, description="Số liệu, tỷ lệ, giá trị tài chính")
    outcome: Optional[str] = Field(default=None, description="Kết quả hoặc tác động")
    evidence: str = Field(description="Đoạn văn bản gốc chính xác làm bằng chứng")

    def to_summary_text(self) -> str:
        parts = [f"{self.subject} {self.predicate} {self.object}"]
        if self.time:
            parts.append(f"vào thời gian {self.time}")
        if self.location:
            parts.append(f"tại {self.location}")
        if self.quantity:
            parts.append(f"với số lượng/giá trị {self.quantity}")
        if self.outcome:
            parts.append(f"kết quả: {self.outcome}")
        return ", ".join(parts)


class ClaimExtractionResult(BaseModel):
    """Extraction output from ClaimExtractor."""
    article_id: str
    is_viable: bool
    claims: List[Claim] = Field(default_factory=list)
    rejection_reason: Optional[str] = None


class ImageVisualInfo(BaseModel):
    """Visual content analysis of an image."""
    image_path: str
    exists: bool = True
    width: Optional[int] = None
    height: Optional[int] = None
    description: str = Field(default="", description="Visual description without hallucinating non-visible entities")
    relevance_score: float = Field(default=0.0, description="Semantic or keyword match to article content")
    matched_claim_idx: Optional[int] = None
    is_contextual_only: bool = Field(default=True, description="True if image only provides context rather than proof")


class ManipulationResult(BaseModel):
    """Output from text generator module."""
    manipulation_type: Literal["G1", "G2", "G3", "G4"]
    original_claim: str
    modified_claim: str
    modified_title: Optional[str] = None
    modified_text: str
    change_summary: str = ""


class VerificationResult(BaseModel):
    """Output from verification and quality control."""
    quality_passed: bool
    verification_status: Literal["verified_contradiction", "source_contradiction", "synthetic_unverified", "rejected"]
    is_contradicting: bool = True
    is_fluent: bool = True
    has_forbidden_tokens: bool = False
    fluency_score: float = 1.0
    contradiction_score: float = 1.0
    image_text_relevance: float = 1.0
    rejection_reason: Optional[str] = None
    audit_notes: Optional[str] = None


class FakeSampleMetadata(BaseModel):
    """Metadata required by Section 9 of doc/plan.md."""
    generation_model: str = "Qwen2.5-7B-Instruct"
    generation_method: str = "controlled_manipulation"
    manipulation_type: str = "G3"
    original_claim: str
    modified_claim: str
    verification_status: str = "source_contradiction"
    image_original: bool = True
    quality_passed: bool = True
    change_summary: Optional[str] = None
    image_description: Optional[str] = None
    image_contextual_only: bool = True
    split: Optional[str] = None


class RealSampleMetadata(BaseModel):
    """Metadata for Real (Good) samples retained in the final dataset."""
    generation_model: str = "original_source"
    generation_method: str = "unaltered"
    manipulation_type: str = "none"
    original_claim: str = ""
    modified_claim: str = ""
    verification_status: str = "source_fact"
    image_original: bool = True
    quality_passed: bool = True
    split: Optional[str] = None


class ExportSample(BaseModel):
    """Final JSON format conforming exactly to Section 9 of doc/plan.md."""
    id: str
    source_id: str
    image_path: str
    text: str
    label: int = Field(description="0 for Real, 1 for Fake")
    metadata: Dict[str, Any]
