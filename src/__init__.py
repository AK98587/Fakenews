"""
Synthetic Multimodal Fake News Generation Package.
"""

from src.schemas import (
    ArticleInput,
    CleanedArticle,
    Claim,
    ImageVisualInfo,
    ManipulationResult,
    VerificationResult,
    ExportSample,
    FakeSampleMetadata,
    RealSampleMetadata,
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
from src.pipeline import FakeNewsPipeline

__all__ = [
    "ArticleInput",
    "CleanedArticle",
    "Claim",
    "ImageVisualInfo",
    "ManipulationResult",
    "VerificationResult",
    "ExportSample",
    "FakeSampleMetadata",
    "RealSampleMetadata",
    "DataLoader",
    "TextCleaner",
    "ClaimExtractor",
    "ImageAnalyzer",
    "ImageSelector",
    "TextGenerator",
    "ContradictionChecker",
    "QualityFilter",
    "DatasetExporter",
    "FakeNewsPipeline",
]
