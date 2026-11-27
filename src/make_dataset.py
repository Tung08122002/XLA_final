"""Tạo bộ dữ liệu 20 ảnh sản phẩm cho Đề tài 4 (so sánh kỹ thuật nén ảnh).

3 nhóm ảnh (theo gợi ý của đề bài):
  P: ảnh chụp nhiều chi tiết (7 ảnh, 500x500) - ảnh thật từ scikit-image / OpenCV samples
  T: ảnh có chữ (thẻ sản phẩm, bảng thông số) (7 ảnh, 4 ảnh 1000x1000 + 3 ảnh 500x500) - tổng hợp
  G: ảnh gradient / vùng màu đồng nhất (ảnh studio nền trơn) (6 ảnh, 3 ảnh 1000 + 3 ảnh 500) - tổng hợp

Tất cả lưu PNG (không mất mát) làm ảnh gốc tham chiếu. Seed cố định = 2026.
Chạy: python src/make_dataset.py
"""
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import skimage.data as skd

SEED = 2026
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "images")
RAW = os.path.join(ROOT, "data", "raw")
rng = np.random.default_rng(SEED)


def find_fonts():
    """Trả về cặp font Unicode regular/bold có tiếng Việt trên Windows, Linux hoặc macOS.

    Có thể ép dùng font riêng bằng hai biến môi trường ``NEN_ANH_FONT`` và
    ``NEN_ANH_FONT_BOLD``.  Việc dò font tại đây giúp ``make_dataset.py`` chạy được
    trên Windows thay vì phụ thuộc vào đường dẫn DejaVu cố định của Linux.
    """
    custom = (os.environ.get("NEN_ANH_FONT"), os.environ.get("NEN_ANH_FONT_BOLD"))
    candidates = [
        custom,
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ]
    for regular, bold in candidates:
        if regular and bold and Path(regular).is_file() and Path(bold).is_file():
            return regular, bold
    raise RuntimeError(
        "Không tìm thấy cặp font Unicode hỗ trợ tiếng Việt. "
        "Trên Windows hãy cài Arial/Segoe UI, hoặc đặt NEN_ANH_FONT và "
        "NEN_ANH_FONT_BOLD thành đường dẫn font regular/bold."
    )


FONT, FONT_B = find_fonts()


def square(img: Image.Image, size: int) -> Image.Image:
    w, h = img.size
    s = min(w, h)
    img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    return img.resize((size, size), Image.LANCZOS)


def photos():
    srcs = {
        "P01_coffee": skd.coffee(),
        "P02_chelsea": skd.chelsea(),
        "P03_astronaut": skd.astronaut(),
        "P04_rocket": skd.rocket(),
        "P05_motorcycle": skd.stereo_motorcycle()[0],
    }
    meta = {}
    for name, arr in srcs.items():
        square(Image.fromarray(arr).convert("RGB"), 500).save(os.path.join(OUT, name + ".png"))
        meta[name] = {"group": "P", "source": "scikit-image data." + name.split("_")[1]}
    bb = Image.open(os.path.join(RAW, "baboon.jpg")).convert("RGB")
    square(bb, 500).save(os.path.join(OUT, "P06_baboon.png"))
    meta["P06_baboon"] = {"group": "P", "source": "OpenCV samples/data/baboon.jpg (nguồn JPEG, đã thu nhỏ)"}
    fr = Image.open(os.path.join(RAW, "fruits.jpg")).convert("RGB")
    square(fr, 500).save(os.path.join(OUT, "P07_fruits.png"))
    meta["P07_fruits"] = {"group": "P", "source": "OpenCV samples/data/fruits.jpg (nguồn JPEG, đã thu nhỏ)"}
    return meta


def font(sz, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, sz)


