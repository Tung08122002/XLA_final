# -*- coding: utf-8 -*-
"""t06 - So sánh cùng chất lượng (iso-quality), khuyến nghị cho website TMĐT và
câu hỏi mở "PSNR hay SSIM".

Chạy:  cd /home/claude/nen_anh && python src/t06_isoquality_recommend.py
       (thêm --reuse để dùng lại results/t06/sweep.csv khi chỉ muốn sửa phần phân tích/hình)

CÁC BƯỚC
1. Quét quality = 5, 10, ..., 100 (20 mức) cho 3 codec trên cả 20 ảnh:
     - JPEG 4:2:0 (mặc định của Pillow, subsampling=2) - cấu hình web phổ biến nhất;
     - JPEG 4:4:4 (subsampling=0) - không giảm mẫu sắc độ, để tách riêng ảnh hưởng của chroma;
     - WebP lossy, method=4 (mặc định của libwebp; cân bằng tốc độ/nén).
   Mỗi điểm gọi common.evaluate(..., repeats=0) (không đo thời gian, tránh nhiễu do máy chia sẻ).
   Bước 5 được chọn theo yêu cầu đề; vì lưới thô nên kèm theo kiểm tra độ nhạy bằng nội suy.
2. Iso-quality: với mỗi (ảnh, codec) và mỗi mục tiêu SSIM >= {0,95; 0,98; 0,99}, PSNR >= {35; 40 dB}
   lấy quality NHỎ NHẤT trên lưới đạt mục tiêu (quét từ thấp lên, dừng ở điểm đầu tiên đạt) và
   dung lượng tương ứng. Không đạt ở q=100 -> ghi "không đạt" (NaN), KHÔNG ngoại suy.
   Thêm cột size_interp_kb: dung lượng nội suy tại đúng ngưỡng (tuyến tính theo chỉ số, theo log-dung lượng)
   giữa hai điểm lưới kề nhau - dùng để kiểm tra % tiết kiệm không bị méo bởi bước lưới 5.
3. Baseline không mất mát: PNG (compress_level=9) và WebP lossless (quality=100, method=4).
   So với dung lượng lossy tại SSIM 0,99 để tìm ảnh mà lossless lại NHỎ HƠN lossy.
4. PSNR hay SSIM: Spearman (loại điểm PSNR = inf, nếu có) trên toàn bộ điểm quét, theo nhóm và theo từng
   ảnh; tỉ lệ cặp "bất đồng" (cùng ảnh, PSNR tăng nhưng SSIM giảm); chọn ví dụ bất đồng và vẽ
   bản đồ SSIM cục bộ (skimage full=True, cùng tham số với common.ssim) + bản đồ sai số tuyệt đối.
5. Khuyến nghị theo loại ảnh: với mỗi nhóm chọn quality tối thiểu trên lưới sao cho TẤT CẢ ảnh trong nhóm
   đạt SSIM >= 0,98 (đảm bảo cho ảnh xấu nhất, không chỉ trung bình), sau đó tra dung lượng kỳ vọng,
   SSIM/PSNR kỳ vọng và phương án dự phòng JPEG cho <picture>.
Hạt giống: SEED từ common (script không dùng ngẫu nhiên, mọi bước xác định).
"""
import argparse
import itertools
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from PIL import Image
from skimage.metrics import structural_similarity

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (list_images, encode, decode, evaluate, ensure_dirs,  # noqa: E402
                    GROUP_NAMES, SEED)

np.random.seed(SEED)
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 11
plt.rcParams["axes.labelsize"] = 11
plt.rcParams["axes.linewidth"] = 1.2
plt.rcParams["text.color"] = "black"
plt.rcParams["axes.edgecolor"] = "black"
plt.rcParams["axes.labelcolor"] = "black"
plt.rcParams["xtick.color"] = "black"
plt.rcParams["ytick.color"] = "black"

QUALITIES = list(range(5, 101, 5))
CODECS = {
    "JPEG 4:2:0": ("JPEG", dict(subsampling=2)),
    "JPEG 4:4:4": ("JPEG", dict(subsampling=0)),
    "WebP lossy": ("WEBP", dict(method=4)),
}
CODEC_ORDER = list(CODECS)
TARGETS = [("ssim", 0.95), ("ssim", 0.98), ("ssim", 0.99), ("psnr", 35.0), ("psnr", 40.0)]
GROUP_COLOR = {"P": "#0072B2", "T": "#D55E00", "G": "#009E73"}
CODEC_COLOR = {"JPEG 4:2:0": "#9a9a9a", "JPEG 4:4:4": "#4d4d4d", "WebP lossy": "#0072B2"}
CODEC_HATCH = {"JPEG 4:2:0": "", "JPEG 4:4:4": "//", "WebP lossy": ""}
REC_TARGET_SSIM = 0.98
SSIM_VMIN = 0.5
RESULT_DIR, FIG_DIR = ensure_dirs("t06")


# ------------------------------------------------------------------ 1. quét
def run_sweep(images):
    rows = []
    for name, grp, im in images:
        W, H = im.size
        for codec, (fmt, kw) in CODECS.items():
            for q in QUALITIES:
                r = evaluate(im, fmt, repeats=0, quality=q, **kw)
                rows.append(dict(image=name, group=grp, w=W, h=H, codec=codec, quality=q, **r))
        print("  quét xong", name, flush=True)
    return pd.DataFrame(rows)


