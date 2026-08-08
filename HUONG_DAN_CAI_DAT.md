# Hướng dẫn cài đặt — YouTube Downloader Pro

Tài liệu này hướng dẫn client cài đặt môi trường và triển khai tool tải playlist/video YouTube (giao diện Streamlit).

---

## 1. Tổng quan

Tool gồm 3 thành phần chính:

| File | Vai trò |
|------|---------|
| `app.py` | Giao diện web (Streamlit) |
| `core.py` | Logic tải video, thumbnail, xử lý playlist |
| `KP_Run.bat` | Script khởi chạy nhanh trên Windows |

**Luồng hoạt động:**

1. Nhập URL playlist hoặc video đơn lẻ.
2. Tool phân tích danh sách video (metadata).
3. Tải song song video + thumbnail theo cấu hình (độ phân giải, số luồng, phạm vi vị trí).
4. File lưu tại thư mục đã chọn, đặt tên dạng: `01 Tiêu đề video.mp4`.

---

## 2. Yêu cầu hệ thống

| Hạng mục | Yêu cầu |
|----------|---------|
| Hệ điều hành | Windows 10/11 (khuyến nghị) |
| Python | **3.10 trở lên** (bắt buộc) |
| FFmpeg | Bắt buộc — dùng để ghép video + audio |
| Kết nối mạng | Ổn định, truy cập được YouTube |
| Dung lượng ổ đĩa | Đủ cho số video cần tải |

---

## 3. Thư viện Python cần thiết

Danh sách trong `requirements.txt`:

| Thư viện | Mục đích |
|----------|----------|
| `streamlit` | Giao diện web |
| `yt-dlp` | Tải video/metadata từ YouTube |
| `curl-cffi` | Giả lập TLS fingerprint Chrome (tránh chặn bot) |
| `requests` | Tải thumbnail từ CDN YouTube |

**Thư viện hệ thống (không cần cài qua pip):**

- `tkinter` — hộp thoại chọn thư mục (đi kèm Python trên Windows).

---

## 4. Cài đặt từng bước (Windows)

### Bước 1: Cài Python

