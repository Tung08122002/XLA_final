# Đề tài 4 — So sánh các kỹ thuật nén ảnh (JPEG, PNG, WebP) cho ảnh sản phẩm TMĐT

## 1. Mục tiêu
So sánh JPEG, PNG và WebP (có mất mát và không mất mát) trên 20 ảnh sản phẩm (500×500 và 1000×1000) về
dung lượng (KB), chất lượng (PSNR, SSIM), thời gian nén/giải nén; phân tích lỗi (chữ nhỏ, cạnh, nền gradient);
đưa ra khuyến nghị định dạng và mức nén cho từng loại ảnh (ảnh có chữ, ảnh gradient, ảnh nhiều chi tiết).
Baseline: JPEG q50/75/90 và PNG. Phương pháp chính: WebP. Có ablation, phân tích thất bại, và demo trực tiếp.

## 2. Cấu trúc thư mục
```
README.md, requirements.txt, run_all.sh, run_all.ps1
data/images/*.png        20 ảnh gốc PNG (tham chiếu không mất mát)
data/metadata.json       nhóm (P/T/G), nguồn, kích thước từng ảnh
data/text_ground_truth.json   các dòng chữ thật trên ảnh nhóm T (cho OCR)
data/raw/                baboon.jpg, fruits.jpg (mẫu OpenCV, nguồn của P06, P07)
data/tessdata/vie.traineddata  dữ liệu OCR tiếng Việt cục bộ cho Tesseract
src/common.py            hàm dùng chung: list_images, encode, decode, psnr, ssim, evaluate, time_ms, ...
src/make_dataset.py      tạo dữ liệu (seed 2026)
src/verify_environment.py kiểm tra package, WebP, dữ liệu, OCR/font trước khi chạy
src/t01_*.py ... t10_*.py  các thí nghiệm (xem mục 5)
src/demo.py              chương trình demo tương tác
results/tXX/*.csv, section.md   số liệu và nội dung báo cáo của từng task
figures/tXX/*.png        hình 300 dpi, kiểu IEEE
```

## 3. Yêu cầu
- Python 3.13 (đã thử); các gói trong `requirements.txt`:
  `pip install -r requirements.txt`. Pillow phải có WebP (bản wheel chính thức đã có;
  kiểm tra: `python -c "from PIL import features; print(features.check('webp'))"`).
- **Tesseract 5 + gói tiếng Việt** (chỉ cần cho thí nghiệm OCR khả năng đọc chữ):
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr tesseract-ocr-vie`
  - macOS (Homebrew): `brew install tesseract tesseract-lang`
  - Windows: cài bản của UB Mannheim, chọn thêm "Vietnamese" khi cài, thêm vào PATH.
  - Kiểm tra: `tesseract --list-langs` phải có dòng `vie`.
- Đồ hoạ: các script ghi hình bằng backend Agg (không cần màn hình). Riêng `demo.py` dạng cửa sổ cần
  backend có GUI (Tk/Qt/macOS) và một màn hình.

### Windows (PowerShell)

Từ thư mục `code_nen_anh`, tạo môi trường riêng và cài đủ package:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python src\verify_environment.py
```
Nếu PowerShell chặn lệnh activate, dùng `Set-ExecutionPolicy -Scope Process Bypass` trong cửa sổ
hiện tại rồi chạy lại. Để chạy đầy đủ phần OCR, cài Tesseract 5 bản Windows (UB Mannheim).
Dự án đã có `data/tessdata/vie.traineddata` và tự cấu hình đường dẫn này, nên không cần tự chép gói
ngôn ngữ Vietnamese hay thêm Tesseract vào `PATH`. Kiểm tra bằng:
```powershell
python src\verify_environment.py --require-ocr
```

**Lưu ý tái tạo dữ liệu:** `make_dataset.py` đã tự dò Arial/Segoe UI trên Windows, DejaVu Sans trên Linux,
và Arial trên macOS. Nếu máy không có cặp font phù hợp, đặt hai biến môi trường `NEN_ANH_FONT` và
`NEN_ANH_FONT_BOLD` tới font regular/bold Unicode hỗ trợ tiếng Việt. Bộ 20 ảnh đã có sẵn, nên thông thường
không cần chạy lại script này.

## 4. Tái lập và seed
- Seed cố định `SEED = 2026` (trong `src/common.py` và `src/make_dataset.py`); các phép nén/giải nén và PSNR/SSIM
  là tất định, nên kích thước, PSNR, SSIM tái lập đúng từng chữ số trên cùng phiên bản thư viện.
- **Thời gian chạy (ms) thì không tất định**: phụ thuộc máy và tải. Tác vụ đo thời gian (t08, t10) phải chạy
  khi máy rảnh, tuần tự. `t10` ghi load average và độ phân tán của một phép đo tham chiếu vào
  `results/t10/machine_info.json` để đánh giá độ nhiễu.
- Phiên bản đã dùng ghi trong `requirements.txt`; thư viện nén (libjpeg-turbo, libwebp, zlib/zlib-ng) là
  bản đi kèm Pillow, ghi lại trong `results/t10/machine_info.json`.