def lossless_table(images):
    rows = []
    for name, grp, im in images:
        png = len(encode(im, "PNG", compress_level=9)) / 1024
        wll = len(encode(im, "WEBP", lossless=True, quality=100, method=4)) / 1024
        # kiểm tra tính không mất mát (đúng từng điểm ảnh)
        ok = np.array_equal(np.asarray(decode(encode(im, "WEBP", lossless=True, quality=100, method=4))),
                            np.asarray(im))
        rows.append(dict(image=name, group=grp, w=im.size[0], h=im.size[1],
                         png_kb=png, webp_lossless_kb=wll, webp_lossless_exact=ok))
    return pd.DataFrame(rows)


# --------------------------------------------------------------- 2. iso-quality
def first_reach(sub, metric, thr):
    """Trả về (q_min, size, bpp, psnr, ssim, size_interp) tại q nhỏ nhất đạt metric >= thr."""
    sub = sub.sort_values("quality").reset_index(drop=True)
    ok = np.where(sub[metric].to_numpy() >= thr)[0]
    if len(ok) == 0:
        return None
    i = int(ok[0])
    r = sub.iloc[i]
    size_i = r["size_kb"]
    interp_flag = "lưới"
    if i > 0:
        m0, m1 = sub.loc[i - 1, metric], sub.loc[i, metric]
        s0, s1 = sub.loc[i - 1, "size_kb"], sub.loc[i, "size_kb"]
        if np.isfinite(m0) and np.isfinite(m1) and m1 > m0:
            t = (thr - m0) / (m1 - m0)
            size_i = float(np.exp(np.log(s0) + t * (np.log(s1) - np.log(s0))))
            interp_flag = "nội suy"
    return dict(q_min=int(r["quality"]), size_kb=r["size_kb"], bpp=r["bpp"], psnr=r["psnr"],
                ssim=r["ssim"], size_interp_kb=size_i, interp=interp_flag)


def build_isoquality(sweep):
    rows = []
    for (img, grp, codec), sub in sweep.groupby(["image", "group", "codec"], sort=True):
        for metric, thr in TARGETS:
            res = first_reach(sub, metric, thr)
            base = dict(image=img, group=grp, codec=codec, target_metric=metric.upper(), target=thr)
            if res is None:
                rows.append(dict(**base, reached=False, q_min=np.nan, size_kb=np.nan, bpp=np.nan,
                                 psnr=np.nan, ssim=np.nan, size_interp_kb=np.nan, interp=""))
            else:
                rows.append(dict(**base, reached=True, **res))
    return pd.DataFrame(rows)


def pct_saving(a, b):
    """% tiết kiệm của a so với b = (b-a)/b*100."""
    return (b - a) / b * 100.0


def build_by_group(iso, lossless):
    out = []
    iso = iso.copy()
    iso["group_all"] = "ALL"
    for gname, gdf in [("ALL", iso)] + [(g, d) for g, d in iso.groupby("group")]:
        for (metric, thr), tdf in gdf.groupby(["target_metric", "target"]):
            piv_sz = tdf.pivot(index="image", columns="codec", values="size_kb")
            piv_si = tdf.pivot(index="image", columns="codec", values="size_interp_kb")
            common = piv_sz[CODEC_ORDER].dropna().index   # ảnh mà CẢ 3 codec đều đạt ngưỡng
            for codec in CODEC_ORDER:
                d = tdf[tdf.codec == codec]
                rd = d[d.reached]
                row = dict(group=gname, target_metric=metric, target=thr, codec=codec,
                           n_images=len(d), n_reached=len(rd),
                           mean_kb=rd.size_kb.mean(), median_kb=rd.size_kb.median(),
                           mean_bpp=rd.bpp.mean(), median_bpp=rd.bpp.median(),
                           median_qmin=rd.q_min.median(),
                           n_common=len(common),
                           mean_kb_common=piv_sz.loc[common, codec].mean() if len(common) else np.nan,
                           median_kb_common=piv_sz.loc[common, codec].median() if len(common) else np.nan)
                if codec == "WebP lossy":
                    for ref in ["JPEG 4:2:0", "JPEG 4:4:4"]:
                        for lab, piv in [("", piv_sz), ("_interp", piv_si)]:
                            ok = piv[[codec, ref]].dropna()
                            s = pct_saving(ok[codec], ok[ref])
                            tag = "420" if ref.endswith("2:0") else "444"
                            row[f"saving_vs_jpeg{tag}{lab}_mean_pct"] = s.mean() if len(s) else np.nan
                            row[f"saving_vs_jpeg{tag}{lab}_median_pct"] = s.median() if len(s) else np.nan
                            row[f"saving_vs_jpeg{tag}{lab}_n_pairs"] = len(s)
                out.append(row)
        # lossless
        ld = lossless if gname == "ALL" else lossless[lossless.group == gname]
        for lab, col in [("PNG (level 9)", "png_kb"), ("WebP lossless", "webp_lossless_kb")]:
            bpp = 8 * ld[col] * 1024 / (ld.w * ld.h)
            out.append(dict(group=gname, target_metric="lossless", target=np.nan, codec=lab,
                            n_images=len(ld), n_reached=len(ld), mean_kb=ld[col].mean(),
                            median_kb=ld[col].median(), mean_bpp=bpp.mean(), median_bpp=bpp.median()))
    return pd.DataFrame(out)


