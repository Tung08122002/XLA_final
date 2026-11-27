#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""t08 - Thí nghiệm ablation cho Đề tài 4 (so sánh JPEG / PNG / WebP).

MỤC TIÊU
    Mỗi ablation chỉ thay đổi MỘT tham số của bộ mã hoá, giữ nguyên mọi thứ khác
    (cùng 20 ảnh, cùng hàm encode/decode/psnr/ssim trong common.py), để tách riêng
    ảnh hưởng của từng tham số lên dung lượng, chất lượng và thời gian mã hoá.

    A1  JPEG lấy mẫu sắc độ (subsampling) 4:4:4 / 4:2:2 / 4:2:0 ở quality 75.
        Đo thêm PSNR riêng Y, Cb, Cr (YCbCr BT.601 toàn dải, do Pillow chuyển) và ΔE CIE76
        (rgb2lab của scikit-image): ΔE trung bình toàn ảnh và ΔE trung bình tại các ĐƯỜNG
        BIÊN MÀU (nơi gradient của Cb/Cr trong ảnh gốc > 30 mức xám/điểm ảnh, giãn 2 px) -
        đó là vị trí chữ đỏ / nhãn giảm giá bị "loang màu" do giảm mẫu sắc độ.
    A2  JPEG optimize=True (bảng Huffman tối ưu theo ảnh) và progressive=True so với
        mặc định ở quality 75. Hai tuỳ chọn này KHÔNG đổi lượng tử hoá nên ảnh giải mã phải
        giống hệt từng điểm ảnh (kiểm tra bằng np.array_equal) - chỉ dung lượng/thời gian đổi.
    A3  WebP có mất mát: tham số method (mức nỗ lực của bộ mã hoá) 0/2/4/6 ở quality 75.
    A4  PNG: compress_level 1/6/9 và optimize=True (đánh đổi tốc độ - kích thước của DEFLATE).
    A5  WebP không mất mát (lossless=True): lưới method {0,4,6} x quality {0,50,100};
        trong chế độ lossless "quality" KHÔNG phải độ trung thực mà là mức nỗ lực nén
        (0 = nhanh/ít nén, 100 = chậm/nén nhiều nhất). So với PNG compress_level=9 làm mốc.
    A6  Độ phân giải: 7 ảnh 1000x1000 (T01-T04, G01-G03) thu nhỏ còn 500x500 bằng Lanczos,
        rồi nén JPEG75 và WebP75; so bpp = 8*bytes/(W*H) giữa hai độ phân giải. Kèm hai số
        đo tương quan không gian: hệ số tương quan giữa hai điểm ảnh liền kề theo chiều ngang
        (kênh sáng Y) và độ lớn gradient trung bình.

QUY ƯỚC
    - Chạy trên CẢ 20 ảnh, báo cáo trung bình theo nhóm P/T/G và toàn bộ (A6: chỉ T, G).
    - Quality cố định 75 (mức khuyến nghị phổ biến của JPEG/WebP) cho các ablation lossy.
    - Mọi số đo thời gian dùng evaluate(..., repeats=N) (trung vị N lần, N=7 mặc định;
      riêng A5 mặc định 3 vì lossless method 6 / quality 100 mất 10-15 s mỗi lần mã hoá).
    - Thời gian CHỈ có ý nghĩa khi chạy tuần tự trên máy rảnh. Script ghi load average vào
      results/t08/run_info.json và tables.md để biết điều kiện đo.
    - Không có thành phần ngẫu nhiên (các bộ mã hoá tất định), SEED chỉ để thống nhất với common.py.

CÁCH CHẠY
    cd /home/claude/nen_anh && python src/t08_ablation.py             # chạy toàn bộ, sinh CSV, bảng, hình, section.md
    python src/t08_ablation.py --only A3,A4                           # chỉ chạy lại một số ablation
    python src/t08_ablation.py --repeats 7 --a5-repeats 7             # đổi số lần lặp đo thời gian
    python src/t08_ablation.py --no-compute                           # chỉ dựng lại bảng/hình/section.md từ CSV

ĐẦU RA
    results/t08/a{1..6}_raw.csv (từng ảnh), a{1..6}_summary.csv (trung bình theo nhóm),
    results/t08/tables.md (bảng markdown tự sinh), results/t08/run_info.json,
    figures/t08/a{1..6}_*.png (300 dpi), results/t08/section.md (sinh từ
    src/t08_section_template.md: mọi con số lấy từ CSV, nên chạy lại sẽ cập nhật cả số thời gian).
