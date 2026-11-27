"""t01 - Bài toán & Dữ liệu: thống kê đặc trưng của 20 ảnh gốc (Chương 1).

Mục đích: định lượng "độ khó nén" của từng ảnh TRƯỚC khi nén, để các chương sau giải thích
được vì sao nhóm ảnh này nén tốt/kém hơn nhóm kia. Mọi đặc trưng tính trên ảnh gốc PNG.

Các đặc trưng (và lý do chọn):
1. raw_kb      : dung lượng ảnh thô W*H*3 byte / 1024 -> mốc 100 % để tính tỉ số nén.
2. entropy_y   : entropy Shannon bậc 0 của kênh độ sáng Y (bit/pixel).
                 Y = 0,299R + 0,587G + 0,114B (ITU-R BT.601, do Pillow convert('L') làm tròn về
                 uint8, trùng định nghĩa Y của JPEG). H = -sum p_k log2 p_k trên histogram 256 mức.
                 Là giới hạn dưới của mã hoá entropy KHÔNG xét tương quan giữa các pixel lân cận
                 (Shannon 1948) -> chỉ là chặn dưới "mô hình bậc 0"; PNG/WebP lossless dùng dự đoán
                 pixel nên có thể đi dưới giá trị này.
3. edge_density: tỉ lệ pixel biên Canny trên ảnh xám (cv2.Canny, ngưỡng thấp/cao = 100/200;
                 tỉ lệ 1:2 theo khuyến nghị của Canny, 200 ~ biên rõ nét có biên độ gradient lớn,
                 đủ cao để bỏ qua nhiễu σ = 1,5 của nhóm G). Đo lượng cạnh/chi tiết cục bộ.
4. hf_energy   : tỉ lệ năng lượng phổ FFT 2-D nằm NGOÀI bán kính 1/4 tần số Nyquist.
                 Tần số chuẩn hoá theo chu kỳ/pixel: Nyquist = 0,5 nên bán kính biên = 0,125
                 chu kỳ/pixel. Trừ giá trị trung bình trước FFT (loại thành phần DC, vốn chiếm
                 phần lớn năng lượng nhưng không liên quan độ khó nén). Bán kính tính theo chuẩn
                 Euclid nên các góc phổ (r tới 0,707) cũng được tính là "cao tần".
5. n_colors    : số màu RGB phân biệt (np.unique trên mã hoá 24 bit). Liên quan trực tiếp tới
                 hiệu quả bảng màu/LZ77 của PNG và độ "mượt" của gradient.
6. grad_std    : độ lệch chuẩn của biên độ gradient Sobel 3x3 (chuẩn hoá chia 8 để có đơn vị
                 mức xám/pixel) trên ảnh xám. Đo độ không đồng đều của chi tiết: nền trơn + vài
                 cạnh sắc cho giá trị khác ảnh có kết cấu đều.
7. entropy_diff: (đặc trưng bổ sung) entropy của sai khác ngang Y[x]-Y[x-1] (bit/pixel), thước đo
                 gần đúng "entropy sau dự đoán" như PNG filter Sub. Bổ sung vì entropy bậc 0 đánh
                 giá quá cao độ khó của ảnh gradient mượt (nhiều mức xám nhưng rất dễ dự đoán).
8. png_bpp_ref : (kiểm chứng sơ bộ, KHÔNG phải kết quả chính) bpp của PNG compress_level=9;
                 dùng để xem các đặc trưng có tương quan thứ hạng (Spearman) với độ khó nén
                 thực tế hay không. Kết quả nén đầy đủ nằm ở các task sau.

Đầu ra: results/t01/dataset_stats.csv, results/t01/group_means.csv, results/t01/correlation.csv,
        figures/t01/contact_sheet.png, figures/t01/dataset_features.png

Chạy: cd /home/claude/nen_anh && python src/t01_dataset_analysis.py
(Tất định: không dùng ngẫu nhiên; SEED chỉ được đặt cho đồng nhất với common.py.)
"""
import os
import sys

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (GROUP_NAMES, SEED, ensure_dirs, encode, list_images,  # noqa: E402
                    load_metadata)

