# -*- coding: utf-8 -*-
"""t07 - "Với ảnh có chữ, nên nén ở mức nào để vẫn đọc được?" bằng thước đo KHÁCH QUAN (OCR).

Ý tưởng: dùng OCR tesseract tiếng Việt (lang='vie') làm "người đọc đại diện". Chữ được coi là
còn đọc được nếu tỉ lệ lỗi ký tự (CER) sau nén không tệ hơn CER trên ảnh PNG gốc quá
δ điểm phần trăm (δ = 1 và 2). Dùng mức chênh so với ảnh gốc vì OCR không hoàn hảo ngay cả khi
ảnh sạch (sai số "nền" của OCR không được tính cho codec).

Các bước
1. Chọn cấu hình OCR TRÊN ẢNH GỐC (PNG): thử {toàn ảnh, cắt vùng chữ} x {phóng 1x, 2x} x
   psm {3, 4, 6, 11}, lấy cấu hình có CER trung bình thấp nhất trong số các cấu hình hướng
   khối-văn-bản (psm 3/4/6; psm 11 "sparse" bị loại vì không đảm bảo thứ tự đọc, CER dễ nhảy
   do đảo dòng chứ không do chất lượng ảnh); hoà thì ưu tiên psm 6. Toàn bộ bảng thử được lưu
   ở ocr_config_selection.csv. Lý do cắt vùng: ground truth (data/text_ground_truth.json) chỉ có
   tên + giá + 6 dòng thông số; toàn ảnh còn có dải tiêu đề, nhãn giảm giá, dòng "Đã bán",
   tiêu đề bảng ... mà GT không chứa => chèn thừa làm CER > 25% ngay cả trên ảnh gốc, không phản
   ánh chất lượng nén.
2. Vùng cắt CỐ ĐỊNH theo bố cục text_card() trong make_dataset.py, hệ số k = S/1000:
     vùng A (tên + giá): x ∈ [440k, S], y ∈ [120k, 270k]
     vùng B (6 dòng thông số): x ∈ [30k, S-30k], y ∈ [585k, S]
   OCR từng vùng, nối văn bản theo thứ tự A rồi B, so với GT = [tên, giá, 6 dòng thông số].
3. Với 7 ảnh nhóm T, mã hoá JPEG 4:2:0 (mặc định Pillow), JPEG 4:4:4 (subsampling=0), WebP lossy
   (method=4) ở quality ∈ {5,10,20,30,40,50,60,75,90}; giải mã bằng common.decode; đo size_kb,
   PSNR, SSIM (common.psnr/ssim trên toàn ảnh) và CER/WER.
4. CER = Levenshtein(ký tự) / số ký tự GT; WER = Levenshtein(từ) / số từ GT; cả hai sau chuẩn
   hoá Unicode NFC và gộp khoảng trắng. Levenshtein tự cài bằng quy hoạch động (2 hàng).
5. "Còn đọc được": CER(nén) <= CER(gốc) + δ. Quality tối thiểu = quality nhỏ nhất trong lưới sao
   cho nó VÀ MỌI quality cao hơn trong lưới đều thoả (chống kết quả đơn điệu giả do OCR nhiễu).

Đầu ra: results/t07/{ocr_config_selection,ocr_results,min_readable_quality,min_readable_summary}.csv,
figures/t07/{cer_vs_quality,cer_vs_size,text_crops}.png.
Chạy: cd /home/claude/nen_anh && python src/t07_text_readability.py
"""
import os
os.environ.setdefault("OMP_THREAD_LIMIT", "1")  # tesseract dùng 1 luồng: máy chỉ 2 lõi, ổn định hơn
import re
import sys
import unicodedata

import numpy as np
import pandas as pd
import pytesseract
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (SEED, GROUP_NAMES, list_images, encode, decode, psnr, ssim,  # noqa: E402
                    ensure_dirs, load_text_gt, configure_tesseract)

np.random.seed(SEED)
configure_tesseract(require_vie=True)
plt.rcParams["font.family"] = "DejaVu Sans"

QUALITIES = [5, 10, 20, 30, 40, 50, 60, 75, 90]
DELTAS = [1.0, 2.0]  # điểm phần trăm
CODECS = {
    "JPEG 4:2:0": ("JPEG", {}),
    "JPEG 4:4:4": ("JPEG", {"subsampling": 0}),
    "WebP lossy": ("WEBP", {"method": 4}),
}