1. Tải Python từ [https://www.python.org/downloads/](https://www.python.org/downloads/) (phiên bản 3.10+).
2. Khi cài, **bật** tùy chọn **"Add python.exe to PATH"**.
3. Kiểm tra:

```powershell
python --version
```

Kết quả mong đợi: `Python 3.10.x` hoặc cao hơn.

### Bước 2: Cài FFmpeg

FFmpeg bắt buộc vì tool ghép video và audio thành file `.mp4`.

**Cách 1 — winget (khuyến nghị):**

```powershell
winget install Gyan.FFmpeg
```

**Cách 2 — tải thủ công:**

1. Tải bản build từ [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/).
2. Giải nén và thêm thư mục `bin` vào biến môi trường **PATH**.

Kiểm tra:

```powershell
ffmpeg -version
```

### Bước 3: Giải nén / copy mã nguồn tool

Đặt toàn bộ thư mục project vào vị trí cố định, ví dụ:

```
D:\Tool\
├── app.py
├── core.py
├── requirements.txt
├── KP_Run.bat
└── HUONG_DAN_CAI_DAT.md
```

### Bước 4: Tạo môi trường ảo (khuyến nghị)

Mở PowerShell tại thư mục project:

```powershell
cd D:\Tool
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> Nếu PowerShell chặn script, chạy một lần:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Bước 5: Cài thư viện Python

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 6: Cấu hình file khởi chạy (tùy chọn)

Mở `KP_Run.bat` và chỉnh nếu cần:

```bat
@echo off
cd /d D:\Tool

:: Bỏ comment dòng dưới nếu dùng venv
call venv\Scripts\activate

streamlit run app.py
```

Đổi `D:\Tool` thành đường dẫn thực tế trên máy client.

---

## 5. Triển khai và chạy tool

### Cách 1: Dùng file batch (đơn giản nhất)

Double-click `KP_Run.bat`.

Trình duyệt sẽ mở giao diện Streamlit (mặc định: `http://localhost:8501`).

### Cách 2: Chạy thủ công

```powershell
cd D:\Tool
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

### Cách 3: Chạy trên mạng nội bộ (LAN)

Cho phép máy khác trong cùng mạng truy cập:

```powershell
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Truy cập từ máy khác: `http://<IP-máy-chủ>:8501`

> Chỉ dùng trong mạng tin cậy. Không expose ra Internet công cộng nếu chưa có bảo mật bổ sung.

---

## 6. Hướng dẫn sử dụng sau khi cài

1. Mở giao diện web.
2. Dán **Playlist URL** hoặc **Video URL** vào ô nhập liệu.
3. Chọn cấu hình:
   - **Độ phân giải:** 1080p / 720p / 480p
   - **Từ vị trí / Đến vị trí:** giới hạn video trong playlist (để trống = tải toàn bộ)
   - **Số luồng tải song song:** 1–5 (mặc định 2)
4. Nhấn **Chọn thư mục** để đặt nơi lưu file.
5. Nhấn **BẮT ĐẦU TẢI**.

**Kết quả tải về:**

- Video: `01 Tiêu đề.mp4`, `02 Tiêu đề.mp4`, ...
- Thumbnail: cùng tên với đuôi `.jpg`

Thư mục mặc định nếu không chọn: `./downloads` (trong thư mục project).

---

## 7. Cập nhật thư viện

Định kỳ nên cập nhật `yt-dlp` vì YouTube thay đổi API thường xuyên:

```powershell
cd D:\Tool
.\venv\Scripts\Activate.ps1
pip install -U yt-dlp curl-cffi streamlit requests
```

---

## 8. Xử lý sự cố thường gặp

### `python` không được nhận diện

- Cài lại Python và bật **Add to PATH**, hoặc dùng `py -3.11` thay cho `python`.

### `ffmpeg` không được nhận diện

- FFmpeg chưa có trong PATH. Cài lại FFmpeg và mở terminal mới.

### Lỗi khi cài `curl-cffi`

- Cập nhật pip: `pip install --upgrade pip`
- Cài lại: `pip install curl-cffi --force-reinstall`
- Đảm bảo dùng Python 64-bit.

### Không tải được video / lỗi extract

- Cập nhật yt-dlp: `pip install -U yt-dlp`
- Kiểm tra URL còn hợp lệ và video không bị giới hạn vùng/riêng tư.
- Thử giảm số luồng tải song song xuống 1–2.

### Không mở được hộp thoại chọn thư mục

- Trên Windows, cần Python cài đầy đủ (có `tkinter`).
- Có thể nhập/sửa đường dẫn thư mục trực tiếp trong code hoặc dùng thư mục mặc định `downloads`.

### Trình duyệt không tự mở

- Mở thủ công: [http://localhost:8501](http://localhost:8501)

---

## 9. Checklist triển khai nhanh

- [ ] Python 3.10+ đã cài và có trong PATH
- [ ] FFmpeg đã cài và có trong PATH
- [ ] Đã chạy `pip install -r requirements.txt`
- [ ] Đã chỉnh đường dẫn trong `KP_Run.bat` (nếu cần)
- [ ] Chạy thử `KP_Run.bat` hoặc `streamlit run app.py`
- [ ] Tải thử 1 video để xác nhận file `.mp4` và `.jpg` xuất hiện đúng thư mục

---

## 10. Liên hệ hỗ trợ

Khi báo lỗi, gửi kèm:

1. Phiên bản Python (`python --version`)
2. Phiên bản FFmpeg (`ffmpeg -version`)
3. Nội dung lỗi trên giao diện hoặc terminal
4. URL playlist/video đang tải (nếu có thể chia sẻ)
