"""t05 - Đường cong tỉ lệ-méo (Rate-Distortion) và chỉ số Bjøntegaard (BD-rate): WebP so với JPEG.

Chạy: cd /home/claude/nen_anh && python src/t05_rd_bdrate.py

VÌ SAO CẦN BD-RATE
    Thang "quality" của JPEG (hệ số nhân bảng lượng tử hoá IJG) và của WebP (tham số
    lượng tử hoá / phân bổ tỉ lệ của libwebp) KHÔNG cùng đơn vị: JPEG q=75 và WebP q=75 cho
    dung lượng và PSNR khác nhau. So sánh "cùng q" vì thế là so sánh không công bằng.
    Cách công bằng: so dung lượng (bitrate) cần thiết để đạt CÙNG chất lượng khách quan,
    tức so hai đường cong R-D. BD-rate (Bjøntegaard 2001, VCEG-M33) là % chênh lệch
    bitrate trung bình của codec thử (WebP) so với codec tham chiếu (JPEG) trên đoạn chất
    lượng chồng lấn; âm = WebP tiết kiệm bitrate hơn.

CÁC BƯỚC
    1. Quét q trong {5,10,20,30,40,50,60,70,75,80,85,90,95} cho JPEG (Pillow mặc định:
       4:2:0, bảng Huffman chuẩn, không optimize) và WebP lossy (method=4), trên 20 ảnh,
       đo bpp, PSNR, SSIM bằng common.evaluate(repeats=0). Lưu rd_sweep.csv.
    2. BD-rate theo công thức hiện đại: với mỗi codec, lấy các điểm (R_i, Q_i), đặt
       r_i = log10(R_i) (R = bpp, cùng số điểm ảnh nên chia cho diện tích không đổi tỉ lệ).
       Nội suy r = f(Q) bằng PCHIP (đơn điệu, không dao động như đa thức bậc 3 của bài gốc),
       tích phân trên [Q_lo, Q_hi] = [max(min Q_JPEG, min Q_WebP), min(max Q_JPEG, max Q_WebP)]:
            BD-rate = 10^( (1/(Q_hi-Q_lo)) * ∫ (f_WebP(Q) - f_JPEG(Q)) dQ ) - 1     (×100 %)
       BD-PSNR (dB): đổi vai, nội suy Q = g(r) theo log-rate, tích phân trên đoạn log-rate
       chồng lấn, lấy trung bình hiệu g_WebP - g_JPEG (dương = WebP chất lượng cao hơn ở
       cùng bitrate).
    3. Hai trục chất lượng: (a) PSNR (dB); (b) SSIM_dB = -10 log10(1 - SSIM) (kéo giãn vùng
       SSIM gần 1 để nội suy/tích phân có ý nghĩa; SSIM thô bị nén vào [0,1]).
    4. Lựa chọn điểm: CHÍNH dùng 6 điểm q ∈ {50,60,70,80,90,95} (dải trung bình-cao, nơi ảnh
       sản phẩm thực tế được dùng; thông lệ BD-rate dùng 4-6 điểm). Phân tích độ nhạy: dải
       thấp {10,20,30,40,50,60}, dải cao {70,75,80,85,90,95}, và JPEG có optimize=True
       (Huffman tối ưu) ở dải chính để xem lợi thế của WebP có do bảng Huffman chuẩn không.
    5. Kiểm tra hàm: (i) đường so với chính nó -> 0 %; (ii) đường dịch bitrate ×0,8 -> -20 %
       (chính xác với PCHIP vì dịch hằng số trong log-rate); (iii) đối chiếu nội suy bậc 3
       (cubic polyfit) của bài gốc trên cùng dữ liệu.
    6. Xuất CSV, 3 hình, và bảng markdown (results/t05/tables.md) để chép vào section.md.
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter
from scipy.interpolate import PchipInterpolator
from scipy.integrate import quad

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import list_images, evaluate, ensure_dirs, GROUP_NAMES, SEED  # noqa: E402

np.random.seed(SEED)

QS = [5, 10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95]
Q_MAIN = [50, 60, 70, 80, 90, 95]
Q_HIGH = [70, 75, 80, 85, 90, 95]
Q_LOW = [10, 20, 30, 40, 50, 60]
CODECS = {"JPEG": ("JPEG", {}), "WebP": ("WEBP", {"method": 4})}
GROUPS = ["P", "T", "G"]
REUSE = "--reuse" in sys.argv   # dùng lại CSV quét đã có (chỉ để chạy nhanh khi chỉnh hình/phân tích)
XTICKS = {"P": [0.3, 0.5, 1, 2, 3], "T": [0.2, 0.3, 0.5, 1, 1.5], "G": [0.04, 0.1, 0.2, 0.4, 0.8]}
COLORS = {"P": "#1f77b4", "T": "#d95f02", "G": "#2a9d4a"}

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams.update({"font.size": 10, "axes.labelsize": 10, "legend.fontsize": 9,
                     "xtick.labelsize": 10, "ytick.labelsize": 10,
                     "axes.edgecolor": "black", "axes.labelcolor": "black",
                     "text.color": "black", "xtick.color": "black", "ytick.color": "black"})


# ------------------------------------------------------------------ BD-rate
def _prep(rate, qual):
    """Sắp theo chất lượng tăng; PCHIP cần x tăng NGHIÊM NGẶT."""
    rate = np.asarray(rate, float)
    qual = np.asarray(qual, float)
    o = np.argsort(qual)
    return np.log10(rate[o]), qual[o]


def _strict(x, y):
    """Bỏ điểm làm x không tăng nghiêm ngặt (hiếm: hai q cho cùng chất lượng)."""
    keep = np.concatenate([[True], np.diff(x) > 1e-12])
    return x[keep], y[keep]


def bd_rate_psnr(rate_ref, q_ref, rate_test, q_test, method="pchip"):
    """Trả về (BD-rate %, BD-quality). rate = bpp (hoặc KB, tỉ lệ không đổi); q = PSNR dB (hoặc SSIM dB).
    method: 'pchip' (chính) hoặc 'cubic' (đa thức bậc 3 của bài gốc, để đối chiếu)."""
    lr_r, q_r = _prep(rate_ref, q_ref)
    lr_t, q_t = _prep(rate_test, q_test)
    # --- BD-rate: log-rate như hàm của chất lượng
    qr, lrr = _strict(q_r, lr_r)
    qt, lrt = _strict(q_t, lr_t)
    lo, hi = max(qr.min(), qt.min()), min(qr.max(), qt.max())
    if hi <= lo:
        return np.nan, np.nan
    if method == "pchip":
        f_r, f_t = PchipInterpolator(qr, lrr), PchipInterpolator(qt, lrt)
        ir = quad(f_r, lo, hi, limit=200)[0]
        it = quad(f_t, lo, hi, limit=200)[0]
    else:
        pr, pt = np.polyfit(qr, lrr, 3), np.polyfit(qt, lrt, 3)
        ir = np.polyval(np.polyint(pr), hi) - np.polyval(np.polyint(pr), lo)
        it = np.polyval(np.polyint(pt), hi) - np.polyval(np.polyint(pt), lo)
    bdr = (10 ** ((it - ir) / (hi - lo)) - 1) * 100
    # --- BD-quality: chất lượng như hàm của log-rate
    xr, yr = _strict(*_prep(rate_ref, q_ref))      # x = log-rate, cần đơn điệu tăng
    xt, yt = _strict(*_prep(rate_test, q_test))
    # sắp lại theo log-rate (chất lượng đơn điệu theo q nên thường đã đúng thứ tự)
    o = np.argsort(xr); xr, yr = _strict(xr[o], yr[o])
    o = np.argsort(xt); xt, yt = _strict(xt[o], yt[o])
    lo2, hi2 = max(xr.min(), xt.min()), min(xr.max(), xt.max())
    if hi2 <= lo2:
        return bdr, np.nan
    if method == "pchip":
        g_r, g_t = PchipInterpolator(xr, yr), PchipInterpolator(xt, yt)
        jr = quad(g_r, lo2, hi2, limit=200)[0]
        jt = quad(g_t, lo2, hi2, limit=200)[0]
    else:
        pr, pt = np.polyfit(xr, yr, 3), np.polyfit(xt, yt, 3)
        jr = np.polyval(np.polyint(pr), hi2) - np.polyval(np.polyint(pr), lo2)
        jt = np.polyval(np.polyint(pt), hi2) - np.polyval(np.polyint(pt), lo2)
    return bdr, (jt - jr) / (hi2 - lo2)


def self_test(df):
    """Phép thử hợp lệ hoá hàm BD-rate trên đường R-D thật của JPEG (từng ảnh)."""
    rows = []
    for name, g in df[(df.codec == "JPEG") & (df.q.isin(Q_MAIN))].groupby("image"):
        for axis in ("psnr", "ssim_db"):
            r, qv = g.bpp.values, g[axis].values
            b0, d0 = bd_rate_psnr(r, qv, r, qv)
            b8, d8 = bd_rate_psnr(r, qv, r * 0.8, qv)
            rows.append((name, axis, b0, d0, b8, d8))
    t = pd.DataFrame(rows, columns=["image", "axis", "self_bdrate", "self_bdq", "shift08_bdrate", "shift08_bdq"])
    assert np.allclose(t.self_bdq, 0, atol=1e-9), "self-test thất bại: BD-quality self != 0"
    assert np.allclose(t.self_bdrate, 0, atol=1e-9), "self-test thất bại: self != 0"
    assert np.allclose(t.shift08_bdrate, -20.0, atol=1e-6), "self-test thất bại: shift 0.8 != -20%"
    return t


# ------------------------------------------------------------------ sweep
def run_sweep(path):
    if REUSE and os.path.exists(path):
        return pd.read_csv(path)
    rows = []
    imgs = list_images()
    for name, grp, im in imgs:
        for cname, (fmt, extra) in CODECS.items():
            for q in QS:
                r = evaluate(im, fmt, repeats=0, quality=q, **extra)
                rows.append(dict(image=name, group=grp, codec=cname, q=q, size_kb=r["size_kb"],
                                 bpp=r["bpp"], psnr=r["psnr"], ssim=r["ssim"]))
        print("sweep xong", name, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def run_jpeg_opt(path):
    """Phân tích độ nhạy: JPEG optimize=True (Huffman tối ưu theo ảnh) trên dải chính."""
    if REUSE and os.path.exists(path):
        return pd.read_csv(path)
    rows = []
    for name, grp, im in list_images():
        for q in Q_MAIN:
            r = evaluate(im, "JPEG", repeats=0, quality=q, optimize=True)
            rows.append(dict(image=name, group=grp, codec="JPEG_opt", q=q, size_kb=r["size_kb"],
                             bpp=r["bpp"], psnr=r["psnr"], ssim=r["ssim"]))
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def add_ssim_db(df):
    df = df.copy()
    df["ssim_db"] = -10 * np.log10(1 - df["ssim"].clip(upper=1 - 1e-12))
    return df


# ------------------------------------------------------------------ BD per image
def bd_table(df, qset, ref="JPEG", test="WebP", method="pchip", tag="main"):
    rows = []
    for name, g in df.groupby("image"):
        grp = g.group.iloc[0]
        a = g[(g.codec == ref) & g.q.isin(qset)]
        b = g[(g.codec == test) & g.q.isin(qset)]
        out = dict(image=name, group=grp, set=tag, method=method)
        for axis, lab in (("psnr", "psnr"), ("ssim_db", "ssimdb")):
            bdr, bdq = bd_rate_psnr(a.bpp.values, a[axis].values, b.bpp.values, b[axis].values, method)
            out[f"bdrate_{lab}"] = bdr
            out[f"bdq_{lab}"] = bdq
            qa, qb = a[axis].values, b[axis].values
            out[f"overlap_{lab}"] = max(qa.min(), qb.min()), min(qa.max(), qb.max())
        out["overlap_psnr_lo"], out["overlap_psnr_hi"] = out.pop("overlap_psnr")
        out["overlap_ssimdb_lo"], out["overlap_ssimdb_hi"] = out.pop("overlap_ssimdb")
        rows.append(out)
    return pd.DataFrame(rows)


def group_summary(t, cols):
    recs = []
    for grp in GROUPS + ["ALL"]:
        s = t if grp == "ALL" else t[t.group == grp]
        rec = dict(group=grp, n=len(s))
        for c in cols:
            rec[f"{c}_median"] = s[c].median()
            rec[f"{c}_mean"] = s[c].mean()
            rec[f"{c}_min"] = s[c].min()
            rec[f"{c}_max"] = s[c].max()
            rec[f"{c}_n_pos"] = int((s[c] > 0).sum())
        recs.append(rec)
    return pd.DataFrame(recs)


# ------------------------------------------------------------------ figures
def fig_rd(df, axis, ylabel, fname, fdir):
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7))
    for ax, grp in zip(axes, GROUPS):
        for cname, col, mk in (("JPEG", "#222222", "o"), ("WebP", "#d62728", "s")):
            s = df[(df.group == grp) & (df.codec == cname)]
            m = s.groupby("q")[["bpp", axis]].mean().sort_index()
            ax.plot(m.bpp, m[axis], "-", color=col, lw=2.0, label=cname + " (trung bình nhóm)")
            for q in (50, 75, 90):
                ax.plot(m.bpp.loc[q], m[axis].loc[q], mk, color=col, ms=7, mfc="white" if cname == "JPEG" else col,
                        mew=1.8)
                ax.annotate(f"q{q}", (m.bpp.loc[q], m[axis].loc[q]), textcoords="offset points",
                            xytext=(5, -12) if cname == "JPEG" else (-4, 6), fontsize=8,
                            color=col, ha="left" if cname == "JPEG" else "right")
        ax.set_xscale("log")
        ax.set_xticks(XTICKS[grp])
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel("Tốc độ bit (bpp, thang log)")
        ax.set_title(f"{grp}: {GROUP_NAMES[grp]}", fontsize=10)
        ax.grid(True, which="both", color="0.85", lw=0.6)
    axes[0].set_ylabel(ylabel)
    axes[0].legend(loc="lower right", frameon=True)
    fig.tight_layout()
    fig.savefig(os.path.join(fdir, fname), dpi=300)
    plt.close(fig)


def fig_bar(t, fdir):
    fig, axes = plt.subplots(2, 1, figsize=(8.5, 6.0), sharex=True)
    t = t.sort_values(["group", "image"], key=lambda s: s.map({"P": 0, "T": 1, "G": 2}) if s.name == "group" else s)
    x = np.arange(len(t))
    for ax, col, lab in ((axes[0], "bdrate_psnr", "BD-rate theo PSNR (%)"),
                         (axes[1], "bdrate_ssimdb", "BD-rate theo SSIM$_{dB}$ (%)")):
        ax.bar(x, t[col].values, color=[COLORS[g] for g in t.group], edgecolor="black", linewidth=0.8)
        ax.axhline(0, color="black", lw=1.8)
        ax.set_ylabel(lab)
        ax.grid(True, axis="y", color="0.85", lw=0.6)
        ax.set_axisbelow(True)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(t.image.values, rotation=90)
    axes[1].set_xlabel("Ảnh")
    handles = [plt.Rectangle((0, 0), 1, 1, fc=COLORS[g], ec="black") for g in GROUPS]
    fig.legend(handles, [f"{g}: {GROUP_NAMES[g]}" for g in GROUPS], loc="upper center", ncol=3,
               frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(fdir, "bdrate_per_image.png"), dpi=300)
    plt.close(fig)


# ------------------------------------------------------------------ phân tích bổ sung
def local_savings(df, qset=Q_MAIN, axis="psnr"):
    """Tiết kiệm bitrate (%) CỤC BỘ: chia đoạn chất lượng chồng lấn thành 3 phần bằng nhau
    (thấp/giữa/cao) và tính BD-rate riêng trên từng phần bằng cùng PCHIP. Cho biết lợi thế của
    WebP co lại hay nở ra ở đầu chất lượng cao."""
    rows = []
    for name, g in df.groupby("image"):
        a = g[(g.codec == "JPEG") & g.q.isin(qset)]
        b = g[(g.codec == "WebP") & g.q.isin(qset)]
        lr, qr = _strict(*_prep(a.bpp.values, a[axis].values))
        lt, qt = _strict(*_prep(b.bpp.values, b[axis].values))
        lo, hi = max(qr.min(), qt.min()), min(qr.max(), qt.max())
        fr, ft = PchipInterpolator(qr, lr), PchipInterpolator(qt, lt)
        edges = np.linspace(lo, hi, 4)
        rec = dict(image=name, group=g.group.iloc[0], axis=axis, q_lo=lo, q_hi=hi)
        for k, lab in enumerate(("low", "mid", "high")):
            x0, x1 = edges[k], edges[k + 1]
            d = (quad(ft, x0, x1)[0] - quad(fr, x0, x1)[0]) / (x1 - x0)
            rec[f"bdrate_{lab}third"] = (10 ** d - 1) * 100
        rows.append(rec)
    return pd.DataFrame(rows)


def saturation_table(df):
    """Bão hoà chất lượng ở q cao: PSNR/SSIM tại q95 và q100 của hai codec (q100 đo thêm)."""
    rows = []
    imgs = {n: (g, im) for n, g, im in list_images()}
    for name, (grp, im) in imgs.items():
        rec = dict(image=name, group=grp)
        for cname, (fmt, extra) in CODECS.items():
            r95 = df[(df.image == name) & (df.codec == cname) & (df.q == 95)].iloc[0]
            r100 = evaluate(im, fmt, repeats=0, quality=100, **extra)
            rec[f"{cname}_psnr_q95"] = r95.psnr
            rec[f"{cname}_psnr_q100"] = r100["psnr"]
            rec[f"{cname}_ssim_q95"] = r95.ssim
            rec[f"{cname}_ssim_q100"] = r100["ssim"]
            rec[f"{cname}_bpp_q95"] = r95.bpp
            rec[f"{cname}_bpp_q100"] = r100["bpp"]
        # trần PSNR do lấy mẫu con sắc độ: JPEG q100 với 4:4:4 (WebP lossy luôn 4:2:0, không tắt được)
        r444 = evaluate(im, "JPEG", repeats=0, quality=100, subsampling=0)
        rec["JPEG444_psnr_q100"] = r444["psnr"]
        rec["JPEG444_bpp_q100"] = r444["bpp"]
        rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ main
def main():
    rdir, fdir = ensure_dirs("t05")
    df = add_ssim_db(run_sweep(os.path.join(rdir, "rd_sweep.csv")))
    dfo = add_ssim_db(run_jpeg_opt(os.path.join(rdir, "rd_sweep_jpeg_optimize.csv")))

    # --- kiểm tra hàm
    st = self_test(df)
    st.to_csv(os.path.join(rdir, "bdrate_selftest.csv"), index=False)
    print("SELF-TEST OK: self=0%, shift x0.8 = -20% trên", len(st), "đường R-D")

    # --- BD-rate chính + độ nhạy
    main_t = bd_table(df, Q_MAIN, tag="main")
    main_t.to_csv(os.path.join(rdir, "bdrate_per_image.csv"), index=False)
    cols = ["bdrate_psnr", "bdrate_ssimdb", "bdq_psnr", "bdq_ssimdb"]
    gs = group_summary(main_t, cols)
    gs.to_csv(os.path.join(rdir, "bdrate_by_group.csv"), index=False)

    sens = []
    for tag, qs in (("low_10-60", Q_LOW), ("main_50-95", Q_MAIN), ("high_70-95", Q_HIGH)):
        sens.append(bd_table(df, qs, tag=tag))
    sens.append(bd_table(df, Q_MAIN, method="cubic", tag="main_cubic"))
    both = pd.concat([df, dfo])
    sens.append(bd_table(both, Q_MAIN, ref="JPEG_opt", tag="main_vs_JPEGopt"))
    sens = pd.concat(sens)
    sens.to_csv(os.path.join(rdir, "bdrate_sensitivity_per_image.csv"), index=False)
    sg = []
    for tag, s in sens.groupby("set", sort=False):
        g = group_summary(s, ["bdrate_psnr", "bdrate_ssimdb"])
        g.insert(0, "set", tag)
        sg.append(g)
    sg = pd.concat(sg)
    sg.to_csv(os.path.join(rdir, "bdrate_sensitivity_by_group.csv"), index=False)

    # --- thống kê mô tả hình dạng đường R-D (bão hoà, bitrate thấp)
    sh = []
    for (grp, cname, q), g in df.groupby(["group", "codec", "q"]):
        sh.append(dict(group=grp, codec=cname, q=q, bpp=g.bpp.mean(), psnr=g.psnr.mean(),
                       ssim=g.ssim.mean(), ssim_db=g.ssim_db.mean()))
    pd.DataFrame(sh).to_csv(os.path.join(rdir, "rd_group_mean.csv"), index=False)

    # --- BD trên toàn dải q (13 điểm): để BD-PSNR xác định được cả ở ảnh G sạch
    full_t = bd_table(df, QS, tag="full_5-95")
    full_t.to_csv(os.path.join(rdir, "bdrate_fullrange_per_image.csv"), index=False)
    group_summary(full_t, cols).to_csv(os.path.join(rdir, "bdrate_fullrange_by_group.csv"), index=False)

    # --- lợi thế cục bộ theo ba phần của đoạn chất lượng chồng lấn
    loc = pd.concat([local_savings(df, axis="psnr"), local_savings(df, axis="ssim_db")])
    loc.to_csv(os.path.join(rdir, "bdrate_local_thirds.csv"), index=False)

    # --- bão hoà ở q cao
    sat = saturation_table(df)
    sat.to_csv(os.path.join(rdir, "saturation_q95_q100.csv"), index=False)

    # --- hình
    fig_rd(df, "psnr", "PSNR (dB)", "rd_psnr_by_group.png", fdir)
    fig_rd(df, "ssim", "SSIM", "rd_ssim_by_group.png", fdir)
    fig_bar(main_t, fdir)

    # --- in tóm tắt
    pd.set_option("display.width", 200)
    print(gs.round(2).to_string())
    print(sg[["set", "group", "bdrate_psnr_median", "bdrate_psnr_min", "bdrate_psnr_max",
              "bdrate_ssimdb_median", "bdrate_ssimdb_min", "bdrate_ssimdb_max"]].round(1).to_string())
    print(main_t[["image", "group", "bdrate_psnr", "bdrate_ssimdb", "bdq_psnr", "bdq_ssimdb"]].round(2).to_string())


if __name__ == "__main__":
    main()
