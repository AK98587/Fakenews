"""
Comprehensive Unit & Integration Test Suite for the Fake News Generation Pipeline.
Verifies each module independently in dry_run mode on real samples from real_data_annotation.csv.
"""

import os
import sys
import yaml
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.schemas import ArticleInput, CleanedArticle, Claim
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


class TestFakeNewsPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open("configs/config.yaml", "r", encoding="utf-8") as f:
            cls.config = yaml.safe_load(f)
        cls.config["general"]["dry_run"] = True
        cls.config["general"]["resume"] = False

    def test_01_data_loader(self):
        """Tests DataLoader parses CSV, resolves images, and splits by source_id."""
        loader = DataLoader(self.config)
        articles = loader.load_raw_articles(limit=15)
        self.assertGreater(len(articles), 0)

        # Check first article
        art1 = articles[0]
        self.assertTrue(art1.id)
        self.assertIsInstance(art1.image_paths, list)

        # Check anti-leakage split
        splits = loader.split_dataset_by_source_id(articles)
        self.assertIn("train", splits)
        self.assertIn("val", splits)
        self.assertIn("test", splits)
        total_split_items = len(splits["train"]) + len(splits["val"]) + len(splits["test"])
        self.assertEqual(total_split_items, len(articles))

    def test_02_text_cleaner_filtering(self):
        """Tests TextCleaner filters categories while keeping event titles."""
        cleaner = TextCleaner(self.config)

        # 1. Test pure category rejection
        cat_art = ArticleInput(
            id="cat_01",
            title="Hành chính – Quản trị",
            content="Phòng ban... Thông báo bán phế liệu... Thông tin mới Xem tất cả Hệ thống đào tạo",
            image_paths=[]
        )
        res_cat = cleaner.clean_and_filter(cat_art)
        self.assertFalse(res_cat.is_valid)
        self.assertIn(res_cat.filter_reason, ["web_navigation_category", "lacks_verifiable_event_signal"])

        # 2. Test 404 / Nothing Found rejection
        err_art = ArticleInput(
            id="err_01",
            title="Điều dưỡng – Kỹ thuật Y học",
            content="Nothing Found It seems we can't find what you're looking for.",
            image_paths=[]
        )
        res_err = cleaner.clean_and_filter(err_art)
        self.assertFalse(res_err.is_valid)

        # 3. Test genuine news article preservation
        good_art = ArticleInput(
            id="good_01",
            title="BCTech ký kết với FPT Telecom – Học nghề gắn với việc làm",
            content="Ngày 26/01/2026, Trường BCTech đã ký kết Biên bản thỏa thuận hợp tác với FPT Telecom tuyển dụng 150 kỹ thuật viên.",
            image_paths=["real_photo/1787621617_IMG_8856_f.jpg"]
        )
        res_good = cleaner.clean_and_filter(good_art)
        self.assertTrue(res_good.is_valid)
        self.assertIn("FPT Telecom", res_good.content)

    def test_03_claim_extractor(self):
        """Tests extracting structured verifiable claims."""
        extractor = ClaimExtractor(self.config)
        sample = CleanedArticle(
            id="test_01",
            title="BCTech ký kết với FPT Telecom",
            content="Ngày 26/01/2026, Trường Cao đẳng BCTech đã ký kết Biên bản thỏa thuận hợp tác với FPT Telecom để tuyển dụng 100-150 kỹ thuật viên mỗi năm.",
            image_paths=[]
        )
        res = extractor.extract_claims(sample)
        self.assertTrue(res.is_viable)
        self.assertGreater(len(res.claims), 0)
        claim = res.claims[0]
        self.assertTrue(claim.subject)
        self.assertTrue(claim.predicate)
        self.assertTrue(claim.evidence)

    def test_04_image_analyzer_and_selector(self):
        """Tests image analysis and single representative image selection."""
        analyzer = ImageAnalyzer(self.config)
        selector = ImageSelector(self.config)

        claim = Claim(
            subject="BCTech",
            predicate="ký kết hợp tác với",
            object="FPT Telecom",
            evidence="Lễ ký kết diễn ra trang trọng."
        )

        test_images = [
            "real_photo/1787621617_IMG_8856_f.jpg",
            "real_photo/1787621617_IMG_8853_f.jpg"
        ]
        infos = analyzer.analyze_images(test_images, [claim])
        self.assertEqual(len(infos), 2)
        self.assertTrue(infos[0].exists)
        self.assertTrue(infos[0].is_contextual_only)

        selected = selector.select_best_image(infos, claim)
        self.assertIsNotNone(selected)
        self.assertIn("real_photo", selected.image_path)

    def test_05_text_manipulation_g1_to_g4(self):
        """Tests G1, G2, G3, G4 text generation."""
        generator = TextGenerator(self.config)
        sample = CleanedArticle(
            id="test_01",
            title="BCTech ký kết với FPT Telecom",
            content="Ngày 26/01/2026, Trường BCTech đã ký kết Biên bản thỏa thuận hợp tác với FPT Telecom tuyển dụng 100-150 kỹ thuật viên.",
            image_paths=[]
        )
        claim = Claim(
            subject="BCTech",
            predicate="đã ký kết Biên bản thỏa thuận hợp tác với",
            object="FPT Telecom",
            time="26/01/2026",
            quantity="100-150 kỹ thuật viên",
            evidence="Ngày 26/01/2026, Trường BCTech đã ký kết Biên bản thỏa thuận hợp tác với FPT Telecom"
        )

        # Test G1 (Numerical)
        g1 = generator.generate_manipulation("G1", sample, claim)
        self.assertEqual(g1.manipulation_type, "G1")
        self.assertNotEqual(g1.original_claim, g1.modified_claim)

        # Test G2 (Entity)
        g2 = generator.generate_manipulation("G2", sample, claim)
        self.assertEqual(g2.manipulation_type, "G2")
        self.assertIn("VNPT", g2.modified_text + g2.modified_claim)

        # Test G3 (Event Outcome Inversion)
        g3 = generator.generate_manipulation("G3", sample, claim)
        self.assertEqual(g3.manipulation_type, "G3")
        self.assertIn("hủy bỏ", g3.modified_text.lower())

        # Test G4 (Multi-claim)
        g4 = generator.generate_manipulation("G4", sample, claim, [claim])
        self.assertEqual(g4.manipulation_type, "G4")
        self.assertTrue(len(g4.modified_text) > 20)

    def test_06_contradiction_and_quality_filter(self):
        """Tests verification and quality gate checks."""
        generator = TextGenerator(self.config)
        checker = ContradictionChecker(self.config)
        qfilter = QualityFilter(self.config)

        sample = CleanedArticle(
            id="test_01",
            title="BCTech ký kết với FPT Telecom",
            content="Trường BCTech đã ký kết hợp tác với FPT Telecom.",
            image_paths=[]
        )
        claim = Claim(
            subject="BCTech",
            predicate="đã ký kết hợp tác với",
            object="FPT Telecom",
            evidence="Trường BCTech đã ký kết hợp tác với FPT Telecom."
        )

        # Valid Fake
        g3 = generator.generate_manipulation("G3", sample, claim)
        verif = checker.verify_contradiction(sample, claim, g3)
        self.assertTrue(verif.quality_passed)
        self.assertIn(verif.verification_status, ["verified_contradiction", "source_contradiction"])

        passed, reason = qfilter.filter_sample(g3, None, verif)
        self.assertTrue(passed)
        self.assertIsNone(reason)

        # Invalid Fake with forbidden token
        g3_bad = generator.generate_manipulation("G3", sample, claim)
        g3_bad.modified_text += " Đây là tin giả nhằm thử nghiệm."
        passed_bad, reason_bad = qfilter.filter_sample(g3_bad, None, verif)
        self.assertFalse(passed_bad)
        self.assertIn("contains_forbidden_phrase", reason_bad)

    def test_07_full_pipeline_run_5_samples(self):
        """Runs the entire pipeline end-to-end on Good articles."""
        pipeline = FakeNewsPipeline(self.config)
        summary = pipeline.run(limit=15)
        self.assertGreater(summary["total_samples"], 0)
        self.assertGreater(summary["real_samples"], 0)
        self.assertGreater(summary["fake_samples"], 0)
        self.assertIn("train", summary["splits"])


if __name__ == "__main__":
    unittest.main()