PRODUCTS = [
    ("Tai nghe Bluetooth TWS Pro", "1.299.000₫", "-35%",
     ["Pin: 6 giờ, hộp sạc 24 giờ", "Chống ồn chủ động ANC", "Bluetooth 5.3, độ trễ 60 ms",
      "Chống nước IPX4", "Bảo hành chính hãng 12 tháng", "Miễn phí vận chuyển toàn quốc"]),
    ("Nồi chiên không dầu 5,5 lít", "2.150.000₫", "-20%",
     ["Công suất 1700 W", "Dung tích 5,5 lít", "Nhiệt độ 80 - 200 độ C",
      "Lòng nồi chống dính", "Hẹn giờ 60 phút", "Tặng kèm sách công thức"]),
    ("Áo thun cotton nam basic", "189.000₫", "-50%",
     ["Chất liệu 100% cotton", "Size: S, M, L, XL, XXL", "Màu: trắng, đen, xanh navy",
      "Giặt máy ở 30 độ C", "Đổi trả trong 7 ngày", "Xuất xứ: Việt Nam"]),
    ("Sữa rửa mặt dịu nhẹ 150 ml", "245.000₫", "-15%",
     ["Dành cho da nhạy cảm", "Không chứa xà phòng", "Độ pH 5,5",
      "Thành phần: nước, glycerin", "Hạn dùng 36 tháng", "Sản xuất tại Hàn Quốc"]),
    ("Bàn phím cơ không dây 87 phím", "890.000₫", "-25%",
     ["Switch: Red linear", "Kết nối: 2.4G, Bluetooth, USB-C", "Pin 4000 mAh",
      "Đèn nền RGB 16,8 triệu màu", "Keycap PBT double-shot", "Tương thích Windows, macOS"]),
    ("Bình giữ nhiệt inox 500 ml", "320.000₫", "-30%",
     ["Inox 304 hai lớp", "Giữ nóng 12 giờ, lạnh 24 giờ", "Nắp chống tràn",
      "Không chứa BPA", "Trọng lượng 350 g", "Bảo hành 6 tháng"]),
    ("Sạc dự phòng 20000 mAh", "560.000₫", "-40%",
     ["Sạc nhanh PD 22,5 W", "2 cổng USB-A, 1 cổng USB-C", "Màn hình LED hiển thị pin",
      "Vỏ nhựa chống cháy", "Kích thước 15 x 7 x 2,8 cm", "Bảo hành 18 tháng"]),
]


def product_thumb(size, hue):
    """Ảnh 'sản phẩm' nhỏ: dùng crop ảnh thật để thẻ có cả vùng ảnh chụp (giống Shopee)."""
    src = [skd.coffee(), skd.rocket(), skd.astronaut(), skd.chelsea(), skd.stereo_motorcycle()[0],
           skd.coffee(), skd.rocket()][hue]
    return square(Image.fromarray(src).convert("RGB"), size)


def text_card(idx, S):
    name, price, off, specs = PRODUCTS[idx]
    k = S / 1000.0
    img = Image.new("RGB", (S, S), (255, 255, 255))
    d = ImageDraw.Draw(img)
    # header bar (màu cam kiểu sàn TMĐT)
    d.rectangle([0, 0, S, int(90 * k)], fill=(238, 77, 45))
    d.text((int(30 * k), int(22 * k)), "FLASH SALE  •  Mall chính hãng", font=font(int(38 * k), True), fill=(255, 255, 255))
    # ảnh sản phẩm
    th = product_thumb(int(380 * k), idx)
    img.paste(th, (int(30 * k), int(120 * k)))
    # tên + giá
    x0 = int(440 * k)
    d.text((x0, int(130 * k)), name, font=font(int(30 * k), True), fill=(20, 20, 20))
    d.text((x0, int(190 * k)), price, font=font(int(56 * k), True), fill=(238, 77, 45))
    d.rounded_rectangle([x0, int(275 * k), x0 + int(120 * k), int(330 * k)], radius=int(8 * k), fill=(255, 0, 0))
    d.text((x0 + int(18 * k), int(282 * k)), off, font=font(int(36 * k), True), fill=(255, 255, 0))
    d.text((x0, int(350 * k)), "Đã bán 12,4k  |  4,9 / 5 sao", font=font(int(24 * k)), fill=(110, 110, 110))
    # bảng thông số chữ nhỏ
    y = int(540 * k)
    d.text((int(30 * k), y), "THÔNG SỐ KỸ THUẬT", font=font(int(30 * k), True), fill=(20, 20, 20))
    y += int(55 * k)
    lines = []
    fs = int(26 * k) if S >= 1000 else 14  # chữ nhỏ ở ảnh 500 px là trường hợp khó
    for i, s in enumerate(specs):
        if i % 2 == 0:
            d.rectangle([int(30 * k), y - int(6 * k), S - int(30 * k), y + int(42 * k)], fill=(245, 245, 245))
        d.text((int(45 * k), y), s, font=font(fs), fill=(40, 40, 40))
        lines.append(s)
        y += int(56 * k)
    return img, [name, price] + lines


