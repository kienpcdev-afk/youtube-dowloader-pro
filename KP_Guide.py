"""Tài liệu hướng dẫn cài đặt — giao diện Streamlit."""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

GUIDE_FILE = Path(__file__).parent / "HUONG_DAN_CAI_DAT.md"

# ── Sections hiển thị trong Sidebar ToC ──────────────────────────────────────
TOC = [
    ("🏠", "1. Tổng quan",                "1-tng-quan"),
    ("💻", "2. Yêu cầu hệ thống",         "2-yu-cu-h-thng"),
    ("📦", "3. Thư viện cần thiết",        "3-th-vin-cn-thit"),
    ("🔧", "4. Cài đặt từng bước",         "4-ci-t-tng-bc-windows"),
    ("🚀", "5. Triển khai & chạy tool",    "5-trin-khai-v-chy-tool"),
    ("🎬", "6. Hướng dẫn sử dụng",        "6-hng-dn-s-dng-sau-khi-ci"),
    ("🔄", "7. Cập nhật thư viện",         "7-cp-nht-th-vin"),
    ("🛠️", "8. Xử lý sự cố",              "8-x-l-s-c-thng-gp"),
    ("✅", "9. Checklist triển khai",       "9-checklist-trin-khai-nhanh"),
    ("📞", "10. Liên hệ hỗ trợ",           "10-lin-h-h-tr"),
]

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ── Sidebar ─────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0f172a;
    min-width: 260px !important;
}
[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] .sidebar-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b !important;
    padding: 0 0 0.5rem 0;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 0.5rem;
}
[data-testid="stSidebar"] a {
    display: block;
    padding: 0.4rem 0.6rem;
    border-radius: 0.4rem;
    font-size: 0.88rem;
    text-decoration: none !important;
    transition: background 0.15s;
}
[data-testid="stSidebar"] a:hover {
    background: #1e293b;
    color: #f1f5f9 !important;
}

/* ── Main content ────────────────────────────────── */
#MainMenu, footer, [data-testid="stDeployButton"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

div[data-testid="stAppViewContainer"] > .main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 860px !important;
}

