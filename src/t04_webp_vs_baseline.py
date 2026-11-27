"""t04 - Phương pháp chính WebP + bảng so sánh baseline vs WebP trên cùng tập test (20 ảnh).

Chạy:  cd /home/claude/nen_anh && python src/t04_webp_vs_baseline.py

Các bước (mỗi bước ứng với một phần trong code):
1. Với CẢ 20 ảnh (nhóm P/T/G) chạy 8 cấu hình:
     - JPEG q=50/75/90   : Pillow mặc định (libjpeg-turbo, 4:2:0, bảng lượng tử chuẩn Annex K
                           co giãn theo q, Huffman tĩnh, không optimize/progressive). Đây là baseline
                           đề bài yêu cầu, nên giữ nguyên mặc định để "baseline" đúng nghĩa.
     - PNG compress_level=9 : DEFLATE mức cao nhất (chậm nhất, nhỏ nhất) - lấy mức nén tốt nhất của PNG
                           để so sánh với WebP lossless một cách công bằng (không "đánh bù" cho WebP).
     - WebP lossy q=50/75/90, method=4 (mặc định Pillow; method 0..6 đánh đổi thời gian lấy dung lượng,
                           4 là điểm cân bằng của libwebp) - VP8 intra, luôn 4:2:0.
     - WebP lossless (lossless=True, quality=100, method=4) - VP8L. Với lossless, `quality` KHÔNG phải
                           độ trung thực mà là "nỗ lực nén"; 100 + method 4 là cấu hình thông dụng.
   `evaluate(..., repeats=0)`: không đo thời gian (máy đang chạy nhiều tác vụ song song, số đo thời gian
   sẽ nhiễu; thời gian do task t08/t10 phụ trách).
   Kiểm tra tính không mất mát: PNG và WebP lossless phải cho PSNR = inf, SSIM = 1 (assert).
2. So sánh cặp CÙNG SỐ quality: WebP qX so với JPEG qX (X = 50, 75, 90) trên TỪNG ảnh rồi tổng hợp theo nhóm:
     - tỉ lệ dung lượng WebP/JPEG (< 1 nghĩa là WebP nhỏ hơn),
     - chênh PSNR (dB) và chênh SSIM (WebP - JPEG),
     - "thắng tuyệt đối" = WebP vừa nhỏ hơn vừa có SSIM cao hơn JPEG trên cùng ảnh.
   CẢNH BÁO PHƯƠNG PHÁP: thang quality của JPEG và của WebP KHÔNG tương đương (hai thuật toán lượng tử
   hoá khác nhau; q=75 của JPEG và q=75 của WebP cho chất lượng/ dung lượng khác nhau). Vì vậy so sánh
   cùng số quality chỉ để tham khảo; so sánh công bằng phải dựa trên đường RD / iso-quality (task t05, t06).
   WebP lossless vs PNG: tính % giảm dung lượng = 1 - size_WebP/size_PNG trên từng ảnh, rồi theo nhóm.
3. Vẽ 4 hình (300 dpi, kiểu IEEE): scatter dung lượng-SSIM, cột dung lượng 8 cấu hình, lossless PNG vs WebP,
   so sánh trực quan vùng cắt phóng to (1 ảnh T + 1 ảnh G sạch: gốc / JPEG75 / WebP75).
4. Ghi CSV + bảng markdown (results/t04/tables_auto.md) để đưa vào section.md.

Seed cố định (SEED từ common); không có thành phần ngẫu nhiên trong thí nghiệm này.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from common import (GROUP_NAMES, SEED, decode, encode, ensure_dirs, evaluate,
                    list_images, psnr, ssim)

np.random.seed(SEED)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 10.5,
    "legend.fontsize": 9,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.linewidth": 1.2,
    "lines.linewidth": 1.8,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.6,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# (tên cấu hình, codec, fmt Pillow, tham số)
CONFIGS = [
    ("JPEG q50", "JPEG", "JPEG", dict(quality=50)),
    ("JPEG q75", "JPEG", "JPEG", dict(quality=75)),
    ("JPEG q90", "JPEG", "JPEG", dict(quality=90)),
    ("PNG", "PNG", "PNG", dict(compress_level=9)),
    ("WebP q50", "WebP", "WEBP", dict(quality=50, method=4)),
    ("WebP q75", "WebP", "WEBP", dict(quality=75, method=4)),
    ("WebP q90", "WebP", "WEBP", dict(quality=90, method=4)),
    ("WebP lossless", "WebP-LL", "WEBP", dict(lossless=True, quality=100, method=4)),
]
CFG_NAMES = [c[0] for c in CONFIGS]
GROUPS = ["P", "T", "G"]
GCOLOR = {"P": "#1f77b4", "T": "#d62728", "G": "#2ca02c"}
GSHORT = {"P": "P: ảnh chụp", "T": "T: ảnh có chữ", "G": "G: gradient"}


def fmt_psnr(x):
    return "∞" if np.isinf(x) else f"{x:.2f}"


# ---------------------------------------------------------------- 1. chạy 8 cấu hình
def run_all(images):
    rows = []
    for name, grp, im in images:
        for cname, codec, fmt, params in CONFIGS:
            r = evaluate(im, fmt, repeats=0, **params)
            if codec in ("PNG", "WebP-LL"):
                assert np.isinf(r["psnr"]) and r["ssim"] == 1.0, (name, cname, "không lossless!")
            rows.append(dict(image=name, group=grp, config=cname, codec=codec,
                             width=im.size[0], height=im.size[1], **r))
    return pd.DataFrame(rows)


def group_table(df):
    """Trung bình theo (nhóm, cấu hình); thêm nhóm 'ALL' (trung bình trên 20 ảnh)."""
    parts = []
    for g in GROUPS + ["ALL"]:
        sub = df if g == "ALL" else df[df.group == g]
        for c in CFG_NAMES:
            s = sub[sub.config == c]
            parts.append(dict(group=g, config=c, n_images=len(s),
                              size_kb=s.size_kb.mean(), size_kb_std=s.size_kb.std(ddof=1),
                              bpp=s.bpp.mean(), ratio=s.ratio.mean(),
                              psnr=s.psnr.mean(),  # lossless -> inf
                              ssim=s.ssim.mean(), ssim_min=s.ssim.min()))
    return pd.DataFrame(parts)


# ---------------------------------------------------------------- 2. so sánh cặp
def pairwise(df):
    piv = {m: df.pivot(index="image", columns="config", values=m) for m in ("size_kb", "psnr", "ssim")}
    grp = df.drop_duplicates("image").set_index("image").group
    per_img = []
    for img in piv["size_kb"].index:
        for q in (50, 75, 90):
            w, j = f"WebP q{q}", f"JPEG q{q}"
            sw, sj = piv["size_kb"].loc[img, w], piv["size_kb"].loc[img, j]
            dw, dj = piv["ssim"].loc[img, w], piv["ssim"].loc[img, j]
            per_img.append(dict(image=img, group=grp[img], comparison=f"WebP q{q} vs JPEG q{q}",
                                size_ratio=sw / sj,
                                d_psnr=piv["psnr"].loc[img, w] - piv["psnr"].loc[img, j],
                                d_ssim=dw - dj,
                                webp_smaller=sw < sj, webp_ssim_higher=dw > dj,
                                abs_win=(sw < sj) and (dw > dj)))
        sw, sp = piv["size_kb"].loc[img, "WebP lossless"], piv["size_kb"].loc[img, "PNG"]
        per_img.append(dict(image=img, group=grp[img], comparison="WebP lossless vs PNG",
                            size_ratio=sw / sp, reduction_pct=100 * (1 - sw / sp),
                            webp_smaller=sw < sp))
    pi = pd.DataFrame(per_img)

    out = []
    for comp, sub_c in pi.groupby("comparison", sort=False):
        for g in GROUPS + ["ALL"]:
            s = sub_c if g == "ALL" else sub_c[sub_c.group == g]
            if comp.endswith("PNG"):
                size_pair = df[df.config.isin(["WebP lossless", "PNG"])]
                sp_ = size_pair if g == "ALL" else size_pair[size_pair.group == g]
                tot_w = sp_[sp_.config == "WebP lossless"].size_kb.sum()
                tot_p = sp_[sp_.config == "PNG"].size_kb.sum()
                out.append(dict(comparison=comp, group=g, n_images=len(s),
                                size_ratio_mean=s.size_ratio.mean(),
                                size_ratio_median=s.size_ratio.median(),
                                reduction_pct_mean=s.reduction_pct.mean(),
                                reduction_pct_min=s.reduction_pct.min(),
                                reduction_pct_max=s.reduction_pct.max(),
                                reduction_pct_total_bytes=100 * (1 - tot_w / tot_p),
                                n_webp_smaller=int(s.webp_smaller.astype(bool).astype(int).sum())))
            else:
                out.append(dict(comparison=comp, group=g, n_images=len(s),
                                size_ratio_mean=s.size_ratio.mean(),
                                size_ratio_median=s.size_ratio.median(),
                                d_psnr_mean=s.d_psnr.mean(), d_ssim_mean=s.d_ssim.mean(),
                                n_webp_smaller=int(s.webp_smaller.astype(bool).astype(int).sum()),
                                n_webp_ssim_higher=int(s.webp_ssim_higher.astype(bool).astype(int).sum()),
                                n_abs_win=int(s.abs_win.astype(bool).astype(int).sum())))
    return pi, pd.DataFrame(out)


# ---------------------------------------------------------------- 3. hình
def fig_scatter(df, path):
    markers = {"JPEG": "o", "PNG": "^", "WebP": "s", "WebP-LL": "D"}
    fig, ax = plt.subplots(figsize=(6.3, 4.6))
    for codec, mk in markers.items():
        for g in GROUPS:
            s = df[(df.codec == codec) & (df.group == g)]
            ax.scatter(s.bpp, s.ssim, marker=mk, s=34, facecolor=GCOLOR[g] if codec in ("JPEG", "PNG") else "none",
                       edgecolor=GCOLOR[g], linewidth=1.3, alpha=0.9)
    ax.set_xscale("log")
    ax.set_xlabel("Tốc độ bit bpp (bit/điểm ảnh, thang log)")
    ax.set_ylabel("SSIM so với ảnh gốc")
    ax.set_ylim(0.66, 1.01)
    h1 = [Line2D([], [], marker=m, linestyle="", color="k", markersize=7,
                 markerfacecolor="k" if k in ("JPEG", "PNG") else "none", label=lab)
          for k, m, lab in [("JPEG", "o", "JPEG (đặc)"), ("PNG", "^", "PNG (đặc)"),
                            ("WebP", "s", "WebP lossy (rỗng)"), ("WebP-LL", "D", "WebP lossless (rỗng)")]]
    h2 = [Line2D([], [], marker="o", linestyle="", color=GCOLOR[g], markersize=7, label=GSHORT[g]) for g in GROUPS]
    leg1 = ax.legend(handles=h1, loc="lower right", title="Codec", framealpha=0.95)
    ax.add_artist(leg1)
    ax.legend(handles=h2, loc="lower center", bbox_to_anchor=(0.42, 0.0), title="Nhóm", framealpha=0.95)
    fig.savefig(path)
    plt.close(fig)


def fig_bar(gt, path):
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    w = 0.26
    x = np.arange(len(CFG_NAMES))
    hatch = {"P": "", "T": "//", "G": ".."}
    for i, g in enumerate(GROUPS):
        v = [gt[(gt.group == g) & (gt.config == c)].size_kb.iloc[0] for c in CFG_NAMES]
        bars = ax.bar(x + (i - 1) * w, v, w, color=GCOLOR[g], edgecolor="k", linewidth=0.8,
                      hatch=hatch[g], label=GSHORT[g])
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace(" ", "\n", 1) for c in CFG_NAMES])
    ax.set_ylabel("Dung lượng trung bình (KB, thang log)")
    ax.set_xlabel("Cấu hình nén")
    ax.legend(loc="upper left", ncol=3, framealpha=0.95, columnspacing=1.0, handlelength=1.4)
    ax.set_ylim(1, 2500)
    ax.grid(axis="x", visible=False)
    fig.savefig(path)
    plt.close(fig)


def fig_lossless(df, pi, gt, path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.9), gridspec_kw=dict(width_ratios=[1, 1.5]))
    x = np.arange(3)
    w = 0.36
    pv = [gt[(gt.group == g) & (gt.config == "PNG")].size_kb.iloc[0] for g in GROUPS]
    wv = [gt[(gt.group == g) & (gt.config == "WebP lossless")].size_kb.iloc[0] for g in GROUPS]
    a.bar(x - w / 2, pv, w, color="#bbbbbb", edgecolor="k", linewidth=0.8, label="PNG (level 9)")
    a.bar(x + w / 2, wv, w, color="#555555", edgecolor="k", linewidth=0.8, hatch="//", label="WebP lossless")
    for xi, p_, w_ in zip(x, pv, wv):
        a.text(xi - w / 2, p_, f"{p_:.0f}", ha="center", va="bottom", fontsize=9)
        a.text(xi + w / 2, w_, f"{w_:.0f}", ha="center", va="bottom", fontsize=9)
    a.set_xticks(x)
    a.set_xticklabels(["P", "T", "G"])
    a.set_xlabel("Nhóm ảnh")
    a.set_ylabel("Dung lượng trung bình (KB)")
    a.set_ylim(0, max(pv) * 1.18)
    a.legend(loc="upper right", framealpha=0.95)
    a.grid(axis="x", visible=False)
    s = pi[pi.comparison == "WebP lossless vs PNG"].copy()
    s["g"] = pd.Categorical(s.group, GROUPS)
    s = s.sort_values(["g", "image"]).reset_index(drop=True)
    b.bar(np.arange(len(s)), s.reduction_pct, 0.75, color=[GCOLOR[g] for g in s.group], edgecolor="k", linewidth=0.6)
    b.set_xticks(np.arange(len(s)))
    b.set_xticklabels([n.split("_")[0] for n in s.image], rotation=90, fontsize=9)
    b.set_ylabel("Giảm dung lượng so với PNG (%)")
    b.set_xlabel("Ảnh (đỏ: T, xanh lá: G, xanh dương: P)")
    b.set_ylim(0, max(s.reduction_pct) * 1.12)
    b.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_visual(images, path):
    d = {n: (g, im) for n, g, im in images}
    picks = [("T01_card1000", (438, 205, 598, 325), "T01 (chữ + nhãn đỏ/vàng)"),
             ("G01_studio1000", (350, 775, 510, 895), "G01 (bóng đổ, tương phản ×6)")]
    fig, axes = plt.subplots(2, 3, figsize=(6.6, 4.9))
    for r, (name, box, lab) in enumerate(picks):
        im = d[name][1]
        ref = np.asarray(im)
        variants = [("Gốc (PNG)", None)]
        for title, fmt, p in [("JPEG q75", "JPEG", dict(quality=75)),
                              ("WebP q75", "WEBP", dict(quality=75, method=4))]:
            data = encode(im, fmt, **p)
            rec = np.asarray(decode(data))
            variants.append((title, (len(data) / 1024, ssim(ref, rec), psnr(ref, rec), rec)))
        x0, y0, x1, y1 = box
        for c, (title, v) in enumerate(variants):
            ax = axes[r, c]
            arr = ref if v is None else v[3]
            crop = arr[y0:y1, x0:x1].astype(np.float64)
            if name.startswith("G"):  # chỉ để HIỂN THỊ: kéo giãn tương phản ×6 quanh trung bình vùng gốc để lộ lỗi nhẹ
                m = ref[y0:y1, x0:x1].astype(np.float64).mean(axis=(0, 1))
                crop = np.clip((crop - m) * 6 + 128, 0, 255)
            ax.imshow(crop.astype(np.uint8), interpolation="nearest")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
            if v is None:
                cap = f"{title}\n{os.path.getsize(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'images', name + '.png')) / 1024:.0f} KB (PNG gốc)\n"
            else:
                cap = f"{title}\n{v[0]:.1f} KB\nSSIM {v[1]:.4f}, PSNR {v[2]:.1f} dB"
            ax.set_title(cap, fontsize=9)
            if c == 0:
                ax.set_ylabel(lab, fontsize=9)
    fig.text(0.5, 0.0, "KB, SSIM, PSNR tính trên toàn ảnh; hiển thị là vùng cắt 160×120 điểm ảnh, phóng to (nearest); hàng G chỉ tăng tương phản để hiển thị.",
             ha="center", fontsize=8.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path)
    plt.close(fig)



def chroma_ceiling(images):
    """Chẩn đoán phụ: trần chất lượng do RIÊNG việc lấy mẫu con màu 4:2:0 (chưa lượng tử hoá DCT).
    RGB -> YCbCr, giảm Cb/Cr còn 1/2 mỗi chiều (BOX), phóng lại (BILINEAR), -> RGB, đo PSNR/SSIM so với gốc.
    Đây là xấp xỉ (bộ lọc lấy mẫu của libjpeg/libwebp không đúng bằng BOX/BILINEAR) nhưng đủ cho bậc độ lớn:
    cho biết ngay cả khi nén 'hoàn hảo' ở kênh Y, 4:2:0 đã làm mất bao nhiêu dB/SSIM ở từng nhóm."""
    from PIL import Image as _I
    rows = []
    for name, grp, im in images:
        y, cb, cr = im.convert("YCbCr").split()
        w, h = im.size
        up = [c.resize((w // 2, h // 2), _I.BOX).resize((w, h), _I.BILINEAR) for c in (cb, cr)]
        rec = _I.merge("YCbCr", (y, up[0], up[1])).convert("RGB")
        a, b = np.asarray(im), np.asarray(rec)
        rows.append(dict(image=name, group=grp, psnr_420_only=psnr(a, b), ssim_420_only=ssim(a, b)))
    return pd.DataFrame(rows)

# ---------------------------------------------------------------- 4. bảng markdown
def md_main_table(gt):
    hdr = ["Cấu hình"]
    for g in GROUPS:
        hdr += [f"{g} KB", f"{g} bpp", f"{g} PSNR", f"{g} SSIM"]
    lines = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for c in CFG_NAMES:
        cells = [c]
        for g in GROUPS:
            r = gt[(gt.group == g) & (gt.config == c)].iloc[0]
            cells += [f"{r.size_kb:.1f}", f"{r.bpp:.2f}", fmt_psnr(r.psnr), f"{r.ssim:.4f}"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def md_pair_table(ps):
    lines = ["| Cặp so sánh | Nhóm | WebP/JPEG (dung lượng, TB) | Trung vị | ΔPSNR (dB) | ΔSSIM | WebP nhỏ hơn | WebP SSIM cao hơn | Thắng tuyệt đối |",
             "|---|---|---|---|---|---|---|---|---|"]
    s = ps[~ps.comparison.str.contains("PNG")]
    for _, r in s.iterrows():
        lines.append(f"| {r.comparison} | {r.group} | {r.size_ratio_mean:.3f} | {r.size_ratio_median:.3f} | "
                     f"{r.d_psnr_mean:+.2f} | {r.d_ssim_mean:+.4f} | {int(r.n_webp_smaller)}/{int(r.n_images)} | "
                     f"{int(r.n_webp_ssim_higher)}/{int(r.n_images)} | {int(r.n_abs_win)}/{int(r.n_images)} |")
    return "\n".join(lines)


def md_ll_table(ps):
    lines = ["| Nhóm | Giảm TB (%) | Nhỏ nhất – lớn nhất (%) | Giảm theo tổng byte (%) | WebP-LL nhỏ hơn PNG |",
             "|---|---|---|---|---|"]
    s = ps[ps.comparison.str.contains("PNG")]
    for _, r in s.iterrows():
        lines.append(f"| {r.group} | {r.reduction_pct_mean:.1f} | {r.reduction_pct_min:.1f} – {r.reduction_pct_max:.1f} | "
                     f"{r.reduction_pct_total_bytes:.1f} | {int(r.n_webp_smaller)}/{int(r.n_images)} |")
    return "\n".join(lines)


def main():
    rdir, fdir = ensure_dirs("t04")
    images = list_images()
    assert len(images) == 20
    df = run_all(images)
    df.to_csv(os.path.join(rdir, "all_configs_per_image.csv"), index=False)
    gt = group_table(df)
    gt.to_csv(os.path.join(rdir, "comparison_by_group.csv"), index=False)
    pi, ps = pairwise(df)
    ps.to_csv(os.path.join(rdir, "pairwise.csv"), index=False)
    pi.to_csv(os.path.join(rdir, "pairwise_per_image.csv"), index=False)

    cc = chroma_ceiling(images)
    cc.to_csv(os.path.join(rdir, "chroma420_ceiling_per_image.csv"), index=False)
    cc.groupby("group")[["psnr_420_only", "ssim_420_only"]].mean().reset_index().to_csv(
        os.path.join(rdir, "chroma420_ceiling_by_group.csv"), index=False)
    fig_scatter(df, os.path.join(fdir, "size_vs_ssim_scatter.png"))
    fig_bar(gt, os.path.join(fdir, "size_bar_all_configs.png"))
    fig_lossless(df, pi, gt, os.path.join(fdir, "lossless_png_vs_webp.png"))
    fig_visual(images, os.path.join(fdir, "visual_compare.png"))

    with open(os.path.join(rdir, "tables_auto.md"), "w", encoding="utf-8") as f:
        f.write("## BANG_CHINH\n" + md_main_table(gt) + "\n\n## BANG_CAP\n" + md_pair_table(ps) +
                "\n\n## BANG_LOSSLESS\n" + md_ll_table(ps) + "\n")
    print(md_main_table(gt))
    print()
    print(md_pair_table(ps))
    print()
    print(md_ll_table(ps))


if __name__ == "__main__":
    main()
