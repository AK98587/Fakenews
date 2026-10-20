"""
Module 2 — Text Cleaning & Filtering
Removes website categories, empty/error pages, HTML noise, boilerplate, and duplicates.
Specifically preserves short event-bearing headlines (e.g. 'BCTech ký kết với FPT Telecom')
while rejecting pure navigation categories (e.g. 'Hành chính – Quản trị').
"""

import os
import re
import html
import hashlib
import logging
from typing import List, Set, Tuple, Dict, Any

from src.schemas import ArticleInput, CleanedArticle

logger = logging.getLogger(__name__)

# Common Vietnamese action verbs and event indicators in news headlines
EVENT_ACTION_VERBS = [
    "ký kết", "ky ket", "tổ chức", "to chuc", "tuyển sinh", "tuyen sinh",
    "tuyển dụng", "tuyen dung", "khai mạc", "khai mac", "bế mạc", "be mac",
    "công nhận", "cong nhan", "bổ nhiệm", "bo nhiem", "phát động", "phat dong",
    "thông báo", "thong bao", "tập huấn", "tap huan", "đạt giải", "dat giai",
    "ra mắt", "ra mat", "hợp tác", "hop tac", "chúc mừng", "chuc mung",
    "trao tặng", "trao tang", "hội thảo", "hoi thao", "hội nghị", "hoi nghi",
    "tiếp nhận", "tiep nhan", "bàn giao", "ban giao", "phê duyệt", "phe duyet",
    "chiêu sinh", "chieu sinh", "khởi công", "khanh thanh", "khánh thành",
    "ban hành", "triển khai", "đánh giá", "kiểm tra", "thanh tra", "hội nhập",
    "khen thưởng", "tuyên dương", "hưởng ứng", "tọa đàm"
]

# Patterns representing pure categories, system error pages or navigation
NAVIGATION_CATEGORY_KEYWORDS = [
    "nothing found", "không tìm thấy", "404 not found",
    "phòng ban", "chuyên mục", "trang chủ", "sơ đồ trang",
    "hành chính – quản trị", "hành chính - quản trị", "hành chính",
    "khảo thí – kiểm định chất lượng", "khảo thí - kiểm định chất lượng", "khảo thí",
    "điều dưỡng – kỹ thuật y học", "điều dưỡng - kỹ thuật y học", "điều dưỡng",
    "công tác học sinh, sinh viên", "công tác học sinh",
    "danh mục website", "chưa có bài viết", "hệ thống đào tạo"
]

# Boilerplate patterns to remove from text body
BOILERPLATE_REGEXES = [
    r"Chia sẻ lên mạng xã hội.*?(?=(\n|$))",
    r"BÀI VIẾT LIÊN QUAN.*?(?=(\n|$))",
    r"Xem tất cả Hệ thống đào tạo.*?(?=(\n|$))",
    r"Thông tin mới\s+Thông báo.*?(?=(\n|$))",
    r"File đính kèm:\s*download.*?(?=(\n|$))",
    r"Đính kèm:\s*Download.*?(?=(\n|$))",
    r"http[s]?://\S+",
]