def lossless_vs_lossy(iso, lossless):
    d = iso[(iso.target_metric == "SSIM") & (iso.target == 0.99)]
    piv = d.pivot(index="image", columns="codec", values="size_kb")
    piv.columns = [f"lossy_{c.replace(' ', '_').replace(':', '')}_ssim099_kb" for c in piv.columns]
    out = lossless.set_index("image").join(piv).reset_index()
    for c in CODEC_ORDER:
        k = f"lossy_{c.replace(' ', '_').replace(':', '')}_ssim099_kb"
        out[f"webp_ll_smaller_than_{k.split('_ssim')[0].replace('lossy_', '')}"] = out.webp_lossless_kb < out[k]
    lossy_cols = [f"lossy_{c.replace(' ', '_').replace(':', '')}_ssim099_kb" for c in CODEC_ORDER]
    out["best_lossy_ssim099_kb"] = out[lossy_cols].min(axis=1)           # NaN (không đạt) bị bỏ qua
    out["best_lossy_ssim099_codec"] = out[lossy_cols].idxmin(axis=1).str.replace("lossy_", "").str.replace(
        "_ssim099_kb", "").str.replace("_", " ")
    out["webp_ll_smaller_than_best_lossy"] = out.webp_lossless_kb < out.best_lossy_ssim099_kb
    out["png_smaller_than_best_lossy"] = out.png_kb < out.best_lossy_ssim099_kb
    out["png_smaller_than_webp_lossy"] = out.png_kb < out["lossy_WebP_lossy_ssim099_kb"]
    out["webp_ll_smaller_than_png"] = out.webp_lossless_kb < out.png_kb
    out["webp_ll_over_webp_lossy_ssim099"] = out.webp_lossless_kb / out["lossy_WebP_lossy_ssim099_kb"]
    return out


# ------------------------------------------------------------ 4. PSNR vs SSIM
def correlation_tables(sweep):
    fin = sweep[np.isfinite(sweep.psnr)]
    rows = []
    rho, p = spearmanr(fin.psnr, fin.ssim)
    rows.append(dict(scope="toàn bộ", key="ALL", n=len(fin), spearman=rho))
    for g, d in fin.groupby("group"):
        rho, p = spearmanr(d.psnr, d.ssim)
        rows.append(dict(scope="nhóm", key=g, n=len(d), spearman=rho))
    for c, d in fin.groupby("codec"):
        rho, p = spearmanr(d.psnr, d.ssim)
        rows.append(dict(scope="codec", key=c, n=len(d), spearman=rho))
    # trong từng ảnh (loại ảnh hưởng của nội dung giữa các ảnh)
    per_img = []
    for (img, g), d in fin.groupby(["image", "group"]):
        rho, _ = spearmanr(d.psnr, d.ssim)
        per_img.append(dict(image=img, group=g, spearman_within=rho))
    per_img = pd.DataFrame(per_img)
    rows.append(dict(scope="trong ảnh (TB 20 ảnh)", key="ALL", n=len(per_img),
                     spearman=per_img.spearman_within.mean()))
    rows.append(dict(scope="trong ảnh (min)", key=per_img.loc[per_img.spearman_within.idxmin(), "image"],
                     n=1, spearman=per_img.spearman_within.min()))
    for g, d in per_img.groupby("group"):
        rows.append(dict(scope="trong ảnh (TB theo nhóm)", key=g, n=len(d), spearman=d.spearman_within.mean()))
    return pd.DataFrame(rows), per_img


def discordant_stats(sweep, min_dpsnr=0.5, min_dssim=0.002):
    """Cùng ảnh, mọi cặp cấu hình (A,B): bất đồng nếu dấu của ΔPSNR và ΔSSIM ngược nhau.
    Chỉ đếm cặp có |ΔPSNR| >= 0,5 dB và |ΔSSIM| >= 0,002 để loại sai khác quá nhỏ (nhiễu số)."""
    fin = sweep[np.isfinite(sweep.psnr)]
    rows, pairs = [], []
    for (img, g), d in fin.groupby(["image", "group"]):
        d = d.reset_index(drop=True)
        P, S = d.psnr.to_numpy(), d.ssim.to_numpy()
        n = len(d)
        iu = np.triu_indices(n, 1)
        dp = P[iu[0]] - P[iu[1]]
        ds = S[iu[0]] - S[iu[1]]
        valid = (np.abs(dp) >= min_dpsnr) & (np.abs(ds) >= min_dssim)
        disc = valid & (np.sign(dp) != np.sign(ds))
        rows.append(dict(image=img, group=g, n_pairs=int(valid.sum()), n_discordant=int(disc.sum())))
        for k in np.where(disc)[0]:
            a, b = iu[0][k], iu[1][k]
            if dp[k] < 0:      # đổi để A là cấu hình có PSNR cao hơn
                a, b = b, a
            pairs.append(dict(
                kind="cùng ảnh", image=img, group=g,
                A_codec=d.codec[a], A_q=int(d.quality[a]), A_psnr=P[a], A_ssim=S[a], A_kb=d.size_kb[a],
                B_codec=d.codec[b], B_q=int(d.quality[b]), B_psnr=P[b], B_ssim=S[b], B_kb=d.size_kb[b],
                dPSNR=P[a] - P[b], dSSIM=S[a] - S[b],
                size_ratio_A_over_B=d.size_kb[a] / d.size_kb[b]))
    stats = pd.DataFrame(rows)
    pairs = pd.DataFrame(pairs)
    return stats, pairs


