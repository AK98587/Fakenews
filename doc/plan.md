# ĐẶC TẢ HỆ THỐNG SINH DỮ LIỆU FAKE NEWS ĐA PHƯƠNG THỨC TỪ TẬP GOOD

## 1. Mục tiêu

Xây dựng hệ thống tự động tạo dữ liệu Fake News đa phương thức (Text + Image) từ tập dữ liệu Good (tin thật).

Hệ thống sử dụng LLM để thay đổi các thông tin thực tế trong văn bản gốc, đồng thời giữ nguyên hình ảnh của bài báo.

Mục tiêu cuối cùng là tạo tập dữ liệu huấn luyện mô hình phát hiện tin giả, trong đó mỗi mẫu gồm một văn bản và một hình ảnh.

Hệ thống không thực hiện sinh ảnh, chỉnh sửa ảnh hoặc thay đổi nội dung pixel của ảnh.

### 1.1. Đầu vào

Mỗi bài báo Good có thể chứa:

- ID bài báo.
- Tiêu đề bài báo.
- Nội dung bài báo (có thể ngắn hoặc dài).
- Danh sách từ 1 đến 19 hình ảnh.
- URL nguồn (nếu có).
- Metadata bổ sung.

Dữ liệu có thể bao gồm bài báo hoàn chỉnh, tiêu đề ngắn, mô tả tóm tắt, thông báo và danh mục website.

### 1.2. Đầu ra

Mỗi bài Good hợp lệ được sử dụng để tạo các biến thể Fake có kiểm soát.

Mỗi mẫu Fake phải có:

- Văn bản đã được biến đổi.
- Một hình ảnh gốc, không chỉnh sửa.
- Nhãn Fake.
- ID bài báo nguồn.
- Loại biến đổi.
- Phát biểu gốc và phát biểu đã thay đổi.
- Thông tin kiểm tra chất lượng.
- Trạng thái xác minh.

Các mẫu Real phải được giữ lại để tạo tập dữ liệu cân bằng và phục vụ đánh giá.

## 2. Kiến trúc tổng thể

Hệ thống sử dụng kiến trúc hai mô hình:

**Model A — Text Manipulation LLM**

- Mô hình đề xuất: `Qwen/Qwen2.5-7B-Instruct`.
- Nhiệm vụ: Phân tích nội dung gốc, trích xuất phát biểu và tạo văn bản Fake.
- Chỉ thay đổi các thông tin được lựa chọn.
- Giữ nguyên những thông tin không liên quan.
- Sinh văn bản tiếng Việt tự nhiên.
- Xuất dữ liệu có cấu trúc JSON.

**Model B — Vision-Language Model**

- Mô hình đề xuất: `google/gemma-3-4b-it`.
- Nhiệm vụ: Phân tích ảnh gốc, mô tả nội dung trực quan, xác định ảnh phù hợp với văn bản.
- Không sinh ảnh mới.
- Không chỉnh sửa ảnh.
- Không suy diễn sự kiện chỉ dựa vào ảnh.

Hai mô hình được chạy tuần tự để giảm mức sử dụng VRAM.

### 2.1. Pipeline

```text
GOOD DATASET
     |
     v
[1] DATA LOADER
     |
     v
[2] TEXT CLEANING & FILTERING
     |
     v
[3] CLAIM EXTRACTION
     |
     +-----------------------+
     |                       |
     v                       v
[4] TEXT ANALYSIS      [5] IMAGE ANALYSIS
    Qwen2.5-7B             Gemma 3 4B
     |                       |
     +-----------+-----------+
                 |
                 v
[6] IMAGE SELECTION
                 |
                 v
[7] CONTROLLED TEXT MANIPULATION
                 |
                 v
[8] FACTUAL CONTRADICTION CHECK
                 |
                 v
[9] TEXT-IMAGE CONSISTENCY CHECK
                 |
                 v
[10] QUALITY FILTERING
                 |
                 v
[11] DATASET EXPORT
                 |
                 v
     REAL + SYNTHETIC FAKE
```

## 3. Module 1 — Data Loader

### Yêu cầu