class TextCleaner:
    """Cleans and filters news articles according to Section 4 of doc/plan.md."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clean_cfg = config.get("cleaning", {})
        self.min_chars = self.clean_cfg.get("min_content_length", 30)
        self.min_words = self.clean_cfg.get("min_words", 6)
        self.skip_duplicates = self.clean_cfg.get("skip_duplicates", True)
        self.filter_categories = self.clean_cfg.get("filter_web_categories", True)
        self.preserve_event_titles = self.clean_cfg.get("preserve_event_titles", True)
        self.seen_content_hashes: Set[str] = set()

    def clean_text(self, text: str) -> str:
        """Strips HTML, removes boilerplate patterns, normalizes spaces."""
        if not text:
            return ""

        # Unescape HTML entities & strip tags
        text = html.unescape(text)
        text = re.sub(r"<[^>]+>", " ", text)

        # Remove known boilerplate lines
        for bp in BOILERPLATE_REGEXES:
            text = re.sub(bp, " ", text, flags=re.IGNORECASE)

        # Normalize whitespace and redundant punctuation
        text = re.sub(r"[\r\t]+", " ", text)
        text = re.sub(r"\s*\.\.\.\s*", "... ", text)
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        return text.strip()

    def has_verifiable_event_signal(self, title: str, text: str) -> bool:
        """
        Determines whether the text or title expresses a verifiable news event
        (subject + action + event) rather than a static website section.
        """
        combined = f"{title} {text}".lower()

        # Check for error indicators
        if "nothing found" in combined or "it seems we can" in combined:
            return False

        # Check if title or text has at least one event action verb
        has_action = any(verb in combined for verb in EVENT_ACTION_VERBS)

        # Check if numbers or dates are present (strong signal of news event)
        has_dates_or_numbers = bool(re.search(r"\b\d{1,4}[/-]\d{1,2}[/-]\d{2,4}\b|\b(năm|tháng|ngày)\s+\d{2,4}\b|\b\d{2,}\b", combined))

        return has_action or has_dates_or_numbers

    def is_navigation_category(self, title: str, content: str) -> bool:
        """Detects if title/content is merely a website directory listing or department banner."""
        title_clean = title.strip().lower()
        
        # Immediate match for known category keywords
        for kw in NAVIGATION_CATEGORY_KEYWORDS:
            if title_clean == kw or title_clean.startswith(kw) or kw in title_clean:
                # If title contains an explicit event verb (e.g. 'BCTech tổ chức...'), it is an event
                has_verb = any(v in title_clean for v in EVENT_ACTION_VERBS)
                if not has_verb:
                    return True

        # Check department patterns: "Phòng...", "Ban...", "Khoa..." without action verbs
        if re.match(r"^(phòng|ban|khoa|bộ môn|trung tâm|tổ)\s+", title_clean) and not any(v in title_clean for v in EVENT_ACTION_VERBS):
            return True

        return False

    def clean_and_filter(self, article: ArticleInput) -> CleanedArticle:
        """Cleans and evaluates an individual article."""
        # 1. Check duplicate flag from dataset
        if self.skip_duplicates and article.is_duplicate == 1:
            return CleanedArticle(
                id=article.id,
                title=article.title,
                content=article.content,
                image_paths=article.image_paths,
                num_images=article.num_images,
                source_url=article.source_url,
                is_valid=False,
                filter_reason="marked_as_duplicate_in_source"
            )

        cleaned_title = self.clean_text(article.title)
        cleaned_content = self.clean_text(article.content)

        # Effective text combines title and content
        combined_text = f"{cleaned_title}. {cleaned_content}".strip()
        words = combined_text.split()
        char_count = len(combined_text)
        word_count = len(words)

        # 2. Check for empty or too short
        if char_count < self.min_chars or word_count < self.min_words:
            # Special case: check if title alone is a strong event title
            if self.preserve_event_titles and self.has_verifiable_event_signal(cleaned_title, ""):
                pass  # Keep valid short event title!
            else:
                return CleanedArticle(
                    id=article.id,
                    title=cleaned_title,
                    content=cleaned_content,
                    image_paths=article.image_paths,
                    num_images=article.num_images,
                    source_url=article.source_url,
                    is_valid=False,
                    filter_reason="text_too_short_or_empty",
                    char_count=char_count,
                    word_count=word_count
                )

        # 3. Check for pure navigation category / website section
        if self.filter_categories and self.is_navigation_category(cleaned_title, cleaned_content):
            return CleanedArticle(
                id=article.id,
                title=cleaned_title,
                content=cleaned_content,
                image_paths=article.image_paths,
                num_images=article.num_images,
                source_url=article.source_url,
                is_valid=False,
                filter_reason="web_navigation_category",
                char_count=char_count,
                word_count=word_count
            )

        # 4. Check for event content
        if not self.has_verifiable_event_signal(cleaned_title, cleaned_content):
            return CleanedArticle(
                id=article.id,
                title=cleaned_title,
                content=cleaned_content,
                image_paths=article.image_paths,
                num_images=article.num_images,
                source_url=article.source_url,
                is_valid=False,
                filter_reason="lacks_verifiable_event_signal",
                char_count=char_count,
                word_count=word_count
            )

        # 5. Check image validity: must have at least 1 readable image with size > 0 on disk
        require_valid_images = self.clean_cfg.get("require_valid_images", True)
        valid_images = [
            p for p in article.image_paths
            if os.path.exists(p) and os.path.getsize(p) > 0
        ]
        if require_valid_images and not valid_images:
            return CleanedArticle(
                id=article.id,
                title=cleaned_title,
                content=cleaned_content,
                image_paths=article.image_paths,
                num_images=article.num_images,
                source_url=article.source_url,
                is_valid=False,
                filter_reason="no_valid_image_on_disk",
                char_count=char_count,
                word_count=word_count
            )

        # 6. Check duplicate content via hash
        content_hash = hashlib.md5(combined_text.encode("utf-8")).hexdigest()
        if content_hash in self.seen_content_hashes:
            return CleanedArticle(
                id=article.id,
                title=cleaned_title,
                content=cleaned_content,
                image_paths=article.image_paths,
                num_images=article.num_images,
                source_url=article.source_url,
                is_valid=False,
                filter_reason="duplicate_content_hash",
                char_count=char_count,
                word_count=word_count
            )
        self.seen_content_hashes.add(content_hash)

        # Valid article passed all filters!
        final_images = valid_images if valid_images else article.image_paths
        return CleanedArticle(
            id=article.id,
            title=cleaned_title,
            content=cleaned_content if cleaned_content else cleaned_title,
            image_paths=final_images,
            num_images=len(final_images),
            source_url=article.source_url,
            is_valid=True,
            filter_reason=None,
            char_count=char_count,
            word_count=word_count
        )

    def process_all(self, articles: List[ArticleInput]) -> Tuple[List[CleanedArticle], List[CleanedArticle]]:
        """Processes a list of raw articles and returns (valid_articles, rejected_articles)."""
        valid_articles = []
        rejected_articles = []

        for art in articles:
            cleaned = self.clean_and_filter(art)
            if cleaned.is_valid:
                valid_articles.append(cleaned)
            else:
                rejected_articles.append(cleaned)

        logger.info(
            f"Text Cleaning & Filtering Summary: Total={len(articles)}, "
            f"Valid={len(valid_articles)}, Rejected={len(rejected_articles)}"
        )
        return valid_articles, rejected_articles