def cross_image_pairs(sweep, tol_db=0.1, top=10):
    """Hai ảnh khác nhau, PSNR trong khoảng ±tol_db nhưng SSIM chênh nhiều nhất."""
    fin = sweep[np.isfinite(sweep.psnr)].reset_index(drop=True)
    P, S = fin.psnr.to_numpy(), fin.ssim.to_numpy()
    order = np.argsort(P)
    best = []
    for ii in range(len(order)):
        a = order[ii]
        for jj in range(ii + 1, len(order)):
            b = order[jj]
            if P[b] - P[a] > tol_db:
                break
            if fin.image[a] == fin.image[b]:
                continue
            best.append((abs(S[a] - S[b]), a, b))
    best.sort(reverse=True)
    rows, used = [], set()
    for diff, a, b in best:
        key = (fin.image[a], fin.image[b])
        if key in used or key[::-1] in used:
            continue
        used.add(key)
        rows.append(dict(kind="khác ảnh", image=f"{fin.image[a]} vs {fin.image[b]}",
                         group=f"{fin.group[a]} vs {fin.group[b]}",
                         A_codec=fin.codec[a], A_q=int(fin.quality[a]), A_psnr=P[a], A_ssim=S[a], A_kb=fin.size_kb[a],
                         B_codec=fin.codec[b], B_q=int(fin.quality[b]), B_psnr=P[b], B_ssim=S[b], B_kb=fin.size_kb[b],
                         dPSNR=P[a] - P[b], dSSIM=S[a] - S[b]))
        if len(rows) >= top:
            break
    return pd.DataFrame(rows)


def choose_example(pairs, sweep):
    """Chọn ví dụ minh hoạ: cùng ảnh, PSNR(A) cao hơn B >= 1 dB mà SSIM(A) thấp hơn B,
    ưu tiên cặp có dung lượng gần nhau (tỉ lệ 0,8-1,25 -> so sánh công bằng) và điểm
    min(ΔPSNR/1 dB, -ΔSSIM/0,01) lớn nhất."""
    p = pairs.copy()
    p["score"] = np.minimum(p.dPSNR / 1.0, -p.dSSIM / 0.01)
    p["fair_size"] = p.size_ratio_A_over_B.between(0.8, 1.25)
    cand = p[(p.dPSNR >= 1.0) & p.fair_size]
    if len(cand) == 0:
        cand = p[p.dPSNR >= 1.0]
    return cand.sort_values("score", ascending=False), p


def ssim_map(ref, test):
    """Bản đồ SSIM cục bộ, cùng tham số với common.ssim; trung bình 3 kênh."""
    mssim, S = structural_similarity(ref, test, channel_axis=2, data_range=255,
                                     gaussian_weights=True, sigma=1.5,
                                     use_sample_covariance=False, full=True)
    return float(mssim), S.mean(axis=2)


def recon(img, codec, q):
    fmt, kw = CODECS[codec]
    return decode(encode(img, fmt, quality=int(q), **kw))


