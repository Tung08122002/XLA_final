"""Module dùng chung cho mọi thí nghiệm của Đề tài 4. MỌI script phải dùng các hàm này
để số liệu giữa các phần nhất quán.

Quy ước đo:
- Ảnh gốc: PNG RGB 8 bit trong data/images (xem data/metadata.json; nhóm P/T/G).
- Mã hoá/giải mã bằng Pillow (libjpeg-turbo, zlib, libwebp) hoàn toàn trong bộ nhớ (BytesIO).
- Dung lượng = len(bytes) / 1024 (KB). bpp = 8*len(bytes) / (W*H).
- PSNR trên cả 3 kênh RGB (MSE trung bình 3 kênh), data_range 255; ảnh trùng khớp -> inf.
- SSIM: skimage structural_similarity trên RGB, channel_axis=2, gaussian_weights=True,
  sigma=1.5, use_sample_covariance=False (đúng theo Wang et al. 2004), data_range=255.
- Thời gian: trung vị của `repeats` lần chạy, time.perf_counter, đơn vị ms.
"""
import io
import json
import os
import shutil
import time

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

SEED = 2026
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "data", "images")
GROUP_NAMES = {"P": "Ảnh chụp nhiều chi tiết", "T": "Ảnh có chữ", "G": "Ảnh gradient / nền trơn"}

np.random.seed(SEED)


def load_metadata():
    with open(os.path.join(ROOT, "data", "metadata.json"), encoding="utf-8") as f:
        return json.load(f)


def load_text_gt():
    with open(os.path.join(ROOT, "data", "text_ground_truth.json"), encoding="utf-8") as f:
        return json.load(f)


def list_images():
    """Trả về list (name, group, PIL.Image RGB) theo thứ tự tên."""
    meta = load_metadata()
    out = []
    for name in sorted(meta):
        im = Image.open(os.path.join(IMG_DIR, name + ".png")).convert("RGB")
        im.load()
        out.append((name, meta[name]["group"], im))
    return out


def encode(img: Image.Image, fmt: str, **params) -> bytes:
    """fmt in {'JPEG','PNG','WEBP'}; params truyền thẳng cho Pillow.
    Ví dụ: encode(im,'JPEG',quality=75) ; encode(im,'JPEG',quality=75,subsampling=0) (4:4:4)
           encode(im,'PNG',compress_level=9) ; encode(im,'WEBP',quality=75,method=4)
           encode(im,'WEBP',lossless=True,quality=100,method=4)"""
    buf = io.BytesIO()
    img.save(buf, format=fmt, **params)
    return buf.getvalue()


def decode(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im.load()
    return im.convert("RGB")


def psnr(ref: np.ndarray, test: np.ndarray) -> float:
    mse = np.mean((ref.astype(np.float64) - test.astype(np.float64)) ** 2)
    return float("inf") if mse == 0 else float(10 * np.log10(255.0 ** 2 / mse))


def ssim(ref: np.ndarray, test: np.ndarray) -> float:
    return float(structural_similarity(ref, test, channel_axis=2, data_range=255,
                                       gaussian_weights=True, sigma=1.5,
                                       use_sample_covariance=False))


def time_ms(fn, repeats=5):
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return float(np.median(ts))


def evaluate(img: Image.Image, fmt: str, repeats=5, **params) -> dict:
    """Nén + giải nén + đo đủ chỉ số cho một cấu hình."""
    data = encode(img, fmt, **params)
    rec = decode(data)
    ref, out = np.asarray(img), np.asarray(rec)
    W, H = img.size
    res = {
        "size_kb": len(data) / 1024,
        "bpp": 8 * len(data) / (W * H),
        "ratio": (W * H * 3) / len(data),
        "psnr": psnr(ref, out),
        "ssim": ssim(ref, out),
    }
    if repeats:
        res["enc_ms"] = time_ms(lambda: encode(img, fmt, **params), repeats)
        res["dec_ms"] = time_ms(lambda: decode(data), repeats)
    return res


def ensure_dirs(task: str):
    r = os.path.join(ROOT, "results", task)
    f = os.path.join(ROOT, "figures", task)
    os.makedirs(r, exist_ok=True)
    os.makedirs(f, exist_ok=True)
    return r, f


def configure_tesseract(require_vie=True):
    """Cấu hình Tesseract đa nền tảng cho các thí nghiệm OCR.

    Ưu tiên biến ``TESSERACT_CMD``/``NEN_ANH_TESSDATA``, sau đó PATH, bản cài
    Windows UB Mannheim và gói ``data/tessdata`` đi kèm dự án. Hàm chỉ được gọi
    từ t07/t09 để các thí nghiệm không OCR không phụ thuộc Tesseract.
    """
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("Thiếu pytesseract. Chạy: python -m pip install -r requirements.txt") from exc

    win_exe = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                           "Tesseract-OCR", "tesseract.exe")
    exe_candidates = [os.environ.get("TESSERACT_CMD"), shutil.which("tesseract"), win_exe]
    executable = next((p for p in exe_candidates if p and os.path.isfile(p)), None)
    if not executable:
        raise RuntimeError(
            "Không tìm thấy Tesseract. Cài Tesseract 5 hoặc đặt biến TESSERACT_CMD tới tesseract.exe."
        )
    pytesseract.pytesseract.tesseract_cmd = executable

    bundled = os.path.join(ROOT, "data", "tessdata")
    installed = os.path.join(os.path.dirname(executable), "tessdata")
    data_candidates = [os.environ.get("NEN_ANH_TESSDATA"), os.environ.get("TESSDATA_PREFIX"),
                       bundled, installed]
    tessdata = next((p for p in data_candidates if p and os.path.isdir(p)), None)
    if tessdata:
        os.environ["TESSDATA_PREFIX"] = tessdata

    try:
        languages = set(pytesseract.get_languages(config=""))
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(f"Không gọi được Tesseract tại {executable}") from exc
    if require_vie and "vie" not in languages:
        raise RuntimeError(
            "Thiếu dữ liệu ngôn ngữ tiếng Việt (vie). Đặt vie.traineddata trong "
            "data/tessdata hoặc NEN_ANH_TESSDATA."
        )
    return executable, tessdata, languages
