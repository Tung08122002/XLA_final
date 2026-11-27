"""t10 — Đo thời gian nén / giải nén và ước tính tác động thực tế cho website.

MỤC TIÊU
    Đo thời gian mã hoá (encode) và giải mã (decode) của 8 cấu hình
    (JPEG q50/75/90, PNG compress_level=9, WebP q50/75/90 method=4, WebP lossless
    quality=100 method=4) trên cả 20 ảnh; quy đổi thông lượng megapixel/giây (MP/s);
    ước tính thời gian tải một trang danh mục 40 ảnh trên 4G và 3G; ước tính chi phí
    CPU để mã hoá 10.000 ảnh.

PHƯƠNG PHÁP (và lý do chọn tham số)
    1. Với mỗi (ảnh, cấu hình): mã hoá một lần để lấy dữ liệu nén và dung lượng, rồi
       chạy KHỞI ĐỘNG 1 lần mã hoá + 1 lần giải mã và BỎ ĐI kết quả (nạp thư viện, làm
       nóng cache lệnh/dữ liệu, cấp phát bộ nhớ lần đầu), sau đó đo 9 lần và lấy TRUNG VỊ
       bằng common.time_ms (trung vị bền vững hơn trung bình trước các giá trị ngoại lai
       do tiến trình khác chen vào; 9 là số lẻ nên trung vị là một lần đo thực).
    2. Toàn bộ trong bộ nhớ (BytesIO), không I/O đĩa; dùng đúng common.encode/decode nên
       thời gian giải mã gồm cả `.load()` và `.convert('RGB')`, đúng như một trình xem ảnh.
    3. Thông lượng: MP/s = (W*H/1e6) / (thời gian/1000). Với một nhóm/kích thước, thông
       lượng GỘP = tổng megapixel / tổng thời gian (không lấy trung bình của các tỉ số).
    4. Tải trang: thời gian = tổng KB * 1024 * 8 / băng thông + (số ảnh * thời gian giải
       mã trung bình). Đây là cận trên giả định tải tuần tự, giải mã trên cùng thiết bị
       đo và bỏ qua độ trễ/bắt tay TCP/TLS; mục đích là so sánh giữa các cấu hình, không
       phải dự báo tuyệt đối. Dùng trung bình dung lượng trên cả 20 ảnh (trang 40 ảnh
       = 40 ảnh có phân bố nhóm/kích thước như bộ dữ liệu). Cũng xuất theo từng nhóm.
    5. Chi phí mã hoá 10.000 ảnh = trung bình thời gian mã hoá * 10.000 (lõi-phút CPU, một
       luồng; Pillow mã hoá đơn luồng nên chia đều cho số lõi nếu chạy song song).

LƯU Ý VỀ NHIỄU
    Khi chạy cùng nhiều tác vụ khác trên máy 2 lõi, số đo thời gian bị nhiễu (tranh chấp
    CPU, cache, turbo). Script ghi load average đầu/cuối và một phép đo tham chiếu
    (JPEG q75, ảnh P01, 9 lần) trước và sau, cùng độ phân tán IQR/trung vị, vào
    results/t10/machine_info.json để người đọc đánh giá độ tin cậy. Để có số đo sạch,
    chạy lại KHI MÁY RẢNH:  python src/t10_timing.py   (chạy tuần tự, không cần sửa).
    Chỉ tạo lại bảng/hình từ CSV có sẵn:  python src/t10_timing.py --tables-only

ĐẦU RA
    results/t10/timing.csv, timing_by_group.csv, page_load.csv, encode_cost.csv,
    machine_info.json, tables.md, section.md (tự sinh, số liệu khớp CSV); figures/t10/enc_dec_time.png, page_load.png.
"""
import argparse
import datetime
import gc
import json
import os
import platform
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (GROUP_NAMES, SEED, decode, encode, ensure_dirs,  # noqa: E402
                    list_images, time_ms)

import matplotlib  # noqa: E402
import matplotlib.ticker  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"

REPEATS = 9          # số lần đo (trung vị); lần khởi động nằm ngoài 9 lần này
N_PAGE_IMAGES = 40   # số ảnh trên trang danh mục
NETWORKS = [("4G", 10.0), ("3G", 2.0)]   # (tên, Mbit/s)
N_BATCH = 10_000     # số ảnh cần mã hoá hàng loạt

CONFIGS = [
    ("JPEG q50", "JPEG", dict(quality=50)),
    ("JPEG q75", "JPEG", dict(quality=75)),
    ("JPEG q90", "JPEG", dict(quality=90)),
    ("PNG L9", "PNG", dict(compress_level=9)),
    ("WebP q50", "WEBP", dict(quality=50, method=4)),
    ("WebP q75", "WEBP", dict(quality=75, method=4)),
    ("WebP q90", "WEBP", dict(quality=90, method=4)),
    ("WebP lossless", "WEBP", dict(lossless=True, quality=100, method=4)),
]
CFG_NAMES = [c[0] for c in CONFIGS]
GROUPS = ["P", "T", "G"]

R_DIR, F_DIR = ensure_dirs("t10")


# ----------------------------------------------------------------------------------
# 1. Thông tin máy
# ----------------------------------------------------------------------------------
def machine_info():
    from PIL import Image, features
    cpu = "unknown"
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
    except OSError:
        cpu = platform.processor() or "unknown"
    try:
        affinity = len(os.sched_getaffinity(0))
    except AttributeError:
        affinity = os.cpu_count()

    def feat(name):
        try:
            return features.version(name)
        except Exception:
            return None

    return {
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "cpu_model": cpu,
        "cpu_count_logical": os.cpu_count(),
        "cpu_usable_by_process": affinity,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pillow": Image.__version__,
        "libjpeg_turbo": feat("libjpeg_turbo"),
        "libjpeg": feat("jpg"),
        "libwebp": feat("webp"),
        "zlib": feat("zlib"),
        "repeats": REPEATS,
        "warmup_runs": 1,
        "seed": SEED,
    }


def load_averages():
    """Load average kiểu Unix; Windows không có API này nên trả về NaN.

    NaN được lưu rõ trong CSV/JSON để phân biệt "không hỗ trợ" với máy có tải 0.
    Các số đo thời gian và phép đo nhiễu JPEG vẫn hoạt động bình thường trên Windows.
    """
    try:
        return [float(x) for x in os.getloadavg()]
    except (AttributeError, OSError):
        return [float("nan")] * 3


def noise_probe(img, n=REPEATS):
    """Phép đo tham chiếu: JPEG q75 trên một ảnh, n lần; trả về thống kê phân tán."""
    encode(img, "JPEG", quality=75)  # khởi động
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        encode(img, "JPEG", quality=75)
        ts.append((time.perf_counter() - t0) * 1000)
    ts = np.array(ts)
    q1, med, q3 = np.percentile(ts, [25, 50, 75])
    return {"median_ms": float(med), "min_ms": float(ts.min()), "max_ms": float(ts.max()),
            "iqr_over_median_pct": float(100 * (q3 - q1) / med),
            "max_over_min": float(ts.max() / ts.min()),
            "loadavg_1min": load_averages()[0]}