- Đọc dữ liệu từ JSON hoặc JSONL.
- Hỗ trợ văn bản dài và ngắn.
- Hỗ trợ danh sách từ 1–19 ảnh.
- Kiểm tra đường dẫn ảnh.
- Không chỉnh sửa file dữ liệu gốc.
- Ghi log các mẫu không hợp lệ.
- Có khả năng tiếp tục xử lý sau khi bị gián đoạn.

Nếu dữ liệu đầu vào có trường `text` thay vì `title` và `content`, hệ thống phải hỗ trợ cấu hình ánh xạ trường dữ liệu.

## 4. Module 2 — Text Cleaning & Filtering

### Yêu cầu

Loại bỏ:

- Danh mục website không chứa phát biểu kiểm chứng được.
- Văn bản rỗng hoặc quá ngắn.
- Nội dung HTML, ký tự thừa.
- Văn bản bị trùng lặp.
- Nội dung không đủ thông tin để xác định sự kiện.

Không được tự động loại bỏ tất cả các tiêu đề ngắn.

Một tiêu đề có chủ thể, hành động và sự kiện rõ ràng vẫn có thể được sử dụng.

Ví dụ:

`BCTech ký kết với FPT Telecom`

Đây là một phát biểu về sự kiện, có thể sử dụng để tạo biến thể.

Ngược lại:

`Hành chính – Quản trị`

Đây là danh mục, không nên sử dụng.

## 5. Module 3 — Claim Extraction

Sử dụng LLM để trích xuất các phát biểu có thể kiểm chứng.

Mỗi phát biểu cần xác định:

- Subject: Chủ thể.
- Predicate: Hành động hoặc quan hệ.
- Object: Đối tượng.
- Time: Thời gian.
- Location: Địa điểm.
- Quantity: Số liệu.
- Outcome: Kết quả.
- Evidence: Đoạn văn bản gốc hỗ trợ phát biểu.

Không tự bổ sung thông tin không xuất hiện trong nguồn.

Nếu không có phát biểu đủ rõ ràng, bỏ qua mẫu.

## 6. Module 4 — Image Analysis & Selection

Một bài Good có thể có tối đa 19 ảnh.

Hệ thống cần:

1. Đọc toàn bộ ảnh hợp lệ.
2. Phân tích nội dung trực quan của từng ảnh.
3. Tạo mô tả ngắn cho ảnh.
4. Xác định mức độ liên quan giữa ảnh và bài báo.
5. Chọn một ảnh đại diện cho mỗi mẫu đầu ra.

Ưu tiên ảnh có nội dung liên quan đến phát biểu được thay đổi.

Nếu ảnh không đủ thông tin để chứng minh hoặc bác bỏ một phát biểu, phải ghi nhận rằng ảnh chỉ cung cấp ngữ cảnh.

Không suy luận danh tính, địa điểm, thời gian hoặc sự kiện nếu ảnh không thể hiện rõ.

Cho phép tái sử dụng cùng một ảnh cho mẫu Real và Fake tương ứng.

## 7. Module 5 — Controlled Text Manipulation

Hệ thống triển khai bốn nhóm biến đổi.

### G1 — Numerical & Temporal Manipulation

Thay đổi:

- Số lượng.
- Tỷ lệ.
- Ngày tháng.
- Năm.
- Giá trị tài chính.

Yêu cầu: Giá trị mới phải làm thay đổi ý nghĩa thực tế của phát biểu, không chỉ thay đổi cách biểu diễn.

### G2 — Entity & Relation Manipulation

Thay đổi:

- Chủ thể.
- Đối tượng.
- Quan hệ hợp tác.
- Vai trò tổ chức.

Không thay đổi ngẫu nhiên thành các thông tin có thể vẫn đúng.

### G3 — Event & Outcome Manipulation

Thay đổi:

- Trạng thái sự kiện.
- Kết quả hoạt động.
- Quyết định.
- Kết luận.

Ưu tiên những biến đổi có thể xác định sự mâu thuẫn với nguồn.

### G4 — Multi-claim Manipulation