# ---------------------------------------------------------------- chỉ số văn bản
def norm(s):
    """NFC + gộp mọi khoảng trắng (kể cả xuống dòng) thành 1 dấu cách."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def levenshtein(a, b):
    """Khoảng cách Levenshtein (chèn/xoá/thay = 1) bằng quy hoạch động, bộ nhớ O(len(b)).
    a, b là chuỗi hoặc list (ký tự hoặc từ)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref, hyp):
    ref, hyp = norm(ref), norm(hyp)
    return 100.0 * levenshtein(ref, hyp) / len(ref)


def wer(ref, hyp):
    r, h = norm(ref).split(), norm(hyp).split()
    return 100.0 * levenshtein(r, h) / len(r)


# ---------------------------------------------------------------- vùng cắt & OCR
def regions(S):
    """Hai vùng chữ cố định theo text_card() (k = S/1000). Trả về [(x0,y0,x1,y1), ...]."""
    k = S / 1000.0
    A = (int(440 * k), int(120 * k), S, int(270 * k))
    B = (int(30 * k), int(585 * k), S - int(30 * k), S)
    return [A, B]


def ocr(im, mode="crop", up=2, psm=6):
    """OCR 1 ảnh PIL. mode 'crop': OCR từng vùng A, B rồi trả về list văn bản; 'full': cả ảnh."""
    S = im.size[0]
    parts = [im] if mode == "full" else [im.crop(r) for r in regions(S)]
    out = []
    for p in parts:
        if up > 1:
            p = p.resize((p.size[0] * up, p.size[1] * up), Image.LANCZOS)
        out.append(pytesseract.image_to_string(p, lang="vie", config=f"--psm {psm}"))
    return out


def gt_parts(lines):
    """GT tách theo vùng: A = [tên, giá], B = 6 dòng thông số."""
    return [" ".join(lines[:2]), " ".join(lines[2:])]


# ---------------------------------------------------------------- bước 1: chọn cấu hình OCR
def select_ocr_config(timgs, gt):
    rows = []
    for mode in ["full", "crop"]:
        for up in [1, 2]:
            for psm in [3, 4, 6, 11]:
                cs = []
                for n, im in timgs:
                    ref = " ".join(gt[n])
                    hyp = " ".join(ocr(im, mode, up, psm))
                    cs.append(cer(ref, hyp))
                rows.append({"mode": mode, "upscale": up, "psm": psm,
                             "cer_mean": float(np.mean(cs)), **{n: c for (n, _), c in zip(timgs, cs)}})
    df = pd.DataFrame(rows)
    cand = df[(df["mode"] == "crop") & (df["psm"].isin([3, 4, 6]))].copy()
    cand["pref"] = (cand["psm"] != 6).astype(int)
    best = cand.sort_values(["cer_mean", "pref", "upscale"]).iloc[0]
    df["chosen"] = (df["mode"] == best["mode"]) & (df["upscale"] == best["upscale"]) & (df["psm"] == best["psm"])
    return df, best["mode"], int(best["upscale"]), int(best["psm"])


# ---------------------------------------------------------------- bước 3: thí nghiệm chính
def run():
    rdir, fdir = ensure_dirs("t07")
    gt = load_text_gt()
    timgs = [(n, im) for n, g, im in list_images() if g == "T"]
    print("Số ảnh T:", len(timgs))

    cfg_df, mode, up, psm = select_ocr_config(timgs, gt)
    cfg_df.to_csv(os.path.join(rdir, "ocr_config_selection.csv"), index=False, float_format="%.3f")
    print(cfg_df[["mode", "upscale", "psm", "cer_mean", "chosen"]].to_string())
    print(f"Chọn OCR: mode={mode}, upscale={up}, psm={psm}")

    def measure(n, ref_im, im):
        parts = ocr(im, mode, up, psm)
        g = gt_parts(gt[n])
        ra = np.asarray(ref_im).astype(np.float64)
        ta = np.asarray(im).astype(np.float64)
        xa0, ya0, xa1, ya1 = regions(im.size[0])[0]
        return {
            "cer": cer(" ".join(g), " ".join(parts)),
            "wer": wer(" ".join(g), " ".join(parts)),
            "cer_name_price": cer(g[0], parts[0]),
            "cer_specs": cer(g[1], parts[1]),
            "mae_rgb_nameprice": float(np.abs(ra[ya0:ya1, xa0:xa1] - ta[ya0:ya1, xa0:xa1]).mean()),
            "ocr_text": norm(" | ".join(norm(p) for p in parts)),
        }

    rows = []
    for n, im in timgs:
        S = im.size[0]
        png = encode(im, "PNG", compress_level=9)
        m0 = measure(n, im, im)
        rows.append({"image": n, "size_px": S, "codec": "PNG gốc", "quality": "", "size_kb": len(png) / 1024,
                     "psnr": float("inf"), "ssim": 1.0, **m0})
        for cname, (fmt, kw) in CODECS.items():
            for q in QUALITIES:
                data = encode(im, fmt, quality=q, **kw)
                rec = decode(data)
                m = measure(n, im, rec)
                rows.append({"image": n, "size_px": S, "codec": cname, "quality": q, "size_kb": len(data) / 1024,
                             "psnr": psnr(np.asarray(im), np.asarray(rec)),
                             "ssim": ssim(np.asarray(im), np.asarray(rec)), **m})
        print(n, "xong", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(rdir, "ocr_results.csv"), index=False, float_format="%.4f")
    return df, rdir, fdir, (mode, up, psm), timgs


