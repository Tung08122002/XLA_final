"""Kiểm tra nhanh môi trường chạy dự án mà không thay đổi dữ liệu hay kết quả.

Ví dụ:
    python src/verify_environment.py
    python src/verify_environment.py --require-ocr
    python src/verify_environment.py --require-font
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


# Console Windows cũ có thể là cp1252 và không in được dấu tiếng Việt. Các script
# của dự án dùng UTF-8, nên ép đầu ra của công cụ kiểm tra về UTF-8 khi có thể.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
IMPORTS = {
    "Pillow": "PIL",
    "NumPy": "numpy",
    "SciPy": "scipy",
    "scikit-image": "skimage",
    "OpenCV": "cv2",
    "Matplotlib": "matplotlib",
    "Pandas": "pandas",
    "pytesseract": "pytesseract",
}


def check_imports():
    missing = []
    for label, module in IMPORTS.items():
        ok = importlib.util.find_spec(module) is not None
        print(f"[{'OK' if ok else 'THIẾU'}] {label}")
        if not ok:
            missing.append(label)
    if "Pillow" not in missing:
        from PIL import features
        webp = features.check("webp")
        print(f"[{'OK' if webp else 'THIẾU'}] Pillow có hỗ trợ WebP")
        if not webp:
            missing.append("Pillow có WebP")
    return missing


def check_data():
    image_dir = ROOT / "data" / "images"
    metadata = ROOT / "data" / "metadata.json"
    images = sorted(image_dir.glob("*.png")) if image_dir.is_dir() else []
    ok = len(images) == 20 and metadata.is_file()
    print(f"[{'OK' if ok else 'THIẾU'}] Dữ liệu: {len(images)}/20 ảnh PNG và metadata.json")
    if ok:
        try:
            meta = json.loads(metadata.read_text(encoding="utf-8"))
            ok = len(meta) == 20
            print(f"[{'OK' if ok else 'THIẾU'}] Metadata: {len(meta)}/20 mục")
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[THIẾU] Không đọc được metadata.json: {exc}")
            ok = False
    return ok


def check_ocr():
    win_exe = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe"
    executable = shutil.which("tesseract")
    if not executable and win_exe.is_file():
        executable = str(win_exe)
    if not executable:
        print("[THIẾU] Tesseract OCR không có trong PATH hoặc C:\\Program Files\\Tesseract-OCR")
        return False
    bundled = ROOT / "data" / "tessdata"
    if bundled.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(bundled)
    try:
        run = subprocess.run([executable, "--list-langs"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", check=True)
        has_vie = "vie" in run.stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"[THIẾU] Không kiểm tra được Tesseract: {exc}")
        return False
    print(f"[{'OK' if has_vie else 'THIẾU'}] Tesseract tiếng Việt (vie): {executable}")
    return has_vie


def check_font():
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from make_dataset import find_fonts
        regular, bold = find_fonts()
        print(f"[OK] Font tạo dữ liệu: {regular} | {bold}")
        return True
    except Exception as exc:  # In lỗi rõ ràng, không làm hỏng kiểm tra các phần khác.
        print(f"[THIẾU] Font tạo dữ liệu: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Kiểm tra môi trường cho dự án nén ảnh")
    parser.add_argument("--require-ocr", action="store_true", help="coi Tesseract + vie là bắt buộc")
    parser.add_argument("--require-font", action="store_true", help="coi font tái tạo dữ liệu là bắt buộc")
    args = parser.parse_args()

    print(f"Python {sys.version.split()[0]}")
    problems = check_imports()
    if not check_data():
        problems.append("dữ liệu")
    if args.require_ocr and not check_ocr():
        problems.append("Tesseract/vie")
    if args.require_font and not check_font():
        problems.append("font")
    if problems:
        print("\nChưa thể chạy đầy đủ. Hãy cài/sửa: " + ", ".join(problems))
        return 1
    print("\nMôi trường sẵn sàng.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