Áp dụng cho văn bản có nhiều phát biểu.

Yêu cầu:

- Giữ phần lớn nội dung gốc.
- Chỉ thay đổi 1–3 phát biểu trọng tâm.
- Duy trì mạch văn tự nhiên.
- Không tạo mâu thuẫn nội bộ không chủ đích.
- Không tự thêm những sự kiện ngoài phạm vi nguồn.

### Yêu cầu chung

- Văn bản đầu ra phải bằng tiếng Việt.
- Không thêm các cụm như "đây là tin giả" vào trường `text`.
- Không thêm lời giải thích hoặc nhãn vào nội dung dùng để huấn luyện.
- Giữ phong cách báo chí của văn bản gốc.
- Không sao chép nguyên văn toàn bộ bài Good.
- Không thay đổi tất cả thông tin trong bài.
- Phải lưu riêng nội dung gốc và nội dung đã thay đổi.

Đối với tiêu đề ngắn, ưu tiên tạo tiêu đề Fake có độ dài tương đương, không tự mở rộng thành bài báo dài khi không có dữ liệu hỗ trợ.

## 8. Module 6 — Verification

Hệ thống phải kiểm tra:

**Factual Contradiction**

Phát biểu mới có mâu thuẫn với bằng chứng trong bài Good hay không.

Có thể sử dụng NLI hoặc LLM làm bộ lọc ban đầu.

**Text Fluency**

Văn bản phải tự nhiên, đúng ngữ pháp, không có dấu hiệu lỗi sinh văn bản.

**Image–Text Relevance**

Văn bản Fake vẫn phải có liên quan đến chủ đề ảnh.

Có thể sử dụng CLIP similarity để đánh giá mức độ liên quan, nhưng không sử dụng cosine similarity làm bằng chứng xác định đúng/sai.

**Duplicate Detection**

Loại bỏ các mẫu Fake gần như trùng nhau.

**Verification Status**

Phân biệt rõ:

- `verified_contradiction`: Có bằng chứng xác minh mâu thuẫn.
- `source_contradiction`: Mâu thuẫn với văn bản nguồn, chưa xác minh độc lập.
- `synthetic_unverified`: Nội dung tổng hợp chưa được xác minh.
- `rejected`: Mẫu không đạt yêu cầu.

Không tự động coi tất cả văn bản LLM sinh ra là Fake đã được xác minh.

## 9. Module 7 — Dataset Export

Định dạng đầu ra JSON:

```json
{
  "id": "fake_000001",
  "source_id": "good_000001",
  "image_path": "images/good_000001_03.jpg",
  "text": "Nội dung bài báo sau khi biến đổi",
  "label": 1,
  "metadata": {
    "generation_model": "Qwen2.5-7B-Instruct",
    "generation_method": "controlled_manipulation",
    "manipulation_type": "G3",
    "original_claim": "Phát biểu gốc",
    "modified_claim": "Phát biểu mới",
    "verification_status": "source_contradiction",
    "image_original": true,
    "quality_passed": true
  }
}
```

Quy ước nhãn:

- `0`: Real.
- `1`: Fake.

Giữ metadata trong dữ liệu gốc phục vụ phân tích, nhưng không cung cấp metadata về cách sinh hoặc nhãn cho mô hình phân loại khi huấn luyện.

## 10. Yêu cầu triển khai kỹ thuật

Ngôn ngữ: Python.

Thư viện chính:

- PyTorch.
- Transformers.
- Accelerate.
- BitsAndBytes (nếu dùng GPU tương thích).
- Pillow.
- Pydantic.
- scikit-learn.
- CLIP hoặc Sentence Transformers cho các bước đánh giá liên quan.

Yêu cầu:

- Hỗ trợ chạy trên Google Colab GPU.
- Hỗ trợ nạp mô hình 4-bit khi khả thi.
- Chạy LLM và VLM tuần tự.
- Cấu hình toàn bộ tham số bằng YAML.
- Lưu kết quả trung gian.
- Hỗ trợ resume.
- Có cơ chế retry khi LLM trả JSON lỗi.
- Ghi log mẫu thành công và thất bại.
- Có seed để tái lập kết quả.
- Không huấn luyện lại mô hình sinh trong giai đoạn đầu.