def fig_ssim_map(images, ex):
    im = dict((n, i) for n, _, i in images)[ex.image]
    ref = np.asarray(im)
    A = np.asarray(recon(im, ex.A_codec, ex.A_q))
    B = np.asarray(recon(im, ex.B_codec, ex.B_q))
    mA, SA = ssim_map(ref, A)
    mB, SB = ssim_map(ref, B)
    eA = np.abs(ref.astype(float) - A.astype(float)).mean(axis=2)
    eB = np.abs(ref.astype(float) - B.astype(float)).mean(axis=2)
    # vùng cắt: cửa sổ 160x160 có tổng suy giảm cấu trúc (1-SSIM_A)+(1-SSIM_B) lớn nhất
    # (nơi mà hai chỉ số dễ khác nhau nhất; ví dụ vùng chữ nhỏ) để nhìn rõ chi tiết
    H, W = ref.shape[:2]
    c = 160
    diff = (1 - SA) + (1 - SB)
    ii = np.cumsum(np.cumsum(np.pad(diff, ((1, 0), (1, 0))), 0), 1)
    best, pos = -1e9, (0, 0)
    for y in range(0, H - c + 1, 20):
        for x in range(0, W - c + 1, 20):
            v = ii[y + c, x + c] - ii[y, x + c] - ii[y + c, x] + ii[y, x]
            if v > best:
                best, pos = v, (y, x)
    y0, x0 = pos
    sl = (slice(y0, y0 + c), slice(x0, x0 + c))
    vmax_e = max(eA[sl].max(), eB[sl].max(), 1)

    fig, axs = plt.subplots(3, 3, figsize=(10.5, 10.5))
    lab = lambda e, which: (f"{which}: {e.A_codec if which=='A' else e.B_codec}, q={e.A_q if which=='A' else e.B_q}")
    axs[0, 0].imshow(ref[sl]); axs[0, 0].set_title("Ảnh gốc (vùng cắt)", fontsize=11)
    axs[0, 1].imshow(A[sl]); axs[0, 1].set_title(f"A: {ex.A_codec}, q={ex.A_q}\nPSNR={ex.A_psnr:.2f} dB, SSIM={mA:.4f}", fontsize=10.5)
    axs[0, 2].imshow(B[sl]); axs[0, 2].set_title(f"B: {ex.B_codec}, q={ex.B_q}\nPSNR={ex.B_psnr:.2f} dB, SSIM={mB:.4f}", fontsize=10.5)
    im1 = axs[1, 1].imshow(SA[sl], cmap="gray", vmin=SSIM_VMIN, vmax=1)
    axs[1, 2].imshow(SB[sl], cmap="gray", vmin=SSIM_VMIN, vmax=1)
    axs[1, 1].set_title("Bản đồ SSIM cục bộ A", fontsize=10.5)
    axs[1, 2].set_title("Bản đồ SSIM cục bộ B", fontsize=10.5)
    im2 = axs[2, 1].imshow(eA[sl], cmap="magma", vmin=0, vmax=vmax_e)
    axs[2, 2].imshow(eB[sl], cmap="magma", vmin=0, vmax=vmax_e)
    axs[2, 1].set_title("|sai số| A (TB 3 kênh, mức xám)", fontsize=10.5)
    axs[2, 2].set_title("|sai số| B (cùng thang màu)", fontsize=10.5)
    for a in axs.ravel():
        a.set_xticks([]); a.set_yticks([])
    # cột 0, hàng 1-2: thông tin + thanh màu
    axs[1, 0].axis("off"); axs[2, 0].axis("off")
    cb1 = fig.colorbar(im1, ax=axs[1, 0], fraction=0.5, location="left", pad=0.0)
    cb1.set_label(f"SSIM cục bộ (thang {SSIM_VMIN:.1f}-1; <{SSIM_VMIN:.1f} hiện đen)", fontsize=10.5)
    cb2 = fig.colorbar(im2, ax=axs[2, 0], fraction=0.5, location="left", pad=0.0)
    cb2.set_label("|sai số| (mức xám, 0-255)", fontsize=11)
    fig.text(0.02, 0.985, f"Ảnh {ex.image}; kích thước tệp A = {ex.A_kb:.1f} KB, B = {ex.B_kb:.1f} KB. "
             f"A có PSNR cao hơn {ex.dPSNR:.2f} dB nhưng SSIM thấp hơn {-ex.dSSIM:.4f}.",
             fontsize=10, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(os.path.join(FIG_DIR, "ssim_map_example.png"), dpi=300)
    plt.close(fig)
    from common import psnr as _psnr
    cropA, cropB, cropR = A[sl], B[sl], ref[sl]
    return dict(mssimA=mA, mssimB=mB, crop=(y0, x0, c),
                crop_psnrA=_psnr(cropR, cropA), crop_psnrB=_psnr(cropR, cropB),
                crop_ssimA=float(SA[sl].mean()), crop_ssimB=float(SB[sl].mean()),
                meanerrA=float(eA.mean()), meanerrB=float(eB.mean()))


def fig_psnr_vs_ssim(sweep, corr):
    fin = sweep[np.isfinite(sweep.psnr)]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    for g in ["P", "T", "G"]:
        d = fin[fin.group == g]
        rho = corr[(corr.scope == "nhóm") & (corr.key == g)].spearman.iloc[0]
        lab = f"{GROUP_NAMES[g]} ({g}), ρ={rho:.3f}".replace(".", ",")
        axs[0].scatter(d.psnr, d.ssim, s=10, alpha=0.55, color=GROUP_COLOR[g], label=lab, linewidths=0)
        axs[1].scatter(d.psnr, -10 * np.log10(np.clip(1 - d.ssim, 1e-6, None)), s=10, alpha=0.55,
                       color=GROUP_COLOR[g], label=lab, linewidths=0)
    axs[0].axhline(0.99, color="black", lw=1.8, ls="--"); axs[0].axvline(40, color="black", lw=1.8, ls=":")
    axs[0].set_xlabel("PSNR (dB)"); axs[0].set_ylabel("SSIM")
    axs[0].set_ylim(0.3, 1.005)
    axs[1].axhline(-10 * np.log10(1 - 0.99), color="black", lw=1.8, ls="--")
    axs[1].axvline(40, color="black", lw=1.8, ls=":")
    axs[1].set_xlabel("PSNR (dB)"); axs[1].set_ylabel("−10·log$_{10}$(1 − SSIM) (dB)")
    for a, t in zip(axs, ["(a) Thang tuyến tính", "(b) SSIM đổi sang thang dB"]):
        a.grid(alpha=0.3); a.text(0.02, 0.88, t, transform=a.transAxes, va="top", fontsize=11)
    axs[0].legend(loc="lower right", fontsize=9.5, frameon=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "psnr_vs_ssim.png"), dpi=300)
    plt.close(fig)