np.random.seed(SEED)
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 10

GROUP_ORDER = ["P", "T", "G"]
COLORS = {"P": "#0072B2", "T": "#D55E00", "G": "#009E73"}   # bảng màu thân thiện mù màu
MARKERS = {"P": "o", "T": "s", "G": "^"}
CANNY_LO, CANNY_HI = 100, 200
HF_RADIUS = 0.125          # = 1/4 tần số Nyquist (0,5 chu kỳ/pixel)


def shannon_entropy(gray_u8: np.ndarray) -> float:
    """Entropy Shannon (bit/pixel) của histogram 256 mức xám."""
    hist = np.bincount(gray_u8.ravel(), minlength=256).astype(np.float64)
    p = hist[hist > 0] / hist.sum()
    return float(-(p * np.log2(p)).sum())


def diff_entropy(gray_u8: np.ndarray) -> float:
    """Entropy (bit/pixel) của sai khác ngang giữa hai pixel kề nhau (dải -255..255)."""
    d = gray_u8[:, 1:].astype(np.int16) - gray_u8[:, :-1].astype(np.int16)
    hist = np.bincount((d + 255).ravel(), minlength=511).astype(np.float64)
    p = hist[hist > 0] / hist.sum()
    return float(-(p * np.log2(p)).sum())


def edge_density(gray_u8: np.ndarray) -> float:
    """Tỉ lệ pixel biên Canny (100/200)."""
    edges = cv2.Canny(gray_u8, CANNY_LO, CANNY_HI)
    return float((edges > 0).mean())


def hf_energy_ratio(gray_u8: np.ndarray) -> float:
    """Tỉ lệ năng lượng phổ ngoài bán kính 1/4 Nyquist (đã loại DC)."""
    g = gray_u8.astype(np.float64)
    g -= g.mean()
    power = np.abs(np.fft.fft2(g)) ** 2
    h, w = g.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    r = np.sqrt(fx ** 2 + fy ** 2)
    total = power.sum()
    return float(power[r > HF_RADIUS].sum() / total)