## 5. Chạy từng script
Luôn chạy từ thư mục gốc:
```
cd nen_anh   # thư mục gốc dự án
python src/make_dataset.py              # (tuỳ chọn) tạo lại data/ — kết quả xác định theo seed
python src/t01_dataset_analysis.py      # t01: thống kê dữ liệu
python src/t02_worked_example.py        # t02: ví dụ tính tay JPEG trên khối 8x8
python src/t03_baseline.py              # t03: baseline JPEG q50/75/90 và PNG
python src/t04_webp_vs_baseline.py      # t04: WebP so với baseline
python src/t05_rd_bdrate.py             # t05: đường cong R-D, BD-rate
python src/t06_isoquality_recommend.py  # t06: so sánh cùng chất lượng, khuyến nghị
python src/t07_text_readability.py      # t07: khả năng đọc chữ bằng OCR (cần tesseract + vie)
python src/t08_ablation.py              # t08: ablation (có đo thời gian)
python src/t09_failure_cases.py         # t09: phân tích lỗi
python src/t10_timing.py                # t10: thời gian nén/giải nén + tác động tải trang (~3-5 phút)
python src/t10_timing.py --tables-only  #      chỉ sinh lại bảng/hình/section từ CSV, không đo lại
```
Mỗi script ghi `results/tXX/` và `figures/tXX/`; `results/tXX/section.md` là nội dung đưa vào báo cáo.
Tên file các task có thể thay đổi, hãy xem `ls src/`.


Chạy toàn bộ, tuần tự:
```
./run_all.sh                  # make_dataset rồi t01 ... t10 (glob src/t[0-9][0-9]_*.py)
SKIP_DATASET=1 ./run_all.sh   # không tạo lại dữ liệu
```
Lưu ý: `make_dataset.py` cần `skimage.data.stereo_motorcycle()` (có thể tải qua mạng ở lần đầu nếu bản
scikit-image không kèm sẵn) và `data/raw/*.jpg`; nếu `data/` đã có đủ thì dùng `SKIP_DATASET=1`.

Trên **PowerShell**, dùng runner riêng (mặc định giữ nguyên bộ dữ liệu có sẵn):
Runner tự chọn `.venv\Scripts\python.exe` nếu môi trường này tồn tại; không cần kích hoạt thủ công.
```powershell
.\run_all.ps1                    # toàn bộ, gồm OCR (cần Tesseract + vie)
.\run_all.ps1 -SkipOcr           # chạy các phần không cần OCR: bỏ t07 và t09
.\run_all.ps1 -RebuildDataset    # tạo lại data/ rồi chạy toàn bộ
```
Runner luôn chạy `src/verify_environment.py` trước, nên sẽ báo rõ package, WebP, dữ liệu, OCR hoặc font
còn thiếu thay vì để từng task lỗi giữa chừng. Các phép đo thời gian ở t08/t10 có thể mất vài phút và nên
chạy khi máy rảnh.

## 6. Chương trình demo
```
python src/demo.py                         # ảnh mặc định data/images/T01_card1000.png
python src/demo.py duong/dan/anh.jpg       # ảnh bất kỳ
python src/demo.py --save out.png --codec "WebP" --quality 30   # không giao diện (Agg), ghi ảnh ra file
```
Cửa sổ có: ảnh gốc và ảnh nén cạnh nhau; Slider quality 5–100; RadioButtons chọn codec (JPEG 4:2:0,
JPEG 4:4:4, WebP, PNG, WebP lossless); KB, bpp, PSNR, SSIM, thời gian mã hoá/giải mã; ô phóng to vùng chọn
(click hoặc kéo chuột trên ảnh để đặt tâm, phím +/− đổi cỡ). Tuỳ chọn: `--codec`, `--quality`, `--center X Y`,
`--zoom-size N`, `--dpi`. Không có màn hình thì dùng `--save`.

## 7. Nguồn dữ liệu
- P01–P05: ảnh mẫu của scikit-image (`coffee`, `chelsea`, `astronaut`, `rocket`, `stereo_motorcycle`), cắt vuông và
  thu về 500×500. P06, P07: `baboon.jpg`, `fruits.jpg` từ thư mục mẫu của OpenCV (nguồn JPEG, đã thu nhỏ — nên
  đã mang sẵn dấu vết nén JPEG; đây là hạn chế khi so sánh với ảnh gốc "sạch").
- T01–T07: thẻ sản phẩm kiểu Shopee **tổng hợp** bằng Pillow (thanh tiêu đề, giá, nhãn giảm giá, bảng thông số
  tiếng Việt); nội dung chữ ở `data/text_ground_truth.json`.
- G01–G06: ảnh studio tổng hợp (nền gradient, vật thể có đổ bóng); G04–G06 thêm nhiễu Gauss σ = 1,5.
- Dữ liệu tổng hợp được tạo bằng seed 2026 (`src/make_dataset.py`); chi tiết từng ảnh ở `data/metadata.json`.
  Kết luận trên ảnh tổng hợp cần kiểm chứng thêm trên ảnh sản phẩm thật quy mô lớn.