# ---------------------------------------------------------------- bước 5: quality tối thiểu
def min_readable(df, rdir):
    base = df[df["codec"] == "PNG gốc"].set_index("image")
    out = []
    for n, g in df[df["codec"] != "PNG gốc"].groupby("image"):
        for cname in CODECS:
            sub = g[g["codec"] == cname].sort_values("quality")
            for d in DELTAS:
                ok = (sub["cer"] <= base.loc[n, "cer"] + d).to_numpy()
                qmin, row = np.nan, None
                for i in range(len(sub)):
                    if ok[i:].all():
                        qmin, row = sub.iloc[i]["quality"], sub.iloc[i]
                        break
                q90 = sub[sub["quality"] == 90].iloc[0]
                out.append({"image": n, "size_px": int(base.loc[n, "size_px"]), "codec": cname, "delta_pp": d,
                            "cer_png": base.loc[n, "cer"], "q_min": qmin,
                            "cer_at_qmin": row["cer"] if row is not None else np.nan,
                            "size_kb_at_qmin": row["size_kb"] if row is not None else np.nan,
                            "size_kb_q90": q90["size_kb"], "size_kb_png": base.loc[n, "size_kb"],
                            "ssim_at_qmin": row["ssim"] if row is not None else np.nan})
    mq = pd.DataFrame(out)
    mq.to_csv(os.path.join(rdir, "min_readable_quality.csv"), index=False, float_format="%.4f")
    summ = (mq.groupby(["size_px", "codec", "delta_pp"])
              .agg(n_img=("image", "count"), n_found=("q_min", lambda s: int(s.notna().sum())),
                   q_min_median=("q_min", "median"), q_min_worst=("q_min", "max"),
                   size_kb_mean=("size_kb_at_qmin", "mean"), size_kb_q90_mean=("size_kb_q90", "mean"),
                   size_kb_png_mean=("size_kb_png", "mean"), cer_png_mean=("cer_png", "mean"))
              .reset_index())
    summ.to_csv(os.path.join(rdir, "min_readable_summary.csv"), index=False, float_format="%.3f")
    return mq, summ


# ---------------------------------------------------------------- hình
STY = {"JPEG 4:2:0": dict(color="#000000", marker="o", ls="-"),
       "JPEG 4:4:4": dict(color="#0072B2", marker="s", ls="--"),
       "WebP lossy": dict(color="#D55E00", marker="^", ls="-.")}


def fig_cer_quality(df, fdir):
    d = df[df["codec"] != "PNG gốc"]
    base = df[df["codec"] == "PNG gốc"]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, S in zip(axs, [1000, 500]):
        for cname in CODECS:
            s = d[(d["codec"] == cname) & (d["size_px"] == S)]
            g = s.groupby("quality")["cer"].agg(["mean", "min", "max"])
            ax.plot(g.index, g["mean"], label=cname, lw=2.0, ms=6, **STY[cname])
            ax.fill_between(g.index, g["min"], g["max"], color=STY[cname]["color"], alpha=0.10, lw=0)
        b = base[base["size_px"] == S]["cer"].mean()
        ax.axhline(b, color="gray", lw=1.8, ls=":", label=f"PNG gốc ({b:.1f} %)")
        ax.axhline(b + 1, color="gray", lw=1.0, ls="--", label="ngưỡng gốc + 1 đ.%")
        lab = "ảnh 1000 px (chữ thông số 26 px)" if S == 1000 else "ảnh 500 px (chữ thông số 14 px)"
        ax.set_xlabel("Quality của bộ mã hoá (0–100)", fontsize=11)
        ax.set_xticks(QUALITIES)
        ax.set_yscale("symlog", linthresh=5)
        ax.set_yticks([0, 1, 2, 5, 10, 20, 50, 100])
        ax.set_yticklabels(["0", "1", "2", "5", "10", "20", "50", "100"])
        ax.set_ylim(0, 110)
        ax.set_title(lab, fontsize=11, color="black")
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=10)
    axs[0].set_ylabel("CER của OCR (%) – trung bình, dải = min–max", fontsize=11)
    axs[0].legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(fdir, "cer_vs_quality.png"), dpi=300)
    plt.close(fig)


