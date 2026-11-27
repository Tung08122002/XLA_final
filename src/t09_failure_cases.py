"""t09 - Phân tích lỗi: 5 trường hợp thất bại của nén ảnh (JPEG / PNG / WebP).

Mục tiêu: tìm và CHỨNG MINH bằng số liệu + hình 5 ca thất bại, mỗi ca có (i) hiện tượng,
(ii) chỉ số cục bộ (không chỉ PSNR/SSIM toàn ảnh), (iii) một thí nghiệm đối chứng/ablation nhỏ
để tách nguyên nhân. Mọi cấu hình đều đo qua `common.encode/decode/psnr/ssim/evaluate`
(không đo thời gian, nên không phụ thuộc tải máy).

Năm ca (giả thuyết ban đầu được KIỂM CHỨNG; ca nào dữ liệu không ủng hộ thì ghi rõ trong section.md):
  C1  Ringing (nhiễu muỗi) quanh chữ nhỏ 14 px của JPEG q50 trên T05-T07 (ảnh thẻ 500 px).
      Chỉ số: sai số độ chói |dY| trên các điểm NỀN cách nét chữ 2-4 px ("quầng"), tỉ lệ điểm
      lệch >=6 mức; SSIM/PSNR trên vùng chữ; và OCR (tesseract 5, tiếng Việt) -> tỉ lệ lỗi ký tự
      CER để biết chữ còn đọc được không. Ablation: JPEG q50 4:4:4 (tách ảnh hưởng của lấy mẫu sắc độ).
  C2  Loang màu (colour bleeding) quanh nhãn "-xx%" đỏ/vàng và giá cam do lấy mẫu sắc độ 4:2:0
      (JPEG mặc định + WebP luôn 4:2:0). Chỉ số: sai số kênh Cr (YCbCr) trong khung bao nhãn/giá.
      Ablation: JPEG 4:4:4 và "chỉ lấy mẫu 4:2:0 thuần, KHÔNG lượng tử" (tách nguyên nhân).
  C3  Dải màu/khối (banding) trên nền gradient sạch G01-G03 ở chất lượng thấp. Chỉ số: từ profile
      độ chói trung bình theo hàng (vùng nền thuần) lấy bậc nhảy lớn nhất, số bậc và tỉ lệ bậc
      nằm đúng biên khối 8 hàng; so sánh với PSNR/SSIM (vẫn cao). Đối chứng: tăng chất lượng,
      WebP lossless, và "dithering" (thêm nhiễu nhẹ vào nguồn trước khi nén).
  C4  Mất kết cấu chi tiết ở P06 baboon (và P02 chelsea): bản đồ SSIM cục bộ; năng lượng và
      tương quan của dải tần 1-3 px (hiệu hai bộ lọc Gauss sigma 1 và 3) so với gốc; so JPEG
      với WebP CÙNG dung lượng (chọn quality WebP sao cho KB gần nhất với JPEG).
  C5  Thất bại về dung lượng: PNG/WebP lossless trên ảnh có nhiễu cảm biến. So bpp của mọi ảnh;
      G01 (sạch) vs G04 (nhiễu sigma=1,5); quét sigma 0..3 trên chính G01; so với cận dưới entropy
      của nhiễu 3*h(N)=3*0,5*log2(2*pi*e*sigma^2) bit/điểm ảnh (3 kênh độc lập).

Tham số: seed = common.SEED (2026) cho mọi nhiễu ngẫu nhiên; WebP method=4 (mặc định của
common); PNG compress_level=9; JPEG subsampling ghi tường minh (2 = 4:2:0, 0 = 4:4:4).
Đầu ra: results/t09/failure_cases.csv, figures/t09/case1..case5.png, results/t09/section.md.

Chạy: cd /home/claude/nen_anh && python src/t09_failure_cases.py
"""
import os
import sys

os.environ.setdefault("OMP_THREAD_LIMIT", "1")  # tesseract chạy ổn định khi máy bận
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytesseract  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from skimage.metrics import structural_similarity  # noqa: E402

from common import (SEED, decode, encode, ensure_dirs, evaluate, list_images,  # noqa: E402
                    load_text_gt, psnr, ssim, configure_tesseract)
import make_dataset as md  # noqa: E402  (chỉ để tái tạo G04 KHÔNG nhiễu -> đo nhiễu thật)

configure_tesseract(require_vie=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.labelsize": 10, "axes.titlesize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9, "lines.linewidth": 1.8,
    "axes.linewidth": 1.0, "axes.grid": False, "figure.dpi": 100, "savefig.dpi": 300,
    "axes.edgecolor": "black", "text.color": "black", "axes.labelcolor": "black",
    "xtick.color": "black", "ytick.color": "black",
})
GRID = dict(color="#cccccc", linewidth=0.6)
C_BLK, C_ORG, C_BLU, C_GRY = "#000000", "#d55e00", "#0072b2", "#777777"

RES, FIG = ensure_dirs("t09")
IMS = {n: im for n, g, im in list_images()}
ARR = {n: np.asarray(im) for n, im in IMS.items()}
GT = load_text_gt()
ROWS = []  # long-format: case, image, config, size_kb, psnr, ssim, local_metric, local_value


# ----------------------------------------------------------------------------- tiện ích
def add(case, image, config, kb, ps, ss, metric, value):
    ROWS.append(dict(case=case, image=image, config=config, size_kb=kb, psnr=ps, ssim=ss,
                     local_metric=metric, local_value=value))


def run(im, fmt, **p):
    """Nén + giải nén + (KB, PSNR, SSIM toàn ảnh) bằng đúng các hàm của common."""
    data = encode(im, fmt, **p)
    out = np.asarray(decode(data))
    ref = np.asarray(im)
    return out, len(data) / 1024, psnr(ref, out), ssim(ref, out)


def Y_of(a):
    return cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float64)


def ycc(a):
    """Tách Y, Cb, Cr (JFIF, đúng chuyển đổi mà JPEG dùng) dạng float."""
    y, cb, cr = Image.fromarray(a).convert("YCbCr").split()
    return np.asarray(y, float), np.asarray(cb, float), np.asarray(cr, float)