def gradient_std(gray_u8: np.ndarray) -> float:
    """Độ lệch chuẩn của |∇I| (Sobel 3x3 chia 8 -> mức xám/pixel)."""
    g = gray_u8.astype(np.float64)
    gx = cv2.Sobel(g, cv2.CV_64F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(g, cv2.CV_64F, 0, 1, ksize=3) / 8.0
    return float(np.std(np.hypot(gx, gy)))


def count_colors(rgb: np.ndarray) -> int:
    packed = (rgb[..., 0].astype(np.uint32) << 16) | (rgb[..., 1].astype(np.uint32) << 8) | rgb[..., 2]
    return int(np.unique(packed).size)


def compute_stats():
    meta = load_metadata()
    rows = []
    for name, grp, im in list_images():
        rgb = np.asarray(im)
        gray = np.asarray(im.convert("L"))        # Y của BT.601, uint8
        W, H = im.size
        rows.append({
            "name": name, "group": grp,
            "width": W, "height": H,
            "raw_kb": W * H * 3 / 1024,
            "entropy_y": shannon_entropy(gray),
            "entropy_diff": diff_entropy(gray),
            "edge_density": edge_density(gray),
            "hf_energy": hf_energy_ratio(gray),
            "n_colors": count_colors(rgb),
            "grad_std": gradient_std(gray),
            "png_bpp_ref": 8 * len(encode(im, "PNG", compress_level=9)) / (W * H),
            "source": meta[name]["source"],
        })
    df = pd.DataFrame(rows)
    df["gorder"] = df["group"].map({g: i for i, g in enumerate(GROUP_ORDER)})
    df = df.sort_values(["gorder", "name"]).drop(columns="gorder").reset_index(drop=True)
    return df


def contact_sheet(df, path):
    """Lưới 4 cột x 5 hàng ảnh thu nhỏ, mỗi ảnh có tên + nhóm + kích thước."""
    imgs = {n: im for n, _, im in list_images()}
    cols, rows = 4, 5
    fig, axes = plt.subplots(rows, cols, figsize=(6.6, 9.0))
    for ax in axes.ravel():
        ax.axis("off")
    for ax, (_, r) in zip(axes.ravel(), df.iterrows()):
        im = imgs[r["name"]].copy()
        im.thumbnail((250, 250))
        ax.axis("on")
        ax.imshow(im)
        ax.set_title(f"{r['name']}\nNhóm {r['group']} · {r['width']}×{r['height']}",
                     fontsize=10, color="black", pad=3, linespacing=1.15)
        for sp in ax.spines.values():       # viền màu theo nhóm
            sp.set_edgecolor(COLORS[r["group"]])
            sp.set_linewidth(2.5)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.01, wspace=0.08, hspace=0.38)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def features_figure(df, path):
    """(a) entropy Y vs mật độ biên; (b) năng lượng tần số cao vs độ lệch chuẩn gradient."""
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.4))
    for ax, (xk, yk, xl, yl, lab) in zip(axes, [
        ("entropy_y", "edge_density", "Entropy kênh Y (bit/pixel)", "Mật độ biên Canny (%)", "(a)"),
        ("hf_energy", "grad_std", "Năng lượng tần số cao (%)", "Độ lệch chuẩn gradient\n(mức xám/pixel)", "(b)"),
    ]):
        for g in GROUP_ORDER:
            d = df[df.group == g]
            x = d[xk] * (100 if xk == "hf_energy" else 1)
            y = d[yk] * (100 if yk == "edge_density" else 1)
            ax.scatter(x, y, s=48, marker=MARKERS[g], color=COLORS[g], edgecolor="black",
                       linewidth=0.7, label=f"{g}: {GROUP_NAMES[g]}", zorder=3)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.grid(True, alpha=0.3, linewidth=0.6)
        ax.text(0.02, 0.96, lab, transform=ax.transAxes, va="top", fontsize=11, fontweight="bold")
    axes[1].set_xscale("log")
    axes[0].set_yscale("log")   # mật độ biên trải từ ~0,2 % đến ~24 %
    from matplotlib.ticker import FixedLocator, FuncFormatter
    plain = FuncFormatter(lambda v, _: f"{v:g}")
    axes[0].yaxis.set_major_locator(FixedLocator([0.2, 0.5, 1, 2, 5, 10, 20]))
    axes[0].yaxis.set_major_formatter(plain)
    axes[0].yaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    axes[1].xaxis.set_major_locator(FixedLocator([0.2, 0.5, 1, 2, 5, 10, 20]))
    axes[1].xaxis.set_major_formatter(plain)
    axes[1].xaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=9,
               handletextpad=0.3, columnspacing=1.2)
    fig.subplots_adjust(left=0.095, right=0.99, top=0.97, bottom=0.30, wspace=0.42)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def main():
    rdir, fdir = ensure_dirs("t01")
    df = compute_stats()
    df.to_csv(os.path.join(rdir, "dataset_stats.csv"), index=False, encoding="utf-8-sig")

    num = ["raw_kb", "entropy_y", "entropy_diff", "edge_density", "hf_energy", "n_colors", "grad_std", "png_bpp_ref"]
    gm = df.groupby("group")[num].mean().reindex(GROUP_ORDER)
    gm.insert(0, "n_images", df.groupby("group").size().reindex(GROUP_ORDER))
    gm.to_csv(os.path.join(rdir, "group_means.csv"), encoding="utf-8-sig")

    feats = ["entropy_y", "entropy_diff", "edge_density", "hf_energy", "n_colors", "grad_std"]
    corr = pd.DataFrame({
        "feature": feats,
        "spearman_vs_png_bpp": [df[f].corr(df["png_bpp_ref"], method="spearman") for f in feats],
    })
    corr.to_csv(os.path.join(rdir, "correlation.csv"), index=False, encoding="utf-8-sig")

    contact_sheet(df, os.path.join(fdir, "contact_sheet.png"))
    features_figure(df, os.path.join(fdir, "dataset_features.png"))

    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(df.drop(columns="source").round(4).to_string())
    print(gm.round(4).to_string())
    print(corr.round(3).to_string())


if __name__ == "__main__":
    main()