"""
import argparse
import datetime
import json
import os
import platform
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import matplotlib
import matplotlib.ticker  # noqa: F401
import numpy as np
import pandas as pd
import PIL
from PIL import Image
from skimage.color import rgb2lab

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from common import (GROUP_NAMES, ROOT, SEED, decode, encode, ensure_dirs,  # noqa: E402
                    evaluate, list_images, psnr)

np.random.seed(SEED)
TASK = "t08"
RES_DIR, FIG_DIR = ensure_dirs(TASK)
GROUPS = ["P", "T", "G"]
GROUP_LABEL = {"P": "P (ảnh chụp)", "T": "T (ảnh có chữ)", "G": "G (gradient)", "ALL": "Tất cả"}
TEMPLATE = os.path.join(ROOT, "src", "t08_section_template.md")
QUALITY = 75


def P(path_name):
    return os.path.join(RES_DIR, path_name)


def F(path_name):
    return os.path.join(FIG_DIR, path_name)


# ----------------------------------------------------------------------------------------------
# Cấu hình các ablation: (nhãn cấu hình ổn định dùng làm khoá, fmt, tham số Pillow)
# Nhãn không được chứa '/' hoặc '|' (dùng trong chỗ giữ chỗ của template).
# ----------------------------------------------------------------------------------------------
A1_CFG = [("4:4:4", "JPEG", dict(quality=QUALITY, subsampling=0)),
          ("4:2:2", "JPEG", dict(quality=QUALITY, subsampling=1)),
          ("4:2:0", "JPEG", dict(quality=QUALITY, subsampling=2))]
A2_CFG = [("mặc định", "JPEG", dict(quality=QUALITY)),
          ("optimize", "JPEG", dict(quality=QUALITY, optimize=True)),
          ("progressive", "JPEG", dict(quality=QUALITY, progressive=True)),
          ("optimize+progressive", "JPEG", dict(quality=QUALITY, optimize=True, progressive=True))]
A3_CFG = [("m%d" % m, "WEBP", dict(quality=QUALITY, method=m)) for m in (0, 2, 4, 6)]
A4_CFG = [("L1", "PNG", dict(compress_level=1)),
          ("L6", "PNG", dict(compress_level=6)),
          ("L9", "PNG", dict(compress_level=9)),
          ("optimize", "PNG", dict(optimize=True)),
          ("L1+optimize", "PNG", dict(compress_level=1, optimize=True))]
A5_CFG = [("m%d-q%d" % (m, q), "WEBP", dict(lossless=True, quality=q, method=m))
          for m in (0, 4, 6) for q in (0, 50, 100)]
A6_FMT = [("JPEG75", "JPEG", dict(quality=QUALITY)), ("WebP75", "WEBP", dict(quality=QUALITY, method=4))]
A6_NAMES = ["T01_card1000", "T02_card1000", "T03_card1000", "T04_card1000",
            "G01_studio1000", "G02_studio1000", "G03_studio1000"]


# ----------------------------------------------------------------------------------------------
# Tiện ích đo
# ----------------------------------------------------------------------------------------------
def ycbcr(arr):
    """RGB uint8 -> YCbCr uint8 (Pillow, BT.601 toàn dải) -> mảng HxWx3."""
    return np.asarray(Image.fromarray(arr).convert("YCbCr"))


def delta_e76(ref, out):
    lab_r = rgb2lab(ref.astype(np.float64) / 255.0)
    lab_o = rgb2lab(out.astype(np.float64) / 255.0)
    return np.sqrt(((lab_r - lab_o) ** 2).sum(axis=2))


def chroma_edge_mask(ref_ycc, thr=30.0, dil=5):
    """Điểm ảnh nằm sát đường biên MÀU của ảnh gốc: max(|∇Cb|,|∇Cr|) > thr (mức xám/px), giãn dil px."""
    cb = ref_ycc[..., 1].astype(np.float64)
    cr = ref_ycc[..., 2].astype(np.float64)
    g = np.zeros(cb.shape)
    for ch in (cb, cr):
        gy, gx = np.gradient(ch)
        g = np.maximum(g, np.hypot(gx, gy))
    m = (g > thr).astype(np.uint8)
    m = cv2.dilate(m, np.ones((dil, dil), np.uint8))
    return m.astype(bool)


def neighbor_corr(img):
    """Hệ số tương quan Pearson giữa các cặp điểm ảnh liền kề theo chiều ngang (kênh Y) và gradient TB."""
    y = np.asarray(img.convert("L")).astype(np.float64)
    a, b = y[:, :-1].ravel(), y[:, 1:].ravel()
    corr = float(np.corrcoef(a, b)[0, 1])
    gy, gx = np.gradient(y)
    return corr, float(np.hypot(gx, gy).mean())


def base_row(name, group, img, label):
    return {"name": name, "group": group, "w": img.size[0], "h": img.size[1], "config": label}


def add_rel(df, base, col, newcol, key="config"):
    """newcol = 100*col/col_của_cấu_hình_cơ_sở (cùng ảnh) - tỉ lệ theo từng ảnh rồi mới lấy trung bình."""
    b = df[df[key] == base].set_index("name")[col]
    df[newcol] = 100.0 * df[col] / df["name"].map(b)
    return df


def load_loadavg():
    try:
        return list(os.getloadavg())
    except (AttributeError, OSError):
        # Windows không cung cấp os.getloadavg(); vẫn chạy thí nghiệm, chỉ không
        # ghi được chỉ số tải hệ thống kiểu Unix.
        return [float("nan")] * 3


def log(*a):
    print(*a, flush=True)


# ----------------------------------------------------------------------------------------------
# Chạy từng ablation -> CSV
# ----------------------------------------------------------------------------------------------
def run_generic(images, cfgs, repeats, extra_fn=None, tag=""):
    rows = []
    for i, (name, grp, im) in enumerate(images):
        for label, fmt, params in cfgs:
            r = base_row(name, grp, im, label)
            r["fmt"] = fmt
            r["params"] = json.dumps(params, ensure_ascii=False)
            ev = evaluate(im, fmt, repeats=repeats, **params)
            r.update(ev)
            if extra_fn is not None:
                r.update(extra_fn(im, fmt, params, label))
            rows.append(r)
        log("  [%s] %2d/%d %s" % (tag, i + 1, len(images), name))
    return pd.DataFrame(rows)


def run_a1(images, repeats):
    def extra(im, fmt, params, label):
        ref = np.asarray(im)
        rec = np.asarray(decode(encode(im, fmt, **params)))
        yr, yo = ycbcr(ref), ycbcr(rec)
        de = delta_e76(ref, rec)
        mask = chroma_edge_mask(yr)
        return {"psnr_y": psnr(yr[..., 0], yo[..., 0]),
                "psnr_cb": psnr(yr[..., 1], yo[..., 1]),
                "psnr_cr": psnr(yr[..., 2], yo[..., 2]),
                "de_mean": float(de.mean()),
                "de_p99": float(np.percentile(de, 99)),
                "edge_frac": float(mask.mean()),
                "de_edge": float(de[mask].mean()) if mask.sum() >= 100 else float("nan")}
    df = run_generic(images, A1_CFG, 0, extra, "A1")  # A1 không đo thời gian
    df = add_rel(df, "4:4:4", "size_kb", "size_rel_pct")
    df.to_csv(P("a1_raw.csv"), index=False)
    return df


def run_a2(images, repeats):
    def extra(im, fmt, params, label):
        return {}
    df = run_generic(images, A2_CFG, repeats, extra, "A2")
    # Kiểm tra ảnh giải mã giống hệt mặc định (từng điểm ảnh)
    ident = {}
    for name, grp, im in images:
        ref = np.asarray(decode(encode(im, "JPEG", quality=QUALITY)))
        for label, fmt, params in A2_CFG:
            out = np.asarray(decode(encode(im, fmt, **params)))
            ident[(name, label)] = bool(np.array_equal(ref, out))
    df["identical"] = [ident[(n, c)] for n, c in zip(df["name"], df["config"])]
    a_ = df[df["config"] == "progressive"].set_index("name")["size_kb"]
    b_ = df[df["config"] == "optimize+progressive"].set_index("name")["size_kb"]
    log("  [A2] progressive == optimize+progressive về dung lượng ở %d/%d ảnh" % ((a_ == b_).sum(), len(a_)))
    df = add_rel(df, "mặc định", "size_kb", "size_rel_pct")
    df["size_reduction_pct"] = 100.0 - df["size_rel_pct"]
    df = add_rel(df, "mặc định", "enc_ms", "enc_rel_pct")
    df = add_rel(df, "mặc định", "dec_ms", "dec_rel_pct")
    df.to_csv(P("a2_raw.csv"), index=False)
    return df


def run_a3(images, repeats):
    df = run_generic(images, A3_CFG, repeats, None, "A3")
    df = add_rel(df, "m4", "size_kb", "size_rel_pct")      # m4 = mặc định của Pillow/libwebp
    df = add_rel(df, "m4", "enc_ms", "enc_rel_pct")
    df.to_csv(P("a3_raw.csv"), index=False)
    return df


def run_a4(images, repeats):
    df = run_generic(images, A4_CFG, repeats, None, "A4")
    df = add_rel(df, "L6", "size_kb", "size_rel_pct")      # L6 = mặc định của Pillow
    df = add_rel(df, "L6", "enc_ms", "enc_rel_pct")
    df["exact"] = np.isinf(df["psnr"])
    df.to_csv(P("a4_raw.csv"), index=False)
    return df


def n_colors_map(images=None):
    """Số màu RGB phân biệt của từng ảnh gốc (giải thích vì sao ảnh G03 rất hợp với PNG/WebP có bảng màu/dự đoán)."""
    images = images or list_images()
    return {n: int(len(np.unique(np.asarray(im).reshape(-1, 3), axis=0))) for n, g, im in images}


def run_a5(images, repeats):
    df = run_generic(images, A5_CFG, repeats, None, "A5")
    df["exact"] = np.isinf(df["psnr"])
    # Mốc PNG compress_level=9 trên cùng ảnh
    ref = {}
    for name, grp, im in images:
        ref[name] = len(encode(im, "PNG", compress_level=9)) / 1024
    df["png9_kb"] = df["name"].map(ref)
    df["n_colors"] = df["name"].map(n_colors_map(images))
    df["size_vs_png9_pct"] = 100.0 * df["size_kb"] / df["png9_kb"]
    df["method"] = [int(c.split("-")[0][1:]) for c in df["config"]]
    df["quality"] = [int(c.split("-")[1][1:]) for c in df["config"]]
    df = add_rel(df, "m4-q50", "enc_ms", "enc_rel_pct")
    df.to_csv(P("a5_raw.csv"), index=False)
    return df


def run_a6(images_all, repeats):
    by_name = {n: (g, im) for n, g, im in images_all}
    rows = []
    for name in A6_NAMES:
        grp, im1000 = by_name[name]
        assert im1000.size == (1000, 1000)
        im500 = im1000.resize((500, 500), Image.LANCZOS)
        for res, im in ((1000, im1000), (500, im500)):
            corr, grad = neighbor_corr(im)
            for label, fmt, params in A6_FMT:
                r = base_row(name, grp, im, "%s-%d" % (label, res))
                r.update({"fmt": label, "res": res, "neighbor_corr": corr, "mean_grad": grad})
                r.update(evaluate(im, fmt, repeats=0, **params))
                rows.append(r)
        log("  [A6] %s" % name)
    df = pd.DataFrame(rows)
    df.to_csv(P("a6_raw.csv"), index=False)
    return df


# ----------------------------------------------------------------------------------------------
# Tổng hợp theo nhóm
# ----------------------------------------------------------------------------------------------
def group_summary(df, cols, key="config"):
    parts = []
    for g in GROUPS + ["ALL"]:
        d = df if g == "ALL" else df[df["group"] == g]
        cc = [c for c in cols if c in d.columns]
        s = d.groupby(key, sort=False)[cc].mean(numeric_only=True).reset_index()
        s.insert(0, "group", g)
        s["n_images"] = d["name"].nunique()
        parts.append(s)
    return pd.concat(parts, ignore_index=True)


def summarize_all():
    out = {}
    spec = {
        "a1": ["size_kb", "bpp", "size_rel_pct", "psnr", "ssim", "psnr_y", "psnr_cb", "psnr_cr",
               "de_mean", "de_p99", "de_edge", "edge_frac"],
        "a2": ["size_kb", "size_reduction_pct", "psnr", "ssim", "enc_ms", "dec_ms", "enc_rel_pct",
               "dec_rel_pct", "identical"],
        "a3": ["size_kb", "bpp", "size_rel_pct", "psnr", "ssim", "enc_ms", "dec_ms", "enc_rel_pct"],
        "a4": ["size_kb", "bpp", "size_rel_pct", "enc_ms", "dec_ms", "enc_rel_pct", "exact"],
        "a5": ["size_kb", "bpp", "size_vs_png9_pct", "enc_ms", "dec_ms", "enc_rel_pct", "exact"],
        "a6": ["size_kb", "bpp", "psnr", "ssim", "neighbor_corr", "mean_grad"],
    }
    for k, cols in spec.items():
        path = P("%s_raw.csv" % k)
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        if k == "a5" and "n_colors" not in df.columns:      # CSV cũ chưa có cột này: bổ sung rồi ghi lại
            df["n_colors"] = df["name"].map(n_colors_map())
            df.to_csv(path, index=False)
        if k == "a6":
            df = df[df["group"].isin(["T", "G"])]
        s = group_summary(df, cols)
        s.to_csv(P("%s_summary.csv" % k), index=False)
        out[k] = (df, s)
    return out


# ----------------------------------------------------------------------------------------------
# Bảng markdown
# ----------------------------------------------------------------------------------------------
def fmt_num(x, nd=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    if isinstance(x, (float, np.floating)) and np.isinf(x):
        return "∞"
    return ("%." + str(nd) + "f") % x


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def grp_cell(g, n):
    return "%s, n=%d" % (GROUP_LABEL[g], n)


def table_a1(df, s):
    rows = []
    for g in GROUPS + ["ALL"]:
        for _, r in s[s["group"] == g].iterrows():
            rows.append([GROUP_LABEL[g], r["config"], fmt_num(r["size_kb"], 1), fmt_num(r["size_rel_pct"], 1),
                         fmt_num(r["psnr"], 2), fmt_num(r["ssim"], 4), fmt_num(r["psnr_cb"], 2),
                         fmt_num(r["psnr_cr"], 2), fmt_num(r["de_mean"], 2), fmt_num(r["de_edge"], 2)])
    t1 = md_table(["Nhóm", "Lấy mẫu sắc độ", "Dung lượng (KB)", "So với 4:4:4 (%)", "PSNR RGB (dB)", "SSIM",
                   "PSNR Cb (dB)", "PSNR Cr (dB)", "ΔE TB", "ΔE tại biên màu"], rows)
    # bảng từng ảnh T
    t = df[df["group"] == "T"]
    piv = {m: t.pivot(index="name", columns="config", values=m) for m in ("psnr_cb", "psnr_cr", "de_edge")}
    rows2 = []
    for name in piv["psnr_cb"].index:
        row = [name]
        for m in ("psnr_cb", "psnr_cr", "de_edge"):
            for c in ("4:4:4", "4:2:2", "4:2:0"):
                row.append(fmt_num(piv[m].loc[name, c], 2))
        rows2.append(row)
    t2 = md_table(["Ảnh T", "Cb 4:4:4", "Cb 4:2:2", "Cb 4:2:0", "Cr 4:4:4", "Cr 4:2:2", "Cr 4:2:0",
                   "ΔE biên 4:4:4", "ΔE biên 4:2:2", "ΔE biên 4:2:0"], rows2)
    return ("**Bảng A1a.** JPEG quality 75, thay đổi lấy mẫu sắc độ (trung bình theo nhóm; PSNR Cb/Cr tính trên "
            "YCbCr BT.601; ΔE là CIE76).\n\n" + t1 +
            "\n\n**Bảng A1b.** Từng ảnh nhóm T: PSNR kênh Cb, Cr (dB) và ΔE CIE76 tại biên màu.\n\n" + t2)


def table_a2(df, s):
    rows = []
    for g in GROUPS + ["ALL"]:
        d = df if g == "ALL" else df[df["group"] == g]
        for _, r in s[s["group"] == g].iterrows():
            dd = d[d["config"] == r["config"]]
            rows.append([GROUP_LABEL[g], r["config"], fmt_num(r["size_kb"], 1), fmt_num(r["size_reduction_pct"], 2),
                         "%d/%d" % (dd["identical"].sum(), len(dd)), fmt_num(r["psnr"], 3),
                         fmt_num(r["enc_ms"], 1), fmt_num(r["enc_rel_pct"], 0), fmt_num(r["dec_ms"], 1),
                         fmt_num(r["dec_rel_pct"], 0)])
    return ("**Bảng A2.** JPEG quality 75: tuỳ chọn optimize / progressive so với mặc định "
            "(\"Giống hệt\" = số ảnh có ảnh giải mã trùng từng điểm ảnh với bản mặc định).\n\n" +
            md_table(["Nhóm", "Cấu hình", "Dung lượng (KB)", "Giảm dung lượng (%)", "Giống hệt", "PSNR (dB)",
                      "Mã hoá (ms)", "Mã hoá so với mặc định (%)", "Giải mã (ms)", "Giải mã so với mặc định (%)"],
                     rows))


def table_a3(df, s):
    rows = []
    for g in GROUPS + ["ALL"]:
        for _, r in s[s["group"] == g].iterrows():
            rows.append([GROUP_LABEL[g], r["config"].replace("m", "method "), fmt_num(r["size_kb"], 1),
                         fmt_num(r["size_rel_pct"], 1), fmt_num(r["psnr"], 2), fmt_num(r["ssim"], 4),
                         fmt_num(r["enc_ms"], 1), fmt_num(r["enc_rel_pct"], 0), fmt_num(r["dec_ms"], 1)])
    return ("**Bảng A3.** WebP lossy quality 75, thay đổi method (so sánh với method 4 là mặc định của Pillow).\n\n" +
            md_table(["Nhóm", "Method", "Dung lượng (KB)", "So với method 4 (%)", "PSNR (dB)", "SSIM",
                      "Mã hoá (ms)", "Mã hoá so với method 4 (%)", "Giải mã (ms)"], rows))


def table_a4(df, s):
    rows = []
    for g in GROUPS + ["ALL"]:
        d = df if g == "ALL" else df[df["group"] == g]
        for _, r in s[s["group"] == g].iterrows():
            dd = d[d["config"] == r["config"]]
            rows.append([GROUP_LABEL[g], r["config"], fmt_num(r["size_kb"], 1), fmt_num(r["size_rel_pct"], 1),
                         fmt_num(r["enc_ms"], 1), fmt_num(r["enc_rel_pct"], 0), fmt_num(r["dec_ms"], 1),
                         "%d/%d" % (dd["exact"].sum(), len(dd))])
    return ("**Bảng A4.** PNG: compress_level 1/6/9 và optimize=True (L6 là mặc định; \"Không mất mát\" = số ảnh "
            "giải mã trùng khớp ảnh gốc).\n\n" +
            md_table(["Nhóm", "Cấu hình", "Dung lượng (KB)", "So với L6 (%)", "Mã hoá (ms)",
                      "Mã hoá so với L6 (%)", "Giải mã (ms)", "Không mất mát"], rows))


def table_a5(df, s):
    rows = []
    for g in GROUPS + ["ALL"]:
        d = df if g == "ALL" else df[df["group"] == g]
        for _, r in s[s["group"] == g].iterrows():
            dd = d[d["config"] == r["config"]]
            m, q = r["config"].split("-")
            rows.append([GROUP_LABEL[g], m.replace("m", "method "), q.replace("q", "quality "),
                         fmt_num(r["size_kb"], 1), fmt_num(r["size_vs_png9_pct"], 1), fmt_num(r["enc_ms"], 0),
                         fmt_num(r["dec_ms"], 1), "%d/%d" % (dd["exact"].sum(), len(dd))])
    return ("**Bảng A5.** WebP lossless: method x quality (quality = mức nỗ lực nén; so với PNG compress_level=9 "
            "trên cùng ảnh).\n\n" +
            md_table(["Nhóm", "Method", "Quality (nỗ lực)", "Dung lượng (KB)", "So với PNG L9 (%)",
                      "Mã hoá (ms)", "Giải mã (ms)", "Không mất mát"], rows))


def table_a6(df, s):
    rows = []
    for name in A6_NAMES:
        d = df[df["name"] == name].set_index("config")
        rows.append([name.split("_")[0],
                     fmt_num(d.loc["JPEG75-1000", "bpp"], 3), fmt_num(d.loc["JPEG75-500", "bpp"], 3),
                     fmt_num(d.loc["JPEG75-500", "bpp"] / d.loc["JPEG75-1000", "bpp"], 2),
                     fmt_num(d.loc["WebP75-1000", "bpp"], 3), fmt_num(d.loc["WebP75-500", "bpp"], 3),
                     fmt_num(d.loc["WebP75-500", "bpp"] / d.loc["WebP75-1000", "bpp"], 2),
                     fmt_num(d.loc["JPEG75-1000", "neighbor_corr"], 4), fmt_num(d.loc["JPEG75-500", "neighbor_corr"], 4),
                     fmt_num(d.loc["JPEG75-1000", "mean_grad"], 2), fmt_num(d.loc["JPEG75-500", "mean_grad"], 2)])
    # dòng trung bình theo nhóm T, G, tất cả
    for g in ["T", "G", "ALL"]:
        d = df if g == "ALL" else df[df["group"] == g]
        m = d.groupby("config")[["bpp", "neighbor_corr", "mean_grad"]].mean()
        lab = {"T": "TB nhóm T", "G": "TB nhóm G", "ALL": "TB 7 ảnh"}[g]
        rows.append(["**%s**" % lab,
                     fmt_num(m.loc["JPEG75-1000", "bpp"], 3), fmt_num(m.loc["JPEG75-500", "bpp"], 3),
                     fmt_num(m.loc["JPEG75-500", "bpp"] / m.loc["JPEG75-1000", "bpp"], 2),
                     fmt_num(m.loc["WebP75-1000", "bpp"], 3), fmt_num(m.loc["WebP75-500", "bpp"], 3),
                     fmt_num(m.loc["WebP75-500", "bpp"] / m.loc["WebP75-1000", "bpp"], 2),
                     fmt_num(m.loc["JPEG75-1000", "neighbor_corr"], 4), fmt_num(m.loc["JPEG75-500", "neighbor_corr"], 4),
                     fmt_num(m.loc["JPEG75-1000", "mean_grad"], 2), fmt_num(m.loc["JPEG75-500", "mean_grad"], 2)])
    return ("**Bảng A6.** Độ phân giải: bpp của JPEG75 và WebP75 (method 4) trước/sau khi thu nhỏ 1000→500 px "
            "(Lanczos). Tỉ số = bpp(500)/bpp(1000); tương quan = hệ số tương quan Pearson của các cặp điểm ảnh "
            "kề ngang (kênh Y); gradient = độ lớn gradient TB (mức xám/px).\n\n" +
            md_table(["Ảnh", "JPEG bpp 1000", "JPEG bpp 500", "Tỉ số JPEG", "WebP bpp 1000", "WebP bpp 500",
                      "Tỉ số WebP", "Tương quan 1000", "Tương quan 500", "Gradient 1000", "Gradient 500"], rows))


TABLE_FN = {"a1": table_a1, "a2": table_a2, "a3": table_a3, "a4": table_a4, "a5": table_a5, "a6": table_a6}


def compact_tables(data):
    """Bảng rút gọn (chỉ nhóm P/T/G và vài cấu hình chính) dùng trong section.md; bảng đầy đủ nằm ở tables.md."""
    out = {}
    if "a1" in data:
        s = data["a1"][1]
        rows = [[GROUP_LABEL[g], r["config"], fmt_num(r["size_kb"], 1), fmt_num(r["size_rel_pct"], 1),
                 fmt_num(r["psnr"], 2), fmt_num(r["ssim"], 4), fmt_num(r["psnr_cb"], 2), fmt_num(r["psnr_cr"], 2),
                 fmt_num(r["de_edge"], 2)]
                for g in GROUPS for _, r in s[s["group"] == g].iterrows()]
        out["c1"] = md_table(["Nhóm", "Lấy mẫu", "Dung lượng (KB)", "So với 4:4:4 (%)", "PSNR RGB (dB)", "SSIM",
                              "PSNR Cb (dB)", "PSNR Cr (dB)", "ΔE tại biên màu"], rows)
    if "a2" in data:
        s = data["a2"][1]
        rows = [[GROUP_LABEL[g], r["config"], fmt_num(r["size_kb"], 1), fmt_num(r["size_reduction_pct"], 1),
                 fmt_num(r["enc_ms"], 1), fmt_num(r["enc_rel_pct"] / 100, 1), fmt_num(r["dec_ms"], 1),
                 fmt_num(r["dec_rel_pct"] / 100, 1)]
                for g in GROUPS for _, r in s[s["group"] == g].iterrows()]
        out["c2"] = md_table(["Nhóm", "Cấu hình", "Dung lượng (KB)", "Giảm (%)", "Mã hoá (ms)", "Mã hoá (×)",
                              "Giải mã (ms)", "Giải mã (×)"], rows)
    if "a3" in data:
        s = data["a3"][1]
        rows = [[GROUP_LABEL[g], r["config"][1:], fmt_num(r["size_kb"], 1), fmt_num(r["size_rel_pct"], 1),
                 fmt_num(r["psnr"], 2), fmt_num(r["ssim"], 4), fmt_num(r["enc_ms"], 1), fmt_num(r["enc_rel_pct"] / 100, 2)]
                for g in GROUPS for _, r in s[s["group"] == g].iterrows()]
        out["c3"] = md_table(["Nhóm", "Method", "Dung lượng (KB)", "So với method 4 (%)", "PSNR (dB)", "SSIM",
                              "Mã hoá (ms)", "Mã hoá (×method 4)"], rows)
    if "a4" in data:
        df, s = data["a4"]
        rows = [[GROUP_LABEL[g], r["config"], fmt_num(r["size_kb"], 1), fmt_num(r["size_rel_pct"], 1),
                 fmt_num(r["enc_ms"], 1), fmt_num(r["enc_rel_pct"] / 100, 2), fmt_num(r["dec_ms"], 1)]
                for g in GROUPS for _, r in s[s["group"] == g].iterrows() if r["config"] != "L1+optimize"]
        out["c4"] = md_table(["Nhóm", "Cấu hình", "Dung lượng (KB)", "So với L6 (%)", "Mã hoá (ms)", "Mã hoá (×L6)",
                              "Giải mã (ms)"], rows)
    if "a5" in data:
        s = data["a5"][1]
        keep = ["m0-q0", "m0-q100", "m4-q0", "m4-q100", "m6-q100"]
        rows = []
        for g in GROUPS:
            for c in keep:
                r = s[(s["group"] == g) & (s["config"] == c)].iloc[0]
                m, q = c.split("-")
                rows.append([GROUP_LABEL[g], "method %s, quality %s" % (m[1:], q[1:]), fmt_num(r["size_kb"], 1),
                             fmt_num(r["size_vs_png9_pct"], 1), fmt_num(r["enc_ms"], 0)])
        out["c5"] = md_table(["Nhóm", "Cấu hình WebP lossless", "Dung lượng (KB)", "So với PNG L9 (%)", "Mã hoá (ms)"], rows)
    if "a6" in data:
        df, s = data["a6"]
        rows = []
        for name in A6_NAMES:
            d = df[df["name"] == name].set_index("config")
            rows.append([name.split("_")[0]] + [fmt_num(d.loc[c, "bpp"], 3) for c in ("JPEG75-1000", "JPEG75-500")] +
                        [fmt_num(d.loc["JPEG75-500", "bpp"] / d.loc["JPEG75-1000", "bpp"], 2)] +
                        [fmt_num(d.loc[c, "bpp"], 3) for c in ("WebP75-1000", "WebP75-500")] +
                        [fmt_num(d.loc["WebP75-500", "bpp"] / d.loc["WebP75-1000", "bpp"], 2)] +
                        [fmt_num(d.loc[c, "neighbor_corr"], 4) for c in ("JPEG75-1000", "JPEG75-500")])
        for g, lab in (("T", "TB nhóm T"), ("G", "TB nhóm G")):
            d = df[df["group"] == g].groupby("config")[["bpp", "neighbor_corr"]].mean()
            rows.append(["**%s**" % lab] + [fmt_num(d.loc[c, "bpp"], 3) for c in ("JPEG75-1000", "JPEG75-500")] +
                        [fmt_num(d.loc["JPEG75-500", "bpp"] / d.loc["JPEG75-1000", "bpp"], 2)] +
                        [fmt_num(d.loc[c, "bpp"], 3) for c in ("WebP75-1000", "WebP75-500")] +
                        [fmt_num(d.loc["WebP75-500", "bpp"] / d.loc["WebP75-1000", "bpp"], 2)] +
                        [fmt_num(d.loc[c, "neighbor_corr"], 4) for c in ("JPEG75-1000", "JPEG75-500")])
        out["c6"] = md_table(["Ảnh", "JPEG 1000", "JPEG 500", "Tỉ số", "WebP 1000", "WebP 500", "Tỉ số",
                              "Tương quan kề 1000", "Tương quan kề 500"], rows)
    return out


def build_tables(data):
    info = {}
    if os.path.exists(P("run_info.json")):
        with open(P("run_info.json"), encoding="utf-8") as f:
            info = json.load(f)
    head = ["# Bảng số liệu t08 (tự sinh từ results/t08/*.csv bởi src/t08_ablation.py)", ""]
    head.append("> **Lưu ý về thời gian đo.** Các cột thời gian (ms) là trung vị của nhiều lần chạy, trên máy 2 lõi. "
                "Nếu cột `load_start` (load average 1 phút khi bắt đầu) lớn hơn khoảng 0,5 thì thời gian bị nhiễu bởi "
                "tiến trình khác, chỉ nên đọc TỈ LỆ tương đối, không đọc giá trị tuyệt đối. Dung lượng, PSNR, SSIM là "
                "tất định và không phụ thuộc điều kiện này.")
    head.append("")
    if info:
        head.append("| Ablation | Số lần lặp đo thời gian | load_start | load_end | Thời điểm |")
        head.append("|---|---|---|---|---|")
        for k in sorted(info):
            i = info[k]
            head.append("| %s | %s | %.2f | %.2f | %s |" % (k.upper(), i.get("repeats", "–"), i["load_start"],
                                                              i["load_end"], i["time"]))
        head.append("")
    blocks = {}
    body = []
    for k in sorted(data):
        df, s = data[k]
        blocks[k] = TABLE_FN[k](df, s)
        body.append("## " + k.upper() + "\n\n" + blocks[k] + "\n")
    ct = compact_tables(data)
    blocks.update(ct)
    body.append("## Bảng rút gọn dùng trong section.md\n\n" + "\n\n".join(ct[k] for k in sorted(ct)) + "\n")
    with open(P("tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(head + body))
    return blocks


# ----------------------------------------------------------------------------------------------
# Hình (kiểu IEEE): chữ đen, font >= 10 pt, nét >= 1.8, lưới nhạt, không tiêu đề; nhãn tiếng Việt
# ----------------------------------------------------------------------------------------------
def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.labelsize": 10, "xtick.labelsize": 10,
        "ytick.labelsize": 10, "legend.fontsize": 10, "axes.edgecolor": "black", "axes.labelcolor": "black",
        "xtick.color": "black", "ytick.color": "black", "text.color": "black", "axes.linewidth": 1.2,
        "lines.linewidth": 2.0, "lines.markersize": 7, "axes.grid": True, "grid.color": "#cccccc",
        "grid.linewidth": 0.6, "axes.axisbelow": True, "savefig.dpi": 300, "figure.dpi": 100,
    })


GCOL = {"P": "#1f77b4", "T": "#d62728", "G": "#2ca02c"}
GHATCH = {"P": "//", "T": "\\\\", "G": ".."}
GMARK = {"P": "o", "T": "s", "G": "^"}
GLAB = {"P": "P: ảnh chụp", "T": "T: ảnh có chữ", "G": "G: gradient"}


def bars(ax, s, configs, col, groups=GROUPS, labels=None, fmt="%.1f", label_fs=8):
    """Cột nhóm: trục x = cấu hình, mỗi nhóm P/T/G một cột (có hatch để đọc được khi in đen trắng)."""
    w = 0.26
    x = np.arange(len(configs))
    for j, g in enumerate(groups):
        vals = [float(s[(s["group"] == g) & (s["config"] == c)][col].iloc[0]) for c in configs]
        b = ax.bar(x + (j - (len(groups) - 1) / 2) * w, vals, w, color=GCOL[g], hatch=GHATCH[g], edgecolor="black",
                   linewidth=0.8, label=GLAB[g])
        for xi, v in zip(x + (j - (len(groups) - 1) / 2) * w, vals):
            ax.text(xi, v, fmt % v, ha="center", va="bottom", fontsize=label_fs, rotation=90)
    ax.set_xticks(x)
    ax.set_xticklabels(labels or configs)


def lines(ax, s, configs, col, groups=GROUPS, xs=None, **kw):
    xs = xs if xs is not None else np.arange(len(configs))
    for g in groups:
        vals = [float(s[(s["group"] == g) & (s["config"] == c)][col].iloc[0]) for c in configs]
        ax.plot(xs, vals, marker=GMARK[g], color=GCOL[g], label=GLAB[g], **kw)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(F(name), dpi=300)
    plt.close(fig)


def pad_top(ax, frac=0.18):
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + (hi - lo) * frac)


def fig_a1(df, s):
    cfgs = ["4:4:4", "4:2:2", "4:2:0"]
    fig, axs = plt.subplots(2, 2, figsize=(6.6, 5.6))
    bars(axs[0, 0], s, cfgs, "size_kb", fmt="%.0f")
    axs[0, 0].set_ylabel("Dung lượng TB (KB)")
    axs[0, 0].set_xlabel("Lấy mẫu sắc độ (JPEG q75)")
    axs[0, 0].set_title("(a)", loc="left", fontsize=10)
    axs[0, 0].legend(loc="upper right", fontsize=9, framealpha=0.95)
    pad_top(axs[0, 0], 0.45)
    bars(axs[0, 1], s, cfgs, "psnr_cb", fmt="%.1f")
    axs[0, 1].set_ylabel("PSNR kênh Cb (dB)")
    axs[0, 1].set_xlabel("Lấy mẫu sắc độ (JPEG q75)")
    axs[0, 1].set_title("(b)", loc="left", fontsize=10)
    lo = min(s["psnr_cb"].min(), s["psnr_cr"].min())
    axs[0, 1].set_ylim(lo - 4, s["psnr_cb"].max() + 6)
    bars(axs[1, 0], s, cfgs, "psnr_cr", fmt="%.1f")
    axs[1, 0].set_ylabel("PSNR kênh Cr (dB)")
    axs[1, 0].set_xlabel("Lấy mẫu sắc độ (JPEG q75)")
    axs[1, 0].set_title("(c)", loc="left", fontsize=10)
    axs[1, 0].set_ylim(lo - 4, s["psnr_cr"].max() + 6)
    bars(axs[1, 1], s, cfgs, "de_edge", fmt="%.1f")
    axs[1, 1].set_ylabel("ΔE CIE76 tại biên màu")
    axs[1, 1].set_xlabel("Lấy mẫu sắc độ (JPEG q75)")
    axs[1, 1].set_title("(d)", loc="left", fontsize=10)
    pad_top(axs[1, 1], 0.2)
    save(fig, "a1_subsampling.png")

    # Hình cắt vùng giá + nhãn giảm giá (T01, T05) cho 4 trường hợp
    ims = {n: im for n, g, im in list_images()}
    crops = {"T01_card1000": (430, 180, 800, 345), "T05_card500": (215, 92, 375, 170)}
    fig, axs = plt.subplots(2, 4, figsize=(6.6, 2.5))
    for i, (name, box) in enumerate(crops.items()):
        im = ims[name]
        variants = [("Gốc", im)] + [(c, decode(encode(im, "JPEG", quality=QUALITY, subsampling=k)))
                                    for c, k in (("4:4:4", 0), ("4:2:2", 1), ("4:2:0", 2))]
        for j, (lab, v) in enumerate(variants):
            cr = v.crop(box)
            cr = cr.resize((cr.size[0] * 3, cr.size[1] * 3), Image.NEAREST) if name.startswith("T05") else cr
            axs[i, j].imshow(cr, interpolation="nearest")
            axs[i, j].set_xticks([])
            axs[i, j].set_yticks([])
            axs[i, j].grid(False)
            if i == 0:
                axs[i, j].set_title(lab, fontsize=10)
        axs[i, 0].set_ylabel(name.split("_")[0], fontsize=10)
    save(fig, "a1_crops.png")

    # Hình phóng đại vùng nhãn giảm giá (lấy mẫu sắc độ làm loang viền đỏ/vàng)
    im = ims["T01_card1000"]
    box = (440, 270, 570, 335)
    fig, axs = plt.subplots(1, 4, figsize=(6.6, 1.5))
    variants = [("Gốc", im)] + [(c, decode(encode(im, "JPEG", quality=QUALITY, subsampling=k)))
                                for c, k in (("4:4:4", 0), ("4:2:2", 1), ("4:2:0", 2))]
    for j, (lab, v) in enumerate(variants):
        cr = v.crop(box)
        cr = cr.resize((cr.size[0] * 4, cr.size[1] * 4), Image.NEAREST)
        axs[j].imshow(cr, interpolation="nearest")
        axs[j].set_xticks([])
        axs[j].set_yticks([])
        axs[j].grid(False)
        axs[j].set_title(lab, fontsize=10)
    save(fig, "a1_badge_zoom.png")


def fig_a2(df, s):
    cfgs = ["optimize", "progressive", "optimize+progressive"]
    labs = ["opt.", "prog.", "opt.\n+prog."]
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 3.6))
    bars(axs[0], s, cfgs, "size_reduction_pct", labels=labs, fmt="%.1f")
    axs[0].set_ylabel("Giảm dung lượng (%)")
    axs[0].set_title("(a)", loc="left", fontsize=10)
    axs[0].legend(loc="upper left", fontsize=8, framealpha=0.95)
    pad_top(axs[0], 0.45)
    cfgs_all = ["mặc định"] + cfgs
    labs_all = ["mặc\nđịnh", "opt.", "prog.", "opt.\n+prog."]
    for ax_ in axs:
        ax_.set_xlabel("Cấu hình JPEG q75")
    bars(axs[1], s, cfgs_all, "enc_rel_pct", labels=labs_all, fmt="%.0f", label_fs=7)
    axs[1].axhline(100, color="black", lw=1.2, ls="--")
    axs[1].set_ylabel("Mã hoá (% so với mặc định)")
    axs[1].set_title("(b)", loc="left", fontsize=10)
    pad_top(axs[1], 0.3)
    bars(axs[2], s, cfgs_all, "dec_rel_pct", labels=labs_all, fmt="%.0f", label_fs=7)
    axs[2].axhline(100, color="black", lw=1.2, ls="--")
    axs[2].set_ylabel("Giải mã (% so với mặc định)")
    axs[2].set_title("(c)", loc="left", fontsize=10)
    pad_top(axs[2], 0.3)
    save(fig, "a2_optimize_progressive.png")


def fig_a3(df, s):
    cfgs = ["m0", "m2", "m4", "m6"]
    xs = np.arange(4)
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 3.3))
    lines(axs[0], s, cfgs, "size_rel_pct")
    axs[0].set_ylabel("Dung lượng (% so với method 4)")
    axs[0].set_title("(a)", loc="left", fontsize=10)
    axs[0].legend(loc="upper right", fontsize=9)
    lines(axs[1], s, cfgs, "ssim")
    axs[1].set_ylabel("SSIM trung bình")
    axs[1].set_title("(b)", loc="left", fontsize=10)
    lines(axs[2], s, cfgs, "enc_ms")
    axs[2].set_yscale("log")
    axs[2].set_ylabel("Thời gian mã hoá (ms, thang log)")
    axs[2].set_title("(c)", loc="left", fontsize=10)
    for ax in axs:
        ax.set_xticks(xs)
        ax.set_xticklabels(["0", "2", "4", "6"])
        ax.set_xlabel("WebP method")
    save(fig, "a3_webp_method.png")


def fig_a4(df, s):
    cfgs = ["L1", "L6", "L9", "optimize"]
    labs = ["L1", "L6", "L9", "opt."]
    fig, axs = plt.subplots(1, 3, figsize=(7.6, 3.7))
    bars(axs[0], s, cfgs, "size_rel_pct", labels=labs, fmt="%.0f", label_fs=7)
    axs[0].set_ylabel("Dung lượng (% so với L6)")
    axs[0].set_ylim(80, 150)
    axs[0].axhline(100, color="black", lw=1.2, ls="--")
    axs[0].set_title("(a)", loc="left", fontsize=10)
    bars(axs[1], s, cfgs, "enc_ms", labels=labs, fmt="%.0f", label_fs=7)
    axs[1].set_yscale("log")
    axs[1].set_ylabel("Mã hoá (ms, log)")
    axs[1].set_title("(b)", loc="left", fontsize=10)
    axs[1].set_ylim(5, 2500)
    for ax in axs[:2]:
        ax.set_xlabel("Cấu hình PNG")
    for g in GROUPS:
        xv = [float(s[(s["group"] == g) & (s["config"] == c)]["enc_ms"].iloc[0]) for c in cfgs]
        yv = [float(s[(s["group"] == g) & (s["config"] == c)]["size_rel_pct"].iloc[0]) for c in cfgs]
        axs[2].plot(xv, yv, marker=GMARK[g], color=GCOL[g], label=GLAB[g])
    axs[2].set_xscale("log")
    axs[2].set_xlabel("Mã hoá (ms, log)")
    axs[2].set_ylabel("Dung lượng (% so với L6)")
    axs[2].set_title("(c)", loc="left", fontsize=10)
    axs[2].legend(loc="upper right", fontsize=9, framealpha=0.95)
    save(fig, "a4_png_compress.png")
    axs[0].figure  # noqa


def fig_a5(df, s):
    fig, axs = plt.subplots(1, 3, figsize=(7.6, 3.6), sharey=True)
    mk = {0: "o", 4: "s", 6: "^"}
    ls = {0: ":", 4: "--", 6: "-"}
    for ax, g, lab in zip(axs, GROUPS, ["(a) P: ảnh chụp", "(b) T: ảnh có chữ", "(c) G: gradient"]):
        for m in (0, 4, 6):
            xv = [float(s[(s["group"] == g) & (s["config"] == "m%d-q%d" % (m, q))]["enc_ms"].iloc[0]) for q in (0, 50, 100)]
            yv = [float(s[(s["group"] == g) & (s["config"] == "m%d-q%d" % (m, q))]["size_vs_png9_pct"].iloc[0]) for q in (0, 50, 100)]
            ax.plot(xv, yv, marker=mk[m], ls=ls[m], color="black", label="method %d" % m)
            if m != 4:
                ax.annotate("q0", (xv[0], yv[0]), textcoords="offset points", xytext=(-4, -13), fontsize=8, ha="center")
                ax.annotate("q100", (xv[2], yv[2]), textcoords="offset points", xytext=(0, 7), fontsize=8, ha="center")
        ax.axhline(100, color="black", lw=1.2, ls="-.")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(6, 2e4)
        ax.set_xlabel("Mã hoá (ms, log)")
        ax.set_title(lab, loc="left", fontsize=10)
    axs[0].set_ylabel("Dung lượng (% so với PNG L9, log)")
    axs[0].set_yticks([60, 80, 100, 150, 200, 400])
    axs[0].set_yticklabels(["60", "80", "100", "150", "200", "400"])
    axs[0].set_ylim(55, 520)
    axs[0].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axs[1].legend(loc="upper right", fontsize=9, framealpha=0.95)
    axs[0].text(0.03, 0.97, "đường chấm gạch:\nPNG L9 = 100%", transform=axs[0].transAxes, ha="left", va="top", fontsize=8)
    save(fig, "a5_webp_lossless.png")


def fig_a6(df, s):
    names = A6_NAMES
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 3.5), gridspec_kw={"width_ratios": [1, 1, 0.9]})
    x = np.arange(len(names))
    w = 0.38
    for ax, fmtl, lab in zip(axs[:2], ["JPEG75", "WebP75"], ["(a) JPEG q75", "(b) WebP q75"]):
        for j, (res, hatch, col) in enumerate([(1000, "//", "#444444"), (500, "..", "#bbbbbb")]):
            vals = [float(df[(df["name"] == n) & (df["config"] == "%s-%d" % (fmtl, res))]["bpp"].iloc[0]) for n in names]
            ax.bar(x + (j - 0.5) * w, vals, w, color=col, hatch=hatch, edgecolor="black", linewidth=0.8,
                   label="%d×%d px" % (res, res))
        ax.set_xticks(x)
        ax.set_xticklabels([n.split("_")[0] for n in names], rotation=60, fontsize=9)
        ax.set_ylabel("bpp (bit/điểm ảnh)")
        ax.set_title(lab, loc="left", fontsize=10)
    pad_top(axs[0], 0.3)
    pad_top(axs[1], 0.3)
    axs[0].legend(loc="upper right", fontsize=9, ncol=1, framealpha=0.95)
    axs[1].legend(loc="upper right", fontsize=9, framealpha=0.95)
    # (c) tương quan kề
    for g in ["T", "G"]:
        xs_, ys_ = [], []
        for n in names:
            d = df[df["name"] == n].set_index("config")
            if d["group"].iloc[0] != g:
                continue
            xs_.append(d.loc["JPEG75-1000", "neighbor_corr"])
            ys_.append(d.loc["JPEG75-500", "neighbor_corr"])
        axs[2].plot(xs_, ys_, ls="none", marker=GMARK[g], color=GCOL[g], label=GLAB[g])
    lo, hi = axs[2].get_xlim()
    lo2, hi2 = axs[2].get_ylim()
    a, b = min(lo, lo2), max(hi, hi2)
    axs[2].plot([a, b], [a, b], color="black", lw=1.2, ls="--")
    axs[2].set_xlabel("Tương quan kề, 1000 px")
    axs[2].set_ylabel("Tương quan kề, 500 px")
    axs[2].set_title("(c)", loc="left", fontsize=10)
    axs[2].legend(loc="upper left", fontsize=9, framealpha=0.95)
    save(fig, "a6_resolution.png")


FIG_FN = {"a1": fig_a1, "a2": fig_a2, "a3": fig_a3, "a4": fig_a4, "a5": fig_a5, "a6": fig_a6}


# ----------------------------------------------------------------------------------------------
# section.md sinh từ template: chỗ giữ chỗ
#   @@TABLE/a3@@                     -> khối bảng markdown của ablation
#   @@S/a3/size_kb/T/m6|.1f@@        -> số từ *_summary.csv (ablation/cột/nhóm/cấu hình|định dạng)
#   @@R/a3/size_kb/T/m6/m4|.1f@@     -> tỉ số hai ô summary (ô1/ô2) (dùng cho "gấp bao nhiêu lần")
#   @@D/ab/cột/nhóm/cfg@@ = 100-giá trị; @@E/...@@ = giá trị-100; @@X/...@@ = giá trị/100
#   @@IMG/ab/cột/tiền_tố_ảnh/cfg@@ -> giá trị của một ảnh (vd G03)
#   @@RAW/ab/cột/hàm/nhóm/cfg@@ -> hàm pandas (count|sum|min|max|mean) trên bảng raw
#   @@LOAD@@                         -> load average khi chạy
# ----------------------------------------------------------------------------------------------
def build_section(data, blocks):
    if not os.path.exists(TEMPLATE):
        log("Không có template section, bỏ qua section.md")
        return
    with open(TEMPLATE, encoding="utf-8") as f:
        text = f.read()
    info = {}
    if os.path.exists(P("run_info.json")):
        with open(P("run_info.json"), encoding="utf-8") as f:
            info = json.load(f)

    def cell(k, col, g, cfg):
        s = data[k][1]
        r = s[(s["group"] == g) & (s["config"] == cfg)]
        if r.empty:
            raise KeyError("thiếu ô %s/%s/%s/%s" % (k, col, g, cfg))
        return float(r[col].iloc[0])

    def sub(m):
        tok = m.group(1)
        fm = "%.2f"
        if "|" in tok:
            tok, f_ = tok.split("|")
            fm = "%" + f_
        parts = tok.split("/")
        if parts[0] == "TABLE":
            return blocks[parts[1]]
        if parts[0] == "LOAD":
            lv = [info[k]["load_start"] for k in info if info[k].get("repeats", 0)]
            return "%.1f–%.1f" % (min(lv), max(lv)) if lv else "n/a"
        if parts[0] == "S":
            v = cell(*parts[1:5])
        elif parts[0] == "R":
            v = cell(*parts[1:5]) / cell(parts[1], parts[2], parts[3], parts[5])
        elif parts[0] == "D":        # D/ab/cột/nhóm/cấu hình : 100 - giá trị (dùng cho % giảm)
            v = 100.0 - cell(*parts[1:5])
        elif parts[0] == "E":        # E/ab/cột/nhóm/cấu hình : giá trị - 100 (phần trăm thừa so với cơ sở)
            v = cell(*parts[1:5]) - 100.0
        elif parts[0] == "X":        # X/ab/cột/nhóm/cấu hình : giá trị/100 (phần trăm -> số lần)
            v = cell(*parts[1:5]) / 100.0
        elif parts[0] == "IMG":      # IMG/ab/cột/tiền_tố_tên_ảnh/cấu hình (giá trị của MỘT ảnh)
            df = data[parts[1]][0]
            d = df[df["name"].str.startswith(parts[3]) & (df["config"] == parts[4])]
            v = float(d[parts[2]].iloc[0])
        elif parts[0] == "RAW":      # RAW/ablation/cột/aggr(min|max|mean)/nhóm(ALL|P|T|G)/cấu hình
            df = data[parts[1]][0]
            d = df if parts[4] == "ALL" else df[df["group"] == parts[4]]
            d = d[d["config"] == parts[5]]
            v = float(getattr(d[parts[2]], parts[3])())
        else:
            raise KeyError(tok)
        return fm % v

    out = re.sub(r"@@(.+?)@@", sub, text)
    with open(P("section.md"), "w", encoding="utf-8") as f:
        f.write(out)
    log("Đã sinh results/t08/section.md")


# ----------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=7, help="số lần lặp đo thời gian (A2-A4)")
    ap.add_argument("--a5-repeats", type=int, default=3, help="số lần lặp đo thời gian cho A5 (rất chậm)")
    ap.add_argument("--only", default="", help="vd A1,A3 : chỉ chạy các ablation này")
    ap.add_argument("--no-compute", action="store_true", help="chỉ dựng lại bảng/hình/section từ CSV")
    args = ap.parse_args()
    style()
    only = [x.strip().lower() for x in args.only.split(",") if x.strip()] or list(TABLE_FN)

    if not args.no_compute:
        images = list_images()
        assert len(images) == 20
        info = {}
        if os.path.exists(P("run_info.json")):
            with open(P("run_info.json"), encoding="utf-8") as f:
                info = json.load(f)
        runners = {"a1": (run_a1, 0), "a2": (run_a2, args.repeats), "a3": (run_a3, args.repeats),
                   "a4": (run_a4, args.repeats), "a5": (run_a5, args.a5_repeats), "a6": (run_a6, 0)}
        for k in only:
            fn, rep = runners[k]
            log("== %s (repeats=%d) load=%s" % (k.upper(), rep, load_loadavg()))
            l0 = load_loadavg()[0]
            fn(images if k != "a6" else images, rep)
            info[k] = {"repeats": rep, "load_start": l0, "load_end": load_loadavg()[0],
                       "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                       "cpu_count": os.cpu_count(), "python": platform.python_version(),
                       "pillow": PIL.__version__, "seed": SEED}
            with open(P("run_info.json"), "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=1)
    data = summarize_all()
    blocks = build_tables(data)
    for k in only:
        if k in data:
            FIG_FN[k](*data[k])
            log("Đã vẽ hình %s" % k.upper())
    build_section(data, blocks)


if __name__ == "__main__":
    main()
