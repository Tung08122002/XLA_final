"""t03 - BASELINE: JPEG chất lượng 50/75/90 và PNG không mất mát (Đề tài 4, nén ảnh).

Mục tiêu
    Lập mốc so sánh (baseline) cho toàn bộ 20 ảnh sản phẩm, để các task sau (WebP - t04...)
    đối chiếu. Task này KHÔNG đo thời gian (do t10 phụ trách) nên gọi evaluate(repeats=0).

Các bước
    1. Đọc 20 ảnh bằng common.list_images() (nhóm P/T/G).
    2. Với mỗi ảnh chạy 4 cấu hình bằng common.evaluate():
         - JPEG quality = 50, 75, 90 với tham số Pillow MẶC ĐỊNH: subsampling 4:2:0
           (sắc độ lấy mẫu thưa 2x2), optimize=False (bảng Huffman chuẩn, không tối ưu),
           progressive=False. Đây là cấu hình "điển hình" mà đa số website/thư viện dùng
           khi chỉ chọn quality, nên thích hợp làm baseline. Cấu hình tinh chỉnh
           (4:4:4, optimize...) thuộc các task ablation khác.
         - PNG compress_level=9 (zlib mạnh nhất), optimize=False. PNG không mất mát nên
           PSNR = inf, SSIM = 1 (được kiểm tra bằng assert).
    3. Ghi CSV theo từng ảnh và CSV tổng hợp theo nhóm (trung bình + độ lệch chuẩn mẫu, ddof=1).
       Nhóm "ALL" là toàn bộ 20 ảnh. PSNR trung bình của PNG (inf) được bỏ qua (ghi NaN).
    4. Vẽ 3 hình (kiểu IEEE, 300 dpi): dung lượng theo nhóm, chất lượng theo nhóm,
       minh hoạ trực quan (cắt 128x128 phóng nearest x3).

Lưu ý thống kê: trung bình dung lượng KB bị chi phối bởi ảnh 1000x1000 (nhóm T, G có
cả ảnh 500 và 1000), nên bpp là thước đo công bằng hơn khi so sánh giữa các ảnh.
Tỉ lệ nén theo nhóm trong bảng là TRUNG BÌNH CỦA TỈ LỆ từng ảnh (không phải tỉ số của tổng).

Chạy:  cd /home/claude/nen_anh && python src/t03_baseline.py
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (SEED, GROUP_NAMES, ROOT, list_images, encode, decode, evaluate,  # noqa: E402
                    ensure_dirs, psnr, ssim)

np.random.seed(SEED)
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 11
plt.rcParams["axes.linewidth"] = 1.2

TASK = "t03"
JPEG_Q = [50, 75, 90]
# (nhãn cấu hình, codec, quality, fmt, tham số Pillow)
CONFIGS = [("JPEG q50", "JPEG", 50), ("JPEG q75", "JPEG", 75), ("JPEG q90", "JPEG", 90),
           ("PNG", "PNG", None)]
GROUPS = ["P", "T", "G"]
GCOLOR = {"P": "#1b6ca8", "T": "#c0392b", "G": "#2e8b57"}
HATCH = {"P": "", "T": "//", "G": ".."}
CFG_LABELS = [c[0] for c in CONFIGS]


def params_of(codec, q):
    if codec == "JPEG":
        # Mặc định Pillow nêu tường minh để ghi lại cấu hình baseline.
        return dict(quality=q, subsampling="4:2:0", optimize=False, progressive=False)
    return dict(compress_level=9, optimize=False)


def run_all(images):
    rows = []
    for name, grp, im in images:
        W, H = im.size
        for label, codec, q in CONFIGS:
            r = evaluate(im, codec, repeats=0, **params_of(codec, q))
            if codec == "PNG":
                assert np.isinf(r["psnr"]) and abs(r["ssim"] - 1) < 1e-12, name
            rows.append(dict(name=name, group=grp, W=W, H=H, codec=codec,
                             quality=("" if q is None else q), config=label,
                             size_kb=r["size_kb"], bpp=r["bpp"], ratio=r["ratio"],
                             psnr=r["psnr"], ssim=r["ssim"]))
    return pd.DataFrame(rows)


def by_group(df):
    d = df.copy()
    d["psnr"] = d["psnr"].replace(np.inf, np.nan)  # PNG: bỏ qua khi lấy trung bình
    d["group"] = d["group"]
    parts = []
    for g in GROUPS + ["ALL"]:
        sub = d if g == "ALL" else d[d["group"] == g]
        agg = sub.groupby(["codec", "quality", "config"], sort=False, dropna=False).agg(
            n=("name", "count"),
            size_kb_mean=("size_kb", "mean"), size_kb_std=("size_kb", "std"),
            bpp_mean=("bpp", "mean"), bpp_std=("bpp", "std"),
            ratio_mean=("ratio", "mean"), ratio_std=("ratio", "std"),
            psnr_mean=("psnr", "mean"), psnr_std=("psnr", "std"),
            ssim_mean=("ssim", "mean"), ssim_std=("ssim", "std")).reset_index()
        agg.insert(0, "group", g)
        parts.append(agg)
    return pd.concat(parts, ignore_index=True)


def fig_size(bg, path):
    """Cột nhóm: bpp (trái) và dung lượng KB (phải), trục log."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for ax, key, ylab in [(axes[0], "bpp", "Số bit trên điểm ảnh (bpp, thang log)"),
                          (axes[1], "size_kb", "Dung lượng trung bình (KB, thang log)")]:
        w = 0.26
        for i, g in enumerate(GROUPS):
            m, s = [], []
            for lab in CFG_LABELS:
                r = bg[(bg.group == g) & (bg.config == lab)].iloc[0]
                m.append(r[key + "_mean"])
                s.append(r[key + "_std"])
            x = np.arange(len(CFG_LABELS)) + (i - 1) * w
            ax.bar(x, m, w, color=GCOLOR[g], edgecolor="black", linewidth=1.0,
                   hatch=HATCH[g], label=f"{g}: {GROUP_NAMES[g]}",
                   yerr=s, error_kw=dict(ecolor="black", lw=1.2, capsize=2.5))
        ax.set_yscale("log")
        ax.set_xticks(np.arange(len(CFG_LABELS)))
        ax.set_xticklabels(CFG_LABELS)
        ax.set_xlabel("Cấu hình nén")
        ax.set_ylabel(ylab)
        ax.grid(True, which="major", axis="y", color="0.85", lw=0.8)
        ax.set_axisbelow(True)
    axes[0].legend(fontsize=9, loc="upper left", frameon=True, edgecolor="black")
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def fig_quality(bg, path):
    """PSNR và SSIM theo cấu hình JPEG cho từng nhóm (PNG: vô cực / 1, ghi chú)."""
    jp = [c for c in CFG_LABELS if c.startswith("JPEG")]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for ax, key, ylab in [(axes[0], "psnr", "PSNR (dB)"), (axes[1], "ssim", "SSIM")]:
        for g, mk in zip(GROUPS, ["o", "s", "^"]):
            m = [bg[(bg.group == g) & (bg.config == c)].iloc[0][key + "_mean"] for c in jp]
            s = [bg[(bg.group == g) & (bg.config == c)].iloc[0][key + "_std"] for c in jp]
            ax.errorbar(range(3), m, yerr=s, color=GCOLOR[g], marker=mk, ms=7, lw=2.0,
                        capsize=3, elinewidth=1.2, label=f"{g}: {GROUP_NAMES[g]}")
        ax.set_xticks(range(3))
        ax.set_xticklabels(["q50", "q75", "q90"])
        ax.set_xlim(-0.3, 2.3)
        ax.set_xlabel("Chất lượng JPEG (4:2:0)")
        ax.set_ylabel(ylab)
        ax.grid(True, color="0.85", lw=0.8)
    axes[0].legend(fontsize=9, loc="lower right", frameon=True, edgecolor="black")
    axes[0].text(0.03, 0.97, "PNG: không mất mát\n(PSNR = ∞, SSIM = 1)", transform=axes[0].transAxes,
                 va="top", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


# vùng cắt 128x128: (ảnh, x0, y0, mô tả)
CROPS = [("T05_card500", 212, 88, "T05: giá, nhãn -25%"),
         ("P06_baboon", 120, 20, "P06: mắt, lông")]
ZOOM = 3
CS = 128


def fig_visual(images, path):
    d = {n: im for n, _, im in images}
    cols = ["Gốc (PNG)", "JPEG q50", "JPEG q75", "JPEG q90"]
    fig, axes = plt.subplots(2, 4, figsize=(11, 7.6))
    for r, (name, x0, y0, desc) in enumerate(CROPS):
        im = d[name]
        variants = [("Gốc (PNG)", im, len(encode(im, "PNG", compress_level=9)) / 1024, None, None)]
        for q in JPEG_Q:
            data = encode(im, "JPEG", **params_of("JPEG", q))
            rec = decode(data)
            variants.append((f"JPEG q{q}", rec, len(data) / 1024,
                             psnr(np.asarray(im), np.asarray(rec)),
                             ssim(np.asarray(im), np.asarray(rec))))
        for c, (lab, img, kb, p, s) in enumerate(variants):
            crop = img.crop((x0, y0, x0 + CS, y0 + CS)).resize((CS * ZOOM, CS * ZOOM), 0)  # NEAREST
            ax = axes[r, c]
            ax.imshow(crop)
            ax.set_xticks([])
            ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_linewidth(1.2)
            if p is None:
                cap = f"{lab}\n{kb:.1f} KB (toàn ảnh)\nPSNR = ∞, SSIM = 1"
            else:
                cap = f"{lab}\n{kb:.1f} KB (toàn ảnh)\nPSNR {p:.1f} dB, SSIM {s:.3f}"
            ax.set_xlabel(cap, fontsize=9.5)
            if c == 0:
                ax.set_ylabel(desc, fontsize=10)
    fig.tight_layout(h_pad=2.5)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def channel_error(images):
    """Phân tích cơ chế artefact: PSNR riêng kênh Y (độ sáng) và Cb, Cr (sắc độ) của JPEG
    theo nhóm, và sai số trong 'vùng quanh chữ/cạnh' (điểm ảnh cách cạnh <= 3 px, cạnh = gradient
    độ sáng gốc > 40). Dùng chuyển YCbCr của Pillow (cùng không gian JPEG dùng).
    Mục đích: chứng minh định lượng rằng sắc độ (bị lấy mẫu 4:2:0) sai nhiều hơn độ sáng ở
    ảnh có chữ màu."""
    from scipy.ndimage import binary_dilation
    rows = []
    for name, grp, im in images:
        ref = np.asarray(im.convert("YCbCr")).astype(np.float64)
        gy, gx = np.gradient(ref[..., 0])
        edge = np.hypot(gx, gy) > 40
        near = binary_dilation(edge, iterations=3)
        for q in JPEG_Q:
            rec = decode(encode(im, "JPEG", **params_of("JPEG", q)))
            out = np.asarray(rec.convert("YCbCr")).astype(np.float64)
            row = dict(name=name, group=grp, quality=q, near_edge_frac=near.mean())
            for k, ch in enumerate(["Y", "Cb", "Cr"]):
                e = (ref[..., k] - out[..., k]) ** 2
                row["mse_" + ch] = e.mean()
                row["mse_" + ch + "_near_edge"] = e[near].mean() if near.any() else np.nan
                row["mse_" + ch + "_flat"] = e[~near].mean()
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    rdir, fdir = ensure_dirs(TASK)
    images = list_images()
    df = run_all(images)
    df_out = df[["name", "group", "W", "H", "codec", "quality", "size_kb", "bpp", "ratio",
                 "psnr", "ssim"]]
    df_out.to_csv(os.path.join(rdir, "baseline_per_image.csv"), index=False,
                  float_format="%.6g")
    bg = by_group(df)
    bg.drop(columns=["config"]).to_csv(os.path.join(rdir, "baseline_by_group.csv"),
                                       index=False, float_format="%.6g")
    ce = channel_error(images)
    ce.to_csv(os.path.join(rdir, "baseline_channel_error.csv"), index=False, float_format="%.6g")
    fig_size(bg, os.path.join(fdir, "baseline_size_by_group.png"))
    fig_quality(bg, os.path.join(fdir, "baseline_quality.png"))
    fig_visual(images, os.path.join(fdir, "baseline_visual.png"))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(bg.round(3).to_string())


if __name__ == "__main__":
    main()