def fig_cer_size(df, fdir):
    d = df[df["codec"] != "PNG gốc"]
    base = df[df["codec"] == "PNG gốc"]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, S in zip(axs, [1000, 500]):
        for cname in CODECS:
            s = d[(d["codec"] == cname) & (d["size_px"] == S)]
            g = s.groupby("quality")[["size_kb", "cer"]].mean()
            ax.plot(g["size_kb"], g["cer"], label=cname, lw=2.0, ms=6, **STY[cname])
            for q, (x, y) in g.iterrows():
                if q in (10, 30, 75):
                    ax.annotate(f"q{q}", (x, y), textcoords="offset points", xytext=(4, 5), fontsize=8)
        b = base[base["size_px"] == S]["cer"].mean()
        ax.axhline(b, color="gray", lw=1.8, ls=":", label=f"PNG gốc ({b:.1f} %)")
        ax.axhline(b + 1, color="gray", lw=1.0, ls="--", label="ngưỡng gốc + 1 đ.%")
        ax.set_xscale("log")
        ax.set_yscale("symlog", linthresh=5)
        ax.set_yticks([0, 1, 2, 5, 10, 20, 50, 100])
        ax.set_yticklabels(["0", "1", "2", "5", "10", "20", "50", "100"])
        ax.set_ylim(0, 110)
        ax.set_xlabel("Dung lượng trung bình (KB, thang log)", fontsize=11)
        ax.set_title("ảnh 1000 px" if S == 1000 else "ảnh 500 px", fontsize=11, color="black")
        ax.grid(alpha=0.3, which="both")
        ax.tick_params(labelsize=10)
    axs[0].set_ylabel("CER của OCR (%) – trung bình", fontsize=11)
    axs[0].legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(fdir, "cer_vs_size.png"), dpi=300)
    plt.close(fig)


def fig_crops(df, fdir, timgs):
    """Cắt 2 dòng thông số của T05 (chữ 14 px) ở: gốc / JPEG q20 / JPEG q50 / WebP q20 / WebP q50."""
    n, im = [t for t in timgs if t[0].startswith("T05")][0]
    S = im.size[0]
    k = S / 1000.0
    box = (int(30 * k), int((595 + 56) * k) - 3, int(640 * k), int((595 + 3 * 56) * k) - 3)  # dòng thông số 2-3
    cfgs = [("PNG gốc", None, None), ("JPEG 4:2:0", 20, "JPEG"), ("JPEG 4:2:0", 50, "JPEG"),
            ("WebP lossy", 20, "WEBP"), ("WebP lossy", 50, "WEBP")]
    fig, axs = plt.subplots(len(cfgs), 1, figsize=(8, 8.6))
    for ax, (cname, q, fmt) in zip(axs, cfgs):
        if q is None:
            rec, kb = im, df[(df["image"] == n) & (df["codec"] == "PNG gốc")].iloc[0]
            lab = "PNG gốc"
        else:
            rec = decode(encode(im, fmt, quality=q, **CODECS[cname][1]))
            kb = df[(df["image"] == n) & (df["codec"] == cname) & (df["quality"] == q)].iloc[0]
            lab = f"{cname} q{q}"
        crop = rec.crop(box)
        ax.imshow(np.asarray(crop), interpolation="nearest")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_ylabel(f"{lab}\nCER = {kb['cer']:.1f} %\n{kb['size_kb']:.1f} KB", rotation=0, ha="right",
                      va="center", fontsize=10)
    fig.tight_layout()
    fig.subplots_adjust(left=0.2)
    fig.savefig(os.path.join(fdir, "text_crops.png"), dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    df, rdir, fdir, cfg, timgs = run()
    mq, summ = min_readable(df, rdir)
    fig_cer_quality(df, fdir)
    fig_cer_size(df, fdir)
    fig_crops(df, fdir, timgs)
    pd.set_option("display.width", 200)
    print(summ.to_string())
    print(df[df["codec"] == "PNG gốc"][["image", "cer", "wer", "size_kb"]].to_string())