# ----------------------------------------------------------------------------------
# 2. Đo thời gian
# ----------------------------------------------------------------------------------
def time_wall_cpu(fn, repeats):
    """Trả về (trung vị thời gian tường - ms, trung vị thời gian CPU của tiến trình - ms).

    Thời gian tường lấy từ common.time_ms (chỉ số chính, đúng quy ước chung). CPU time
    được đo theo lô nhỏ: trên Windows, độ phân giải của time.process_time có thể là 15,625 ms;
    đo một lần JPEG vài ms sẽ cho 0 và làm hỏng tỉ số wall/CPU. Mỗi lô nhắm tối thiểu 25 ms,
    sau đó chia lại theo số lần gọi để vẫn có đơn vị ms/ảnh."""
    wall = time_ms(fn, repeats)
    batch = max(1, min(100, int(np.ceil(25.0 / max(wall, 0.1)))))
    cpu = []
    for _ in range(repeats):
        c0 = time.process_time()
        for _ in range(batch):
            fn()
        cpu.append((time.process_time() - c0) * 1000 / batch)
    return wall, float(np.median(cpu))


def run_measurements(repeats=REPEATS):
    images = list_images()
    info = machine_info()
    info["repeats"] = repeats
    info["loadavg_start"] = load_averages()
    info["noise_probe_before"] = noise_probe(images[0][2], repeats)
    gc.collect()
    rows = []
    t_start = time.time()
    for k, (name, grp, im) in enumerate(images):
        W, H = im.size
        mp = W * H / 1e6
        for cname, fmt, params in CONFIGS:
            data = encode(im, fmt, **params)          # dữ liệu nén + dung lượng
            encode(im, fmt, **params)                 # khởi động (bỏ đi)
            decode(data)                              # khởi động (bỏ đi)
            enc, enc_cpu = time_wall_cpu(lambda: encode(im, fmt, **params), repeats)
            dec, dec_cpu = time_wall_cpu(lambda: decode(data), repeats)
            rows.append({
                "image": name, "group": grp, "width": W, "height": H, "megapixels": mp,
                "config": cname, "size_kb": len(data) / 1024,
                "enc_ms": enc, "dec_ms": dec, "enc_cpu_ms": enc_cpu, "dec_cpu_ms": dec_cpu,
                "enc_mps": mp / (enc / 1000), "dec_mps": mp / (dec / 1000),
                "loadavg_1min": load_averages()[0],
            })
        print(f"[{k + 1:2d}/{len(images)}] {name}  ({time.time() - t_start:.0f}s)", flush=True)
    info["noise_probe_after"] = noise_probe(images[0][2], repeats)
    info["loadavg_end"] = load_averages()
    info["total_measure_seconds"] = round(time.time() - t_start, 1)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(R_DIR, "timing.csv"), index=False, float_format="%.4f")
    with open(os.path.join(R_DIR, "machine_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return df, info


# ----------------------------------------------------------------------------------
# 3. Tổng hợp
# ----------------------------------------------------------------------------------
def _agg(sub):
    """Tổng hợp một tập (ảnh × một cấu hình)."""
    return pd.Series({
        "n_images": len(sub),
        "size_kb_mean": sub["size_kb"].mean(),
        "enc_ms_median": sub["enc_ms"].median(),
        "dec_ms_median": sub["dec_ms"].median(),
        "enc_ms_mean": sub["enc_ms"].mean(),
        "dec_ms_mean": sub["dec_ms"].mean(),
        "enc_cpu_ms_median": sub["enc_cpu_ms"].median(),
        "dec_cpu_ms_median": sub["dec_cpu_ms"].median(),
        # thông lượng gộp = tổng MP / tổng thời gian
        "enc_mps": sub["megapixels"].sum() / (sub["enc_ms"].sum() / 1000),
        "dec_mps": sub["megapixels"].sum() / (sub["dec_ms"].sum() / 1000),
    })


def summarise(df):
    parts = []
    for cname in CFG_NAMES:
        d = df[df["config"] == cname]
        for key in GROUPS:
            parts.append(("group", key, cname, _agg(d[d["group"] == key])))
        for key in sorted(d["width"].unique()):
            parts.append(("size", str(int(key)), cname, _agg(d[d["width"] == key])))
        parts.append(("all", "all", cname, _agg(d)))
    out = pd.DataFrame([{"level": a, "key": b, "config": c, **s.to_dict()} for a, b, c, s in parts])
    out["n_images"] = out["n_images"].astype(int)
    out.to_csv(os.path.join(R_DIR, "timing_by_group.csv"), index=False, float_format="%.4f")
    return out


def page_load(df):
    rows = []
    scopes = [("all", df)] + [(g, df[df["group"] == g]) for g in GROUPS]
    for scope, d in scopes:
        for cname in CFG_NAMES:
            s = d[d["config"] == cname]
            avg_kb = s["size_kb"].mean()
            page_kb = N_PAGE_IMAGES * avg_kb
            dec_s = N_PAGE_IMAGES * s["dec_ms"].mean() / 1000
            for net, mbps in NETWORKS:
                tr_s = page_kb * 1024 * 8 / (mbps * 1e6)
                rows.append({"scope": scope, "config": cname, "network": net, "mbps": mbps,
                             "n_images": N_PAGE_IMAGES, "avg_kb_per_image": avg_kb,
                             "page_kb": page_kb, "transfer_s": tr_s, "decode_s": dec_s,
                             "total_s": tr_s + dec_s, "decode_share_pct": 100 * dec_s / (tr_s + dec_s)})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(R_DIR, "page_load.csv"), index=False, float_format="%.4f")
    return out


def encode_cost(df):
    rows = []
    scopes = [("all", df), ("500", df[df["width"] == 500]), ("1000", df[df["width"] == 1000])]
    for scope, d in scopes:
        for cname in CFG_NAMES:
            m = d[d["config"] == cname]["enc_ms"].mean()
            rows.append({"scope": scope, "config": cname, "n_images_measured": int(len(d["image"].unique())),
                         "mean_enc_ms": m, "n_batch": N_BATCH,
                         "core_minutes": m * N_BATCH / 1000 / 60,
                         "core_hours": m * N_BATCH / 1000 / 3600})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(R_DIR, "encode_cost.csv"), index=False, float_format="%.4f")
    return out


# ----------------------------------------------------------------------------------
# 4. Hình (kiểu IEEE)
# ----------------------------------------------------------------------------------
COLORS = {"P": "#4D4D4D", "T": "#E69F00", "G": "#56B4E9"}
HATCH = {"P": "///", "T": "", "G": "xx"}
SHORT = {"P": "P: ảnh chụp chi tiết", "T": "T: ảnh có chữ", "G": "G: gradient / nền trơn"}


def _style():
    plt.rcParams.update({"font.size": 10.5, "axes.labelsize": 11, "legend.fontsize": 9.5,
                         "xtick.labelsize": 10, "ytick.labelsize": 10, "axes.linewidth": 1.4,
                         "text.color": "black", "axes.labelcolor": "black",
                         "xtick.color": "black", "ytick.color": "black"})