def texts():
    meta, gt = {}, {}
    sizes = [1000, 1000, 1000, 1000, 500, 500, 500]
    for i, S in enumerate(sizes):
        nm = f"T{i + 1:02d}_card{S}"
        img, lines = text_card(i, S)
        img.save(os.path.join(OUT, nm + ".png"))
        meta[nm] = {"group": "T", "source": "tổng hợp (thẻ sản phẩm có chữ tiếng Việt, DejaVu Sans)"}
        gt[nm] = lines
    return meta, gt


def shade_object(S, kind, bg, objcol, noise):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float64) / S
    # nền gradient tuyến tính/xuyên tâm
    if kind % 2 == 0:
        t = yy[..., None]
    else:
        t = np.sqrt((xx - 0.5) ** 2 + (yy - 0.45) ** 2)[..., None] / 0.75
    c0, c1 = np.array(bg[0], float), np.array(bg[1], float)
    img = c0 * (1 - t) + c1 * t
    # bóng đổ mềm
    sh = np.exp(-(((xx - 0.5) / 0.28) ** 2 + ((yy - 0.83) / 0.04) ** 2))
    img *= (1 - 0.35 * sh)[..., None]
    # vật thể: hình cầu / trụ (chai) có chiếu sáng Lambert + specular
    oc = np.array(objcol, float)
    if kind in (0, 3):  # cầu
        r = 0.27
        dx, dy = (xx - 0.5) / r, (yy - 0.5) / r
        m = dx ** 2 + dy ** 2 <= 1
        nz = np.sqrt(np.clip(1 - dx ** 2 - dy ** 2, 0, 1))
        L = np.array([-0.4, -0.5, 0.77]); L /= np.linalg.norm(L)
        lam = np.clip(-dx * L[0] * -1 + dy * L[1] + nz * L[2], 0, 1)
        lam = np.clip(dx * L[0] + dy * L[1] + nz * L[2], 0, 1)
        spec = lam ** 40
    else:  # trụ (chai/lọ)
        w = 0.17
        dx = (xx - 0.5) / w
        m = (np.abs(dx) <= 1) & (yy > 0.25) & (yy < 0.8)
        nz = np.sqrt(np.clip(1 - dx ** 2, 0, 1))
        lam = np.clip(-0.45 * dx + 0.9 * nz, 0, 1)
        spec = np.clip(1 - np.abs(dx + 0.45) / 0.08, 0, 1) ** 2
        # nắp
        cap = (np.abs(dx) <= 0.55) & (yy > 0.17) & (yy <= 0.25)
        img[cap] = np.array([40, 40, 45], float)
    shade = (0.25 + 0.75 * lam)[..., None] * oc + (spec[..., None] * 255 * 0.8)
    img[m] = np.clip(shade[m], 0, 255)
    if noise > 0:
        img = img + rng.normal(0, noise, img.shape)
    out = Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8))
    return out.filter(ImageFilter.GaussianBlur(0.6))  # khử răng cưa biên


def gradients():
    meta = {}
    cfg = [  # (kind, S, bg pair, object color, noise sigma)
        (0, 1000, ((250, 236, 222), (214, 170, 140)), (200, 40, 60), 0.0),
        (1, 1000, ((235, 242, 255), (120, 150, 210)), (230, 230, 235), 0.0),
        (2, 1000, ((245, 245, 245), (190, 190, 190)), (30, 120, 70), 0.0),
        (3, 500, ((255, 250, 235), (240, 200, 120)), (60, 90, 200), 1.5),
        (4, 500, ((230, 255, 245), (90, 170, 150)), (240, 180, 40), 1.5),
        (5, 500, ((250, 235, 245), (200, 140, 180)), (90, 60, 50), 1.5),
    ]
    for i, (k, S, bg, oc, nz) in enumerate(cfg):
        nm = f"G{i + 1:02d}_studio{S}" + ("_noise" if nz else "")
        shade_object(S, k, bg, oc, nz).save(os.path.join(OUT, nm + ".png"))
        meta[nm] = {"group": "G", "source": "tổng hợp (ảnh studio nền gradient" + (", nhiễu cảm biến σ=1,5)" if nz else ", sạch)")}
    return meta


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    meta = photos()
    m2, gt = texts()
    meta.update(m2)
    meta.update(gradients())
    for nm in meta:
        im = Image.open(os.path.join(OUT, nm + ".png"))
        meta[nm]["size"] = list(im.size)
    with open(os.path.join(ROOT, "data", "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "data", "text_ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(gt, f, ensure_ascii=False, indent=1)
    print(len(meta), "ảnh ->", OUT)