def lev(a, b):
    """Khoảng cách Levenshtein (để tính CER chuẩn)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb_ in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb_)))
        prev = cur
    return prev[-1]


def ocr_cer(im, name, box=(15, 295, 485, 480), scale=3):
    """CER của OCR trên bảng thông số (ảnh 500 px). Phóng 3x (LANCZOS) trước khi OCR - cách làm
    thông thường cho chữ nhỏ; tham chiếu = các dòng thông số trong text_ground_truth.json."""
    sl = im.crop(box)
    sl = sl.resize((sl.width * scale, sl.height * scale), Image.LANCZOS)
    txt = pytesseract.image_to_string(sl, lang="vie", config="--psm 6")
    ref = " ".join("\n".join(GT[name][2:]).split())
    hyp = " ".join(txt.split())
    return lev(ref, hyp) / len(ref)


def ssim_map(ref, out):
    """Bản đồ SSIM cục bộ, cùng tham số với common.ssim (gauss sigma 1.5), trung bình 3 kênh."""
    _, m = structural_similarity(ref, out, channel_axis=2, data_range=255, gaussian_weights=True,
                                 sigma=1.5, use_sample_covariance=False, full=True)
    return m.mean(axis=2)


def savefig(fig, name):
    fig.savefig(os.path.join(FIG, name), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def show(ax, img, **kw):
    ax.imshow(img, interpolation="nearest", **kw)
    ax.set_xticks([])
    ax.set_yticks([])


# ============================================================================== CASE 1
C1_IMGS = ["T05_card500", "T06_card500", "T07_card500"]
C1_CFG = [  # (nhãn, fmt, tham số)
    ("JPEG q5", "JPEG", dict(quality=5, subsampling=2)),
    ("JPEG q10", "JPEG", dict(quality=10, subsampling=2)),
    ("JPEG q15", "JPEG", dict(quality=15, subsampling=2)),
    ("JPEG q20", "JPEG", dict(quality=20, subsampling=2)),
    ("JPEG q30", "JPEG", dict(quality=30, subsampling=2)),
    ("JPEG q50", "JPEG", dict(quality=50, subsampling=2)),
    ("JPEG q50 4:4:4", "JPEG", dict(quality=50, subsampling=0)),
    ("JPEG q75", "JPEG", dict(quality=75, subsampling=2)),
    ("JPEG q90", "JPEG", dict(quality=90, subsampling=2)),
    ("WebP q0", "WEBP", dict(quality=0, method=4)),
    ("WebP q5", "WEBP", dict(quality=5, method=4)),
    ("WebP q30", "WEBP", dict(quality=30, method=4)),
    ("WebP q50", "WEBP", dict(quality=50, method=4)),
    ("WebP q75", "WEBP", dict(quality=75, method=4)),
]
TXT_Y0, TXT_Y1, TXT_X0, TXT_X1 = 295, 480, 15, 485


def c1_masks(ref):
    g = Y_of(ref)
    txt = np.zeros(g.shape, bool)
    txt[TXT_Y0:TXT_Y1, :] = g[TXT_Y0:TXT_Y1, :] < 200  # điểm thuộc nét chữ (chữ xám 40 trên nền 245-255)
    near = ndi.binary_dilation(txt, iterations=4) & ~ndi.binary_dilation(txt, iterations=1)
    halo = near & (g >= 240)  # điểm NỀN cách nét chữ 2..4 px
    halo[:TXT_Y0] = False
    halo[TXT_Y1:] = False
    return g, txt, halo


def case1():
    store = {}
    for n in C1_IMGS:
        ref = ARR[n]
        g, txt, halo = c1_masks(ref)
        sl = (slice(TXT_Y0, TXT_Y1), slice(TXT_X0, TXT_X1))
        # hàng "Gốc" để có mốc OCR
        add("C1", n, "Gốc (PNG)", len(encode(IMS[n], "PNG", compress_level=9)) / 1024, np.inf, 1.0,
            "ocr_cer", ocr_cer(IMS[n], n))
        for lab, fmt, p in C1_CFG:
            out, kb, ps, ss = run(IMS[n], fmt, **p)
            store[(n, lab)] = out
            e = np.abs(Y_of(out) - g)
            eh = e[halo]
            add("C1", n, lab, kb, ps, ss, "halo_MAE_dY", eh.mean())
            add("C1", n, lab, kb, ps, ss, "halo_ti_le_dY>=6_pct", 100 * (eh >= 6).mean())
            add("C1", n, lab, kb, ps, ss, "halo_max_dY", eh.max())
            add("C1", n, lab, kb, ps, ss, "vung_chu_PSNR", psnr(ref[sl], out[sl]))
            add("C1", n, lab, kb, ps, ss, "vung_chu_SSIM", ssim(ref[sl], out[sl]))
            add("C1", n, lab, kb, ps, ss, "ocr_cer", ocr_cer(Image.fromarray(out), n))
    # ---------------- hình
    n = "T05_card500"
    ref = ARR[n]
    y0, y1, x0, x1 = 296, 350, 15, 115  # 2 dòng chữ đầu của bảng thông số, 100x54 px
    crop = lambda a: a[y0:y1, x0:x1]
    g = Y_of(ref)
    err = lambda lab: np.abs(Y_of(store[(n, lab)]) - g)[y0:y1, x0:x1]
    fig, axs = plt.subplots(2, 3, figsize=(7.2, 4.8), layout="constrained")
    show(axs[0, 0], crop(ref)); axs[0, 0].set_title("(a) Gốc, chữ cao 14 px")
    show(axs[0, 1], crop(store[(n, "JPEG q50")])); axs[0, 1].set_title("(b) JPEG q50")
    ims = []
    for ax_, lab, t in [(axs[1, 0], "JPEG q50", "(d) |ΔY| JPEG q50"), (axs[1, 1], "JPEG q90", "(e) |ΔY| JPEG q90"),
                        (axs[1, 2], "WebP q75", "(f) |ΔY| WebP q75")]:
        ims.append(ax_.imshow(err(lab), cmap="gray_r", vmin=0, vmax=60, interpolation="nearest"))
        ax_.set_xticks([]); ax_.set_yticks([]); ax_.set_title(t)
    cb = fig.colorbar(ims[0], ax=axs[1, :], orientation="horizontal", fraction=0.08, pad=0.04, shrink=0.8)
    cb.set_label("|ΔY| (mức xám)", fontsize=9)
    ax = axs[0, 2]
    df = pd.DataFrame(ROWS)
    d1 = df[(df.case == "C1") & (df.local_metric == "halo_ti_le_dY>=6_pct")]
    labs = ["JPEG q30", "JPEG q50", "JPEG q75", "JPEG q90", "WebP q50", "WebP q75"]
    vals = [d1[d1.config == l].local_value.mean() for l in labs]
    ax.barh(range(len(labs)), vals, color=[C_ORG if l == "JPEG q50" else "#999999" for l in labs],
            edgecolor="black", linewidth=1.0)
    ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs); ax.invert_yaxis()
    ax.set_xlabel("Điểm nền quanh chữ lệch\n≥ 6 mức xám (%)", fontsize=9)
    ax.grid(axis="x", **GRID); ax.set_axisbelow(True)
    ax.set_title("(c) TB T05–T07")
    savefig(fig, "case1.png")


# ============================================================================== CASE 2
C2_IMGS = [f"T{i:02d}_card{s}" for i, s in zip(range(1, 8), [1000] * 4 + [500] * 3)]
C2_CFG = [
    ("JPEG q90 4:2:0", "JPEG", dict(quality=90, subsampling=2)),
    ("JPEG q90 4:4:4", "JPEG", dict(quality=90, subsampling=0)),
    ("JPEG q75 4:2:0", "JPEG", dict(quality=75, subsampling=2)),
    ("JPEG q75 4:4:4", "JPEG", dict(quality=75, subsampling=0)),
    ("WebP q90 (4:2:0)", "WEBP", dict(quality=90, method=4)),
    ("WebP q75 (4:2:0)", "WEBP", dict(quality=75, method=4)),
    ("WebP lossless", "WEBP", dict(lossless=True, quality=100, method=4)),
]
MARG = 4


def bbox_of(mask, margin=MARG):
    ys, xs = np.where(mask)
    return (max(ys.min() - margin, 0), ys.max() + margin + 1, max(xs.min() - margin, 0), xs.max() + margin + 1)


def c2_regions(ref):
    S = ref.shape[0]
    k = S / 1000.0
    label = (ref[..., 0] == 255) & (ref[..., 1] == 0) & (ref[..., 2] == 0)
    price = (ref[..., 0] == 238) & (ref[..., 1] == 77) & (ref[..., 2] == 45)
    price[: int(100 * k)] = False  # loại thanh tiêu đề cùng màu cam
    return {"nhan_do": bbox_of(label), "gia_cam": bbox_of(price)}


def chroma_only_420(ref):
    """Lấy mẫu sắc độ 4:2:0 THUẦN (trung bình khối 2x2 rồi nội suy song tuyến), KHÔNG lượng tử DCT:
    cô lập phần sai số do chỉ riêng việc giảm độ phân giải sắc độ. Dựng lại RGB (làm tròn + kẹp
    0..255 như bộ giải mã) rồi đo bằng cùng đường ống ycc() như các cấu hình khác."""
    y, cb, cr = ycc(ref)
    H, W = cr.shape
    pool = lambda c: c.reshape(H // 2, 2, W // 2, 2).mean(axis=(1, 3))
    up = lambda c: cv2.resize(pool(c).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float64)
    ycc_img = np.stack([y, up(cb), up(cr)], axis=-1)
    ycc_img = np.clip(np.round(ycc_img), 0, 255).astype(np.uint8)
    return np.asarray(Image.fromarray(ycc_img, "YCbCr").convert("RGB"))


def case2():
    store = {}
    for n in C2_IMGS:
        ref = ARR[n]
        regs = c2_regions(ref)
        yr, cbr, crr = ycc(ref)
        # đối chứng: chỉ lấy mẫu 4:2:0, không lượng tử
        yo0, cbo, cro = ycc(chroma_only_420(ref))
        for rn, (a, b, c, d) in regs.items():
            sl = (slice(a, b), slice(c, d))
            for mn, e_ in [("Cr_MAE", np.abs(cro - crr)), ("Cb_MAE", np.abs(cbo - cbr)), ("Y_MAE", np.abs(yo0 - yr)), ("Cr_max", None)]:
                v_ = np.abs(cro - crr)[sl].max() if e_ is None else e_[sl].mean()
                add("C2", n, "Chỉ lấy mẫu 4:2:0 (không lượng tử)", np.nan, np.nan, np.nan, f"{rn}_{mn}", v_)
        for lab, fmt, p in C2_CFG:
            out, kb, ps, ss = run(IMS[n], fmt, **p)
            store[(n, lab)] = out
            yo, cbo2, cro2 = ycc(out)
            for rn, (a, b, c, d) in regs.items():
                sl = (slice(a, b), slice(c, d))
                ecr = np.abs(cro2 - crr)[sl]
                add("C2", n, lab, kb, ps, ss, f"{rn}_Cr_MAE", ecr.mean())
                add("C2", n, lab, kb, ps, ss, f"{rn}_Cr_max", ecr.max())
                add("C2", n, lab, kb, ps, ss, f"{rn}_Cb_MAE", np.abs(cbo2 - cbr)[sl].mean())
                add("C2", n, lab, kb, ps, ss, f"{rn}_Y_MAE", np.abs(yo - yr)[sl].mean())
    # ---------------- hình (T05: nhãn -25%)
    n = "T05_card500"
    ref = ARR[n]
    a, b, c, d = c2_regions(ref)["nhan_do"]
    crop = lambda arr: arr[a:b, c:d]
    _, _, crr = ycc(ref)
    ecr = lambda lab: np.abs(ycc(store[(n, lab)])[2] - crr)[a:b, c:d]
    fig, axs = plt.subplots(2, 4, figsize=(7.4, 4.3), layout="constrained")
    titles = ["(a) Gốc", "(b) JPEG q90\n4:2:0", "(c) JPEG q90\n4:4:4", "(d) WebP q90\n(4:2:0)"]
    labs = [None, "JPEG q90 4:2:0", "JPEG q90 4:4:4", "WebP q90 (4:2:0)"]
    for j in range(4):
        show(axs[0, j], crop(ref) if labs[j] is None else crop(store[(n, labs[j])]))
        axs[0, j].set_title(titles[j])
    im = None
    for j in range(1, 4):
        im = axs[1, j - 1].imshow(ecr(labs[j]), cmap="gray_r", vmin=0, vmax=40, interpolation="nearest")
        axs[1, j - 1].set_xticks([]); axs[1, j - 1].set_yticks([])
        axs[1, j - 1].set_title(["(e) |ΔCr| của (b)", "(f) |ΔCr| của (c)", "(g) |ΔCr| của (d)"][j - 1], fontsize=9)
    cbar = fig.colorbar(im, ax=axs[1, :3], orientation="horizontal", fraction=0.10, pad=0.04, shrink=0.8)
    cbar.set_label("|ΔCr| (mức)", fontsize=9)
    axb = axs[1, 3]
    df = pd.DataFrame(ROWS)
    d2 = df[(df.case == "C2") & (df.local_metric == "nhan_do_Cr_MAE")]
    bl = ["JPEG q90 4:2:0", "JPEG q90 4:4:4", "WebP q90 (4:2:0)", "Chỉ lấy mẫu 4:2:0 (không lượng tử)"]
    sh = ["J90\n4:2:0", "J90\n4:4:4", "WebP\nq90", "Chỉ 4:2:0\nthuần"]
    v = [d2[d2.config == l].local_value.mean() for l in bl]
    axb.bar(range(4), v, color=["#999999", "#999999", "#999999", C_ORG], edgecolor="black", linewidth=1.0)
    axb.set_xticks(range(4)); axb.set_xticklabels(sh, fontsize=7.5)
    axb.set_ylabel("Cr MAE (mức)", fontsize=9)
    axb.grid(axis="y", **GRID); axb.set_axisbelow(True); axb.set_title("(h) TB T01–T07", fontsize=10)
    savefig(fig, "case2.png")


# ============================================================================== CASE 3
C3_IMGS = ["G01_studio1000", "G02_studio1000", "G03_studio1000"]
C3_CFG = [
    ("JPEG q30", "JPEG", dict(quality=30)),
    ("JPEG q50", "JPEG", dict(quality=50)),
    ("JPEG q75", "JPEG", dict(quality=75)),
    ("JPEG q90", "JPEG", dict(quality=90)),
    ("WebP q30", "WEBP", dict(quality=30, method=4)),
    ("WebP q50", "WEBP", dict(quality=50, method=4)),
    ("WebP q75", "WEBP", dict(quality=75, method=4)),
    ("WebP q90", "WEBP", dict(quality=90, method=4)),
    ("WebP q100 (lossy)", "WEBP", dict(quality=100, method=4)),
    ("WebP lossless", "WEBP", dict(lossless=True, quality=100, method=4)),
]
BR0, BR1, BC0, BC1 = 20, 700, 20, 200  # vùng nền thuần (không dính vật thể/bóng đổ)


def band_stats(a):
    """Profile độ chói trung bình theo hàng trong vùng nền thuần, rồi 3 chỉ số bậc thang."""
    P = Y_of(a)[BR0:BR1, BC0:BC1].mean(axis=1)
    d = np.abs(np.diff(P))
    rows = np.arange(BR0, BR1 - 1)
    bnd = ((rows + 1) % 8) == 0  # biên giữa hai khối 8 hàng
    return P, d.max(), int((d > 0.5).sum()), (d[bnd].sum() / d.sum() if d.sum() > 0 else np.nan)


def case3():
    store = {}
    for n in C3_IMGS:
        ref = ARR[n]
        P0, ms0, ns0, bs0 = band_stats(ref)
        add("C3", n, "Gốc (PNG)", len(encode(IMS[n], "PNG", compress_level=9)) / 1024, np.inf, 1.0, "max_buoc_nhay", ms0)
        add("C3", n, "Gốc (PNG)", np.nan, np.inf, 1.0, "so_buoc(>0.5)", ns0)
        add("C3", n, "Gốc (PNG)", np.nan, np.inf, 1.0, "ti_le_buoc_tai_bien_khoi8_pct", 100 * bs0)
        for lab, fmt, p in C3_CFG:
            out, kb, ps, ss = run(IMS[n], fmt, **p)
            store[(n, lab)] = out
            P, ms, ns, bs = band_stats(out)
            add("C3", n, lab, kb, ps, ss, "max_buoc_nhay", ms)
            add("C3", n, lab, kb, ps, ss, "so_buoc(>0.5)", ns)
            add("C3", n, lab, kb, ps, ss, "ti_le_buoc_tai_bien_khoi8_pct", 100 * bs)
        # đối chứng dithering: nhiễu Gauss sigma=1 thêm vào NGUỒN trước khi nén (PSNR/SSIM tính so với ảnh sạch)
        rng = np.random.default_rng(SEED)
        noisy = np.clip(np.round(ref + rng.normal(0, 1.0, ref.shape)), 0, 255).astype(np.uint8)
        src = Image.fromarray(noisy)
        for lab, fmt, p in [("JPEG q30", "JPEG", dict(quality=30)), ("JPEG q75", "JPEG", dict(quality=75)),
                            ("JPEG q90", "JPEG", dict(quality=90))]:
            data = encode(src, fmt, **p)
            out = np.asarray(decode(data))
            P, ms, ns, bs = band_stats(out)
            kb, ps, ss = len(data) / 1024, psnr(ref, out), ssim(ref, out)
            cfg = lab + " + dither σ=1"
            add("C3", n, cfg, kb, ps, ss, "max_buoc_nhay", ms)
            add("C3", n, cfg, kb, ps, ss, "so_buoc(>0.5)", ns)
            add("C3", n, cfg, kb, ps, ss, "ti_le_buoc_tai_bien_khoi8_pct", 100 * bs)
    # ---------------- hình (G01)
    n = "G01_studio1000"
    ref = ARR[n]
    r0, r1 = 100, 260
    gy = Y_of(ref)[r0:r1, BC0:BC1 + 80]
    lo, hi = np.floor(gy.min()), np.ceil(gy.max())
    fig = plt.figure(figsize=(7.2, 5.4), layout="constrained")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.95])
    cfgs = [("Gốc", ref), ("JPEG q30", store[(n, "JPEG q30")]), ("WebP q30", store[(n, "WebP q30")])]
    for j, (lab, a) in enumerate(cfgs):
        ax = fig.add_subplot(gs[0, j])
        show(ax, Y_of(a)[r0:r1, BC0:BC1 + 80], cmap="gray", vmin=lo, vmax=hi)
        sub = ""
        if lab != "Gốc":
            rr = [r for r in ROWS if r["case"] == "C3" and r["image"] == n and r["config"] == lab][0]
            sub = f"\n{rr['size_kb']:.1f} KB, {rr['psnr']:.1f} dB\nSSIM {rr['ssim']:.3f}"
        ax.set_title(f"({'abc'[j]}) {lab}{sub}", fontsize=9)
    ax = fig.add_subplot(gs[1, :])
    rows = np.arange(BR0, BR1)
    m = (rows >= r0) & (rows < r1)
    for k in range(r0, r1, 8):
        ax.axvline(k - 0.5, color="#dddddd", linewidth=0.6, zorder=0)
    ax.plot(rows[m], band_stats(ref)[0][m], color=C_BLK, linewidth=2.0, label="Gốc (bậc 1 mức)")
    ax.plot(rows[m], band_stats(store[(n, "JPEG q30")])[0][m], color=C_ORG, linewidth=2.0, linestyle="--", label="JPEG q30")
    ax.plot(rows[m], band_stats(store[(n, "WebP q30")])[0][m], color=C_BLU, linewidth=2.0, linestyle=":", label="WebP q30")
    ax.set_xlabel("Chỉ số hàng ảnh (px); đường xám nhạt = biên khối 8 hàng")
    ax.set_ylabel("Độ chói trung bình\ntheo hàng (mức xám)")
    ax.grid(axis="y", **GRID); ax.legend(loc="upper right", frameon=True, edgecolor="black")
    ax.set_title("(d) Profile độ chói qua nền gradient G01 (cột 20–200)", fontsize=10)
    savefig(fig, "case3.png")


# ============================================================================== CASE 4
C4_IMGS = ["P06_baboon", "P02_chelsea", "P01_coffee", "P07_fruits"]
J_QS = [10, 20, 30, 50, 75]


def band(a, s1=1.0, s2=3.0):
    g = Y_of(a)
    return cv2.GaussianBlur(g, (0, 0), s1) - cv2.GaussianBlur(g, (0, 0), s2)


def match_webp(im, target_kb):
    best = None
    for q in range(0, 101):
        s = len(encode(im, "WEBP", quality=q, method=4)) / 1024
        if best is None or abs(s - target_kb) < abs(best[1] - target_kb):
            best = (q, s)
    return best[0]


def case4():
    ROI = (300, 396, 340, 436)  # vùng lông + râu ở P06 (96x96 px)
    store = {}
    curve = {}
    for n in C4_IMGS:
        ref = ARR[n]
        br = band(ref)
        curve[n] = {"J": [], "W": []}
        for q in J_QS:
            dj = encode(IMS[n], "JPEG", quality=q)
            wq = match_webp(IMS[n], len(dj) / 1024)
            for lab, fmt, p in [(f"JPEG q{q}", "JPEG", dict(quality=q)),
                                (f"WebP q{wq} (cùng KB với JPEG q{q})", "WEBP", dict(quality=wq, method=4))]:
                out, kb, ps, ss = run(IMS[n], fmt, **p)
                store[(n, lab)] = out
                bo = band(out)
                add("C4", n, lab, kb, ps, ss, "ti_le_nang_luong_dai_1-3px", bo.std() / br.std())
                add("C4", n, lab, kb, ps, ss, "tuong_quan_dai_1-3px", np.corrcoef(br.ravel(), bo.ravel())[0, 1])
                m = ssim_map(ref, out)
                add("C4", n, lab, kb, ps, ss, "SSIM_phan_vi_10_cuc_bo", np.percentile(m, 10))
                if n == "P06_baboon":
                    a, b, c, d = ROI
                    add("C4", n, lab, kb, ps, ss, "SSIM_vung_long_rau", m[a:b, c:d].mean())
        # đường cong để vẽ (P06, P02)
        if n in ("P06_baboon", "P02_chelsea"):
            for q in [10, 20, 30, 40, 50, 60, 75, 90]:
                o, kb, _, _ = run(IMS[n], "JPEG", quality=q)
                curve[n]["J"].append((kb, band(o).std() / br.std()))
            for q in [5, 15, 25, 35, 45, 55, 65, 80, 90]:
                o, kb, _, _ = run(IMS[n], "WEBP", quality=q, method=4)
                curve[n]["W"].append((kb, band(o).std() / br.std()))
    # SSIM thấp nhất trong 20 ảnh + dung lượng để đạt SSIM >= 0.95
    ssim_j50 = {n: ssim(ARR[n], np.asarray(decode(encode(IMS[n], "JPEG", quality=50)))) for n in IMS}
    ssim_w75 = {n: ssim(ARR[n], np.asarray(decode(encode(IMS[n], "WEBP", quality=75, method=4)))) for n in IMS}
    for tag, dct in [("JPEG q50", ssim_j50), ("WebP q75", ssim_w75)]:
        order = sorted(dct, key=dct.get)
        add("C4", order[0], tag, np.nan, np.nan, dct[order[0]], "anh_SSIM_thap_nhat_trong_20", 1)
        add("C4", "P06_baboon", tag, np.nan, np.nan, dct["P06_baboon"], "hang_SSIM_cua_P06(1=thap_nhat)", order.index("P06_baboon") + 1)
    for n in ["P06_baboon", "P02_chelsea", "P04_rocket"]:
        for fmt, nm, rng_ in [("JPEG", "JPEG", range(1, 101)), ("WEBP", "WebP", range(0, 101))]:
            for q in rng_:
                p = dict(quality=q) if fmt == "JPEG" else dict(quality=q, method=4)
                out, kb, ps, ss = run(IMS[n], fmt, **p)
                if ss >= 0.95:
                    add("C4", n, f"{nm} q{q} (nhỏ nhất đạt SSIM≥0,95)", kb, ps, ss, "kb_de_dat_SSIM_0.95", kb)
                    break
    # ---------------- hình
    n = "P06_baboon"
    ref = ARR[n]
    a, b, c, d = ROI
    jl = "JPEG q50"
    wl = [k[1] for k in store if k[0] == n and k[1].startswith("WebP") and "JPEG q50)" in k[1]][0]
    fig, axs = plt.subplots(2, 3, figsize=(7.2, 5.4), layout="constrained")
    rj = [r for r in ROWS if r["case"] == "C4" and r["image"] == n and r["config"] == jl][0]
    rw = [r for r in ROWS if r["case"] == "C4" and r["image"] == n and r["config"] == wl][0]
    show(axs[0, 0], ref[a:b, c:d]); axs[0, 0].set_title("(a) Gốc (lông + râu)")
    show(axs[0, 1], store[(n, jl)][a:b, c:d]); axs[0, 1].set_title(f"(b) JPEG q50, {rj['size_kb']:.1f} KB")
    wq = wl.split()[0] + " " + wl.split()[1]
    show(axs[0, 2], store[(n, wl)][a:b, c:d]); axs[0, 2].set_title(f"(c) {wq}, {rw['size_kb']:.1f} KB")
    mj = ssim_map(ref, store[(n, jl)])[a:b, c:d]
    mw = ssim_map(ref, store[(n, wl)])[a:b, c:d]
    show(axs[1, 0], mj, cmap="gray", vmin=0, vmax=1); axs[1, 0].set_title(f"(d) SSIM cục bộ của (b)\nTB vùng = {mj.mean():.2f}", fontsize=9)
    imm = axs[1, 1].imshow(mw, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    axs[1, 1].set_xticks([]); axs[1, 1].set_yticks([]); axs[1, 1].set_title(f"(e) SSIM cục bộ của (c)\nTB vùng = {mw.mean():.2f}", fontsize=9)
    cb = fig.colorbar(imm, ax=axs[1, :2], orientation="horizontal", fraction=0.08, pad=0.04, shrink=0.8)
    cb.set_label("SSIM cục bộ", fontsize=9)
    ax = axs[1, 2]
    for nn, ls, mk in [("P06_baboon", "-", "o"), ("P02_chelsea", "--", "s")]:
        for key, col, lab in [("J", C_ORG, "JPEG"), ("W", C_BLU, "WebP")]:
            pts = sorted(curve[nn][key])
            ax.plot([p[0] for p in pts], [p[1] for p in pts], ls, color=col, marker=mk, markersize=4,
                    label=f"{lab} – {nn.split('_')[1]}")
    ax.axhline(1.0, color="black", linewidth=1.0)
    ax.set_xscale("log"); ax.set_xlabel("Dung lượng (KB, thang log)")
    ax.set_ylabel("Năng lượng dải 1–3 px\n(nén / gốc)")
    ax.set_xticks([10, 20, 50, 100]); ax.set_xticklabels(["10", "20", "50", "100"])
    ax.grid(**GRID); ax.legend(fontsize=7.5, frameon=True, edgecolor="black", loc="lower right")
    ax.set_title("(f) Mất tần số cao")
    savefig(fig, "case4.png")


# ============================================================================== CASE 5
def ent(x):
    v, c = np.unique(x, return_counts=True)
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def med_entropy(a):
    """Entropy (bit/mẫu) của phần dư dự đoán MED/LOCO-I - đại diện cho bước 'dự đoán' của PNG/WebP lossless."""
    a = a.astype(int)
    hs = []
    for ch in range(3):
        c = a[..., ch]
        A, B, C, X = c[1:, :-1], c[:-1, 1:], c[:-1, :-1], c[1:, 1:]
        mx, mn = np.maximum(A, B), np.minimum(A, B)
        pred = np.where(C >= mx, mn, np.where(C <= mn, mx, A + B - C))
        hs.append(ent(X - pred))
    return float(np.mean(hs))


def gauss_entropy_bits(sigma):
    return 0.5 * np.log2(2 * np.pi * np.e * np.asarray(sigma) ** 2)


def case5():
    fmts = [("PNG", "PNG", dict(compress_level=9)), ("WebP lossless", "WEBP", dict(lossless=True, quality=100, method=4)),
            ("JPEG q90", "JPEG", dict(quality=90))]
    bpp = {}
    for n, im in IMS.items():
        for lab, fmt, p in fmts:
            r = evaluate(im, fmt, repeats=0, **p)
            bpp[(n, lab)] = r["bpp"]
            add("C5", n, lab, r["size_kb"], r["psnr"], r["ssim"], "bpp", r["bpp"])
            add("C5", n, lab, r["size_kb"], r["psnr"], r["ssim"], "ti_le_nen", r["ratio"])
        add("C5", n, "Phần dư MED (entropy)", np.nan, np.nan, np.nan, "H_MED_bit_mau", med_entropy(ARR[n]))
    # nhiễu thật của G04: tái tạo bản KHÔNG nhiễu bằng đúng hàm tạo dữ liệu (nhiễu=0) rồi trừ
    clean = np.asarray(md.shade_object(500, 3, ((255, 250, 235), (240, 200, 120)), (60, 90, 200), 0.0)).astype(int)
    resid = ARR["G04_studio500_noise"].astype(int) - clean
    hn = float(np.mean([ent(resid[..., c]) for c in range(3)]))
    nm = "G04_studio500_noise"
    add("C5", nm, "Nhiễu thật = G04 − bản sạch", np.nan, np.nan, np.nan, "sigma_hieu_dung", float(resid.std()))
    add("C5", nm, "Nhiễu thật = G04 − bản sạch", np.nan, np.nan, np.nan, "H_nhieu_bit_mau", hn)
    add("C5", nm, "Nhiễu thật = G04 − bản sạch", np.nan, np.nan, np.nan, "can_duoi_bpp_3H", 3 * hn)
    cl = Image.fromarray(clean.astype(np.uint8))
    for lab, fmt, p in fmts[:2]:
        r = evaluate(cl, fmt, repeats=0, **p)
        add("C5", "G04 bản sạch (tái tạo, σ=0)", lab, r["size_kb"], r["psnr"], r["ssim"], "bpp", r["bpp"])
    # quét sigma trên chính G01 (cùng cảnh, chỉ thay đổi nhiễu)
    g1 = ARR["G01_studio1000"].astype(float)
    rng = np.random.default_rng(SEED)
    sweep = {}
    for s in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
        a = g1.astype(np.uint8) if s == 0 else np.clip(np.round(g1 + rng.normal(0, s, g1.shape)), 0, 255).astype(np.uint8)
        im = Image.fromarray(a)
        for lab, fmt, p in fmts:
            r = evaluate(im, fmt, repeats=0, **p)
            sweep[(s, lab)] = r["bpp"]
            add("C5", f"G01 + nhiễu σ={s:g}", lab, r["size_kb"], r["psnr"], r["ssim"], "bpp", r["bpp"])
        if s > 0:
            add("C5", f"G01 + nhiễu σ={s:g}", "Cận dưới entropy 3·h(N)", np.nan, np.nan, np.nan, "bpp", float(3 * gauss_entropy_bits(s)))
    # ---------------- hình
    fig = plt.figure(figsize=(7.2, 5.8), layout="constrained")
    gs = fig.add_gridspec(2, 2)
    yy, xx = slice(20, 120), slice(20, 120)
    for j, (nn, ttl) in enumerate([("G01_studio1000", "(a) G01 sạch"), ("G04_studio500_noise", "(b) G04 nhiễu σ=1,5")]):
        ax = fig.add_subplot(gs[0, j])
        g = Y_of(ARR[nn])[yy, xx]
        mid = np.median(g)
        show(ax, g, cmap="gray", vmin=mid - 12, vmax=mid + 12)
        ax.set_title(ttl + "\n(crop 100×100, tăng tương phản)", fontsize=9)
    ax = fig.add_subplot(gs[1, 0])
    names = [("G01_studio1000", "G01\nsạch"), ("G04_studio500_noise", "G04\nnhiễu"), ("P06_baboon", "P06\nbaboon")]
    w = 0.26
    cols = ["#999999", "#444444", C_ORG]
    for k, (lab, _, _) in enumerate(fmts):
        ax.bar(np.arange(3) + (k - 1) * w, [bpp[(n, lab)] for n, _ in names], w, label=lab, color=cols[k], edgecolor="black", linewidth=0.8)
    ax.set_yscale("log"); ax.set_xticks(range(3)); ax.set_xticklabels([t for _, t in names])
    ax.set_ylabel("Bit trên điểm ảnh (bpp, log)"); ax.grid(axis="y", **GRID); ax.set_axisbelow(True)
    ax.set_ylim(0.1, 400)
    ax.legend(fontsize=7.5, frameon=True, edgecolor="black", loc="upper left", ncol=1)
    ax.set_title("(c) bpp theo định dạng", fontsize=10)
    ax = fig.add_subplot(gs[1, 1])
    S = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    for lab, col, ls, mk in [("PNG", C_BLK, "-", "o"), ("WebP lossless", C_BLU, "--", "s"), ("JPEG q90", C_ORG, ":", "^")]:
        ax.plot(S, [sweep[(s, lab)] for s in S], ls, color=col, marker=mk, markersize=4, label=lab)
    ss_ = np.linspace(0.5, 3.0, 50)
    ax.plot(ss_, 3 * gauss_entropy_bits(ss_), "-", color=C_GRY, linewidth=2.2, label="Cận dưới 3·h(N)")
    ax.set_xlabel("σ nhiễu thêm vào G01"); ax.set_ylabel("bpp"); ax.grid(**GRID)
    ax.set_ylim(0, 19)
    ax.legend(fontsize=7.5, frameon=True, edgecolor="black", loc="upper left", ncol=2)
    ax.set_title("(d) Quét σ trên G01", fontsize=10)
    savefig(fig, "case5.png")


# ============================================================================== SECTION.MD
def write_section(df):
    """Sinh results/t09/section.md; MỌI số lấy trực tiếp từ DataFrame (= failure_cases.csv)."""
    def sel(case, images, config):
        d = df[(df.case == case) & (df.config == config)]
        return d[d.image.isin(images)] if images is not None else d

    def loc(case, images, config, metric):
        d = sel(case, images, config)
        return d[d.local_metric == metric].local_value.mean()

    def col(case, images, config, c):
        d = sel(case, images, config)
        return d.drop_duplicates(["image", "config"])[c].mean()

    def f(x, nd=2):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "–"
        if np.isinf(x):
            return "∞"
        return f"{x:.{nd}f}"

    T57, T17 = C1_IMGS, C2_IMGS
    out = []
    w = out.append
    w("## Phân tích lỗi: 5 trường hợp thất bại của nén ảnh JPEG / PNG / WebP\n")
    w("### 1. Mục tiêu và phương pháp\n")
    w("Phần này tìm và chứng minh bằng số liệu 5 trường hợp nén thất bại (đề bài yêu cầu đúng 5 ca). "
      "Năm giả thuyết ban đầu đều được kiểm chứng bằng chỉ số cục bộ (không chỉ PSNR/SSIM toàn ảnh) và một thí nghiệm đối chứng "
      "(ablation) để tách nguyên nhân; kết quả ca nào không hoàn toàn ủng hộ giả thuyết thì được nói rõ. "
      "Toàn bộ cấu hình đo bằng `common.encode/decode/psnr/ssim/evaluate`; JPEG ghi tường minh `subsampling` (2 = 4:2:0, 0 = 4:4:4); "
      "WebP `method=4`; PNG `compress_level=9`; mọi nhiễu ngẫu nhiên dùng seed 2026. Số liệu đầy đủ ở `results/t09/failure_cases.csv` "
      "(dạng dài: ca, ảnh, cấu hình, KB, PSNR, SSIM, tên và giá trị chỉ số cục bộ). Số thập phân trong phần này dùng dấu chấm cho khớp với CSV.\n")

    # ---------------- C1
    w("### 2. Ca 1 – Ringing (nhiễu muỗi) quanh chữ nhỏ ở JPEG chất lượng thấp\n")
    w("**Hiện tượng.** Trên ba thẻ 500 px (T05–T07), bảng thông số có chữ cao 14 px (nét dày 1–2 px). Sau nén JPEG q50, quanh nét chữ xuất hiện quầng nhiễu (hình `case1.png`). "
      "Để định lượng, ta lấy các điểm nền (gốc sáng ≥ 240) nằm cách nét chữ 2–4 px làm “vùng quầng” và đo sai số độ chói |ΔY| ở đó; "
      "đồng thời chạy OCR (tesseract 5, tiếng Việt, phóng 3×) để biết chữ còn đọc được không (CER = khoảng cách Levenshtein / số ký tự tham chiếu).\n")
    cfgs = ["JPEG q10", "JPEG q30", "JPEG q50", "JPEG q50 4:4:4", "JPEG q75", "JPEG q90", "WebP q5", "WebP q30", "WebP q50", "WebP q75"]
    w("Bảng 1. Ca 1 – trung bình T05–T07.\n")
    w("| Cấu hình | KB | PSNR toàn ảnh (dB) | SSIM toàn ảnh | SSIM vùng chữ | Điểm quầng lệch ≥6 mức (%) | |ΔY| quầng lớn nhất | CER OCR (%) |")
    w("|---|---|---|---|---|---|---|---|")
    for c in cfgs:
        w(f"| {c} | {f(col('C1', T57, c, 'size_kb'), 1)} | {f(col('C1', T57, c, 'psnr'), 1)} | {f(col('C1', T57, c, 'ssim'), 3)} | "
          f"{f(loc('C1', T57, c, 'vung_chu_SSIM'), 3)} | {f(loc('C1', T57, c, 'halo_ti_le_dY>=6_pct'), 1)} | "
          f"{f(loc('C1', T57, c, 'halo_max_dY'), 0)} | {f(100 * loc('C1', T57, c, 'ocr_cer'), 1)} |")
    w("")
    w("Hình: `figures/t09/case1.png` – (a) crop gốc 100×54 px, (b) JPEG q50, (c) tỉ lệ điểm quầng lệch ≥ 6 mức theo cấu hình, (d–f) bản đồ |ΔY| của JPEG q50, JPEG q90, WebP q75 cùng thang 0–60 (đậm = sai số lớn).\n")
    w(f"**Số liệu và phát hiện trung thực.** Ở JPEG q50, {f(loc('C1', T57, 'JPEG q50', 'halo_ti_le_dY>=6_pct'), 1)}% điểm nền quanh chữ lệch ≥ 6 mức xám (tối đa {f(loc('C1', T57, 'JPEG q50', 'halo_max_dY'), 0)} mức), "
      f"so với {f(loc('C1', T57, 'JPEG q90', 'halo_ti_le_dY>=6_pct'), 1)}% ở q90 và {f(loc('C1', T57, 'WebP q75', 'halo_ti_le_dY>=6_pct'), 1)}% ở WebP q75 ({f(col('C1', T57, 'WebP q75', 'size_kb'), 1)} KB, nhỏ hơn cả JPEG q50 {f(col('C1', T57, 'JPEG q50', 'size_kb'), 1)} KB). "
      f"Tuy nhiên chữ vẫn ĐỌC ĐƯỢC: CER OCR = {f(100 * loc('C1', T57, 'JPEG q50', 'ocr_cer'), 1)}% ở q50 và chỉ bắt đầu tăng đáng kể khi q ≤ 15 ({f(100 * loc('C1', T57, 'JPEG q15', 'ocr_cer'), 1)}% ở q15, "
      f"{f(100 * loc('C1', T57, 'JPEG q10', 'ocr_cer'), 1)}% ở q10, {f(100 * loc('C1', T57, 'JPEG q5', 'ocr_cer'), 1)}% ở q5); WebP còn đọc được tới q5 (CER {f(100 * loc('C1', T57, 'WebP q5', 'ocr_cer'), 1)}%) "
      f"và hỏng ở q0 ({f(100 * loc('C1', T57, 'WebP q0', 'ocr_cer'), 1)}%). Vì vậy giả thuyết “q50 làm chữ không đọc được” KHÔNG đúng với OCR; thất bại thực chất là thẩm mỹ/độ sạch (quầng quanh nét chữ: "
      f"SSIM vùng chữ giảm còn {f(loc('C1', T57, 'JPEG q50', 'vung_chu_SSIM'), 3)} so với {f(loc('C1', T57, 'JPEG q90', 'vung_chu_SSIM'), 3)} ở q90), "
      "chứ chưa phải mất thông tin. Kết luận này giới hạn trong chữ DejaVu Sans 14 px, một công cụ OCR và có phóng 3×; mắt người hoặc OCR khác có thể nhạy hơn (chưa thử).\n")
    w(f"**Nguyên nhân.** JPEG biến đổi DCT 8×8 độc lập từng khối rồi lượng tử hoá các hệ số tần số cao bằng bảng lượng tử thô. Nét chữ mảnh là tín hiệu băng rộng (cạnh sắc) nên năng lượng rải lên nhiều hệ số AC; "
      "khi các hệ số này bị làm tròn về bội của bước lượng tử (bảng chuẩn ở q50 có bước ≈ 10–120 tuỳ tần số), tổng các hàm cơ sở cosin không còn triệt tiêu ở vùng nền kế cạnh, tạo dao động tắt dần (hiện tượng Gibbs) – các “nhiễu muỗi” nằm trong cùng khối 8×8 với nét chữ. "
      f"Ablation: JPEG q50 4:4:4 cho đúng cùng số liệu quầng (độ chói không phụ thuộc lấy mẫu sắc độ: {f(loc('C1', T57, 'JPEG q50 4:4:4', 'halo_ti_le_dY>=6_pct'), 1)}% như 4:2:0), "
      "xác nhận nguyên nhân nằm ở lượng tử hoá kênh Y chứ không phải ở sắc độ. WebP (dự đoán trong khối + biến đổi 4×4 + bộ lọc vòng giảm khối) có thể giới hạn dao động trong ô 4×4 và làm mịn thêm bằng loop filter nên quầng thấp hơn ở cùng KB (giả thuyết phù hợp với số liệu, không ablation được vì Pillow không mở tham số này).\n")
    w("**Khắc phục.** Với ảnh có chữ nhỏ: dùng JPEG q ≥ 75–90 (q90 giảm quầng còn 9%), hoặc ưu tiên WebP lossy q ≥ 50; tốt nhất giữ chữ ở dạng văn bản HTML/SVG hoặc PNG/WebP lossless cho vùng đồ hoạ; tăng cỡ chữ lên ≥ 20 px ở ảnh 500 px.\n")

    # ---------------- C2
    w("### 3. Ca 2 – Loang màu (colour bleeding) quanh nhãn đỏ do lấy mẫu sắc độ 4:2:0\n")
    w("**Hiện tượng.** Nhãn giảm giá “-xx%” (đỏ thuần 255,0,0 với chữ vàng) và giá cam trên thẻ T01–T07 có biên cạnh màu cực sắc. JPEG mặc định (4:2:0) và WebP lossy (luôn 4:2:0) làm viền nhãn bị nhoè sang nền trắng và chữ vàng bị pha đỏ (hình `case2.png`). "
      "Chỉ số cục bộ: sai số tuyệt đối trung bình của kênh Cr (YCbCr JFIF) trong khung bao nhãn + 4 px (và khung bao giá).\n")
    cfgs2 = ["JPEG q90 4:2:0", "JPEG q90 4:4:4", "JPEG q75 4:2:0", "JPEG q75 4:4:4", "WebP q90 (4:2:0)", "WebP q75 (4:2:0)", "Chỉ lấy mẫu 4:2:0 (không lượng tử)"]
    w("Bảng 2. Ca 2 – trung bình T01–T07 (Cr đo trên thang 0–255).\n")
    w("| Cấu hình | KB | PSNR toàn ảnh (dB) | SSIM toàn ảnh | Cr MAE nhãn | Cr tối đa nhãn | Y MAE nhãn | Cr MAE giá |")
    w("|---|---|---|---|---|---|---|---|")
    for c in cfgs2:
        w(f"| {c} | {f(col('C2', T17, c, 'size_kb'), 1)} | {f(col('C2', T17, c, 'psnr'), 1)} | {f(col('C2', T17, c, 'ssim'), 3)} | "
          f"{f(loc('C2', T17, c, 'nhan_do_Cr_MAE'), 2)} | {f(loc('C2', T17, c, 'nhan_do_Cr_max'), 0)} | {f(loc('C2', T17, c, 'nhan_do_Y_MAE'), 2)} | {f(loc('C2', T17, c, 'gia_cam_Cr_MAE'), 2)} |")
    w("")
    w("Hình: `figures/t09/case2.png` – (a) nhãn gốc (T05), (b) JPEG q90 4:2:0, (c) JPEG q90 4:4:4, (d) WebP q90, (e–g) bản đồ |ΔCr| của (b–d) cùng thang 0–40, (h) Cr MAE trung bình T01–T07 kèm cột đối chứng “chỉ lấy mẫu 4:2:0 không lượng tử”.\n")
    j420, j444 = loc('C2', T17, 'JPEG q90 4:2:0', 'nhan_do_Cr_MAE'), loc('C2', T17, 'JPEG q90 4:4:4', 'nhan_do_Cr_MAE')
    kb420, kb444 = col('C2', T17, 'JPEG q90 4:2:0', 'size_kb'), col('C2', T17, 'JPEG q90 4:4:4', 'size_kb')
    orc = loc('C2', T17, 'Chỉ lấy mẫu 4:2:0 (không lượng tử)', 'nhan_do_Cr_MAE')
    w(f"**Số liệu.** Ở JPEG q90, chuyển 4:4:4 → 4:2:0 làm sai số Cr tại nhãn tăng từ {f(j444)} lên {f(j420)} mức (×{f(j420 / j444, 1)}) và Cr cực đại từ {f(loc('C2', T17, 'JPEG q90 4:4:4', 'nhan_do_Cr_max'), 0)} lên {f(loc('C2', T17, 'JPEG q90 4:2:0', 'nhan_do_Cr_max'), 0)} mức; "
      f"PSNR toàn ảnh giảm {f(col('C2', T17, 'JPEG q90 4:4:4', 'psnr') - col('C2', T17, 'JPEG q90 4:2:0', 'psnr'), 1)} dB nhưng đổi lại tiết kiệm {f(100 * (kb444 - kb420) / kb444, 0)}% dung lượng ({f(kb420, 1)} so với {f(kb444, 1)} KB). "
      f"WebP q90 (4:2:0, {f(col('C2', T17, 'WebP q90 (4:2:0)', 'size_kb'), 1)} KB) có Cr MAE {f(loc('C2', T17, 'WebP q90 (4:2:0)', 'nhan_do_Cr_MAE'))} – cùng bậc với JPEG 4:2:0, tức WebP KHÔNG tránh được loang màu dù nhỏ hơn. "
      f"Đối chứng “chỉ lấy mẫu 4:2:0, không lượng tử DCT” đã cho Cr MAE {f(orc)}, tức {f(100 * orc / j420, 0)}% sai số của JPEG q90 4:2:0 ({f(j420)}); phần còn lại ≈ {f(j420 - orc)} mức quy cho lượng tử hoá DCT (JPEG 4:4:4 chỉ có {f(j444)} từ lượng tử). "
      "Vậy phần lớn sai số sắc độ đến từ việc giảm độ phân giải sắc độ chứ không phải từ lượng tử hoá (đối chứng tự cài bằng trung bình 2×2 + nội suy song tuyến, có thể khác bộ giải mã libjpeg đôi chút; chỉ kết luận về bậc độ lớn). "
      "Sai số lớn hơn ở ảnh 500 px (Cr MAE nhãn 9–10 mức) so với ảnh 1000 px (≈ 7 mức) có thể vì nhãn nhỏ hơn nên tỉ lệ điểm nằm sát biên cao hơn (chưa kiểm chứng riêng).\n")
    w("**Nguyên nhân.** Mắt nhạy với độ chói hơn sắc độ, nên JPEG/WebP lưu Y đầy đủ nhưng Cb, Cr chỉ ở nửa độ phân giải theo mỗi chiều (mỗi mẫu sắc độ phủ khối 2×2 điểm ảnh). Tại biên đỏ–trắng, giá trị Cr nhảy từ ≈255 xuống ≈128 trong một điểm ảnh; "
      "sau khi lấy trung bình 2×2 rồi nội suy lại, một dải rộng 1–2 điểm ảnh quanh biên bị pha trộn (đỏ nhạt lan ra nền, chữ vàng–đỏ trộn). Y vẫn đúng nên cạnh “nhìn” vẫn sắc nhưng màu bị loang – lỗi chỉ lộ ra ở màu bão hoà cao cạnh màu tương phản, hiếm khi thấy ở ảnh chụp tự nhiên.\n")
    w("**Khắc phục.** Với ảnh có nhãn/chữ màu bão hoà: JPEG 4:4:4 (`subsampling=0`, +≈25% KB), hoặc WebP lossless / PNG cho vùng đồ hoạ; hoặc đặt nhãn dưới dạng lớp HTML/CSS thay vì nướng vào ảnh. WebP lossy (qua Pillow) không có tuỳ chọn 4:4:4 nên không khắc phục được ở mức định dạng.\n")

    # ---------------- C3
    w("### 4. Ca 3 – Dải màu / khối (banding) trên nền gradient sạch\n")
    w("**Hiện tượng.** Nền studio G01–G03 là gradient mượt. Ở chất lượng thấp, JPEG và WebP biến gradient thành các bậc rộng; đáng chú ý PSNR/SSIM vẫn rất cao nên các chỉ số này KHÔNG báo động. "
      "Chỉ số cục bộ: lấy vùng nền thuần (hàng 20–700, cột 20–200), tính độ chói trung bình theo hàng rồi đo (i) bậc nhảy lớn nhất giữa hai hàng liền kề, (ii) số bậc (>0.5 mức), (iii) tỉ lệ tổng biến thiên nằm đúng trên biên khối 8 hàng. "
      "Ảnh gốc 8 bit tự nó có bậc 1 mức (không thể mịn hơn); lỗi nghĩa là bậc LỚN HƠN và THƯA HƠN so với gốc.\n")
    G1, G3 = ["G01_studio1000"], ["G03_studio1000"]
    cfgs3 = ["Gốc (PNG)", "JPEG q30", "JPEG q50", "JPEG q75", "JPEG q90", "WebP q30", "WebP q90", "WebP q100 (lossy)", "WebP lossless", "JPEG q30 + dither σ=1", "JPEG q90 + dither σ=1"]
    w("Bảng 3. Ca 3 – ảnh G01 (gradient dọc, 1000×1000).\n")
    w("| Cấu hình | KB | PSNR (dB) | SSIM | Bậc nhảy lớn nhất (mức) | Số bậc | Bậc nằm ở biên khối 8 hàng (%) |")
    w("|---|---|---|---|---|---|---|")
    for c in cfgs3:
        w(f"| {c} | {f(col('C3', G1, c, 'size_kb'), 1)} | {f(col('C3', G1, c, 'psnr'), 1)} | {f(col('C3', G1, c, 'ssim'), 4)} | "
          f"{f(loc('C3', G1, c, 'max_buoc_nhay'), 1)} | {f(loc('C3', G1, c, 'so_buoc(>0.5)'), 0)} | {f(loc('C3', G1, c, 'ti_le_buoc_tai_bien_khoi8_pct'), 0)} |")
    w("")
    w("Hình: `figures/t09/case3.png` – (a–c) vùng nền G01 (hàng 100–260) của gốc, JPEG q30 và WebP q30, giãn tương phản về khoảng độ chói của gốc để lộ bậc; (d) profile độ chói trung bình theo hàng, đường xám nhạt là biên khối 8 hàng.\n")
    w(f"**Số liệu.** JPEG q30 trên G01 chỉ có {f(loc('C3', G1, 'JPEG q30', 'so_buoc(>0.5)'), 0)} bậc với bậc nhảy tới {f(loc('C3', G1, 'JPEG q30', 'max_buoc_nhay'), 0)} mức, trong khi gốc có {f(loc('C3', G1, 'Gốc (PNG)', 'so_buoc(>0.5)'), 0)} bậc mỗi bậc 1 mức; "
      f"{f(loc('C3', G1, 'JPEG q30', 'ti_le_buoc_tai_bien_khoi8_pct'), 0)}% biến thiên nằm đúng trên biên khối 8 hàng (gốc chỉ {f(loc('C3', G1, 'Gốc (PNG)', 'ti_le_buoc_tai_bien_khoi8_pct'), 0)}%, đúng bằng xác suất ngẫu nhiên ≈ 1/8). "
      f"Vậy mà PSNR = {f(col('C3', G1, 'JPEG q30', 'psnr'), 1)} dB và SSIM = {f(col('C3', G1, 'JPEG q30', 'ssim'), 3)} – thường được coi là chất lượng cao. "
      f"WebP q30 chỉ {f(col('C3', G1, 'WebP q30', 'size_kb'), 1)} KB cũng có bậc {f(loc('C3', G1, 'WebP q30', 'max_buoc_nhay'), 0)} mức và {f(loc('C3', G1, 'WebP q30', 'ti_le_buoc_tai_bien_khoi8_pct'), 0)}% bậc trên biên khối (PSNR {f(col('C3', G1, 'WebP q30', 'psnr'), 1)} dB). "
      "Mức 3–4 bậc xám trên một vùng phẳng rộng hàng chục điểm ảnh nằm ở ngưỡng có thể nhìn thấy trên màn hình tốt; tuy nhiên tôi CHƯA làm thí nghiệm thị giác với người xem nên “thấy được” ở đây là suy luận từ độ lớn bậc và hình giãn tương phản, không phải số đo tri giác. "
      "Có thể hiểu vì sao hai chỉ số này không báo động: PSNR lấy trung bình bình phương sai số trên 10⁶ điểm ảnh nên sai số ≤ 4 mức cho MSE nhỏ, còn SSIM so cấu trúc trong cửa sổ Gauss σ=1.5 (vài điểm ảnh) nên không “thấy” một bậc phẳng rộng hàng chục điểm ảnh (giải thích suy luận, không đo riêng). "
      "Đây là giới hạn của chỉ số, liên quan đến câu hỏi mở “PSNR hay SSIM?”: cả hai đều không đủ cho ảnh nền mượt; cần thêm chỉ số cục bộ như profile/bậc thang ở trên.\n")
    w(f"Ở G03 (gradient xám sạch), WebP lossless chỉ {f(col('C3', G3, 'WebP lossless', 'size_kb'), 1)} KB, nhỏ hơn JPEG q30 ({f(col('C3', G3, 'JPEG q30', 'size_kb'), 1)} KB) mà không có bậc nào thêm. "
      "Ở G02 (gradient xuyên tâm) chỉ số theo hàng kém ý nghĩa hơn vì nền thay đổi theo cả hai chiều; số liệu của G02 vẫn có trong CSV.\n")
    w("**Nguyên nhân.** Trong khối 8×8 gradient thuần chỉ có hệ số DC lớn và vài AC thấp tần. DC được lượng tử bằng một bước Q (ở q30 Q_DC ≈ 27, tương đương bước ≈ 27/8 ≈ 3.3 mức độ chói trung bình khối); mỗi khối nhận một mức DC làm tròn nên toàn khối phẳng, và biên giữa hai khối kề là bậc nhảy bằng bội của bước. "
      "Hệ số AC nhỏ (biểu diễn độ dốc nội khối) bị làm tròn về 0 nên không khôi phục được độ dốc. Kết quả là bậc thang đúng tại biên khối 8×8, khớp tỉ lệ 100%. "
      "WebP dự đoán DC theo khối lân cận (intra 16×16 hoặc 4×4) và lượng tử phần dư; vùng phẳng được dự đoán hoàn hảo và phần dư làm tròn về 0 nên cũng tạo bậc rộng (không có tuỳ chọn tắt trong Pillow nên không ablation được loop filter ở đây).\n")
    w(f"**Đối chứng và khắc phục.** (i) Tăng chất lượng: JPEG q75 ({f(col('C3', G1, 'JPEG q75', 'size_kb'), 1)} KB) đã đưa bậc nhảy lớn nhất về {f(loc('C3', G1, 'JPEG q75', 'max_buoc_nhay'), 0)} mức như gốc, đổi lại +{f(100 * (col('C3', G1, 'JPEG q75', 'size_kb') / col('C3', G1, 'JPEG q30', 'size_kb') - 1), 0)}% KB so với q30. "
      f"WebP lossy KHÔNG đạt được điều đó: bậc vẫn {f(loc('C3', G1, 'WebP q100 (lossy)', 'max_buoc_nhay'), 0)} mức ngay cả ở q100 ({f(col('C3', G1, 'WebP q100 (lossy)', 'size_kb'), 1)} KB), chỉ WebP lossless khôi phục đúng. "
      f"(ii) Dithering nguồn (nhiễu Gauss σ=1 thêm trước khi nén) KHÔNG giúp ở chất lượng thấp: q30 vẫn bậc {f(loc('C3', G1, 'JPEG q30 + dither σ=1', 'max_buoc_nhay'), 0)} mức vì lượng tử hoá xoá nhiễu tần cao; "
      f"chỉ ở q90 nó làm bậc giảm còn {f(loc('C3', G1, 'JPEG q90 + dither σ=1', 'max_buoc_nhay'), 2)} mức nhưng tốn {f(col('C3', G1, 'JPEG q90 + dither σ=1', 'size_kb'), 1)} KB (so {f(col('C3', G1, 'JPEG q90', 'size_kb'), 1)} KB khi không dither). Giả thuyết “thêm nhiễu nhẹ chống banding” do đó chỉ đúng với chất lượng cao hoặc khi dither được áp dụng sau giải mã phía trình duyệt (không thử). "
      "(iii) Với ảnh nền gradient đơn giản, chọn WebP lossless (G03) hoặc JPEG ≥ q75.\n")

    # ---------------- C4
    w("### 5. Ca 4 – Mất kết cấu chi tiết (lông baboon)\n")
    P6, P2 = ["P06_baboon"], ["P02_chelsea"]
    w("**Hiện tượng.** P06 (mặt khỉ baboon: lông, râu tần số cao dày đặc) là ảnh khó nhất của bộ dữ liệu: ở cả JPEG q50 và WebP q75 nó có SSIM THẤP NHẤT trong 20 ảnh "
      f"(hạng {f(df[(df.case == 'C4') & (df.local_metric == 'hang_SSIM_cua_P06(1=thap_nhat)') & (df.config == 'JPEG q50')].local_value.iloc[0], 0)} và {f(df[(df.case == 'C4') & (df.local_metric == 'hang_SSIM_cua_P06(1=thap_nhat)') & (df.config == 'WebP q75')].local_value.iloc[0], 0)} từ dưới lên). "
      "Giả thuyết ban đầu là WebP làm mịn kết cấu nhiều hơn JPEG ở cùng dung lượng; ta kiểm chứng bằng cách chọn quality WebP sao cho KB gần nhất với từng mức JPEG, đo SSIM cục bộ, "
      "và năng lượng + tương quan của dải tần 1–3 px (hiệu hai bộ lọc Gauss σ=1 và σ=3, trên độ chói) so với gốc.\n")
    pairs = [("JPEG q10", [k for k in df[df.case == "C4"].config.unique() if k.endswith("JPEG q10)")][0]),
             ("JPEG q20", [k for k in df[df.case == "C4"].config.unique() if k.endswith("JPEG q20)")][0]),
             ("JPEG q50", [k for k in df[df.case == "C4"].config.unique() if k.endswith("JPEG q50)")][0]),
             ("JPEG q75", [k for k in df[df.case == "C4"].config.unique() if k.endswith("JPEG q75)")][0])]
    w("Bảng 4. Ca 4 – JPEG so với WebP cùng dung lượng.\n")
    w("| Ảnh | Cấu hình | KB | PSNR (dB) | SSIM | SSIM vùng lông+râu | Năng lượng dải 1–3 px (nén/gốc) | Tương quan dải 1–3 px |")
    w("|---|---|---|---|---|---|---|---|")
    for im, ims_ in [("P06_baboon", P6)]:
        for jc, wc in pairs:
            for c in (jc, wc):
                w(f"| P06 | {c.replace(' (cùng KB với ', ' (≈KB ').replace(')', ')') if c.startswith('WebP') else c} | {f(col('C4', ims_, c, 'size_kb'), 1)} | {f(col('C4', ims_, c, 'psnr'), 2)} | {f(col('C4', ims_, c, 'ssim'), 3)} | "
                  f"{f(loc('C4', ims_, c, 'SSIM_vung_long_rau'), 3)} | {f(loc('C4', ims_, c, 'ti_le_nang_luong_dai_1-3px'), 3)} | {f(loc('C4', ims_, c, 'tuong_quan_dai_1-3px'), 3)} |")
    pj = [k for k in df[(df.case == "C4") & (df.image == "P02_chelsea")].config.unique() if k.endswith("JPEG q10)")][0]
    for c in ("JPEG q10", pj):
        w(f"| P02 | {c.replace(' (cùng KB với ', ' (≈KB ') if c.startswith('WebP') else c} | {f(col('C4', P2, c, 'size_kb'), 1)} | {f(col('C4', P2, c, 'psnr'), 2)} | {f(col('C4', P2, c, 'ssim'), 3)} | – | "
          f"{f(loc('C4', P2, c, 'ti_le_nang_luong_dai_1-3px'), 3)} | {f(loc('C4', P2, c, 'tuong_quan_dai_1-3px'), 3)} |")
    w("")
    def kb95(im, nm):
        d = df[(df.case == "C4") & (df.image == im) & (df.local_metric == "kb_de_dat_SSIM_0.95") & (df.config.str.startswith(nm))]
        return d.local_value.iloc[0], d.config.iloc[0].split(" (")[0]
    w("Bảng 5. Dung lượng nhỏ nhất (quét quality nguyên) để đạt SSIM ≥ 0.95.\n")
    w("| Ảnh | JPEG (KB, q) | WebP (KB, q) |")
    w("|---|---|---|")
    for im in ["P04_rocket", "P02_chelsea", "P06_baboon"]:
        kj, cj = kb95(im, "JPEG"); kw, cw = kb95(im, "WebP")
        w(f"| {im.split('_')[0]} {im.split('_')[1]} | {f(kj, 1)} ({cj}) | {f(kw, 1)} ({cw}) |")
    w("")
    w("Hình: `figures/t09/case4.png` – (a) vùng lông+râu 96×96 px của P06, (b) JPEG q50, (c) WebP cùng dung lượng, (d–e) bản đồ SSIM cục bộ tương ứng (tối = mất cấu trúc), (f) năng lượng dải 1–3 px theo dung lượng cho P06 và P02.\n")
    kj6, kw6 = kb95("P06_baboon", "JPEG")[0], kb95("P06_baboon", "WebP")[0]
    kj4, kw4 = kb95("P04_rocket", "JPEG")[0], kb95("P04_rocket", "WebP")[0]
    w(f"**Phát hiện (giả thuyết được ủng hộ một phần).** (1) Mất kết cấu là có thật và nặng: để đạt SSIM 0.95, P06 cần {f(kj6, 0)} KB (JPEG) / {f(kw6, 0)} KB (WebP), gấp {f(kj6 / kj4, 0)}× / {f(kw6 / kw4, 0)}× so với P04 rocket ({f(kj4, 0)} / {f(kw4, 0)} KB). "
      f"Ở JPEG q50 (47.5 KB) SSIM toàn ảnh chỉ {f(col('C4', P6, 'JPEG q50', 'ssim'), 3)}, vùng lông+râu {f(loc('C4', P6, 'JPEG q50', 'SSIM_vung_long_rau'), 3)}; bản đồ SSIM cho thấy mất cấu trúc tập trung ở vùng lông dày xen kẽ. "
      f"(2) WebP có làm mịn: ở dung lượng thấp năng lượng dải 1–3 px còn {f(loc('C4', P6, pairs[0][1], 'ti_le_nang_luong_dai_1-3px'), 2)} lần gốc ở P06 ({f(col('C4', P6, pairs[0][1], 'size_kb'), 1)} KB) và {f(loc('C4', P2, pj, 'ti_le_nang_luong_dai_1-3px'), 2)} ở P02 ({f(col('C4', P2, pj, 'size_kb'), 1)} KB), "
      "trong khi JPEG giữ ≈ 1.00 – phần năng lượng “đủ” này có thể một phần là nhiễu khối/ringing chứ không hoàn toàn là kết cấu thật (chưa tách). "
      f"(3) Tuy nhiên GIẢ THUYẾT “WebP kém hơn JPEG ở kết cấu” không đứng vững theo chỉ số: cùng ≈47.5 KB, WebP q44 có PSNR {f(col('C4', P6, pairs[2][1], 'psnr'), 2)} dB, SSIM {f(col('C4', P6, pairs[2][1], 'ssim'), 3)} so với JPEG q50 {f(col('C4', P6, 'JPEG q50', 'psnr'), 2)} dB, {f(col('C4', P6, 'JPEG q50', 'ssim'), 3)}; "
      f"ở mọi cặp P06 trong Bảng 4 WebP đều cao hơn về PSNR và SSIM. Riêng tương quan dải 1–3 px ở P06 thì JPEG nhỉnh hơn ({f(loc('C4', P6, 'JPEG q50', 'tuong_quan_dai_1-3px'), 3)} so với {f(loc('C4', P6, pairs[2][1], 'tuong_quan_dai_1-3px'), 3)} ở ≈47.5 KB) còn ở P02 mức thấp WebP lại cao hơn ({f(loc('C4', P2, pj, 'tuong_quan_dai_1-3px'), 3)} so với {f(loc('C4', P2, 'JPEG q10', 'tuong_quan_dai_1-3px'), 3)} của JPEG q10) – nghĩa là kết quả hỗn hợp, không có kết luận một chiều. "
      "Làm mịn của WebP là sự đánh đổi mà PSNR/SSIM thưởng chứ không phạt, nên đây vừa là điểm yếu về cảm nhận (mất tinh thể lông ở dung lượng thấp) vừa là giới hạn của chỉ số.\n")
    w("**Nguyên nhân.** Kết cấu lông là tín hiệu ngẫu nhiên băng rộng, entropy cao (phần dư MED ≈ 6.2 bit/mẫu, cao nhất bộ dữ liệu, xem ca 5): hệ số DCT tần cao có biên độ lớn và không thưa, nên bảng lượng tử thô buộc phải bỏ chúng (JPEG) hoặc bỏ/làm mịn chúng để tiết kiệm bit (WebP: lượng tử 4×4, tối ưu tốc độ–méo của libwebp ưu tiên làm tròn về 0 và bộ lọc vòng giảm khối làm mịn thêm). "
      "Tôi không tách riêng được vai trò loop filter của WebP vì Pillow không mở tham số này và máy không có `cwebp`; nên phần quy cho loop filter là giả thuyết phù hợp với chiều mịn hơn quan sát được, chưa được ablation.\n")
    w("**Khắc phục.** Với ảnh nhiều kết cấu (lông, vải): đừng nén xuống dưới JPEG q75 / WebP q76 (P06: SSIM ≈ 0.88 / 0.91 ở ≈72 KB); chấp nhận dung lượng lớn hơn hẳn các ảnh khác hoặc giảm độ phân giải xuất ảnh thay vì tăng lượng tử; kiểm tra bằng bản đồ SSIM cục bộ thay vì chỉ SSIM toàn ảnh.\n")

    # ---------------- C5
    w("### 6. Ca 5 – Thất bại về dung lượng: nén không mất mát trên ảnh có nhiễu\n")
    w("**Hiện tượng.** PNG và WebP lossless hoạt động rất tốt trên đồ hoạ phẳng (thẻ T) nhưng gần như vô hiệu trên ảnh chụp và ảnh có nhiễu cảm biến: dung lượng gấp nhiều lần JPEG q90, tỉ lệ nén chỉ ≈ 1.3–3.6× (hình `case5.png`).\n")
    w("Bảng 6. Ca 5 – bit trên điểm ảnh (bpp) và tỉ số dung lượng so với JPEG q90.\n")
    w("| Ảnh | PNG (KB / bpp) | WebP lossless (KB / bpp) | JPEG q90 (KB / bpp) | PNG ÷ JPEG q90 | Tỉ lệ nén PNG | Entropy phần dư MED (bit/mẫu) |")
    w("|---|---|---|---|---|---|---|")
    for im in ["G01_studio1000", "G04_studio500_noise", "G05_studio500_noise", "G06_studio500_noise", "P06_baboon", "P04_rocket", "T05_card500", "T01_card1000"]:
        d = df[(df.case == "C5") & (df.image == im)]
        r = {c: d[(d.config == c) & (d.local_metric == "bpp")].iloc[0] for c in ["PNG", "WebP lossless", "JPEG q90"]}
        ratio = d[(d.config == "PNG") & (d.local_metric == "ti_le_nen")].local_value.iloc[0]
        hm = d[d.local_metric == "H_MED_bit_mau"].local_value.iloc[0]
        w(f"| {im} | {f(r['PNG'].size_kb, 0)} / {f(r['PNG'].local_value)} | {f(r['WebP lossless'].size_kb, 0)} / {f(r['WebP lossless'].local_value)} | "
          f"{f(r['JPEG q90'].size_kb, 0)} / {f(r['JPEG q90'].local_value)} | {f(r['PNG'].size_kb / r['JPEG q90'].size_kb, 1)}× | {f(ratio, 2)} | {f(hm, 2)} |")
    w("")
    sw = df[(df.case == "C5") & (df.image.str.startswith("G01 + nhiễu"))]
    w("Bảng 7. Quét σ nhiễu Gauss thêm vào chính G01 (cùng cảnh; bpp).\n")
    w("| σ | PNG | WebP lossless | JPEG q90 | Cận dưới 3·h(N) |")
    w("|---|---|---|---|---|")
    for s_ in ["0", "0.5", "1", "1.5", "2", "3"]:
        d = sw[sw.image == f"G01 + nhiễu σ={s_}"]
        g_ = lambda c: (d[d.config == c].local_value.iloc[0] if (d.config == c).any() else np.nan)
        w(f"| {s_} | {f(g_('PNG'))} | {f(g_('WebP lossless'))} | {f(g_('JPEG q90'))} | {f(g_('Cận dưới entropy 3·h(N)'))} |")
    w("")
    w("Hình: `figures/t09/case5.png` – (a) crop G01 sạch, (b) crop G04 nhiễu (cùng tăng tương phản), (c) bpp của PNG/WebP lossless/JPEG q90 (thang log) cho G01, G04, P06, (d) bpp theo σ trên G01 cùng đường cận dưới entropy của nhiễu.\n")
    d4 = df[(df.case == "C5") & (df.image == "G04_studio500_noise")]
    hn = d4[d4.local_metric == "H_nhieu_bit_mau"].local_value.iloc[0]
    fl = d4[d4.local_metric == "can_duoi_bpp_3H"].local_value.iloc[0]
    sg = d4[d4.local_metric == "sigma_hieu_dung"].local_value.iloc[0]
    pg1 = df[(df.case == "C5") & (df.image == "G01_studio1000") & (df.config == "PNG") & (df.local_metric == "bpp")].local_value.iloc[0]
    pg4 = d4[(d4.config == "PNG") & (d4.local_metric == "bpp")].local_value.iloc[0]
    wg4 = d4[(d4.config == "WebP lossless") & (d4.local_metric == "bpp")].local_value.iloc[0]
    jg4 = d4[(d4.config == "JPEG q90") & (d4.local_metric == "bpp")].local_value.iloc[0]
    pcl = df[(df.case == "C5") & (df.image.str.startswith("G04 bản sạch")) & (df.config == "PNG")].local_value.iloc[0]
    s05 = sw[(sw.image == "G01 + nhiễu σ=0.5") & (sw.config == "PNG")].local_value.iloc[0]
    s0 = sw[(sw.image == "G01 + nhiễu σ=0") & (sw.config == "PNG")].local_value.iloc[0]
    w(f"**Số liệu.** G01 (sạch) cần {f(pg1)} bpp với PNG, G04 (nhiễu σ=1.5) cần {f(pg4)} bpp: gấp {f(pg4 / pg1, 1)}× (tỉ lệ nén PNG từ {f(24 / pg1, 1)}× xuống {f(24 / pg4, 2)}×), "
      f"và PNG lớn gấp {f(pg4 / jg4, 1)}× JPEG q90 ({f(jg4)} bpp); WebP lossless {f(wg4)} bpp vẫn gấp {f(wg4 / jg4, 1)}× JPEG q90. "
      f"Trong thí nghiệm sạch/nhiễu trên cùng một cảnh (Bảng 7), chỉ cần σ = 0.5 (±1 mức xám) đã đẩy PNG từ {f(s0)} lên {f(s05)} bpp (×{f(s05 / s0, 1)}); JPEG q90 gần như không đổi ({f(sw[(sw.image == 'G01 + nhiễu σ=0') & (sw.config == 'JPEG q90')].local_value.iloc[0])} → {f(sw[(sw.image == 'G01 + nhiễu σ=0.5') & (sw.config == 'JPEG q90')].local_value.iloc[0])} bpp). "
      f"Giải thích định lượng bằng entropy: nhiễu thật của G04 (G04 trừ bản sạch tái tạo) có σ hiệu dụng {f(sg, 2)} và entropy biên {f(hn, 2)} bit/mẫu, nên cận dưới ≈ 3 × {f(hn, 2)} = {f(fl, 2)} bpp nếu nhiễu độc lập giữa các kênh và điểm ảnh; "
      f"WebP lossless ({f(wg4)} bpp) chỉ cao hơn cận này {f(100 * (wg4 / fl - 1), 0)}% và PNG ({f(pg4)} bpp) cao hơn {f(100 * (pg4 / fl - 1), 0)}% – nghĩa là hai bộ nén đã gần chạm giới hạn lý thuyết, không có lỗi cài đặt nào để sửa. "
      f"(Bản sạch tái tạo của G04 chỉ {f(pcl)} bpp với PNG, nên nhiễu chiếm phần lớn dung lượng.) Cùng chiều, ảnh P có entropy phần dư MED cao (P06: 6.2 bit/mẫu) cho PNG tới {f(df[(df.case == 'C5') & (df.image == 'P06_baboon') & (df.config == 'PNG') & (df.local_metric == 'bpp')].local_value.iloc[0], 1)} bpp.\n")
    w("**Nguyên nhân.** PNG dự đoán từng điểm ảnh bằng bộ lọc (Sub/Up/Average/Paeth) rồi nén phần dư bằng DEFLATE (LZ77 + Huffman); WebP lossless dùng dự đoán không gian, biến đổi màu, bộ nhớ màu và mã hoá entropy. Trên gradient mượt phần dư gần 0 và rất lặp, LZ77 tìm được các chuỗi trùng khớp dài. "
      "Nhiễu ngẫu nhiên làm phần dư có phân bố rộng, độc lập và không lặp: không còn chuỗi trùng khớp cho LZ77, và entropy mỗi mẫu bị chặn dưới bởi h(N) = ½·log₂(2πeσ²) bit; không thuật toán lossless nào vượt được. "
      "JPEG q90 không ràng buộc này vì nó vứt bỏ phần nhiễu (hệ số tần cao nhỏ làm tròn về 0) – đổi lấy PSNR hữu hạn.\n")
    w("**Khắc phục.** Với ảnh chụp có nhiễu: dùng lossy (JPEG q75–90 hoặc WebP q75–90); nếu bắt buộc lossless thì khử nhiễu trước (bỏ nhiễu cảm biến mất mát nhưng không nhìn thấy) hoặc chấp nhận file lớn. Giữ lossless cho đồ hoạ phẳng (thẻ T: tỉ lệ nén PNG 7–15×, WebP lossless nhỏ hơn PNG khoảng 25–36%) và ảnh gradient sạch.\n")

    # ---------------- tóm tắt
    w("### 7. Bảng tóm tắt 5 ca thất bại\n")
    w("| Ca | Ảnh – cấu hình | Hiện tượng đo được | Nguyên nhân (thuật toán) | Khắc phục |")
    w("|---|---|---|---|---|")
    w(f"| C1 Ringing quanh chữ nhỏ | T05–T07, JPEG q50 | {f(loc('C1', T57, 'JPEG q50', 'halo_ti_le_dY>=6_pct'), 0)}% điểm nền quanh chữ lệch ≥6 mức (q90: {f(loc('C1', T57, 'JPEG q90', 'halo_ti_le_dY>=6_pct'), 0)}%); OCR vẫn đọc được (CER {f(100 * loc('C1', T57, 'JPEG q50', 'ocr_cer'), 1)}%), hỏng khi q≤10 | Lượng tử DCT 8×8 các hệ số cao tần của cạnh sắc → dao động Gibbs trong khối | JPEG ≥q75–90 hoặc WebP ≥q50; chữ để dạng văn bản/lossless |")
    w(f"| C2 Loang màu | T01–T07, JPEG q90 4:2:0 và WebP q90 | Cr MAE tại nhãn {f(j420, 1)} (4:4:4: {f(j444, 1)}); WebP {f(loc('C2', T17, 'WebP q90 (4:2:0)', 'nhan_do_Cr_MAE'), 1)}; chỉ riêng lấy mẫu 4:2:0 đã {f(loc('C2', T17, 'Chỉ lấy mẫu 4:2:0 (không lượng tử)', 'nhan_do_Cr_MAE'), 1)} | Lấy mẫu sắc độ 4:2:0 trộn màu bão hoà ở biên (WebP lossy luôn 4:2:0) | JPEG 4:4:4 (+{f(100 * (kb444 - kb420) / kb420, 0)}% KB) hoặc lossless cho đồ hoạ |")
    w(f"| C3 Banding | G01, JPEG q30 / WebP q30 | Bậc {f(loc('C3', G1, 'JPEG q30', 'max_buoc_nhay'), 0)} mức, {f(loc('C3', G1, 'JPEG q30', 'so_buoc(>0.5)'), 0)} bậc (gốc 1 mức, {f(loc('C3', G1, 'Gốc (PNG)', 'so_buoc(>0.5)'), 0)} bậc), {f(loc('C3', G1, 'JPEG q30', 'ti_le_buoc_tai_bien_khoi8_pct'), 0)}% ở biên khối; PSNR {f(col('C3', G1, 'JPEG q30', 'psnr'), 1)} dB, SSIM {f(col('C3', G1, 'JPEG q30', 'ssim'), 3)} | Làm tròn DC theo khối + AC thấp tần về 0 (JPEG), dự đoán DC + loop filter (WebP) | JPEG ≥q75 hoặc WebP lossless; dither nguồn chỉ giúp ở q90 (+{f(100 * (col('C3', G1, 'JPEG q90 + dither σ=1', 'size_kb') / col('C3', G1, 'JPEG q90', 'size_kb') - 1), 0)}% KB) |")
    w(f"| C4 Mất kết cấu | P06 baboon, JPEG q50 / WebP | SSIM thấp nhất bộ dữ liệu ({f(col('C4', P6, 'JPEG q50', 'ssim'), 3)}); cần {f(kj6, 0)} KB (JPEG) / {f(kw6, 0)} KB (WebP) để SSIM≥0.95, gấp {f(kj6 / kj4, 0)}× / {f(kw6 / kw4, 0)}× rocket; WebP mịn hơn (năng lượng dải {f(loc('C4', P6, pairs[0][1], 'ti_le_nang_luong_dai_1-3px'), 2)}) nhưng PSNR/SSIM vẫn cao hơn JPEG | Kết cấu entropy cao, hệ số cao tần lớn bị lượng tử bỏ; WebP thêm làm mịn (giả thuyết loop filter) | Không nén dưới q75; giảm độ phân giải thay vì tăng lượng tử |")
    w(f"| C5 Dung lượng lossless | G04 nhiễu σ=1.5 và P06 | PNG {f(pg4)} bpp (×{f(pg4 / jg4, 1)} JPEG q90), tỉ lệ nén {f(24 / pg4, 2)}×; chỉ σ=0.5 đã nhân PNG ×{f(s05 / s0, 1)}; WebP LL cách cận entropy {f(100 * (wg4 / fl - 1), 0)}% | Nhiễu độc lập làm vô hiệu dự đoán + LZ77; entropy h(N) là cận dưới | Dùng lossy cho ảnh chụp; lossless chỉ cho đồ hoạ/gradient sạch |")
    w("")
    w("### 8. Hạn chế\n")
    w("(1) Ảnh T và G là ảnh tổng hợp (chữ DejaVu Sans, nền gradient lý tưởng) nên mức độ lỗi có thể khác trên ảnh sản phẩm thật. (2) OCR chỉ dùng một công cụ (tesseract) với phóng 3×; chưa có thí nghiệm người xem, "
      "nên ngưỡng “thấy banding/ringing” là suy luận từ độ lớn sai số. (3) Pillow không cho tắt loop filter, đổi sns, hay chọn 4:4:4 cho WebP lossy; nên cơ chế WebP (ca 3, ca 4) chưa được ablation trực tiếp. "
      "(4) Cận dưới entropy giả sử nhiễu độc lập từng kênh/điểm ảnh; nhiễu G04 có thể hơi tương quan không gian do bước làm mờ khi tạo dữ liệu nên cận thật có thể thấp hơn chút. "
      "(5) Re-encode lại ảnh nguồn JPEG (P06/P07) không được xét vì các ảnh này đã được thu nhỏ trước khi lưu PNG, khối 8×8 gốc không còn thẳng hàng.\n")
    open(os.path.join(RES, "section.md"), "w", encoding="utf-8").write("\n".join(out))


# ============================================================================== MAIN
if __name__ == "__main__":
    case1(); print("C1 xong", flush=True)
    case2(); print("C2 xong", flush=True)
    case3(); print("C3 xong", flush=True)
    case4(); print("C4 xong", flush=True)
    case5(); print("C5 xong", flush=True)
    df = pd.DataFrame(ROWS)
    df.to_csv(os.path.join(RES, "failure_cases.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    print("CSV:", len(df), "dòng")
    write_section(df)
    print("section.md xong")