/* Typography */
h1 { font-size: 2rem !important; font-weight: 700 !important; color: #0f172a !important; margin-bottom: 0.25rem !important; }
h2 { font-size: 1.45rem !important; font-weight: 600 !important; color: #1e3a5f !important;
     border-bottom: 2px solid #e2e8f0; padding-bottom: 0.4rem; margin-top: 2.5rem !important; }
h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: #334155 !important; margin-top: 1.5rem !important; }
p, li { font-size: 1rem !important; line-height: 1.8 !important; color: #374151 !important; }
code { font-size: 0.9em !important; background: #f1f5f9 !important; padding: 0.15em 0.4em !important;
       border-radius: 0.3em !important; color: #be185d !important; }
pre code { color: #e2e8f0 !important; background: transparent !important; padding: 0 !important; font-size: 0.88rem !important; }
pre { background: #1e293b !important; border-radius: 0.6rem !important; padding: 1rem 1.25rem !important;
      overflow-x: auto; border-left: 4px solid #3b82f6 !important; }
blockquote { border-left: 4px solid #f59e0b !important; background: #fffbeb !important;
             padding: 0.75rem 1rem !important; border-radius: 0 0.5rem 0.5rem 0 !important; margin: 1rem 0 !important; }
blockquote p { color: #92400e !important; margin: 0 !important; }
table { width: 100% !important; border-collapse: collapse !important; margin: 1rem 0 !important; }
th { background: #1e3a5f !important; color: #f8fafc !important; font-weight: 600 !important;
     padding: 0.65rem 1rem !important; text-align: left !important; font-size: 0.9rem !important; }
td { padding: 0.6rem 1rem !important; border-bottom: 1px solid #e2e8f0 !important; font-size: 0.95rem !important; }
tr:nth-child(even) td { background: #f8fafc !important; }
hr { border: none !important; border-top: 1px solid #e2e8f0 !important; margin: 2rem 0 !important; }

/* Expander (sự cố / checklist) */
details summary { font-weight: 600 !important; color: #1e3a5f !important; }
[data-testid="stExpander"] { border: 1px solid #e2e8f0 !important; border-radius: 0.6rem !important; }

/* Badge trạng thái */
.badge-ok   { display:inline-block; padding:0.2em 0.65em; border-radius:999px;
               background:#dcfce7; color:#166534; font-size:0.78rem; font-weight:600; }
.badge-warn { display:inline-block; padding:0.2em 0.65em; border-radius:999px;
               background:#fef3c7; color:#92400e; font-size:0.78rem; font-weight:600; }
</style>
"""


def _parse_sections(text: str) -> dict[str, str]:
    """Tách nội dung .md thành dict {heading_line: body_text}."""
    pattern = re.compile(r"^(#{1,2}\s+.+)$", re.MULTILINE)
    positions = [(m.start(), m.group(1)) for m in pattern.finditer(text)]
    sections: dict[str, str] = {}
    for i, (start, heading) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections[heading] = text[start:end].strip()
    return sections


def _load_guide() -> str | None:
    if not GUIDE_FILE.exists():
        return None
    return GUIDE_FILE.read_text(encoding="utf-8")


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<p class="sidebar-title">📚 Mục lục</p>', unsafe_allow_html=True)
        for icon, label, anchor in TOC:
            st.markdown(
                f'<a href="#{anchor}">{icon} {label}</a>',
                unsafe_allow_html=True,
            )
        st.markdown("---")
        st.markdown(
            '<p style="font-size:0.75rem;color:#475569!important;">'
            "YouTube Downloader Pro<br>Tài liệu nội bộ</p>",
            unsafe_allow_html=True,
        )


def render_hero() -> None:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
            border-radius: 1rem;
            padding: 2rem 2.5rem 1.75rem;
            margin-bottom: 2rem;
            color: #fff;
        ">
            <div style="font-size:2.5rem;margin-bottom:0.5rem;">📥</div>
            <h1 style="color:#fff!important;margin:0 0 0.4rem!important;font-size:1.8rem!important;">
                YouTube Downloader Pro
            </h1>
            <p style="color:#bfdbfe!important;margin:0!important;font-size:1rem!important;line-height:1.6!important;">
                Hướng dẫn cài đặt và triển khai tool tải playlist/video YouTube.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_checklist_section(body: str) -> None:
    """Render riêng section checklist với checkbox tương tác."""
    st.markdown("## ✅ 9. Checklist triển khai nhanh")
    items = [
        ("Python 3.10+ đã cài và có trong PATH", False),
        ("FFmpeg đã cài và có trong PATH", False),
        ("Đã chạy `pip install -r requirements.txt`", False),
        ("Đã chỉnh đường dẫn trong `KP_Run.bat` (nếu cần)", False),
        ("Chạy thử `KP_Run.bat` hoặc `streamlit run app.py`", False),
        ("Tải thử 1 video để xác nhận file `.mp4` và `.jpg` xuất hiện đúng thư mục", False),
    ]
    all_done = True
    for i, (label, _) in enumerate(items):
        checked = st.checkbox(label, key=f"chk_{i}")
        if not checked:
            all_done = False

    if all_done:
        st.success("Hoàn tất! Tool đã sẵn sàng sử dụng. 🎉")
    else:
        st.info("Hoàn thành lần lượt từng mục trước khi chạy tool.")


def render_troubleshoot_section() -> None:
    """Render section xử lý sự cố với st.expander."""
    st.markdown("## 🛠️ 8. Xử lý sự cố thường gặp")
    issues = [
        (
            "`python` không được nhận diện",
            "Cài lại Python và bật **Add to PATH**, hoặc dùng `py -3.11` thay cho `python`.",
        ),
        (
            "`ffmpeg` không được nhận diện",
            "FFmpeg chưa có trong PATH. Cài lại FFmpeg và **mở terminal mới** sau khi cài.",
        ),
        (
            "Lỗi khi cài `curl-cffi`",
            "Cập nhật pip trước: `pip install --upgrade pip`\n\nCài lại: `pip install curl-cffi --force-reinstall`\n\nĐảm bảo dùng **Python 64-bit**.",
        ),
        (
            "Không tải được video / lỗi extract",
            "Cập nhật yt-dlp: `pip install -U yt-dlp`\n\nKiểm tra URL còn hợp lệ và video không bị giới hạn vùng/riêng tư.\n\nThử giảm số luồng tải song song xuống 1–2.",
        ),
        (
            "Không mở được hộp thoại chọn thư mục",
            "Trên Windows, cần Python cài đầy đủ (có `tkinter`). Có thể dùng thư mục mặc định `downloads` thay thế.",
        ),
        (
            "Trình duyệt không tự mở",
            "Mở thủ công: [http://localhost:8501](http://localhost:8501)",
        ),
    ]
    for title, detail in issues:
        with st.expander(f"❓ {title}"):
            st.markdown(detail)


def render_main_content(md_text: str) -> None:
    """Render từng section, thay section 8 và 9 bằng UI tùy chỉnh."""
    sections = _parse_sections(md_text)

    SKIP_PREFIXES = ("## 8.", "## 9.")

    for heading, body in sections.items():
        skip = any(heading.strip().startswith(p) for p in SKIP_PREFIXES)
        if skip:
            continue
        st.markdown(body, unsafe_allow_html=False)

    render_troubleshoot_section()
    render_checklist_section("")

    # Section 10 — liên hệ
    support_heading = next((h for h in sections if "10." in h), None)
    if support_heading:
        st.markdown(sections[support_heading])


def main() -> None:
    st.set_page_config(
        page_title="Hướng dẫn cài đặt — YouTube Downloader Pro",
        page_icon="📥",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    render_sidebar()

    md_text = _load_guide()

    if md_text is None:
        st.error(
            "**Không tìm thấy file hướng dẫn.**\n\n"
            f"Đường dẫn mong đợi: `{GUIDE_FILE}`\n\n"
            "Vui lòng đảm bảo file `HUONG_DAN_CAI_DAT.md` nằm cùng thư mục với `KP_Guide.py`.",
        )
        st.stop()

    render_hero()
    render_main_content(md_text)


if __name__ == "__main__":
    main()
