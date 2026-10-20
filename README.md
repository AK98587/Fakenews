# Hệ Thống Sinh Dữ Liệu Fake News Đa Phương Thức Từ Tập Good (Tin Thật)

Hệ thống mã nguồn mở triển khai tự động hóa pipeline sinh dữ liệu Fake News đa phương thức (Text + Image) có kiểm soát từ tập dữ liệu Good (tin tức báo chí thật), tuân thủ 100% tài liệu đặc tả kỹ thuật [`doc/plan.md`](file:///c:/Users/This%20MC/Downloads/real_data/doc/plan.md).

Hệ thống sử dụng các mô hình ngôn ngữ lớn (LLM: `Qwen/Qwen2.5-7B-Instruct`) và mô hình thị giác - ngôn ngữ (VLM: `google/gemma-3-4b-it`) để tạo các biến thể văn bản có kiểm soát, đồng thời giữ nguyên vẹn hình ảnh gốc báo chí (không sinh ảnh, không chỉnh sửa pixel).

---

## 1. Kiến trúc Hệ Thống và Pipeline 11 Bước

```text
       GOOD DATASET (CSV/JSON/JSONL)
                    |
                    v
          [1] DATA LOADER (Field Mapping, Anti-Leakage Split)
                    |
                    v
          [2] TEXT CLEANING & FILTERING (Lọc danh mục, giữ sự kiện)
                    |
                    v
          [3] CLAIM EXTRACTION (Subject, Predicate, Object, Time, ...)
                    |
                    +-----------------------+
                    |                       |
                    v                       v
          [4] TEXT ANALYSIS       [5] IMAGE ANALYSIS
              Qwen2.5-7B               Gemma 3 4B
                    |                       |
                    +-----------+-----------+
                                |
                                v
          [6] IMAGE SELECTION (Chọn 1 ảnh đại diện phù hợp nhất)
                                |
                                v
          [7] CONTROLLED TEXT MANIPULATION (G1, G2, G3, G4)
                                |
                                v
          [8] FACTUAL CONTRADICTION CHECK (Kiểm tra mâu thuẫn)
                                |
                                v
          [9] TEXT-IMAGE CONSISTENCY CHECK (Độ tương quan ảnh - chữ)
                                |
                                v
          [10] QUALITY FILTERING (Ngữ pháp, lặp từ, từ cấm)
                                |
                                v
          [11] DATASET EXPORT (Chia tập Train/Val/Test, Cân bằng nhãn)
                                |
                                v
                  REAL (0) + SYNTHETIC FAKE (1)
```

### Các nhóm biến đổi thông tin (Module 5):
- **G1 — Numerical & Temporal Manipulation**: Thay đổi số liệu, tỷ lệ, ngày tháng, năm, giá trị tài chính làm sai lệch bản chất sự thật.
- **G2 — Entity & Relation Manipulation**: Thay đổi chủ thể, đối tượng, quan hệ hợp tác hoặc vai trò tổ chức thành một thực thể mâu thuẫn với bài gốc.
- **G3 — Event & Outcome Manipulation**: Đảo ngược kết quả sự kiện, quyết định, hủy bỏ/từ chối/đình chỉ thay vì ký kết/công nhận.
- **G4 — Multi-claim Manipulation**: Áp dụng cho bài có nhiều phát biểu, thay đổi có kiểm soát 1–3 phát biểu trọng tâm trong khi giữ mạch văn báo chí tự nhiên.

---

## 2. Cấu Trúc Thư Mục Dự Án

```text
real_data/
├── configs/
│   └── config.yaml               # Cấu hình toàn bộ tham số hệ thống
├── prompts/
│   ├── claim_extraction.txt      # Prompt trích xuất phát biểu có cấu trúc
│   ├── g1_numerical.txt          # Prompt biến đổi số liệu/thời gian
│   ├── g2_relation.txt           # Prompt biến đổi thực thể/đối tác
│   ├── g3_event.txt              # Prompt đảo ngược kết quả sự kiện
│   ├── g4_multiclaim.txt         # Prompt biến đổi đa phát biểu
│   └── verification.txt          # Prompt kiểm tra mâu thuẫn và chất lượng
├── src/                          # Mã nguồn các module chính
│   ├── __init__.py
│   ├── schemas.py                # Pydantic schemas cho dữ liệu & metadata
│   ├── data_loader.py            # Module 1: Đọc dữ liệu, chia tập chống Data Leakage
│   ├── text_cleaner.py           # Module 2: Làm sạch, lọc danh mục, giữ tiêu đề sự kiện
│   ├── claim_extractor.py        # Module 3: Trích xuất phát biểu (LLM + Dry-run)
│   ├── image_analyzer.py         # Module 4a: Phân tích trực quan 1-19 ảnh
│   ├── image_selector.py         # Module 4b: Chọn 1 ảnh đại diện phù hợp
│   ├── text_generator.py         # Module 5: Sinh biến thể G1-G4 tiếng Việt tự nhiên
│   ├── contradiction_checker.py  # Module 6a: Thẩm định mâu thuẫn sự kiện
│   ├── quality_filter.py         # Module 6b: Kiểm tra độ trôi chảy & từ cấm
│   ├── dataset_exporter.py       # Module 7: Xuất tập dữ liệu JSON/JSONL
│   └── pipeline.py               # Bộ điều phối toàn diện 11 bước & quản lý mô hình
├── scr/                          # Alias tương thích ngược trỏ đến src
│   └── __init__.py
├── outputs/
│   ├── intermediate/             # Kết quả trung gian & file checkpoint
│   ├── final_dataset/            # Tập dữ liệu hoàn chỉnh (train, val, test, dataset.json)
│   ├── rejected/                 # Log các mẫu bị loại bỏ và lý do kiểm toán
│   └── logs/                     # Log hệ thống chi tiết
├── main.py                       # CLI Entry Point
├── run_dry_run_test.py           # Test suite kiểm thử toàn diện các module
├── colab_guide.ipynb             # Notebook hướng dẫn chạy trực tiếp trên Colab
├── requirements.txt              # Danh sách thư viện phụ thuộc
└── README.md
```

---

## 3. Cài Đặt và Môi Trường

### Yêu cầu:
- Python 3.10+
- PyTorch (khuyến nghị có CUDA khi chạy với mô hình 7B/4B)

### Cài đặt thư viện:
```bash
pip install -r requirements.txt
```

---

## 4. Hướng Dẫn Chạy Thử Nghiệm

Hệ thống được thiết kế hỗ trợ sẵn chế độ `dry_run` với các bộ quy tắc (rule-based heuristic) thông minh, cho phép kiểm thử toàn diện toàn bộ pipeline mà không cần tải mô hình nặng hay yêu cầu GPU.

### 4.1. Chạy Test Suite Tự Động (7 Bài Test):
```bash
python run_dry_run_test.py
```
Test suite sẽ kiểm tra:
1. `DataLoader`: Phân tích CSV, xử lý pipe-separated images, chia train/val/test theo `source_id`.
2. `TextCleaner`: Lọc danh mục website (e.g. `Hành chính – Quản trị`) và giữ tiêu đề có sự kiện (e.g. `BCTech ký kết với FPT Telecom`).
3. `ClaimExtractor`: Trích xuất phát biểu có cấu trúc.
4. `ImageAnalyzer` & `ImageSelector`: Phân tích và chọn ảnh đại diện.
5. `TextGenerator`: Sinh văn bản cho 4 nhóm G1, G2, G3, G4.
6. `ContradictionChecker` & `QualityFilter`: Phát hiện mâu thuẫn và chặn từ cấm ("đây là tin giả").
7. `FakeNewsPipeline`: Chạy end-to-end trên mẫu bài báo thật.

### 4.2. Chạy thử nghiệm với CLI:
Chạy thử nghiệm 15 bài báo Good (không cần tải mô hình):
```bash
python main.py --dry-run --limit 15 --no-resume
```

---

## 5. Cách Kiểm Tra Kết Quả Xuất Ra

Dữ liệu đầu ra được lưu tại thư mục `outputs/final_dataset/`:
- `train.jsonl`, `val.jsonl`, `test.jsonl`: Các tập dữ liệu phân chia chống Data Leakage theo `source_id`.
- `dataset.json`: Toàn bộ tập dữ liệu tổng hợp.
- `dataset_summary.json`: Báo cáo thống kê chi tiết tỷ lệ Real:Fake, phân bố G1-G4, lý do reject.

### Cấu trúc mỗi bản ghi (chuẩn Mục 9 của plan.md):
```json
{
  "id": "fake_000001",
  "source_id": "good_000010",
  "image_path": "real_photo/1787621617_IMG_8856_f.jpg",
  "text": "Nội dung bài báo tiếng Việt sau khi đã được biến đổi sự thật...",
  "label": 1,
  "metadata": {
    "generation_model": "Qwen2.5-7B-Instruct",
    "generation_method": "controlled_manipulation",
    "manipulation_type": "G3",
    "original_claim": "Trường BCTech ký kết hợp tác với FPT Telecom...",
    "modified_claim": "Trường BCTech tuyên bố hủy bỏ kế hoạch ký kết và chấm dứt hợp tác...",
    "verification_status": "verified_contradiction",
    "image_original": true,
    "quality_passed": true,
    "change_summary": "Đảo ngược kết quả sự kiện: 'ký kết' -> 'hủy bỏ'",
    "split": "train"
  }
}
```

Mẫu tin thật (`Real`) được lưu song song với `label: 0`, giữ nguyên vẹn nội dung gốc và hình ảnh tương ứng.

---

## 6. Hướng Dẫn Chạy Trên Google Colab GPU

Hệ thống đã được tối ưu hóa đặc biệt cho môi trường Google Colab GPU (T4 15GB VRAM hoặc A100):
1. **4-bit Quantization**: Tự động sử dụng `BitsAndBytes` nạp mô hình 4-bit (`load_in_4bit: true`), tiêu tốn chỉ ~5GB VRAM cho model 7B.
2. **Nạp tuần tự (Sequential Execution)**: Chạy xong LLM sẽ giải phóng VRAM (`gc.collect()` + `torch.cuda.empty_cache()`) trước khi nạp VLM, ngăn ngừa lỗi Out-Of-Memory (OOM).
3. **Cơ chế Resume**: Tự động lưu tiến độ vào `outputs/intermediate/checkpoint_source_ids.json`. Nếu phiên Colab bị ngắt kết nối, chỉ cần chạy lại thì hệ thống sẽ tự động tiếp tục xử lý các bài chưa làm.

### Các bước thực hiện trên Colab:
1. Mở file notebook [`colab_guide.ipynb`](file:///c:/Users/This%20MC/Downloads/real_data/colab_guide.ipynb) hoặc tải toàn bộ thư mục lên Google Drive.
2. Bật GPU: **Runtime -> Change runtime type -> T4 GPU**.
3. Cài đặt môi trường:
```bash
!pip install -q -r requirements.txt
!pip install -q bitsandbytes accelerate
```
4. Chạy thực nghiệm giai đoạn 1 (100 bài Good):
```bash
!python main.py --limit 100
```
5. Chạy toàn bộ dữ liệu:
```bash
!python main.py
```