## 11. Cấu trúc dự án

```text
synthetic_fakenews/
|
|-- configs/
|   |-- config.yaml
|
|-- data/
|   |-- good/
|   |-- images/
|   |-- processed/
|
|-- src/
|   |-- data_loader.py
|   |-- text_cleaner.py
|   |-- claim_extractor.py
|   |-- image_analyzer.py
|   |-- image_selector.py
|   |-- text_generator.py
|   |-- contradiction_checker.py
|   |-- quality_filter.py
|   |-- dataset_exporter.py
|
|-- prompts/
|   |-- claim_extraction.txt
|   |-- g1_numerical.txt
|   |-- g2_relation.txt
|   |-- g3_event.txt
|   |-- g4_multiclaim.txt
|   |-- verification.txt
|
|-- outputs/
|   |-- generated/
|   |-- validated/
|   |-- rejected/
|   |-- logs/
|
|-- main.py
|-- requirements.txt
|-- README.md
```

## 12. Quy trình thực nghiệm

Giai đoạn 1: Chạy thử trên 100 bài Good.

Giai đoạn 2: Tạo các biến thể G1, G2, G3 và G4.

Giai đoạn 3: Đánh giá thủ công một tập mẫu, kiểm tra tính chính xác của nhãn và chất lượng văn bản.

Giai đoạn 4: Lọc dữ liệu không đạt yêu cầu.

Giai đoạn 5: Xuất tập Real và Synthetic Fake.

Giai đoạn 6: Huấn luyện mô hình phát hiện Fake News trên dữ liệu mới.

Giai đoạn 7: Đánh giá trên tập kiểm thử độc lập có nguồn gốc rõ ràng.

### Ràng buộc chống Data Leakage

- Chia Train/Validation/Test theo `source_id` trước khi sinh dữ liệu.
- Các biến thể của cùng một bài Good chỉ được nằm trong một tập.
- Không sử dụng tập Test để điều chỉnh prompt sinh Fake.
- Không dùng mẫu Fake được sinh từ bài Good thuộc Test trong Train.
- Bổ sung mẫu Real được paraphrase để kiểm tra mô hình có học dấu hiệu văn phong LLM hay không.

## 13. Tiêu chí hoàn thành

Hệ thống được xem là hoàn thành khi:

1. Đọc được tập Good có từ 1–19 ảnh/bài.
2. Phân biệt được tin tức với danh mục website.
3. Trích xuất được phát biểu có thể kiểm chứng.
4. Tạo được các biến thể văn bản bằng bốn nhóm kỹ thuật.
5. Giữ nguyên ảnh gốc.
6. Xuất được một ảnh và một văn bản cho mỗi mẫu.
7. Kiểm tra và lưu trạng thái xác minh.
8. Không ghi đè dữ liệu nguồn.
9. Hỗ trợ chạy thử, lưu tiến độ và tiếp tục xử lý.
10. Tạo được dữ liệu JSON tương thích với pipeline huấn luyện Fake News Detection.

## 14. Yêu cầu đối với AI Coding Agent

Hãy triển khai dự án theo kiến trúc trên.

Ưu tiên mã nguồn rõ ràng, chia module độc lập, dễ kiểm thử và phù hợp môi trường Google Colab.

Trước tiên hãy tạo cấu trúc dự án, file cấu hình, data loader, các schema dữ liệu và prompt templates. Sau đó triển khai từng module theo pipeline.

Không tự giả định cấu trúc JSON đầu vào nếu chưa được cung cấp. Hãy thiết kế lớp ánh xạ trường dữ liệu có thể cấu hình.

Không tự động tải toàn bộ mô hình khi chạy unit test.

Cung cấp chế độ `dry_run` để kiểm tra pipeline mà không cần tải LLM hoặc VLM.

Sau khi hoàn thành, cung cấp hướng dẫn chạy thử với 5 mẫu Good, cách kiểm tra kết quả và cách chạy trên Google Colab.