def fig_enc_dec(summ):
    _style()
    fig, axes = plt.subplots(2, 1, figsize=(6.6, 7.6), sharex=True)
    w = 0.26
    x = np.arange(len(CFG_NAMES))
    for ax, col, lab in zip(axes, ["enc_ms_median", "dec_ms_median"],
                            ["(a) Thời gian mã hoá (ms)", "(b) Thời gian giải mã (ms)"]):
        for i, g in enumerate(GROUPS):
            d = summ[(summ["level"] == "group") & (summ["key"] == g)].set_index("config").loc[CFG_NAMES]
            ax.bar(x + (i - 1) * w, d[col].values, w, color=COLORS[g], edgecolor="black",
                   linewidth=1.2, hatch=HATCH[g], label=SHORT[g])
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        top = max(summ[(summ["level"] == "group")][col].max(), 1)
        ax.set_ylim(top=top * (4 if col == "enc_ms_median" else 1.6))   # chừa chỗ cho chú thích
        lo, hi = ax.get_ylim()
        ticks = [t for t in [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000] if lo <= t <= hi]
        ax.set_yticks(ticks)
        ax.set_ylabel(lab)
        ax.grid(True, axis="y", which="major", color="0.82", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.text(0.01, 0.97, lab.split(")")[0] + ")", transform=ax.transAxes, va="top", fontweight="bold")
    axes[0].legend(loc="upper center", ncol=3, frameon=True, edgecolor="black", fontsize=8.5, columnspacing=1.0, handlelength=1.5)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(CFG_NAMES, rotation=30, ha="right")
    axes[1].set_xlabel("Cấu hình nén")
    fig.tight_layout()
    fig.savefig(os.path.join(F_DIR, "enc_dec_time.png"), dpi=300)
    plt.close(fig)


def fig_page_load(pl):
    _style()
    fig, axes = plt.subplots(2, 1, figsize=(6.6, 7.6), sharex=True)
    x = np.arange(len(CFG_NAMES))
    for ax, (net, mbps), tag in zip(axes, NETWORKS, ["(a)", "(b)"]):
        d = pl[(pl["scope"] == "all") & (pl["network"] == net)].set_index("config").loc[CFG_NAMES]
        ax.bar(x, d["transfer_s"].values, 0.62, color="#56B4E9", edgecolor="black", linewidth=1.2,
               hatch="//", label="Thời gian truyền")
        ax.bar(x, d["decode_s"].values, 0.62, bottom=d["transfer_s"].values, color="#E69F00",
               edgecolor="black", linewidth=1.2, label="Thời gian giải mã (40 ảnh)")
        for xi, tot in zip(x, d["total_s"].values):
            ax.text(xi, tot, f"{tot:.2f}", ha="center", va="bottom", fontsize=9.5)
        ax.set_ylabel(f"{tag} Tải trang 40 ảnh, {net} {mbps:g} Mbit/s (s)")
        ax.set_ylim(0, d["total_s"].max() * 1.15)
        ax.grid(True, axis="y", color="0.82", linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0].legend(loc="upper left", frameon=True, edgecolor="black")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(CFG_NAMES, rotation=30, ha="right")
    axes[1].set_xlabel("Cấu hình nén")
    fig.tight_layout()
    fig.savefig(os.path.join(F_DIR, "page_load.png"), dpi=300)
    plt.close(fig)


# ----------------------------------------------------------------------------------
# 5. tables.md (tự sinh từ CSV)
# ----------------------------------------------------------------------------------
def _f(x, nd=None):
    if not np.isfinite(x):
        return "N/A"
    if nd is not None:
        return f"{x:.{nd}f}"
    return f"{x:.2f}" if x < 10 else (f"{x:.1f}" if x < 1000 else f"{x:,.0f}")


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] + ["---:"] * (len(header) - 1)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def write_tables():
    df = pd.read_csv(os.path.join(R_DIR, "timing.csv"))
    summ = pd.read_csv(os.path.join(R_DIR, "timing_by_group.csv"))
    pl = pd.read_csv(os.path.join(R_DIR, "page_load.csv"))
    ec = pd.read_csv(os.path.join(R_DIR, "encode_cost.csv"))
    with open(os.path.join(R_DIR, "machine_info.json"), encoding="utf-8") as f:
        info = json.load(f)

    def get(level, key, cfg, col):
        r = summ[(summ["level"] == level) & (summ["key"].astype(str) == str(key)) & (summ["config"] == cfg)]
        return r.iloc[0][col]

    L = ["# Bảng số liệu t10 (tự sinh bởi src/t10_timing.py từ các file CSV)\n"]
    nb, na = info["noise_probe_before"], info["noise_probe_after"]
    L.append("## Môi trường đo\n")
    L.append(f"- CPU: {info['cpu_model']}; {info['cpu_count_logical']} lõi logic "
             f"({info['cpu_usable_by_process']} lõi dùng được); Python {info['python']}.")
    L.append(f"- Pillow {info['pillow']}; libjpeg-turbo {info['libjpeg_turbo']}; libwebp {info['libwebp']}; "
             f"zlib {info['zlib']}.")
    L.append(f"- Quy trình: 1 lần khởi động bỏ đi + {info['repeats']} lần đo, lấy trung vị; toàn bộ trong bộ nhớ; "
             f"ngày đo {info['date']}.")
    has_loadavg = np.isfinite(info["loadavg_start"][0]) and np.isfinite(info["loadavg_end"][0])
    if has_loadavg:
        L.append(f"- Độ nhiễu: load average 1 phút khi bắt đầu = {info['loadavg_start'][0]:.2f}, khi kết thúc = "
                 f"{info['loadavg_end'][0]:.2f} (máy có {info['cpu_count_logical']} lõi).")
    else:
        L.append("- Độ nhiễu: Windows không hỗ trợ `os.getloadavg()`, nên dùng phép đo tham chiếu thay cho load average.")
    L.append(f"- Phép đo tham chiếu (JPEG q75, ảnh P01, {info['repeats']} lần): trước {nb['median_ms']:.2f} ms "
             f"(IQR/trung vị {nb['iqr_over_median_pct']:.0f}%, max/min {nb['max_over_min']:.2f}), "
             f"sau {na['median_ms']:.2f} ms (IQR/trung vị {na['iqr_over_median_pct']:.0f}%, "
             f"max/min {na['max_over_min']:.2f}).")
    busy = has_loadavg and max(info["loadavg_start"][0], info["loadavg_end"][0]) > 0.7 * info["cpu_count_logical"]
    if not has_loadavg:
        L.append("- Không kết luận trạng thái rảnh/bận từ load average trên Windows; xem IQR/trung vị của phép đo tham chiếu.")
    elif busy:
        L.append("- **Cảnh báo:** máy đang bận (load average cao so với số lõi) khi đo, số liệu thời gian có thể "
                 "bị thổi phồng và nhiễu; thứ tự tương đối giữa các cấu hình đáng tin hơn giá trị tuyệt đối. "
                 "Chạy lại khi máy rảnh để có số đo sạch.")
    else:
        L.append("- Máy tương đối rảnh khi đo (load average thấp so với số lõi).")
    L.append("")

    hdr_g = ["Cấu hình"] + [f"{g}" for g in GROUPS] + ["Tất cả"]
    for title, col in [("B1. Thời gian mã hoá, trung vị theo nhóm (ms/ảnh)", "enc_ms_median"),
                       ("B2. Thời gian giải mã, trung vị theo nhóm (ms/ảnh)", "dec_ms_median")]:
        rows = [[c] + [_f(get("group", g, c, col)) for g in GROUPS] + [_f(get("all", "all", c, col))]
                for c in CFG_NAMES]
        L.append(f"## {title}\n")
        L.append("P: ảnh chụp chi tiết (7 ảnh 500 px); T: ảnh có chữ (3×500 px + 4×1000 px); "
                 "G: gradient/nền trơn (3×500 px + 3×1000 px).\n")
        L.append(md_table(hdr_g, rows) + "\n")

    hdr_s = ["Cấu hình", "Mã hoá 500 px (ms)", "Mã hoá 1000 px (ms)", "Tỉ số 1000/500",
             "Giải mã 500 px (ms)", "Giải mã 1000 px (ms)", "Tỉ số 1000/500"]
    rows = []
    for c in CFG_NAMES:
        e5, e10 = get("size", 500, c, "enc_ms_median"), get("size", 1000, c, "enc_ms_median")
        d5, d10 = get("size", 500, c, "dec_ms_median"), get("size", 1000, c, "dec_ms_median")
        rows.append([c, _f(e5), _f(e10), _f(e10 / e5, 2), _f(d5), _f(d10), _f(d10 / d5, 2)])
    L.append("## B3. Theo kích thước ảnh (trung vị ms/ảnh; 13 ảnh 500 px, 7 ảnh 1000 px)\n")
    L.append("Lưu ý: nội dung và kích thước không độc lập (ảnh 1000 px chỉ thuộc nhóm T và G), nên tỉ số 1000/500 "
             "lẫn cả ảnh hưởng của nội dung; lý thuyết thuần tuý theo diện tích là 4,00.\n")
    L.append(md_table(hdr_s, rows) + "\n")

    hdr_t = ["Cấu hình", "Mã hoá 500 px", "Mã hoá 1000 px", "Mã hoá tất cả", "Giải mã 500 px",
             "Giải mã 1000 px", "Giải mã tất cả"]
    rows = []
    for c in CFG_NAMES:
        rows.append([c, _f(get("size", 500, c, "enc_mps")), _f(get("size", 1000, c, "enc_mps")),
                     _f(get("all", "all", c, "enc_mps")), _f(get("size", 500, c, "dec_mps")),
                     _f(get("size", 1000, c, "dec_mps")), _f(get("all", "all", c, "dec_mps"))])
    L.append("## B4. Thông lượng gộp (megapixel/giây; tổng MP / tổng thời gian)\n")
    L.append(md_table(hdr_t, rows) + "\n")

    for net, mbps in NETWORKS:
        d = pl[(pl["scope"] == "all") & (pl["network"] == net)].set_index("config").loc[CFG_NAMES]
        ref = d.loc["JPEG q75", "total_s"]
        rows = [[c, _f(d.loc[c, "avg_kb_per_image"]), _f(d.loc[c, "page_kb"]), _f(d.loc[c, "transfer_s"]),
                 _f(d.loc[c, "decode_s"]), _f(d.loc[c, "total_s"]), _f(d.loc[c, "decode_share_pct"], 2),
                 _f(d.loc[c, "total_s"] / ref, 2)] for c in CFG_NAMES]
        L.append(f"## B5{'a' if net == '4G' else 'b'}. Tải trang danh mục {N_PAGE_IMAGES} ảnh trên {net} "
                 f"({mbps:g} Mbit/s), trung bình cả 20 ảnh\n")
        L.append(md_table(["Cấu hình", "KB/ảnh", "KB/trang", "Truyền (s)", "Giải mã (s)", "Tổng (s)",
                           "Giải mã / tổng (%)", "Tổng so với JPEG q75"], rows) + "\n")

    # Tải trang theo nhóm (tổng, 4G)
    rows = []
    for c in CFG_NAMES:
        r = [c]
        for scope in GROUPS:
            x = pl[(pl["scope"] == scope) & (pl["network"] == "4G") & (pl["config"] == c)].iloc[0]
            y = pl[(pl["scope"] == scope) & (pl["network"] == "3G") & (pl["config"] == c)].iloc[0]
            r += [_f(x["total_s"]), _f(y["total_s"])]
        rows.append(r)
    L.append("## B6. Tổng thời gian tải trang 40 ảnh theo nhóm (s)\n")
    L.append(md_table(["Cấu hình", "P 4G", "P 3G", "T 4G", "T 3G", "G 4G", "G 3G"], rows) + "\n")

    # Điểm hoà vốn: 1 KB truyền mất bao nhiêu ms
    for net, mbps in NETWORKS:
        ms_per_kb = 1024 * 8 / (mbps * 1e6) * 1000
        L.append(f"- Trên {net} ({mbps:g} Mbit/s), truyền 1 KB mất {ms_per_kb:.2f} ms; "
                 f"tức 1 ms giải mã tương đương {1 / ms_per_kb:.2f} KB dung lượng.")
    L.append("")

    rows = []
    for c in CFG_NAMES:
        r = [c]
        for scope in ["500", "1000", "all"]:
            x = ec[(ec["scope"] == scope) & (ec["config"] == c)].iloc[0]
            r += [_f(x["mean_enc_ms"]), _f(x["core_minutes"])]
        rows.append(r)
    L.append(f"## B7. Chi phí mã hoá {N_BATCH:,} ảnh (một luồng; lõi-phút CPU)\n".replace(",", "."))
    L.append(md_table(["Cấu hình", "500 px: ms/ảnh", "500 px: lõi-phút", "1000 px: ms/ảnh",
                       "1000 px: lõi-phút", "Cả 20 ảnh: ms/ảnh", "Cả 20 ảnh: lõi-phút"], rows) + "\n")

    rows = []
    for c in CFG_NAMES:
        ew, ec_, dw, dc = (get("all", "all", c, k) for k in
                           ["enc_ms_median", "enc_cpu_ms_median", "dec_ms_median", "dec_cpu_ms_median"])
        rows.append([c, _f(ew), _f(ec_), _f(ew / ec_ if ec_ > 0 else np.nan, 2),
                     _f(dw), _f(dc), _f(dw / dc if dc > 0 else np.nan, 2)])
    L.append("## B9. Đối chiếu thời gian tường (wall) và thời gian CPU của tiến trình (trung vị, tất cả 20 ảnh)\n")
    L.append("Thời gian CPU ít nhạy với việc tiến trình khác chen vào lõi; tỉ số wall/CPU xa 1 cho biết mức nhiễu "
             "(≈1 khi máy rảnh).\n")
    L.append(md_table(["Cấu hình", "Mã hoá wall (ms)", "Mã hoá CPU (ms)", "wall/CPU", "Giải mã wall (ms)",
                       "Giải mã CPU (ms)", "wall/CPU"], rows) + "\n")

    rows = [[c] + [_f(get("group", g, c, "size_kb_mean")) for g in GROUPS] + [_f(get("all", "all", c, "size_kb_mean"))]
            for c in CFG_NAMES]
    L.append("## B8. Dung lượng trung bình (KB/ảnh) dùng cho ước tính tải trang\n")
    L.append(md_table(hdr_g, rows) + "\n")

    with open(os.path.join(R_DIR, "tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# ----------------------------------------------------------------------------------
# 6. section.md (tự sinh: mọi con số lấy từ CSV nên luôn khớp sau khi chạy lại)
# ----------------------------------------------------------------------------------
def write_section():
    df = pd.read_csv(os.path.join(R_DIR, "timing.csv"))
    summ = pd.read_csv(os.path.join(R_DIR, "timing_by_group.csv"))
    pl = pd.read_csv(os.path.join(R_DIR, "page_load.csv"))
    ec = pd.read_csv(os.path.join(R_DIR, "encode_cost.csv"))
    with open(os.path.join(R_DIR, "machine_info.json"), encoding="utf-8") as f:
        info = json.load(f)

    def get(level, key, cfg, col):
        r = summ[(summ["level"] == level) & (summ["key"].astype(str) == str(key)) & (summ["config"] == cfg)]
        return float(r.iloc[0][col])

    def plr(scope, net, cfg, col):
        r = pl[(pl["scope"] == scope) & (pl["network"] == net) & (pl["config"] == cfg)]
        return float(r.iloc[0][col])

    def ecr(scope, cfg, col):
        r = ec[(ec["scope"].astype(str) == scope) & (ec["config"] == cfg)]
        return float(r.iloc[0][col])

    E = {c: get("all", "all", c, "enc_ms_median") for c in CFG_NAMES}
    D = {c: get("all", "all", c, "dec_ms_median") for c in CFG_NAMES}
    Ec = {c: get("all", "all", c, "enc_cpu_ms_median") for c in CFG_NAMES}
    Dc = {c: get("all", "all", c, "dec_cpu_ms_median") for c in CFG_NAMES}
    KB = {c: get("all", "all", c, "size_kb_mean") for c in CFG_NAMES}
    lossy = [c for c in CFG_NAMES if c not in ("PNG L9", "WebP lossless")]
    nb, na = info["noise_probe_before"], info["noise_probe_after"]
    total_cpu = float(df["enc_cpu_ms"].sum())
    wall_cpu = float(df["enc_ms"].sum() / total_cpu) if total_cpu > 0 else float("nan")
    has_loadavg = np.isfinite(info["loadavg_start"][0]) and np.isfinite(info["loadavg_end"][0])
    busy = has_loadavg and max(info["loadavg_start"][0], info["loadavg_end"][0]) > 0.7 * info["cpu_count_logical"]

    def x(a, b):
        return "N/A" if not (np.isfinite(a) and np.isfinite(b)) or b <= 0 else f"{a / b:.1f}"

    L = []
    L.append("# Thời gian nén/giải nén, tác động tới trang web và chương trình demo (t10)\n")
    L.append("## 1. Mục tiêu\n")
    L.append("Phần này đo **chi phí tính toán** của việc nén: thời gian mã hoá (xảy ra một lần, ở máy chủ khi tải ảnh "
             "lên) và thời gian giải mã (xảy ra ở mỗi lượt xem, trên thiết bị người dùng), quy đổi thông lượng "
             "megapixel/giây, rồi đặt các con số đó cạnh thời gian truyền qua mạng để xem yếu tố nào thực sự quyết "
             "định tốc độ trang danh mục 40 ảnh. Phần cuối mô tả chương trình demo trực tiếp `src/demo.py`.\n")

    L.append("## 2. Phương pháp và tham số\n")
    L.append("Tám cấu hình, mã hoá/giải mã hoàn toàn trong bộ nhớ bằng Pillow (cùng hàm `encode/decode` của "
             "`common.py`) trên cả 20 ảnh:\n")
    L.append("| Cấu hình | Tham số Pillow | Lý do |\n|---|---|---|")
    L.append("| JPEG q50 / q75 / q90 | `quality=q` (4:2:0 mặc định, không `optimize`) | Ba mức baseline của đề bài |")
    L.append("| PNG L9 | `compress_level=9` | Mức nén tối đa của zlib: cận trên chi phí mã hoá của PNG |")
    L.append("| WebP q50 / q75 / q90 | `quality=q, method=4` | `method=4` là mặc định của libwebp (thang 0–6), "
             "cân bằng tốc độ và hiệu quả |")
    L.append("| WebP lossless | `lossless=True, quality=100, method=4` | Với WebP không mất mát, `quality` là mức nỗ lực "
             "nén (100 = tối đa), không phải độ trung thực |\n")
    L.append(f"Mỗi cặp (ảnh, cấu hình) được chạy **1 lần khởi động và bỏ đi** (nạp thư viện, làm nóng cache, cấp phát "
             f"bộ nhớ lần đầu), sau đó đo **{info['repeats']} lần** và lấy **trung vị** (`common.time_ms`): trung vị bền "
             f"vững trước các lần đo bị tiến trình khác chen vào, và số lần lẻ cho một giá trị đo thực. Thông lượng gộp = "
             f"tổng megapixel / tổng thời gian. Thời gian giải mã gồm cả `load()` và đổi sang RGB như một trình xem ảnh. "
             f"Bên cạnh thời gian tường còn ghi thời gian CPU của tiến trình (`time.process_time`, cùng các lần chạy) để "
             f"đối chiếu độ nhiễu. Máy đo: {info['cpu_model']}, {info['cpu_count_logical']} lõi, Pillow "
             f"{info['pillow']} (libjpeg-turbo {info['libjpeg_turbo']}, libwebp {info['libwebp']}, zlib "
             f"{info['zlib']}).\n")
    if not has_loadavg:
        L.append(f"**Lưu ý độ tin cậy.** Windows không cung cấp load average, nên độ bận của máy được đánh giá bằng "
                 f"phép đo tham chiếu JPEG q75: IQR/trung vị {nb['iqr_over_median_pct']:.0f}% trước và "
                 f"{na['iqr_over_median_pct']:.0f}% sau; tổng thời gian tường mã hoá / CPU = {wall_cpu:.2f}. "
                 f"Chạy lại khi máy rảnh nếu IQR lớn hoặc tỉ số wall/CPU xa 1.\n")
    elif busy:
        L.append(f"**Lưu ý độ tin cậy.** Số đo trong lần chạy này thu khi máy đang bận (load average 1 phút "
                 f"{info['loadavg_start'][0]:.1f} → {info['loadavg_end'][0]:.1f} trên {info['cpu_count_logical']} lõi; "
                 f"phép đo tham chiếu JPEG q75 có IQR/trung vị {nb['iqr_over_median_pct']:.0f}% và "
                 f"{na['iqr_over_median_pct']:.0f}%; tổng thời gian tường mã hoá lớn gấp {wall_cpu:.1f} lần tổng thời gian CPU), "
                 f"nên thời gian tuyệt đối — nhất là của các phép chỉ vài mili-giây như JPEG — bị thổi phồng và dao động. "
                 f"Thứ hạng giữa các nhóm cấu hình (chênh nhau hàng chục lần) vẫn đáng tin; các tỉ số nhỏ thì không. "
                 f"Script chạy lại nguyên vẹn khi máy rảnh và `section.md` được sinh lại cùng số liệu.\n")
    else:
        L.append(f"Máy tương đối rảnh khi đo (load average 1 phút {info['loadavg_start'][0]:.1f} → "
                 f"{info['loadavg_end'][0]:.1f} trên {info['cpu_count_logical']} lõi; tổng thời gian tường mã hoá lớn gấp "
                 f"{wall_cpu:.2f} lần tổng thời gian CPU; phép đo tham chiếu có IQR/trung vị {nb['iqr_over_median_pct']:.0f}% "
                 f"và {na['iqr_over_median_pct']:.0f}%).\n")

    L.append("## 3. Kết quả đo\n")
    L.append("**Bảng 1.** Thời gian mã hoá và giải mã (trung vị, ms/ảnh) theo nhóm: P = ảnh chụp nhiều chi tiết "
             "(7 ảnh, 500 px), T = ảnh có chữ (3 ảnh 500 px + 4 ảnh 1000 px), G = gradient/nền trơn (3 + 3 ảnh).\n")
    rows = [[c] + [_f(get("group", g, c, "enc_ms_median")) for g in GROUPS]
            + [_f(get("group", g, c, "dec_ms_median")) for g in GROUPS] for c in CFG_NAMES]
    L.append(md_table(["Cấu hình", "Mã hoá P", "Mã hoá T", "Mã hoá G", "Giải mã P", "Giải mã T", "Giải mã G"], rows) + "\n")
    L.append("**Bảng 2.** Theo kích thước ảnh (trung vị ms/ảnh; 13 ảnh 500 px, 7 ảnh 1000 px) và thông lượng gộp "
             "trên cả 20 ảnh (megapixel/giây).\n")
    rows = [[c, _f(get("size", 500, c, "enc_ms_median")), _f(get("size", 1000, c, "enc_ms_median")),
             _f(get("all", "all", c, "enc_mps")),
             _f(get("size", 500, c, "dec_ms_median")), _f(get("size", 1000, c, "dec_ms_median")),
             _f(get("all", "all", c, "dec_mps"))] for c in CFG_NAMES]
    L.append(md_table(["Cấu hình", "Mã hoá 500 px", "Mã hoá 1000 px", "Mã hoá MP/s", "Giải mã 500 px",
                       "Giải mã 1000 px", "Giải mã MP/s"], rows) + "\n")
    L.append("Hình: `figures/t10/enc_dec_time.png` — (a) thời gian mã hoá và (b) thời gian giải mã (ms, thang log) "
             "của 8 cấu hình theo ba nhóm ảnh P, T, G.\n")
    L.append(f"Trên trung vị cả 20 ảnh (thời gian tường), mã hoá PNG L9 chậm hơn JPEG q75 khoảng "
             f"{x(E['PNG L9'], E['JPEG q75'])} lần ({_f(E['PNG L9'])} so với {_f(E['JPEG q75'])} ms); WebP q75 chậm hơn "
             f"JPEG q75 khoảng {x(E['WebP q75'], E['JPEG q75'])} lần ({_f(E['WebP q75'])} ms); WebP lossless là cấu hình "
             f"chậm nhất ({_f(E['WebP lossless'])} ms, chậm hơn PNG L9 {x(E['WebP lossless'], E['PNG L9'])} lần). Theo "
             f"thời gian CPU, các tỉ số tương ứng là {x(Ec['PNG L9'], Ec['JPEG q75'])}, "
             f"{x(Ec['WebP q75'], Ec['JPEG q75'])} và {x(Ec['WebP lossless'], Ec['PNG L9'])} lần. "
             f"Ở phía giải mã, mọi cấu hình đều nhanh: tối đa {_f(max(D.values()))} ms/ảnh (trung vị toàn bộ), "
             f"JPEG q75 {_f(D['JPEG q75'])} ms, WebP q75 {_f(D['WebP q75'])} ms ({x(D['WebP q75'], D['JPEG q75'])} lần JPEG), "
             f"PNG L9 {_f(D['PNG L9'])} ms; chênh lệch giữa các codec nhỏ hơn rất nhiều so với phía mã hoá.\n")

    L.append("## 4. Giải thích cơ chế\n")
    L.append("**JPEG mã hoá nhanh nhất** vì mọi bước là phép tính cố định trên từng khối 8×8: đổi màu sang YCbCr, "
             "giảm mẫu sắc độ (4:2:0), DCT, lượng tử hoá bằng bảng cố định theo quality và mã hoá Huffman. Không có vòng "
             "lặp tìm kiếm, và libjpeg-turbo viết bằng SIMD cho các bước nặng nên đạt hàng trăm MP/s (thông lượng gộp "
             f"{_f(get('all', 'all', 'JPEG q75', 'enc_mps'))} MP/s ở q75); đổi quality chỉ đổi bảng lượng tử nên thời gian "
             f"ít đổi ({_f(E['JPEG q50'])} ms ở q50 và {_f(E['JPEG q90'])} ms ở q90).\n")
    L.append("**WebP lossy mã hoá chậm hơn JPEG** vì bộ mã hoá VP8 phải *quyết định* nhiều hơn: với mỗi macroblock 16×16 "
             "nó thử các chế độ dự đoán nội ảnh (intra 16×16, intra 4×4, chế độ cho sắc độ), chọn chế độ theo hàm chi phí "
             "tỉ lệ–méo (RDO), nghĩa là phải biến đổi, lượng tử và tái dựng từng ứng viên; sau đó dùng bộ mã hoá số học "
             "nhị phân thích nghi theo ngữ cảnh (chậm hơn Huffman tĩnh vì từng bit đi qua mô hình xác suất) và bộ lọc khử "
             "khối trong vòng lặp. Đổi lại dung lượng nhỏ hơn (trung bình "
             f"{_f(KB['WebP q75'])} KB/ảnh ở q75 so với {_f(KB['JPEG q75'])} KB của JPEG q75; hai mức q không tương "
             f"đương về chất lượng). `method` càng cao thì thử càng nhiều ứng viên; q cao hơn có nhiều hệ số khác không hơn "
             f"nên thời gian cũng tăng ({_f(E['WebP q50'])} ms ở q50, {_f(E['WebP q90'])} ms ở q90).\n")
    L.append("**PNG L9 chậm do tìm kiếm LZ77.** PNG trước hết áp bộ lọc dự đoán theo từng hàng rồi nén bằng deflate; ở "
             "mức 9 zlib duyệt chuỗi băm rất dài và so khớp “lười” (lazy matching) để tìm chuỗi lặp dài nhất, tức là đánh "
             "đổi thời gian lấy vài phần trăm dung lượng. Chi phí phụ thuộc vào số vị trí phải thử chứ không chỉ vào số "
             "điểm ảnh. Lưu ý bản Pillow đo ở đây liên kết với zlib-ng, có chiến lược cho từng mức khác zlib cổ điển, nên "
             "con số tuyệt đối có thể khác trên môi trường dùng zlib chuẩn.\n")
    L.append("**WebP lossless chậm nhất khi mã hoá, nhưng gọn hơn PNG.** Nó kết hợp biến đổi dự đoán theo ô, biến đổi "
             "tương quan màu, trừ kênh lục, LZ77 với bộ nhớ đệm màu và nhiều bảng Huffman theo vùng; ở `quality=100` bộ mã "
             f"hoá thử nhiều tổ hợp tham số để chọn cái tốt nhất. Kết quả: dung lượng trung bình {_f(KB['WebP lossless'])} KB/ảnh "
             f"so với {_f(KB['PNG L9'])} KB của PNG L9, nhưng thời gian mã hoá cao hơn.\n")
    L.append("**Giải mã cả ba đều nhanh** vì giải mã không phải tìm kiếm: JPEG chỉ giải Huffman rồi IDCT (SIMD); WebP lossy "
             "giải số học, dựng lại dự đoán nội ảnh từ các khối lân cận (phụ thuộc tuần tự, khó SIMD hơn) và lọc khử khối "
             "nên thường chậm hơn JPEG vài lần; PNG chỉ inflate rồi đảo bộ lọc, thời gian tỉ lệ với lượng dữ liệu "
             "phải giải nén, và WebP lossless giải Huffman/LZ77 rồi đảo các phép biến đổi. Tỉ số thời gian mã hoá/giải mã "
             f"(trung vị toàn bộ) là {x(E['JPEG q75'], D['JPEG q75'])} với JPEG q75, {x(E['WebP q75'], D['WebP q75'])} với "
             f"WebP q75, {x(E['PNG L9'], D['PNG L9'])} với PNG L9 và {x(E['WebP lossless'], D['WebP lossless'])} với WebP "
             f"lossless: nén có tìm kiếm (PNG L9, WebP) bất đối xứng mạnh, mã hoá tốn hơn giải mã nhiều lần.\n")

    L.append("## 5. Ý nghĩa đối với website\n")
    L.append("Quy trình thực tế là **mã hoá một lần ở máy chủ** (khi tải ảnh lên hoặc trong bước build), còn **giải mã ở "
             "mỗi lượt xem**. Vì vậy chi phí mã hoá được chia cho mọi lượt xem, còn thời gian giải mã cộng thẳng vào độ "
             "trễ người dùng, nhưng so với thời gian truyền qua mạng thì chỉ chiếm phần nhỏ. Ước tính trang danh mục 40 ảnh "
             "(dung lượng bằng trung bình 20 ảnh của bộ dữ liệu; thời gian = tổng KB×8/băng thông + 40 × thời gian giải mã "
             "trung bình; tải tuần tự, bỏ qua độ trễ TCP/TLS):\n")
    L.append("**Bảng 3.** Thời gian tải trang 40 ảnh (s).\n")
    rows = [[c, _f(plr("all", "4G", c, "avg_kb_per_image")), _f(plr("all", "4G", c, "transfer_s")),
             _f(plr("all", "4G", c, "decode_s")), _f(plr("all", "4G", c, "total_s")),
             _f(plr("all", "3G", c, "transfer_s")), _f(plr("all", "3G", c, "total_s"))] for c in CFG_NAMES]
    L.append(md_table(["Cấu hình", "KB/ảnh", "4G: truyền", "4G: giải mã", "4G: tổng", "3G: truyền", "3G: tổng"],
                      rows) + "\n")
    L.append("Hình: `figures/t10/page_load.png` — thời gian tải trang 40 ảnh (cột xếp chồng: truyền + giải mã) trên (a) 4G "
             "10 Mbit/s và (b) 3G 2 Mbit/s.\n")

    ms4 = 1024 * 8 / (10e6) * 1000
    ms3 = 1024 * 8 / (2e6) * 1000
    sh4 = {c: plr("all", "4G", c, "decode_share_pct") for c in CFG_NAMES}
    sh3 = {c: plr("all", "3G", c, "decode_share_pct") for c in CFG_NAMES}
    c4max = max(CFG_NAMES, key=lambda c: sh4[c])
    c3max = max(CFG_NAMES, key=lambda c: sh3[c])
    dom4 = max(sh4.values()) < 50
    dom3 = max(sh3.values()) < 50
    txt = (f"Truyền 1 KB mất {ms4:.2f} ms trên 4G và {ms3:.2f} ms trên 3G, nên 1 ms giải mã chỉ đáng bằng "
           f"{1 / ms4:.2f} KB (4G) hoặc {1 / ms3:.2f} KB (3G) dung lượng. Thời gian giải mã chiếm tối đa {sh4[c4max]:.0f}% "
           f"tổng thời gian trên 4G (cấu hình {c4max}) và {sh3[c3max]:.0f}% trên 3G (cấu hình {c3max}); ")
    if dom4 and dom3:
        txt += "trong mọi cấu hình, **thời gian truyền chiếm ưu thế**, nên tiêu chí chọn định dạng phải là dung lượng. "
    elif dom3:
        txt += ("trên 3G thời gian truyền chiếm ưu thế ở mọi cấu hình, còn trên 4G các cấu hình rất nhẹ (WebP) có phần "
                "giải mã đáng kể, nên mạng càng nhanh thì chi phí giải mã càng đáng cân nhắc. ")
    else:
        txt += "giải mã đáng kể ở một số cấu hình nhẹ; cần đo lại trên máy rảnh. "
    # So sánh WebP q75 với JPEG q75
    dk = KB["JPEG q75"] - KB["WebP q75"]
    ddec = D["WebP q75"] - D["JPEG q75"]
    net4 = dk * ms4 - ddec
    net3 = dk * ms3 - ddec
    txt += (f"Ví dụ so sánh danh nghĩa WebP q75 với JPEG q75: dung lượng chênh {_f(dk)} KB/ảnh, tương ứng "
            f"{_f(dk * ms4)} ms (4G) hoặc {_f(dk * ms3)} ms (3G) truyền, trong khi giải mã tốn thêm {_f(ddec)} ms/ảnh; "
            f"chênh lệch ròng là {_f(net4)} ms/ảnh trên 4G và {_f(net3)} ms/ảnh trên 3G (dương = WebP có lợi). Cần nhớ "
            f"q75 của hai codec không cho cùng chất lượng; so sánh công bằng theo PSNR/SSIM nằm ở các phần đánh giá chất "
            f"lượng của báo cáo. Ngược lại, PNG L9 và WebP lossless nặng gấp {x(KB['PNG L9'], KB['JPEG q75'])} và "
            f"{x(KB['WebP lossless'], KB['JPEG q75'])} lần JPEG q75 "
            f"(tải trang {_f(plr('all', '4G', 'PNG L9', 'total_s'))} s và {_f(plr('all', '4G', 'WebP lossless', 'total_s'))} s "
            f"trên 4G; {_f(plr('all', '3G', 'PNG L9', 'total_s'))} s và {_f(plr('all', '3G', 'WebP lossless', 'total_s'))} s "
            f"trên 3G), nên chỉ phù hợp cho ảnh phải giữ nguyên từng điểm ảnh.")
    L.append(txt + "\n")

    L.append(f"**Bảng 4.** Chi phí mã hoá {N_BATCH:,} ảnh".replace(",", ".")
             + ", một luồng (lõi-phút; chia cho số lõi khi chạy song song).\n")
    rows = [[c, _f(ecr("all", c, "mean_enc_ms")), _f(ecr("all", c, "core_minutes")), _f(ecr("500", c, "core_minutes")),
             _f(ecr("1000", c, "core_minutes"))] for c in CFG_NAMES]
    L.append(md_table(["Cấu hình", "ms/ảnh (trung bình 20 ảnh)", "Lõi-phút, ảnh trộn", "Lõi-phút, ảnh 500 px",
                       "Lõi-phút, ảnh 1000 px"], rows) + "\n")
    worst = max(CFG_NAMES, key=lambda c: ecr("all", c, "core_minutes"))
    L.append(f"Mã hoá hàng loạt 10.000 ảnh bằng WebP q75 tốn khoảng {_f(ecr('all', 'WebP q75', 'core_minutes'))} lõi-phút, "
             f"bằng JPEG q75 khoảng {_f(ecr('all', 'JPEG q75', 'core_minutes'))} lõi-phút, còn cấu hình tốn nhất ({worst}) "
             f"khoảng {_f(ecr('all', worst, 'core_hours'))} lõi-giờ. Đó là chi phí một lần, song song hoá dễ dàng theo ảnh; "
             f"so với việc phục vụ hàng triệu lượt xem, phần chênh lệch chi phí mã hoá của WebP là không đáng kể và được "
             f"bù bằng dung lượng truyền giảm ở mỗi lượt xem. Mã hoá chậm chỉ thành vấn đề khi phải nén theo yêu cầu (on the "
             f"fly) cho từng lượt truy cập, khi đó nên dùng mức nỗ lực thấp hơn hoặc lưu đệm kết quả.\n")

    L.append("## 6. Chương trình demo (`src/demo.py`)\n")
    L.append("Demo chạy cục bộ, nhận đường dẫn ảnh bất kỳ làm tham số dòng lệnh (mặc định `data/images/T01_card1000.png`) và "
             "mở cửa sổ matplotlib tương tác gồm: ảnh gốc và ảnh sau nén–giải nén cạnh nhau; **Slider Quality (5–100)**; "
             "**RadioButtons** chọn codec (JPEG 4:2:0, JPEG 4:4:4, WebP, PNG, WebP lossless); bảng số liệu gồm KB, bpp, "
             "tỉ lệ nén, PSNR, SSIM của cả ảnh, PSNR cục bộ của vùng chọn, thời gian mã hoá/giải mã; và hai ô **phóng to** "
             "(gốc và nén) quanh tâm do người dùng **click/kéo chuột** chọn trên ảnh (phím +/− đổi cỡ vùng). Tâm mặc định "
             "được chọn tự động tại vùng có gradient lớn nhất để lỗi nén hiện rõ ngay. Slider bị khoá với PNG và WebP "
             "lossless vì hai codec này không mất mát. Chế độ `--save out.png` chạy không giao diện (backend Agg), lưu "
             "ảnh chụp giao diện và in chỉ số ra màn hình, dùng để kiểm thử trong môi trường không có màn hình:\n")
    L.append("```\npython src/demo.py                                    # cửa sổ tương tác\n"
             "python src/demo.py anh.jpg --codec WebP --quality 40   # chọn trạng thái ban đầu\n"
             "python src/demo.py --save out.png --codec \"JPEG 4:2:0\" --quality 30 --center 480 300\n```\n")
    L.append("Hình: `figures/t10/demo_headless.png` — ảnh chụp giao diện demo ở chế độ không giao diện (ảnh T01, WebP "
             "quality 30; hình này được sinh khi kiểm thử demo, không do `t10_timing.py` tạo ra). Đây là công cụ minh "
             "hoạ: kéo slider xuống thấp trên ảnh có chữ sẽ thấy ngay vết nhoè quanh nét chữ và lỗi khối ở JPEG.\n")

    L.append("## 7. Hạn chế\n")
    L.append("- Đo trên một máy chủ (Xeon, không GPU, Pillow đơn luồng), không phải điện thoại; thiết bị yếu có thể giải mã "
             "chậm hơn vài lần nên phần giải mã trong Bảng 3 là cận dưới đối với thiết bị di động. Mức độ chậm đi chưa được đo.")
    L.append("- Mô hình tải trang đơn giản: tải tuần tự, bỏ qua RTT, TLS, HTTP/2 song song, tải lười và hiển thị lũy tiến; "
             "ảnh trong bộ dữ liệu (500/1000 px) lớn hơn thumbnail danh mục thông thường, nên số giây chỉ để so sánh tương "
             "đối giữa các cấu hình.")
    L.append("- Thời gian JPEG chỉ vài mili-giây nên rất nhạy với nhiễu hệ thống; các tỉ số giữa 500 px và 1000 px lẫn "
             "ảnh hưởng của nội dung (ảnh 1000 px chỉ thuộc nhóm T, G) và của nhiễu, không nên suy ra quy luật tỉ lệ diện tích "
             "từ bảng này.")
    L.append("- Kết quả PNG phụ thuộc bản zlib (ở đây là zlib-ng) và bộ lọc dòng mà Pillow chọn; kết quả WebP phụ thuộc "
             "`method` (chỉ đo `method=4`). Chất lượng ảnh (PSNR/SSIM) không đo ở phần này.\n")
    with open(os.path.join(R_DIR, "section.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# ----------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tables-only", action="store_true",
                    help="không đo lại; chỉ sinh bảng/hình từ CSV hiện có")
    ap.add_argument("--repeats", type=int, default=REPEATS, help="số lần đo mỗi cấu hình (mặc định 9)")
    a = ap.parse_args()
    if a.tables_only:
        df = pd.read_csv(os.path.join(R_DIR, "timing.csv"))
    else:
        df, _ = run_measurements(a.repeats)
    summ = summarise(df)
    pl = page_load(df)
    encode_cost(df)
    fig_enc_dec(summ)
    fig_page_load(pl)
    write_tables()
    write_section()
    print("Xong. Kết quả ở", R_DIR, "và", F_DIR)


if __name__ == "__main__":
    main()