def fig_iso(iso, lossless):
    lossless_mean = lossless.groupby("group")[["png_kb", "webp_lossless_kb"]].mean()
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.6), sharey=False)
    tg = [0.95, 0.98, 0.99]
    width = 0.26
    for ax, g in zip(axs, ["P", "T", "G"]):
        for k, codec in enumerate(CODEC_ORDER):
            vals, nr = [], []
            for t in tg:
                d = iso[(iso.group == g) & (iso.codec == codec) & (iso.target_metric == "SSIM") & (iso.target == t)]
                vals.append(d[d.reached].size_kb.mean() if d.reached.any() else np.nan)
                nr.append(int(d.reached.sum()))
            x = np.arange(len(tg)) + (k - 1) * width
            ax.bar(x, vals, width, color=CODEC_COLOR[codec], hatch=CODEC_HATCH[codec], edgecolor="black",
                   linewidth=1.2, label=codec)
            n_img = iso[iso.group == g].image.nunique()
            for xi, v, n in zip(x, vals, nr):
                if np.isfinite(v):
                    ax.text(xi, v * 1.04, f"{v:.0f}\n({n}/{n_img})", ha="center", va="bottom", fontsize=8)
                else:
                    ax.text(xi, 1.2, f"0/{n_img}\nkhông đạt", ha="center", va="bottom", fontsize=8, rotation=90)
        ax.set_xticks(np.arange(len(tg))); ax.set_xticklabels([str(t).replace(".", ",") for t in tg])
        ax.set_xlabel("Ngưỡng SSIM mục tiêu"); ax.set_yscale("log")
        n_img = iso[iso.group == g].image.nunique()
        ax.set_title(f"{GROUP_NAMES[g]} ({g}, {n_img} ảnh)", fontsize=11)
        ax.grid(alpha=0.3, which="both", axis="y")
        ax.set_ylim(1, 2000)
        ax.axhline(lossless_mean.loc[g, "webp_lossless_kb"], color="black", lw=1.8, ls="--",
                   label="WebP lossless (TB nhóm)")
    axs[0].set_ylabel("Dung lượng TB tại quality nhỏ nhất đạt ngưỡng (KB)\n(số ảnh đạt/tổng ghi trong ngoặc)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(os.path.join(FIG_DIR, "iso_ssim_size.png"), dpi=300)
    plt.close(fig)


# --------------------------------------------------------------- 3. khuyến nghị
Q_FLOOR = 50   # sàn quality thận trọng (xem docstring build_recommendation)
SUBGROUPS = [("T", "Ảnh có chữ (T)"), ("G_clean", "Gradient/nền trơn, sạch (G01-G03)"),
             ("G_noisy", "Gradient/nền trơn, nhiễu cảm biến (G04-G06)"), ("P", "Ảnh chụp nhiều chi tiết (P)")]
TIERS = [("tiết kiệm", 0.95), ("chất lượng cao", 0.98)]


def subgroup_images(sweep, key):
    if key == "G_clean":
        return sorted(i for i in sweep[sweep.group == "G"].image.unique() if "noise" not in i)
    if key == "G_noisy":
        return sorted(i for i in sweep[sweep.group == "G"].image.unique() if "noise" in i)
    return sorted(sweep[sweep.group == key].image.unique())


def build_recommendation(sweep, iso, lossless):
    """Bảng khuyến nghị theo loại ảnh và hai mức mục tiêu (SSIM >= 0,95 "tiết kiệm", >= 0,98 "chất lượng cao").
    Quy tắc (xác định, không chủ quan):
      * q_metric = quality NHỎ NHẤT trên lưới sao cho TẤT CẢ ảnh trong nhóm đạt SSIM mục tiêu (max của q_min
        theo ảnh) - bảo đảm cho ảnh xấu nhất; nếu có ảnh không đạt ở q=100 thì codec đó "không đạt".
      * q_khuyến_nghị = max(q_metric, 50). Sàn 50 là biên an toàn kinh nghiệm cho các lỗi mà PSNR/SSIM đánh giá
        thấp (dải màu - banding trên nền gradient, viền chữ nhỏ); quan sát bằng mắt trên G01 cho thấy dải mờ ở
        WebP q=5. Đây KHÔNG phải kết quả đo, chỉ là biên an toàn.
      * Định dạng chính = ứng viên (WebP lossy, JPEG 4:2:0, JPEG 4:4:4, WebP lossless) đạt mục tiêu cho mọi ảnh
        và có dung lượng TB nhỏ nhất tại q_khuyến_nghị.
      * Dự phòng cho <picture> = JPEG (4:2:0 hoặc 4:4:4) có dung lượng TB nhỏ nhất đạt mục tiêu; nếu không có
        JPEG nào đạt (SSIM 0,98 trên ảnh nhiễu/ảnh chi tiết) thì dự phòng là PNG (không mất mát)."""
    rows = []
    for key, label in SUBGROUPS:
        imgs = subgroup_images(sweep, key)
        sw = sweep[sweep.image.isin(imgs)]
        ll = lossless[lossless.image.isin(imgs)]
        for tier, thr in TIERS:
            gi = iso[iso.image.isin(imgs) & (iso.target_metric == "SSIM") & (iso.target == thr)]
            cands = {}
            for codec in CODEC_ORDER:
                d = gi[gi.codec == codec]
                if not d.reached.all():
                    cands[codec] = None
                    continue
                qm = int(d.q_min.max())
                qr = max(qm, Q_FLOOR)
                x = sw[(sw.codec == codec) & (sw.quality == qr)]
                cands[codec] = dict(q_metric=qm, q_rec=qr, kb=x.size_kb.mean(), bpp=x.bpp.mean(),
                                    ssim_mean=x.ssim.mean(), ssim_min=x.ssim.min(),
                                    psnr_mean=x.psnr.mean(), psnr_min=x.psnr.min())
            cands["WebP lossless"] = dict(q_metric=np.nan, q_rec=np.nan, kb=ll.webp_lossless_kb.mean(),
                                          bpp=(8 * ll.webp_lossless_kb * 1024 / (ll.w * ll.h)).mean(),
                                          ssim_mean=1.0, ssim_min=1.0, psnr_mean=np.inf, psnr_min=np.inf)
            ok = {k: v for k, v in cands.items() if v is not None}
            prim = min(ok, key=lambda k: ok[k]["kb"])
            jp = {k: v for k, v in ok.items() if k.startswith("JPEG")}
            if jp:
                fb = min(jp, key=lambda k: jp[k]["kb"])
                fbd = jp[fb]
            else:
                fb = "PNG (level 9)"
                fbd = dict(q_metric=np.nan, q_rec=np.nan, kb=ll.png_kb.mean(),
                           bpp=(8 * ll.png_kb * 1024 / (ll.w * ll.h)).mean(), ssim_mean=1.0, ssim_min=1.0,
                           psnr_mean=np.inf, psnr_min=np.inf)
            P = ok[prim]
            row = dict(image_type=label, subgroup=key, n_images=len(imgs), tier=tier, target_ssim=thr,
                       primary_format=prim, primary_quality=P["q_rec"], primary_q_metric=P["q_metric"],
                       exp_size_kb=P["kb"], exp_bpp=P["bpp"], exp_ssim_mean=P["ssim_mean"],
                       exp_ssim_min=P["ssim_min"], exp_psnr_mean=P["psnr_mean"], exp_psnr_min=P["psnr_min"],
                       fallback_format=fb, fallback_quality=fbd["q_rec"], fallback_q_metric=fbd["q_metric"],
                       fallback_size_kb=fbd["kb"], fallback_ssim_min=fbd["ssim_min"],
                       fallback_overhead_pct=(fbd["kb"] / P["kb"] - 1) * 100,
                       webp_lossless_kb=ll.webp_lossless_kb.mean(), png_kb=ll.png_kb.mean(),
                       webp_lossy_reaches_all=cands["WebP lossy"] is not None,
                       jpeg420_reaches_all=cands["JPEG 4:2:0"] is not None,
                       jpeg444_reaches_all=cands["JPEG 4:4:4"] is not None)
            rows.append(row)
    return pd.DataFrame(rows)


def mechanism(images, ex):
    """Chẩn đoán cơ chế: tại quality=100 mỗi codec, tách SSIM/PSNR thành phần độ sáng Y và sắc độ Cb, Cr
    (YCbCr của Pillow). Nếu SSIM_Y ~ 1 nhưng SSIM RGB thấp hơn nhiều -> trần SSIM do giảm mẫu sắc độ."""
    def ycc(a):
        return np.asarray(Image.fromarray(a).convert("YCbCr")).astype(np.float64)
    def p(a, b):
        mse = np.mean((a - b) ** 2)
        return float("inf") if mse == 0 else float(10 * np.log10(255.0 ** 2 / mse))
    def s2(a, b):
        return float(structural_similarity(a, b, data_range=255, gaussian_weights=True, sigma=1.5,
                                           use_sample_covariance=False))
    def row(name, grp, tag, ref, out):
        yr, yo = ycc(ref), ycc(out)
        return dict(image=name, group=grp, config=tag, ssim_rgb=float(
            structural_similarity(ref, out, channel_axis=2, data_range=255, gaussian_weights=True, sigma=1.5,
                                  use_sample_covariance=False)),
            ssim_Y=s2(yr[..., 0], yo[..., 0]), ssim_Cb=s2(yr[..., 1], yo[..., 1]), ssim_Cr=s2(yr[..., 2], yo[..., 2]),
            psnr_Y=p(yr[..., 0], yo[..., 0]), psnr_Cb=p(yr[..., 1], yo[..., 1]), psnr_Cr=p(yr[..., 2], yo[..., 2]),
            psnr_rgb=p(ref.astype(float), out.astype(float)))
    rows = []
    for name, grp, im in images:
        ref = np.asarray(im)
        for codec in CODEC_ORDER:
            rows.append(row(name, grp, f"{codec} q=100", ref, np.asarray(recon(im, codec, 100))))
    im = dict((n, i) for n, _, i in images)[ex.image]
    ref = np.asarray(im)
    for tag, codec, q in [("A", ex.A_codec, ex.A_q), ("B", ex.B_codec, ex.B_q)]:
        rows.append(row(ex.image, "T", f"ví dụ {tag}: {codec} q={q}", ref, np.asarray(recon(im, codec, q))))
    return pd.DataFrame(rows)


def vn(x, nd=1):
    """Định dạng số theo kiểu Việt Nam (dấu phẩy thập phân); NaN -> '–'."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return f"{x:.{nd}f}".replace(".", ",")


def write_section_tables(bygroup, llv, corr, dstats, rec, lossless):
    """Sinh các bảng markdown cho section.md trực tiếp từ CSV (tránh chép số tay)."""
    L = []
    L.append("### Bảng 1 - Iso-quality (SSIM)\n")
    L.append("| Nhóm | Ngưỡng SSIM | JPEG 4:2:0: trung vị KB (số ảnh đạt) | JPEG 4:4:4 | WebP lossy | WebP tiết kiệm so với JPEG 4:2:0: trung vị % (số cặp) |")
    L.append("|---|---|---|---|---|---|")
    for g in ["P", "T", "G", "ALL"]:
        for t in [0.95, 0.98, 0.99]:
            d = bygroup[(bygroup.group == g) & (bygroup.target_metric == "SSIM") & (np.isclose(bygroup.target, t))]
            cells = []
            for c in CODEC_ORDER:
                r = d[d.codec == c].iloc[0]
                n_all = int(r.n_images)
                cells.append(f"{vn(r.median_kb)} ({int(r.n_reached)}/{n_all})")
            w = d[d.codec == "WebP lossy"].iloc[0]
            sv = f"{vn(w.saving_vs_jpeg420_median_pct)} ({int(w.saving_vs_jpeg420_n_pairs)})" if w.saving_vs_jpeg420_n_pairs else "–"
            L.append(f"| {g} | {vn(t, 2)} | " + " | ".join(cells) + f" | {sv} |")
    L.append("\n### Bảng 2 - Iso-quality (PSNR), toàn bộ 20 ảnh\n")
    L.append("| Ngưỡng PSNR | JPEG 4:2:0: trung vị KB (số ảnh đạt) | JPEG 4:4:4 | WebP lossy | WebP tiết kiệm so với JPEG 4:2:0: trung vị % (số cặp) |")
    L.append("|---|---|---|---|---|")
    for t in [35.0, 40.0]:
        d = bygroup[(bygroup.group == "ALL") & (bygroup.target_metric == "PSNR") & (np.isclose(bygroup.target, t))]
        cells = [f"{vn(d[d.codec == c].iloc[0].median_kb)} ({int(d[d.codec == c].iloc[0].n_reached)}/20)" for c in CODEC_ORDER]
        w = d[d.codec == "WebP lossy"].iloc[0]
        L.append(f"| {vn(t, 0)} dB | " + " | ".join(cells) + f" | {vn(w.saving_vs_jpeg420_median_pct)} ({int(w.saving_vs_jpeg420_n_pairs)}) |")
    L.append("\n### Bảng 3 - Không mất mát so với lossy tại SSIM 0,99 (dung lượng TB, KB)\n")
    L.append("| Nhóm | PNG (level 9) | WebP lossless | Số ảnh WebP lossless NHỎ HƠN lossy tốt nhất đạt 0,99 |")
    L.append("|---|---|---|---|")
    for g in ["P", "T", "G"]:
        d = llv[llv.group == g]
        L.append(f"| {g} | {vn(d.png_kb.mean())} | {vn(d.webp_lossless_kb.mean())} | {int(d.webp_ll_smaller_than_best_lossy.sum())}/{len(d)} |")
    L.append(f"| Cả 20 ảnh | {vn(llv.png_kb.mean())} | {vn(llv.webp_lossless_kb.mean())} | {int(llv.webp_ll_smaller_than_best_lossy.sum())}/20 |")
    L.append("\n### Bảng 4 - Tương quan PSNR-SSIM (Spearman)\n")
    L.append("| Phạm vi | n | rho |")
    L.append("|---|---|---|")
    for _, r in corr.iterrows():
        L.append(f"| {r.scope} - {r.key} | {int(r.n)} | {vn(r.spearman, 3)} |")
    nd, nt = int(dstats.n_discordant.sum()), int(dstats.n_pairs.sum())
    L.append(f"\nCặp bất đồng (cùng ảnh, |dPSNR|>=0,5 dB và |dSSIM|>=0,002): {nd}/{nt} = {vn(100*nd/nt, 2)} %")
    for g, d in dstats.groupby("group"):
        L.append(f"- Nhóm {g}: {int(d.n_discordant.sum())}/{int(d.n_pairs.sum())} = {vn(100*d.n_discordant.sum()/d.n_pairs.sum(), 2)} %")
    L.append("\n### Bảng 5 - Khuyến nghị\n")
    L.append("| Loại ảnh (số ảnh) | Mục tiêu SSIM | Định dạng chính, quality (q đo được) | Dung lượng TB KB (bpp) | SSIM TB (min) | PSNR TB (min) dB | Dự phòng cho `<picture>`: định dạng, quality, KB (so với chính) | WebP lossless / PNG KB |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, r in rec.iterrows():
        q = "" if not np.isfinite(r.primary_quality) else f" q={int(r.primary_quality)} (q đo {int(r.primary_q_metric)})"
        pm = "–" if not np.isfinite(r.exp_psnr_mean) else f"{vn(r.exp_psnr_mean)} ({vn(r.exp_psnr_min)})"
        fq = "" if not np.isfinite(r.fallback_quality) else f" q={int(r.fallback_quality)}"
        L.append(f"| {r.image_type} ({r.n_images}) | >= {vn(r.target_ssim, 2)} | {r.primary_format}{q} | {vn(r.exp_size_kb)} ({vn(r.exp_bpp, 2)}) | "
                 f"{vn(r.exp_ssim_mean, 3)} ({vn(r.exp_ssim_min, 3)}) | {pm} | {r.fallback_format}{fq}, {vn(r.fallback_size_kb)} KB (+{vn(r.fallback_overhead_pct, 0)} %) | "
                 f"{vn(r.webp_lossless_kb)} / {vn(r.png_kb)} |")
    open(os.path.join(RESULT_DIR, "section_tables.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", action="store_true")
    args = ap.parse_args()
    images = list_images()
    sweep_path = os.path.join(RESULT_DIR, "sweep.csv")
    if args.reuse and os.path.exists(sweep_path):
        sweep = pd.read_csv(sweep_path)
    else:
        print("Quét quality ...", flush=True)
        sweep = run_sweep(images)
        sweep.to_csv(sweep_path, index=False, float_format="%.6g")
    lossless = lossless_table(images)

    iso = build_isoquality(sweep)
    iso.to_csv(os.path.join(RESULT_DIR, "isoquality.csv"), index=False, float_format="%.6g")
    bygroup = build_by_group(iso, lossless)
    bygroup.to_csv(os.path.join(RESULT_DIR, "isoquality_by_group.csv"), index=False, float_format="%.6g")
    llv = lossless_vs_lossy(iso, lossless)
    llv.to_csv(os.path.join(RESULT_DIR, "lossless_vs_lossy.csv"), index=False, float_format="%.6g")

    corr, per_img = correlation_tables(sweep)
    corr.to_csv(os.path.join(RESULT_DIR, "spearman_psnr_ssim.csv"), index=False, float_format="%.6g")
    dstats, pairs = discordant_stats(sweep)
    dstats.to_csv(os.path.join(RESULT_DIR, "discordant_by_image.csv"), index=False)
    cand, pairs_scored = choose_example(pairs, sweep)
    cross = cross_image_pairs(sweep)
    pd.concat([cand.head(15).assign(kind="cùng ảnh (top)"), cross], ignore_index=True).to_csv(
        os.path.join(RESULT_DIR, "disagreement_examples.csv"), index=False, float_format="%.6g")

    rec = build_recommendation(sweep, iso, lossless)
    rec.to_csv(os.path.join(RESULT_DIR, "recommendation.csv"), index=False, float_format="%.6g")

    fig_iso(iso, lossless)
    corr_all = corr
    fig_psnr_vs_ssim(sweep, corr_all)
    ex = cand.iloc[0]
    info = fig_ssim_map(images, ex)
    print("Ví dụ:", dict(ex), info)
    pd.Series({**ex.to_dict(), **{k: str(v) for k, v in info.items()}}).to_csv(
        os.path.join(RESULT_DIR, "ssim_map_example_info.csv"), header=False)
    write_section_tables(bygroup, llv, corr, dstats, rec, lossless)
    mech = mechanism(images, ex)
    mech.to_csv(os.path.join(RESULT_DIR, "mechanism_diagnostic.csv"), index=False, float_format="%.6g")
    print("Xong phần số liệu/hình.")


if __name__ == "__main__":
    main()
