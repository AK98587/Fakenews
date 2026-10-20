"""
Generates an interactive, responsive HTML application for Human Verification of
Original (Real) vs Generated (Fake) articles with side-by-side diffs, image previews,
claim inspection, review approval actions, and JSON export.
"""

import os
import json
from datetime import datetime

def get_html_template(json_payload: str, base_href: str = "./", run_id: str = "") -> str:
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    created_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <base href="{base_href}">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Human Check - So Sánh Bài Gốc & Biến Thể Fake News</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0a0e17;
      --bg-secondary: #111827;
      --bg-card: #162032;
      --bg-card-hover: #1c2942;
      --border-color: #23324d;
      --border-focus: #3b82f6;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      
      --accent-blue: #38bdf8;
      --accent-cyan: #06b6d4;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --accent-purple: #a855f7;

      --real-color: #10b981;
      --fake-color: #f43f5e;
      --shadow-sm: 0 2px 4px rgba(0,0,0,0.3);
      --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
      --shadow-lg: 0 10px 25px rgba(0,0,0,0.5);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      line-height: 1.6;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* HEADER & STATS BAR */
    header {{
      background: linear-gradient(180deg, #131c2e 0%, #0d1524 100%);
      border-bottom: 1px solid var(--border-color);
      padding: 16px 28px;
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(12px);
    }}

    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 16px;
    }}

    .logo-area {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .logo-icon {{
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, #06b6d4, #3b82f6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      color: white;
      box-shadow: 0 0 15px rgba(6,182,212,0.4);
    }}

    .logo-title h1 {{
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}

    .logo-title p {{
      font-size: 0.78rem;
      color: var(--text-muted);
    }}

    .stats-pills {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .stat-pill {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .stat-pill strong {{
      font-weight: 700;
      color: var(--accent-blue);
    }}

    .stat-pill.pill-approved strong {{ color: var(--accent-emerald); }}
    .stat-pill.pill-rejected strong {{ color: var(--accent-rose); }}

    /* CONTROLS BAR */
    .controls-bar {{
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }}

    .search-box {{
      position: relative;
      flex: 1;
      min-width: 260px;
    }}

    .search-box input {{
      width: 100%;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 8px 14px 8px 36px;
      border-radius: 8px;
      font-size: 0.88rem;
      outline: none;
      transition: border 0.2s;
    }}

    .search-box input:focus {{
      border-color: var(--border-focus);
    }}

    .search-box svg {{
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      width: 16px;
      height: 16px;
      fill: var(--text-dim);
    }}

    .filter-select {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
      outline: none;
      cursor: pointer;
    }}

    .btn {{
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .btn-primary {{
      background: linear-gradient(135deg, #0284c7, #2563eb);
      color: white;
    }}
    .btn-primary:hover {{
      background: linear-gradient(135deg, #0369a1, #1d4ed8);
      transform: translateY(-1px);
    }}

    .btn-success {{
      background: #059669;
      color: white;
    }}
    .btn-success:hover {{ background: #047857; }}

    .btn-danger {{
      background: #dc2626;
      color: white;
    }}
    .btn-danger:hover {{ background: #b91c1c; }}

    .btn-secondary {{
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
    }}
    .btn-secondary:hover {{
      background: var(--bg-card-hover);
    }}

    /* MAIN CONTAINER */
    main {{
      flex: 1;
      padding: 24px 28px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      max-width: 1700px;
      width: 100%;
      margin: 0 auto;
    }}

    /* NAV BAR FOR ARTICLE CAROUSEL */
    .article-nav {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      padding: 10px 18px;
      border-radius: 12px;
      box-shadow: var(--shadow-sm);
    }}

    .nav-buttons {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}

    .article-counter {{
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--accent-cyan);
    }}

    /* ARTICLE CONTAINER */
    .article-view {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .article-header-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 18px 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 20px;
      box-shadow: var(--shadow-md);
    }}

    .header-details h2 {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 8px;
    }}

    .header-tags {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}

    .badge {{
      display: inline-block;
      padding: 3px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .badge-real {{ background: rgba(16,185,129,0.18); color: #34d399; border: 1px solid rgba(16,185,129,0.4); }}
    .badge-fake {{ background: rgba(244,63,94,0.18); color: #fb7185; border: 1px solid rgba(244,63,94,0.4); }}
    .badge-g1 {{ background: rgba(56,189,248,0.18); color: #38bdf8; border: 1px solid rgba(56,189,248,0.4); }}
    .badge-g2 {{ background: rgba(168,85,247,0.18); color: #c084fc; border: 1px solid rgba(168,85,247,0.4); }}
    .badge-g3 {{ background: rgba(245,158,11,0.18); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); }}
    .badge-g4 {{ background: rgba(236,72,153,0.18); color: #f472b6; border: 1px solid rgba(236,72,153,0.4); }}
    .badge-split {{ background: rgba(100,116,139,0.25); color: #cbd5e1; border: 1px solid #475569; }}
    .badge-verified {{ background: rgba(16,185,129,0.2); color: #10b981; border: 1px solid #10b981; }}
    .badge-source {{ background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid #3b82f6; }}

    /* SIDE BY SIDE COMPARISON GRID */
    .comparison-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }}

    @media (max-width: 1024px) {{
      .comparison-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .column-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-md);
      transition: border-color 0.2s;
    }}

    .column-card.real-card {{
      border-top: 4px solid var(--real-color);
    }}

    .column-card.fake-card {{
      border-top: 4px solid var(--fake-color);
    }}

    .card-top {{
      padding: 14px 20px;
      background: rgba(0,0,0,0.2);
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .card-top h3 {{
      font-size: 1rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .tabs {{
      display: flex;
      gap: 6px;
    }}

    .tab-btn {{
      padding: 5px 12px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
    }}

    .tab-btn.active {{
      background: var(--fake-color);
      color: white;
      border-color: var(--fake-color);
    }}

    .card-body {{
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      flex: 1;
    }}

    /* IMAGE SECTION */
    .image-preview-box {{
      width: 100%;
      height: 240px;
      background: #090d14;
      border: 1px solid var(--border-color);
      border-radius: 10px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }}

    .image-preview-box img {{
      max-width: 100%;
      max-height: 100%;
      width: 100%;
      height: 100%;
      object-fit: cover;
      cursor: zoom-in;
      transition: transform 0.2s;
      display: block;
    }}
    .image-preview-box img:hover {{
      transform: scale(1.02);
    }}

    .image-placeholder {{
      color: var(--text-dim);
      font-size: 0.82rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      padding: 20px;
      text-align: center;
    }}

    .image-caption {{
      font-size: 0.78rem;
      color: var(--text-muted);
      background: rgba(0,0,0,0.3);
      padding: 6px 12px;
      border-radius: 6px;
      border-left: 3px solid var(--accent-cyan);
    }}

    /* CLAIMS BOX */
    .claim-box {{
      background: rgba(0,0,0,0.25);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px 16px;
    }}

    .claim-box.real-claim {{
      border-left: 3px solid var(--real-color);
    }}

    .claim-box.fake-claim {{
      border-left: 3px solid var(--fake-color);
    }}

    .claim-label {{
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
    }}

    .real-claim .claim-label {{ color: var(--real-color); }}
    .fake-claim .claim-label {{ color: var(--fake-color); }}

    .claim-text {{
      font-size: 0.9rem;
      font-weight: 500;
      color: #e2e8f0;
    }}

    .change-summary-box {{
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      color: #fde68a;
    }}

    /* ARTICLE TEXT AREA */
    .article-text-container {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 18px;
      font-size: 0.92rem;
      line-height: 1.7;
      max-height: 380px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    /* HUMAN CHECK ACTION BAR */
    .review-action-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 18px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
      box-shadow: var(--shadow-sm);
    }}

    .review-status-label {{
      font-size: 0.9rem;
      font-weight: 600;
    }}

    .review-buttons {{
      display: flex;
      gap: 10px;
    }}

    .notes-input {{
      flex: 1;
      min-width: 250px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      outline: none;
    }}

    /* MODAL FOR IMAGE ZOOM */
    .modal {{
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.88);
      z-index: 1000;
      align-items: center;
      justify-content: center;
      cursor: zoom-out;
      backdrop-filter: blur(8px);
    }}

    .modal img {{
      max-width: 90%;
      max-height: 90%;
      border-radius: 10px;
      box-shadow: 0 0 35px rgba(0,0,0,0.9);
      object-fit: contain;
    }}

    /* FOOTER */
    footer {{
      background: var(--bg-secondary);
      border-top: 1px solid var(--border-color);
      padding: 16px 28px;
      font-size: 0.82rem;
      color: var(--text-dim);
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: auto;
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <header>
    <div class="header-top">
      <div class="logo-area">
        <div class="logo-icon">FN</div>
        <div class="logo-title">
          <h1>Hệ Thống Thẩm Định Dữ Liệu Fake News Đa Phương Thức</h1>
          <p>Khởi tạo lúc: {created_time} &bull; Mã phiên: {run_id} &bull; <span style="color:var(--accent-emerald);font-weight:600">✓ Sạch 100% từ đầu</span></p>
        </div>
      </div>
      <div class="stats-pills">
        <div class="stat-pill">Tổng số bài Good: <strong id="stat-total-sources">0</strong></div>
        <div class="stat-pill">Tổng số mẫu: <strong id="stat-total-samples">0</strong></div>
        <div class="stat-pill">Mẫu Real: <strong id="stat-real-count" style="color:var(--real-color)">0</strong></div>
        <div class="stat-pill">Mẫu Fake: <strong id="stat-fake-count" style="color:var(--fake-color)">0</strong></div>
        <div class="stat-pill pill-approved">Đã duyệt: <strong id="stat-approved">0</strong></div>
        <div class="stat-pill pill-rejected">Từ chối: <strong id="stat-rejected">0</strong></div>
      </div>
    </div>

    <!-- CONTROLS -->
    <div class="controls-bar">
      <div class="search-box">
        <svg viewBox="0 0 24 24"><path d="M10 18a7.952 7.952 0 0 0 4.897-1.688l4.396 4.396 1.414-1.414-4.396-4.396A7.952 7.952 0 0 0 18 10c0-4.411-3.589-8-8-8s-8 3.589-8 8 3.589 8 8 8zm0-14c3.309 0 6 2.691 6 6s-2.691 6-6 6-6-2.691-6-6 2.691-6 6-6z"/></svg>
        <input type="text" id="searchInput" placeholder="Tìm theo ID bài báo, tiêu đề, hoặc từ khóa nội dung..." oninput="handleSearch()">
      </div>

      <select id="groupFilter" class="filter-select" onchange="handleFilter()">
        <option value="ALL">Tất cả nhóm biến đổi (G1 - G4)</option>
        <option value="G1">G1 - Số liệu & Thời gian</option>
        <option value="G2">G2 - Thực thể & Đối tác</option>
        <option value="G3">G3 - Đảo ngược sự kiện</option>
        <option value="G4">G4 - Đa phát biểu</option>
      </select>

      <select id="splitFilter" class="filter-select" onchange="handleFilter()">
        <option value="ALL">Tất cả tập dữ liệu (Train / Val / Test)</option>
        <option value="train">Tập Train</option>
        <option value="val">Tập Validation</option>
        <option value="test">Tập Test</option>
      </select>

      <select id="statusFilter" class="filter-select" onchange="handleFilter()">
        <option value="ALL">Tất cả trạng thái duyệt</option>
        <option value="pending">Chưa thẩm định</option>
        <option value="approved">Đã phê duyệt (Pass)</option>
        <option value="rejected">Bị từ chối (Reject)</option>
      </select>

      <button class="btn btn-primary" onclick="exportReviewReport()">
        <svg style="width:14px;height:14px;fill:currentColor" viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
        Xuất Báo Cáo Kiểm Duyệt
      </button>

      <button class="btn" style="background:#b45309;color:white" onclick="resetAllReviews()" title="Xóa toàn bộ các đánh giá và bắt đầu lại sạch sẽ">
        <svg style="width:14px;height:14px;fill:currentColor" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
        Xóa Lịch Sử Duyệt (Reset)
      </button>
    </div>
  </header>

  <!-- MAIN -->
  <main>
    <!-- ARTICLE NAVIGATION -->
    <div class="article-nav">
      <div class="nav-buttons">
        <button class="btn btn-secondary" onclick="prevArticle()">&larr; Bài trước (Phím &larr;)</button>
        <button class="btn btn-secondary" onclick="nextArticle()">Bài tiếp theo (Phím &rarr;) &rarr;</button>
      </div>
      <div class="article-counter">
        Bài <span id="currentIdx">1</span> / <span id="totalFiltered">1</span>
        (ID Nguồn: <strong id="currentSourceId">...</strong>)
      </div>
      <div class="nav-buttons">
        <button class="btn btn-secondary" onclick="jumpToRandom()">Ngẫu nhiên</button>
      </div>
    </div>

    <!-- ARTICLE VIEW -->
    <div class="article-view" id="articleViewContainer">
      <!-- Article Header -->
      <div class="article-header-card">
        <div class="header-details">
          <div class="header-tags" style="margin-bottom:8px">
            <span class="badge badge-split" id="currentSplitBadge">TRAIN</span>
            <span class="badge badge-source" id="currentSourceIdBadge">source_id</span>
            <span class="badge" id="currentReviewBadge" style="background:#334155;color:#e2e8f0">CHƯA DUYỆT</span>
          </div>
          <h2 id="currentArticleTitle">Tiêu đề bài báo</h2>
          <p style="font-size:0.85rem;color:var(--text-muted)" id="currentArticleSubtitle">Đang nạp dữ liệu...</p>
        </div>
      </div>

      <!-- Comparison Grid -->
      <div class="comparison-grid">
        <!-- REAL COLUMN -->
        <div class="column-card real-card">
          <div class="card-top">
            <h3>
              <span class="badge badge-real">REAL (TIN THẬT)</span>
              Mẫu Gốc Chưa Chỉnh Sửa
            </h3>
            <span style="font-size:0.75rem;color:var(--text-dim)" id="realSampleId">ID: real_000000</span>
          </div>
          <div class="card-body">
            <!-- Image Box -->
            <div class="image-preview-box" id="realImageBox">
              <img id="realImg" src="" alt="Real Image" onclick="openZoom(this.src)" onerror="handleImageError(this)">
            </div>
            <div class="image-caption" id="realImageCaption">
              Mô tả ảnh: Ảnh gốc phản ánh sự kiện thực tế.
            </div>

            <!-- Original Claim Box -->
            <div class="claim-box real-claim">
              <div class="claim-label">
                <span>Phát biểu sự thật gốc (Ground Truth Claim)</span>
                <span>Label: 1</span>
              </div>
              <div class="claim-text" id="realClaimText">...</div>
            </div>

            <!-- Original Text -->
            <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);text-transform:uppercase">
              Văn bản bài báo gốc (Good Text):
            </div>
            <div class="article-text-container" id="realArticleText">...</div>
          </div>
        </div>

        <!-- FAKE COLUMN -->
        <div class="column-card fake-card">
          <div class="card-top">
            <h3>
              <span class="badge badge-fake">SYNTHETIC FAKE (TIN GIẢ)</span>
              Biến Thể Biến Đổi Có Kiểm Soát
            </h3>
            <div class="tabs" id="fakeTabsContainer">
              <!-- Tabs for Fake 1, Fake 2 -->
            </div>
          </div>
          <div class="card-body">
            <!-- Image Box (Reused original image) -->
            <div class="image-preview-box" id="fakeImageBox">
              <img id="fakeImg" src="" alt="Fake Image (Original Unaltered)" onclick="openZoom(this.src)" onerror="handleImageError(this)">
            </div>
            <div class="image-caption" id="fakeImageCaption">
              Ảnh gốc không sửa pixel (Multi-modal Fake News).
            </div>

            <!-- Manipulation Info Badges -->
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span class="badge" id="fakeManipBadge">G1</span>
              <span class="badge" id="fakeVerifBadge">source_contradiction</span>
              <span style="font-size:0.75rem;color:var(--text-dim);margin-left:auto" id="fakeSampleId">ID: fake_000000</span>
            </div>

            <!-- Change Summary -->
            <div class="change-summary-box" id="fakeChangeSummary">
              Tóm tắt thay đổi: ...
            </div>

            <!-- Modified Claim Box -->
            <div class="claim-box fake-claim">
              <div class="claim-label">
                <span>Phát biểu đã bị làm sai lệch (Modified Claim)</span>
                <span>Label: 0</span>
              </div>
              <div class="claim-text" id="fakeClaimText">...</div>
            </div>

            <!-- Modified Text -->
            <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);text-transform:uppercase">
              Văn bản sau biến đổi (Đã kiểm duyệt mâu thuẫn & ngữ pháp tiếng Việt):
            </div>
            <div class="article-text-container" id="fakeArticleText">...</div>
          </div>
        </div>
      </div>

      <!-- Human Verification Actions -->
      <div class="review-action-card">
        <div class="review-status-label">
          Đánh giá chuyên gia (Human Check):
        </div>
        <input type="text" class="notes-input" id="reviewNoteInput" placeholder="Nhập nhận xét / ghi chú kiểm định chất lượng (tùy chọn)..." onchange="saveNote()">
        <div class="review-buttons">
          <button class="btn btn-success" onclick="markApproval('approved')">
            <svg style="width:14px;height:14px;fill:currentColor" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
            Phê Duyệt Đạt (Phím 1)
          </button>
          <button class="btn btn-danger" onclick="markApproval('rejected')">
            <svg style="width:14px;height:14px;fill:currentColor" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            Từ Chối / Lỗi (Phím 2)
          </button>
        </div>
      </div>
    </div>
  </main>

  <!-- IMAGE ZOOM MODAL -->
  <div class="modal" id="zoomModal" onclick="this.style.display='none'">
    <img id="modalImg" src="">
  </div>

  <!-- FOOTER -->
  <footer>
    <div>Hệ Thống Sinh Dữ Liệu Fake News Đa Phương Thức &bull; Tuân thủ cấu trúc doc/plan.md</div>
    <div>Phím tắt: &larr; Bài trước | &rarr; Bài sau | Phím [1]: Phê duyệt | Phím [2]: Từ chối</div>
  </footer>

  <script>
    const rawData = {json_payload};

    let filteredData = [...rawData];
    let currentIndex = 0;
    let currentFakeIndex = 0;

    const CURRENT_RUN_ID = "{run_id}";
    const STORAGE_KEY = "fakenews_human_check_reviews_" + CURRENT_RUN_ID;

    // Tự động dọn sạch tất cả các phiên đánh giá cũ trong localStorage của trình duyệt
    try {{
      for (let i = localStorage.length - 1; i >= 0; i--) {{
        const k = localStorage.key(i);
        if (k && (k.startsWith("fakenews_") || k.startsWith("fakenews_human_check_reviews")) && k !== STORAGE_KEY) {{
          localStorage.removeItem(k);
        }}
      }}
    }} catch (e) {{
      console.warn("Storage cleanup note:", e);
    }}

    let reviews = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}");

    function resetAllReviews() {{
      if (confirm("Bạn có chắc chắn muốn xóa toàn bộ đánh giá đã duyệt / từ chối để bắt đầu lại sạch 100% không?")) {{
        reviews = {{}};
        try {{
          localStorage.removeItem(STORAGE_KEY);
        }} catch(e) {{}}
        updateStats();
        renderCurrentArticle();
      }}
    }}

    function updateStats() {{
      const totalSources = rawData.length;
      let totalSamples = 0;
      let realCount = 0;
      let fakeCount = 0;

      rawData.forEach(g => {{
        if (g.real) {{ totalSamples++; realCount++; }}
        if (g.fakes) {{ totalSamples += g.fakes.length; fakeCount += g.fakes.length; }}
      }});

      let approvedCount = 0;
      let rejectedCount = 0;
      Object.values(reviews).forEach(r => {{
        if (r.status === 'approved') approvedCount++;
        if (r.status === 'rejected') rejectedCount++;
      }});

      document.getElementById('stat-total-sources').innerText = totalSources;
      document.getElementById('stat-total-samples').innerText = totalSamples;
      document.getElementById('stat-real-count').innerText = realCount;
      document.getElementById('stat-fake-count').innerText = fakeCount;
      document.getElementById('stat-approved').innerText = approvedCount;
      document.getElementById('stat-rejected').innerText = rejectedCount;
    }}

    function setImageSource(imgId, src) {{
      const img = document.getElementById(imgId);
      if (!img) return;
      const box = img.parentElement;
      const placeholder = box.querySelector('.image-placeholder');
      if (placeholder) placeholder.remove();

      img.style.display = 'block';
      img.dataset.hasFailed = 'false';
      img.src = src;
    }}

    function handleImageError(imgEl) {{
      if (imgEl.dataset.hasFailed === 'true') return;
      imgEl.dataset.hasFailed = 'true';
      imgEl.style.display = 'none';

      const box = imgEl.parentElement;
      if (!box.querySelector('.image-placeholder')) {{
        const placeholder = document.createElement('div');
        placeholder.className = 'image-placeholder';
        placeholder.innerHTML = `
          <svg style="width:36px;height:36px;fill:#64748b" viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>
          <span style="font-weight:600;color:#94a3b8">Không tìm thấy hoặc tập tin ảnh 0 byte</span>
          <span style="font-size:0.75rem;color:#64748b">${{imgEl.getAttribute('src')}}</span>
        `;
        box.appendChild(placeholder);
      }}
    }}

    function renderCurrentArticle() {{
      if (filteredData.length === 0) {{
        document.getElementById('articleViewContainer').innerHTML = `
          <div style="text-align:center;padding:80px 20px;color:var(--text-muted)">
            <h3>Không tìm thấy bài báo nào phù hợp với bộ lọc</h3>
            <p style="margin-top:8px">Vui lòng xóa ô tìm kiếm hoặc đổi điều kiện lọc.</p>
          </div>
        `;
        document.getElementById('currentIdx').innerText = '0';
        document.getElementById('totalFiltered').innerText = '0';
        return;
      }}

      if (currentIndex >= filteredData.length) currentIndex = 0;
      if (currentIndex < 0) currentIndex = filteredData.length - 1;

      const group = filteredData[currentIndex];
      const real = group.real;
      const fakes = group.fakes || [];

      document.getElementById('currentIdx').innerText = currentIndex + 1;
      document.getElementById('totalFiltered').innerText = filteredData.length;
      document.getElementById('currentSourceId').innerText = group.source_id;

      // Header Tags
      const split = (real && real.metadata && real.metadata.split) || 'TRAIN';
      document.getElementById('currentSplitBadge').innerText = split.toUpperCase();
      document.getElementById('currentSourceIdBadge').innerText = group.source_id;

      // Review Status
      const rev = reviews[group.source_id] || {{ status: 'pending', note: '' }};
      const revBadge = document.getElementById('currentReviewBadge');
      if (rev.status === 'approved') {{
        revBadge.innerText = '✓ ĐÃ PHÊ DUYỆT';
        revBadge.style.background = '#059669';
        revBadge.style.color = '#fff';
      }} else if (rev.status === 'rejected') {{
        revBadge.innerText = '✗ BỊ TỪ CHỐI';
        revBadge.style.background = '#dc2626';
        revBadge.style.color = '#fff';
      }} else {{
        revBadge.innerText = 'CHƯA DUYỆT';
        revBadge.style.background = '#334155';
        revBadge.style.color = '#e2e8f0';
      }}
      document.getElementById('reviewNoteInput').value = rev.note || '';

      // Title & Subtitle
      const fullText = real ? real.text : '';
      const title = fullText.split('.')[0] || 'Bài báo Good';
      document.getElementById('currentArticleTitle').innerText = title;
      document.getElementById('currentArticleSubtitle').innerText = `Chứa ${{fakes.length}} biến thể Fake được sinh tự động`;

      // Real Column Details
      if (real) {{
        document.getElementById('realSampleId').innerText = `ID: ${{real.id}}`;
        setImageSource('realImg', real.image_path);
        document.getElementById('realClaimText').innerText = (real.metadata && real.metadata.original_claim) || 'Không có phát biểu';
        document.getElementById('realArticleText').innerText = real.text;
      }}

      // Fake Column Tabs
      const tabsContainer = document.getElementById('fakeTabsContainer');
      tabsContainer.innerHTML = '';
      if (currentFakeIndex >= fakes.length) currentFakeIndex = 0;

      fakes.forEach((fk, idx) => {{
        const btn = document.createElement('button');
        btn.className = `tab-btn ${{idx === currentFakeIndex ? 'active' : ''}}`;
        const mtype = (fk.metadata && fk.metadata.manipulation_type) || `Fake ${{idx+1}}`;
        btn.innerText = `${{mtype}} (Mẫu ${{idx+1}})`;
        btn.onclick = () => {{
          currentFakeIndex = idx;
          renderCurrentFake();
        }};
        tabsContainer.appendChild(btn);
      }});

      renderCurrentFake();
    }}

    function renderCurrentFake() {{
      const group = filteredData[currentIndex];
      const fakes = group.fakes || [];
      if (fakes.length === 0) return;

      const fk = fakes[currentFakeIndex];
      const meta = fk.metadata || {{}};

      document.getElementById('fakeSampleId').innerText = `ID: ${{fk.id}}`;
      setImageSource('fakeImg', fk.image_path);
      document.getElementById('fakeClaimText').innerText = meta.modified_claim || 'Không có';
      document.getElementById('fakeChangeSummary').innerText = `Tóm tắt thay đổi: ${{meta.change_summary || 'Sinh theo biến thể ' + meta.manipulation_type}}`;

      // Badges
      const mtype = meta.manipulation_type || 'G3';
      const mbadge = document.getElementById('fakeManipBadge');
      mbadge.className = `badge badge-${{mtype.toLowerCase()}}`;
      mbadge.innerText = `${{mtype}} - ${{getGroupDesc(mtype)}}`;

      const vbadge = document.getElementById('fakeVerifBadge');
      const vstatus = meta.verification_status || 'source_contradiction';
      vbadge.className = vstatus === 'verified_contradiction' ? 'badge badge-verified' : 'badge badge-source';
      vbadge.innerText = vstatus;

      document.getElementById('fakeArticleText').innerText = fk.text;

      // Update active tab buttons
      const tabBtns = document.querySelectorAll('#fakeTabsContainer .tab-btn');
      tabBtns.forEach((b, i) => {{
        if (i === currentFakeIndex) b.classList.add('active');
        else b.classList.remove('active');
      }});
    }}

    function getGroupDesc(g) {{
      switch(g) {{
        case 'G1': return 'Số liệu & Thời gian';
        case 'G2': return 'Thực thể & Đối tác';
        case 'G3': return 'Đảo ngược sự kiện';
        case 'G4': return 'Đa phát biểu';
        default: return 'Biến đổi';
      }}
    }}

    function openZoom(src) {{
      if (!src) return;
      document.getElementById('modalImg').src = src;
      document.getElementById('zoomModal').style.display = 'flex';
    }}

    function prevArticle() {{
      currentIndex--;
      currentFakeIndex = 0;
      renderCurrentArticle();
    }}

    function nextArticle() {{
      currentIndex++;
      currentFakeIndex = 0;
      renderCurrentArticle();
    }}

    function jumpToRandom() {{
      if (filteredData.length > 0) {{
        currentIndex = Math.floor(Math.random() * filteredData.length);
        currentFakeIndex = 0;
        renderCurrentArticle();
      }}
    }}

    function markApproval(status) {{
      const group = filteredData[currentIndex];
      if (!group) return;
      const note = document.getElementById('reviewNoteInput').value.trim();

      // Nếu bấm lại cùng một trạng thái đã chọn (ví dụ: đang 'rejected' bấm lại 'rejected') -> Hoàn tác về Chưa duyệt
      if (reviews[group.source_id] && reviews[group.source_id].status === status) {{
        delete reviews[group.source_id];
      }} else {{
        reviews[group.source_id] = {{
          source_id: group.source_id,
          status: status,
          note: note,
          reviewed_at: new Date().toISOString()
        }};
      }}
      localStorage.setItem(STORAGE_KEY, JSON.stringify(reviews));
      updateStats();
      renderCurrentArticle();
    }}

    function saveNote() {{
      const group = filteredData[currentIndex];
      if (!group) return;
      const note = document.getElementById('reviewNoteInput').value.trim();
      if (!reviews[group.source_id]) {{
        reviews[group.source_id] = {{ source_id: group.source_id, status: 'pending', note: note }};
      }} else {{
        reviews[group.source_id].note = note;
      }}
      localStorage.setItem(STORAGE_KEY, JSON.stringify(reviews));
    }}

    function handleFilter() {{
      const groupVal = document.getElementById('groupFilter').value;
      const splitVal = document.getElementById('splitFilter').value;
      const statusVal = document.getElementById('statusFilter').value;
      const query = document.getElementById('searchInput').value.toLowerCase().trim();

      filteredData = rawData.filter(g => {{
        if (groupVal !== 'ALL') {{
          const hasGroup = g.fakes.some(fk => (fk.metadata && fk.metadata.manipulation_type) === groupVal);
          if (!hasGroup) return false;
        }}

        if (splitVal !== 'ALL') {{
          const split = (g.real && g.real.metadata && g.real.metadata.split) || 'train';
          if (split !== splitVal) return false;
        }}

        if (statusVal !== 'ALL') {{
          const rev = reviews[g.source_id] || {{ status: 'pending' }};
          if (rev.status !== statusVal) return false;
        }}

        if (query) {{
          const textToSearch = [
            g.source_id,
            g.real ? g.real.text : '',
            ...(g.fakes.map(f => f.text + ' ' + (f.metadata ? f.metadata.change_summary : '')))
          ].join(' ').toLowerCase();
          if (!textToSearch.includes(query)) return false;
        }}

        return true;
      }});

      currentIndex = 0;
      currentFakeIndex = 0;
      renderCurrentArticle();
    }}

    function handleSearch() {{
      handleFilter();
    }}

    function exportReviewReport() {{
      const report = {{
        timestamp: new Date().toISOString(),
        total_sources: rawData.length,
        reviews: reviews
      }};
      const blob = new Blob([JSON.stringify(report, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fake_news_human_check_report_${{new Date().toISOString().slice(0,10)}}.json`;
      a.click();
    }}

    // KEYBOARD SHORTCUTS
    document.addEventListener('keydown', (e) => {{
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'ArrowRight') {{ nextArticle(); }}
      else if (e.key === 'ArrowLeft') {{ prevArticle(); }}
      else if (e.key === '1') {{ markApproval('approved'); }}
      else if (e.key === '2') {{ markApproval('rejected'); }}
    }});

    // INIT
    updateStats();
    renderCurrentArticle();
  </script>
</body>
</html>
"""

def build_human_check_html(dataset_path: str = "outputs/final_dataset/dataset.json"):
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    with open(dataset_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Group by source_id
    grouped = {}
    for r in records:
        sid = r["source_id"]
        grouped.setdefault(sid, {"real": None, "fakes": []})
        if r.get("label") == 1 or str(r.get("id", "")).startswith("real_"):
            grouped[sid]["real"] = r
        else:
            grouped[sid]["fakes"].append(r)

    groups_list = []
    for sid, data in grouped.items():
        groups_list.append({
            "source_id": sid,
            "real": data["real"],
            "fakes": data["fakes"]
        })

    json_payload = json.dumps(groups_list, ensure_ascii=False)

    root_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Root human_check.html
    root_html = get_html_template(json_payload, base_href="./", run_id=run_id)
    root_path = os.path.join(root_dir, "human_check.html")
    with open(root_path, "w", encoding="utf-8") as f:
        f.write(root_html)

    # 2. outputs/human_check.html
    outputs_html = get_html_template(json_payload, base_href="../", run_id=run_id)
    outputs_path = os.path.join(root_dir, "outputs", "human_check.html")
    os.makedirs(os.path.dirname(outputs_path), exist_ok=True)
    with open(outputs_path, "w", encoding="utf-8") as f:
        f.write(outputs_html)

    print(f"Generated human check HTML successfully (Run ID: {run_id}): {root_path} and {outputs_path}")

if __name__ == "__main__":
    build_human_check_html()
