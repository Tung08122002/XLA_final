"""t02 - Ví dụ tính tay JPEG trên một khối 8x8 thật + hình minh hoạ cho Chương 2.

Chạy:  cd /home/claude/nen_anh && python src/t02_worked_example.py

Các bước (đúng như bộ mã hoá JPEG baseline, nhưng tự cài bằng numpy/scipy để không dùng hộp đen):
 1. Đọc ảnh data/images/T01_card1000.png, đổi sang kênh Y theo công thức JFIF
    Y = 0,299R + 0,587G + 0,114B (làm tròn về số nguyên 0..255).
 2. Chọn khối 8x8 THẬT nằm trên dòng chữ "Chống nước IPX4" (vùng y=760..799, x=40..279):
    khối căn lưới 8x8 có độ lệch chuẩn lớn nhất (khối nhiều biên chữ nhất, là trường hợp
    "khó" cho DCT). Lưới 8x8 căn theo gốc ảnh như JPEG thật.
 3. Trừ 128 (level shift) -> DCT-II 2D chuẩn trực giao (scipy.fft.dctn, norm='ortho').
    Với norm='ortho' công thức trùng đúng định nghĩa của chuẩn JPEG (có hệ số C(u)C(v)/4).
 4. Lượng tử hoá bằng bảng luminance chuẩn Annex K, nhân hệ số tỉ lệ IJG:
    S = 5000/q (q<50) hoặc 200-2q (q>=50); Q' = clip(floor((Q*S+50)/100), 1, 255).
    Làm tròn hệ số F/Q' về số nguyên gần nhất (half away from zero, như libjpeg).
    Chọn q=50 (S=100, bảng gốc) và q=90 (S=20) để thấy ảnh hưởng của quality.
 5. Giải lượng tử (nhân lại Q'), IDCT, cộng 128, làm tròn + cắt về [0,255]; tính MSE, PSNR
    (L=255) và đếm số hệ số khác 0 (tổng và AC), quét zigzag + RLE (run, level).
 6. Kiểm chứng chéo: bảng Q' tự tính phải trùng bảng Pillow/libjpeg thực sự dùng khi
    save(quality=q); và phép DCT tự cài phải trùng ma trận DCT viết tay (kiểm tra trực giao).
 7. Ví dụ PSNR/SSIM tính tay nhỏ: hai khối 3x3 (một cửa sổ, thống kê toàn khối), có đối chiếu
    skimage.structural_similarity (win_size=3, trọng số đều) để chắc chắn công thức đúng.

Bổ sung: áp 5 bộ lọc PNG (Sub/Up/Average/Paeth) lên chính khối này để minh hoạ bước dự đoán.

Đầu ra: results/t02/worked_example.txt, results/t02/worked_example_summary.csv,
        results/t02/qtable_scale.csv, figures/t02/dct_example.png,
        figures/t02/jpeg_qtable_scale.png, figures/t02/pipeline.png (sơ đồ khối pipeline).
Không có yếu tố ngẫu nhiên (không cần seed), kết quả tất định.
"""
import io
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.fft import dctn, idctn
from skimage.metrics import structural_similarity

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, IMG_DIR, SEED, ensure_dirs  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 10

IMG_NAME = "T01_card1000.png"
SEARCH = (760, 800, 40, 280)   # vùng dòng chữ "Chống nước IPX4": y0,y1,x0,x1

# Bảng lượng tử luminance chuẩn (ITU-T T.81 Annex K, Bảng K.1)
Q_LUM = np.array([
    [16, 11, 10, 16, 24, 40, 51, 61],
    [12, 12, 14, 19, 26, 58, 60, 55],
    [14, 13, 16, 24, 40, 57, 69, 56],
    [14, 17, 22, 29, 51, 87, 80, 62],
    [18, 22, 37, 56, 68, 109, 103, 77],
    [24, 35, 55, 64, 81, 104, 113, 92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103, 99]], dtype=np.int64)


def ijg_scale(q):
    q = int(min(max(q, 1), 100))
    return 5000 // q if q < 50 else 200 - 2 * q  # libjpeg: 5000/quality (chia nguyên)


def scaled_qtable(q, base=Q_LUM):
    s = ijg_scale(q)
    return np.clip((base * s + 50) // 100, 1, 255)


def round_half_away(x):
    return np.sign(x) * np.floor(np.abs(x) + 0.5)


def zigzag_indices(n=8):
    idx = sorted(((i, j) for i in range(n) for j in range(n)),
                 key=lambda p: (p[0] + p[1], p[1] if (p[0] + p[1]) % 2 == 0 else p[0]))
    return idx


def dct_matrix(n=8):
    """Ma trận DCT-II trực giao: C[k,m] = a(k) cos((2m+1)k*pi/(2n))."""
    C = np.zeros((n, n))
    for k in range(n):
        a = np.sqrt(1.0 / n) if k == 0 else np.sqrt(2.0 / n)
        for m in range(n):
            C[k, m] = a * np.cos((2 * m + 1) * k * np.pi / (2 * n))
    return C


def rgb_to_y(arr):
    r, g, b = [arr[..., i].astype(np.float64) for i in range(3)]
    return np.clip(np.round(0.299 * r + 0.587 * g + 0.114 * b), 0, 255).astype(np.int64)


def mse_psnr(a, b):
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return mse, (float("inf") if mse == 0 else 10 * np.log10(255.0 ** 2 / mse))


def fmt_matrix(M, width=5, fmt="d"):
    lines = []
    for row in M:
        lines.append(" ".join(f"{(int(v) if fmt == 'd' else v):{width}{'d' if fmt == 'd' else fmt}}" for v in row))
    return "\n".join(lines)


def fmt_float(M, width=8, dec=1):
    return "\n".join(" ".join(f"{v:{width}.{dec}f}" for v in row) for row in M)


def global_ssim(x, y, L=255.0):
    """SSIM trên MỘT cửa sổ (toàn khối), trọng số đều, phương sai tổng thể (chia N)."""
    x = x.astype(np.float64).ravel()
    y = y.astype(np.float64).ravel()
    C1, C2 = (0.01 * L) ** 2, (0.03 * L) ** 2
    mx, my = x.mean(), y.mean()
    vx, vy = x.var(), y.var()
    cxy = np.mean((x - mx) * (y - my))
    num = (2 * mx * my + C1) * (2 * cxy + C2)
    den = (mx ** 2 + my ** 2 + C1) * (vx + vy + C2)
    return dict(mx=mx, my=my, vx=vx, vy=vy, cxy=cxy, C1=C1, C2=C2,
                lum=(2 * mx * my + C1) / (mx ** 2 + my ** 2 + C1),
                cs=(2 * cxy + C2) / (vx + vy + C2), ssim=num / den)


def png_filters(img):
    """Áp 5 bộ lọc PNG (None/Sub/Up/Average/Paeth) lên ảnh xám 8 bit, phép trừ modulo 256.
    Điểm ảnh ngoài biên (bên trái, phía trên) coi bằng 0 đúng như đặc tả PNG."""
    a_img = img.astype(np.int64)
    H, W = a_img.shape
    out = {k: np.zeros((H, W), np.int64) for k in ("None", "Sub", "Up", "Average", "Paeth")}
    for y in range(H):
        for x in range(W):
            v = a_img[y, x]
            a = a_img[y, x - 1] if x > 0 else 0
            b = a_img[y - 1, x] if y > 0 else 0
            c = a_img[y - 1, x - 1] if x > 0 and y > 0 else 0
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            out["None"][y, x] = v
            out["Sub"][y, x] = (v - a) % 256
            out["Up"][y, x] = (v - b) % 256
            out["Average"][y, x] = (v - (a + b) // 2) % 256
            out["Paeth"][y, x] = (v - pred) % 256
    return out


def draw_pipeline(fig_dir):
    """Sơ đồ khối nằm ngang của pipeline thí nghiệm (matplotlib patches, nét 2, chữ đen)."""
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    fig, ax = plt.subplots(figsize=(8.0, 3.6))
    ax.set_xlim(0, 101); ax.set_ylim(0, 48); ax.axis("off")
    boxes = [
        ("1. ĐẦU VÀO", ["20 ảnh PNG", "P: 7 ảnh chụp", "T: 7 thẻ chữ", "G: 6 gradient", "list_images()"]),
        ("2. TIỀN\nXỬ LÝ", ["convert('RGB')", "RGB 8 bit", "cắt vuông", "resize LANCZOS", "500² / 1000²"]),
        ("3. XỬ LÝ\nCHÍNH", ["Image.save()", "JPEG 50/75/90", "PNG level 9", "WebP lossy q", "WebP lossless"]),
        ("4. HẬU\nXỬ LÝ", ["Image.open()", "KB, bpp, tỉ lệ", "PSNR numpy", "SSIM skimage", "gộp theo nhóm"]),
        ("5. ĐẦU RA", ["Bảng CSV", "Đồ thị RD", "Khuyến nghị", "định dạng và", "mức nén"]),
    ]
    n = len(boxes)
    w, gap = 17.4, 3.2
    x = 0.6
    for i, (title, lines) in enumerate(boxes):
        ax.add_patch(FancyBboxPatch((x, 8), w, 38, boxstyle="round,pad=0.0,rounding_size=1.2",
                                    fc="white", ec="black", lw=2))
        ax.add_patch(FancyBboxPatch((x, 38), w, 8, boxstyle="round,pad=0.0,rounding_size=1.2",
                                    fc="0.88", ec="black", lw=2))
        ax.text(x + w / 2, 42, title, ha="center", va="center", fontsize=10, fontweight="bold")
        for k, t in enumerate(lines):
            ax.text(x + w / 2, 33 - 5.4 * k, t, ha="center", va="center", fontsize=9)
        if i < n - 1:
            ax.add_patch(FancyArrowPatch((x + w + 0.15, 26), (x + w + gap - 0.15, 26), arrowstyle="-|>",
                                         mutation_scale=14, lw=2, color="black"))
        x += w + gap
    ax.text(50, 3, "Bước 3–4 lặp cho mọi cặp (ảnh, định dạng, tham số); so sánh ảnh gốc với ảnh giải mã",
            ha="center", va="center", fontsize=9)
    fig.savefig(os.path.join(fig_dir, "pipeline.png"), dpi=300, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def main():
    res_dir, fig_dir = ensure_dirs("t02")
    out = []
    P = out.append

    # ---- 1-2. Lấy khối thật -------------------------------------------------
    im = Image.open(os.path.join(IMG_DIR, IMG_NAME)).convert("RGB")
    Y = rgb_to_y(np.asarray(im))
    y0, y1, x0, x1 = SEARCH
    if Y.shape[0] < y1 or Y.shape[1] < x1:
        raise ValueError(f"Ảnh {IMG_NAME} quá nhỏ cho vùng tìm khối {SEARCH}: {Y.shape}")
    cand = [(Y[j:j + 8, i:i + 8].std(), j, i) for j in range(y0, y1, 8) for i in range(x0, x1, 8)]
    _, by, bx = max(cand)
    blk = Y[by:by + 8, bx:bx + 8]
    P(f"VÍ DỤ TÍNH TAY JPEG TRÊN KHỐI 8x8 THẬT")
    P(f"Ảnh: {IMG_NAME}; kênh Y (JFIF); khối góc trên-trái (y={by}, x={bx}); "
      f"độ lệch chuẩn khối = {blk.std():.2f}; min={blk.min()}, max={blk.max()}")
    P("\n[1] Khối gốc f(x,y) (Y, 0..255):")
    P(fmt_matrix(blk))
    shifted = blk.astype(np.float64) - 128
    P("\n[2] Sau khi trừ 128 (level shift):")
    P(fmt_matrix(shifted.astype(int)))

    # ---- 3. DCT -------------------------------------------------------------
    F = dctn(shifted, type=2, norm="ortho")
    C = dct_matrix(8)
    F_manual = C @ shifted @ C.T
    assert np.allclose(F, F_manual, atol=1e-9), "DCT scipy khác DCT ma trận viết tay"
    assert np.allclose(C @ C.T, np.eye(8), atol=1e-12), "Ma trận DCT không trực giao"
    P("\n[3] Hệ số DCT-II 2D chuẩn trực giao F(u,v) = C f C^T (đã kiểm tra trùng scipy.fft.dctn; "
      "hàng u = tần số dọc, cột v = tần số ngang):")
    P(fmt_float(F, 8, 1))
    P(f"    DC = F(0,0) = {F[0, 0]:.2f} (= 8 * trung bình khối đã trừ 128 = {8 * shifted.mean():.2f}); "
      f"kiểm tra Parseval: tổng bình phương = {np.sum(shifted ** 2):.1f} (không gian) vs {np.sum(F ** 2):.1f} (tần số)")
    assert np.isclose(np.sum(shifted ** 2), np.sum(F ** 2))

    # ---- 4-5. Lượng tử hoá ----------------------------------------------------
    # kiểm chứng bảng Q' tự tính với libjpeg (Pillow) trên nhiều quality, không chỉ 50 và 90
    for qq in (1, 10, 25, 49, 50, 75, 90, 95, 99, 100):
        b_ = io.BytesIO()
        Image.fromarray(np.full((16, 16), 128, np.uint8)).save(b_, "JPEG", quality=qq)
        t_ = np.array(Image.open(io.BytesIO(b_.getvalue())).quantization[0]).reshape(8, 8)
        assert np.array_equal(t_, scaled_qtable(qq)), f"Q' khác libjpeg tại quality={qq}"
    P("Đã kiểm tra bảng Q' tự tính trùng libjpeg (Pillow) tại quality = 1, 10, 25, 49, 50, 75, 90, 95, 99, 100.")
    rows = []
    zz = zigzag_indices()
    results = {}
    for q in (50, 90):
        S = ijg_scale(q)
        Qp = scaled_qtable(q)
        # kiểm chứng chéo với bảng thật của libjpeg trong Pillow
        buf = io.BytesIO()
        Image.fromarray(np.full((16, 16), 128, np.uint8)).save(buf, "JPEG", quality=q)
        # Pillow trả bảng lượng tử đã sắp lại theo vị trí (i,j) (thứ tự tự nhiên, không phải zigzag)
        pil_q_nat = np.array(Image.open(io.BytesIO(buf.getvalue())).quantization[0]).reshape(8, 8)
        match = bool(np.array_equal(pil_q_nat, Qp))
        assert match, f"Bảng Q' q={q} khác libjpeg/Pillow"
        Fq = round_half_away(F / Qp).astype(np.int64)
        Fdq = Fq * Qp
        rec_f = idctn(Fdq.astype(np.float64), type=2, norm="ortho")
        rec = np.clip(np.round(rec_f + 128), 0, 255).astype(np.int64)
        mse, ps = mse_psnr(blk, rec)
        nz = int(np.count_nonzero(Fq))
        nz_ac = nz - int(Fq[0, 0] != 0)
        zig = [int(Fq[i, j]) for i, j in zz]
        # RLE (run of zeros, level) cho AC, kết thúc bằng EOB
        rle, run = [], 0
        for v in zig[1:]:
            if v == 0:
                run += 1
            else:
                rle.append((run, v))
                run = 0
        eob = run > 0
        ssim_blk = global_ssim(blk, rec)["ssim"]
        results[q] = dict(S=S, Qp=Qp, Fq=Fq, Fdq=Fdq, rec=rec, mse=mse, psnr=ps, nz=nz, nz_ac=nz_ac,
                          zig=zig, rle=rle, eob=eob, ssim=ssim_blk)
        P(f"\n{'=' * 70}\nQUALITY q = {q}:  S = {S}  (bảng Q' = floor((Q*S+50)/100), kiểm tra trùng libjpeg/Pillow: {match})")
        P("Bảng lượng tử Q':")
        P(fmt_matrix(Qp, 4))
        P(f"\nHệ số lượng tử hoá Fq = round(F/Q'):")
        P(fmt_matrix(Fq, 4))
        P(f"\nSố hệ số khác 0: {nz}/64 (AC khác 0: {nz_ac}/63); hệ số bằng 0: {64 - nz}")
        P(f"Chuỗi zigzag (64 phần tử): {zig}")
        P(f"RLE của 63 hệ số AC dạng (số 0 đứng trước, giá trị): {rle}{' + EOB' if eob else ' (không cần EOB)'}")
        P(f"\nHệ số giải lượng tử Fq*Q':")
        P(fmt_matrix(Fdq, 5))
        P(f"\nKhối khôi phục (IDCT + 128, làm tròn, cắt 0..255):")
        P(fmt_matrix(rec))
        P(f"\nSai số e = gốc - khôi phục (|e|max = {np.abs(blk - rec).max()}):")
        P(fmt_matrix(blk - rec, 4))
        P(f"MSE = {mse:.3f}; PSNR = 10 log10(255^2/MSE) = {ps:.2f} dB; SSIM (1 cửa sổ 8x8, trọng số đều) = {ssim_blk:.4f}")
        rows.append(dict(quality=q, S=S, nonzero=nz, nonzero_ac=nz_ac, zeros=64 - nz,
                         rle_pairs=len(rle), mse=round(mse, 3), psnr_db=round(ps, 2), ssim_block=round(ssim_blk, 4)))

    # sanity: so với Pillow thật trên cả ảnh (chỉ in ra để tham khảo, không dùng cho số liệu)
    P(f"\n{'=' * 70}\nGHI CHÚ: tự cài chỉ mô phỏng bước DCT/lượng tử trên kênh Y của MỘT khối; libjpeg còn thêm "
      f"chuyển YCbCr, lấy mẫu 4:2:0 và mã hoá entropy nên số liệu cả ảnh (t03...) sẽ khác số liệu khối này.")

    # ---- 7. PSNR / SSIM tính tay nhỏ -----------------------------------------
    P(f"\n{'=' * 70}\nVÍ DỤ NHỎ TÍNH TAY PSNR/SSIM (L = 255)")
    x = np.array([[52, 55, 61], [68, 70, 66], [63, 59, 55]])
    y = np.array([[50, 56, 60], [70, 72, 62], [61, 60, 57]])
    P("Khối gốc x:\n" + fmt_matrix(x, 4))
    P("Khối nén y:\n" + fmt_matrix(y, 4))
    d = x - y
    P("Sai số x-y:\n" + fmt_matrix(d, 4))
    P("Bình phương sai số:\n" + fmt_matrix(d ** 2, 4))
    mse = float(np.mean(d ** 2))
    psnr_v = 10 * np.log10(255 ** 2 / mse)
    P(f"Tổng bình phương = {int(np.sum(d ** 2))}; MSE = {int(np.sum(d ** 2))}/9 = {mse:.4f}")
    P(f"PSNR = 10 log10(65025/{mse:.4f}) = {psnr_v:.2f} dB")
    g = global_ssim(x, y)
    P(f"mu_x = {g['mx']:.4f}; mu_y = {g['my']:.4f}; var_x = {g['vx']:.4f}; var_y = {g['vy']:.4f}; cov_xy = {g['cxy']:.4f}")
    P(f"C1 = (0,01*255)^2 = {g['C1']:.4f}; C2 = (0,03*255)^2 = {g['C2']:.4f}")
    P(f"Thành phần độ sáng l = (2 mu_x mu_y + C1)/(mu_x^2 + mu_y^2 + C1) = {g['lum']:.6f}")
    P(f"Thành phần tương phản-cấu trúc cs = (2 cov + C2)/(var_x + var_y + C2) = {g['cs']:.6f}")
    P(f"SSIM = l * cs = {g['ssim']:.6f}")
    sk = structural_similarity(x.astype(np.uint8), y.astype(np.uint8), win_size=3, data_range=255,
                               gaussian_weights=False, use_sample_covariance=False)
    P(f"Đối chiếu skimage (win_size=3, trọng số đều, không dùng covariance mẫu): {sk:.6f}")
    assert np.isclose(sk, g["ssim"], atol=1e-6)
    # vector 1 chiều
    v1 = np.array([10, 20, 30, 40]); v2 = np.array([12, 18, 33, 37])
    mv = float(np.mean((v1 - v2) ** 2))
    P(f"\nVí dụ 2 vector: v1 = {v1.tolist()}, v2 = {v2.tolist()}: MSE = (4+4+9+9)/4 = {mv:.2f}; "
      f"PSNR = 10 log10(65025/{mv:.2f}) = {10 * np.log10(255 ** 2 / mv):.2f} dB")
    P(f"Mỗi lần MSE giảm một nửa thì PSNR tăng 10 log10(2) = {10 * np.log10(2):.2f} dB; "
      f"PSNR = 30 dB tương ứng MSE = {255 ** 2 / 10 ** 3:.1f}, 40 dB ứng MSE = {255 ** 2 / 10 ** 4:.2f}.")

    # ---- 8. Bộ lọc PNG trên chính khối 8x8 ------------------------------------
    P(f"\n{'=' * 70}\nBỘ LỌC DỰ ĐOÁN PNG TRÊN CHÍNH KHỐI 8x8 NÀY (ảnh xám, residual mod 256; "
      f"đo bằng tổng |giá trị| khi coi byte > 127 là số âm, đúng heuristic 'minimum sum of absolute differences' của libpng)")
    pf = png_filters(blk)
    prow = []
    for name, R in pf.items():
        signed = np.where(R > 127, R - 256, R)
        n0 = int(np.count_nonzero(R == 0))
        P(f"{name:8s}: số byte = 0: {n0:2d}/64; tổng |residual| = {int(np.abs(signed).sum())}")
        prow.append(dict(filter=name, zero_bytes=n0, sum_abs=int(np.abs(signed).sum())))
    P("Residual Paeth (mod 256):\n" + fmt_matrix(pf["Paeth"], 4))
    pd.DataFrame(prow).to_csv(os.path.join(res_dir, "png_filter_block.csv"), index=False)


    # ---- 9. Ước lượng chặn dưới entropy do nhiễu Gauss (giải thích PNG kém với ảnh nhiễu) ----
    sig = 1.5  # σ nhiễu của nhóm G04-G06 (BRIEF.md)
    h_gauss = lambda var: 0.5 * np.log2(2 * np.pi * np.e * var)
    P(f"\n{'=' * 70}\nƯỚC LƯỢNG GIẢI TÍCH: nhiễu Gauss σ={sig} cộng độc lập vào từng điểm ảnh")
    P(f"Bộ lọc Sub/Up: residual = x_i - x_(i-1): phương sai 2σ² = {2 * sig ** 2:.2f} -> entropy vi phân "
      f"h = 0,5 log2(2πe·2σ²) = {h_gauss(2 * sig ** 2):.2f} bit/mẫu = {3 * h_gauss(2 * sig ** 2):.2f} bpp (RGB)")
    P(f"Bộ lọc Average (dự đoán = trung bình 2 láng giềng): phương sai 1,5σ² = {1.5 * sig ** 2:.3f} -> "
      f"h = {h_gauss(1.5 * sig ** 2):.2f} bit/mẫu = {3 * h_gauss(1.5 * sig ** 2):.2f} bpp")
    P(f"Tương ứng tỉ lệ nén tối đa chỉ do nhiễu ≈ 24/bpp = {24 / (3 * h_gauss(2 * sig ** 2)):.1f}:1 (Sub/Up) đến "
      f"{24 / (3 * h_gauss(1.5 * sig ** 2)):.1f}:1 (Average), CHƯA kể cấu trúc ảnh. Đây là ước lượng lý thuyết (nền ảnh phẳng, "
      f"bỏ qua làm tròn/cắt ngưỡng), không phải số đo thực nghiệm.")

    pd.DataFrame(rows).to_csv(os.path.join(res_dir, "worked_example_summary.csv"), index=False)
    pd.DataFrame([dict(example="3x3", mse=round(mse, 4), psnr_db=round(psnr_v, 2), ssim=round(g["ssim"], 6))]
                 ).to_csv(os.path.join(res_dir, "small_example_3x3.csv"), index=False)

    # ---- bảng scale theo quality --------------------------------------------
    qs = np.arange(1, 101)
    Ss = np.array([ijg_scale(q) for q in qs])
    pd.DataFrame({"quality": qs, "S": Ss,
                  "mean_Qprime": [scaled_qtable(q).mean() for q in qs],
                  "Qprime_DC": [scaled_qtable(q)[0, 0] for q in qs],
                  "Qprime_max": [scaled_qtable(q).max() for q in qs]}
                 ).to_csv(os.path.join(res_dir, "qtable_scale.csv"), index=False)

    with open(os.path.join(res_dir, "worked_example.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))

    # ======================= HÌNH: dct_example.png =========================
    r50, r90 = results[50], results[90]
    fig, axs = plt.subplots(3, 2, figsize=(6.4, 8.2))
    lw = 1.8

    def gray(ax, M, title):
        ax.imshow(M, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        ax.set_title(title, fontsize=10)
        ax.set_xticks(range(0, 8, 2)); ax.set_yticks(range(0, 8, 2))
        ax.tick_params(labelsize=10)
        for s in ax.spines.values():
            s.set_linewidth(lw)

    def coef(ax, M, title):
        absM = np.abs(M)
        ax.imshow(np.log10(1 + absM), cmap="Greys", vmin=0, vmax=np.log10(1 + np.abs(F).max()),
                  interpolation="nearest")
        for i in range(8):
            for j in range(8):
                if M[i, j] != 0:
                    val = np.log10(1 + absM[i, j]) / np.log10(1 + np.abs(F).max())
                    ax.text(j, i, f"{int(M[i, j])}", ha="center", va="center", fontsize=10,
                            color="white" if val > 0.5 else "black")
        ax.set_title(title, fontsize=10)
        ax.set_xticks(range(0, 8, 2)); ax.set_yticks(range(0, 8, 2))
        ax.tick_params(labelsize=10)
        for s in ax.spines.values():
            s.set_linewidth(lw)

    gray(axs[0, 0], blk, "(a) Khối Y gốc 8×8")
    ax = axs[0, 1]
    ax.imshow(np.log10(1 + np.abs(F)), cmap="Greys", interpolation="nearest")
    ax.set_title("(b) Hệ số DCT, log₁₀(1+|F|)", fontsize=10)
    ax.set_xticks(range(0, 8, 2)); ax.set_yticks(range(0, 8, 2)); ax.tick_params(labelsize=10)
    ax.set_xlabel("tần số ngang v", fontsize=10); ax.set_ylabel("tần số dọc u", fontsize=10)
    for s_ in ax.spines.values():
        s_.set_linewidth(lw)
    coef(axs[1, 0], r50["Fq"], f"(c) Lượng tử hoá q=50 ({r50['nz']} hệ số ≠ 0)")
    gray(axs[1, 1], r50["rec"], f"(d) Khôi phục q=50, PSNR={r50['psnr']:.1f} dB")
    coef(axs[2, 0], r90["Fq"], f"(e) Lượng tử hoá q=90 ({r90['nz']} hệ số ≠ 0)")
    gray(axs[2, 1], r90["rec"], f"(f) Khôi phục q=90, PSNR={r90['psnr']:.1f} dB")
    fig.tight_layout(h_pad=0.8, w_pad=0.5)
    fig.savefig(os.path.join(fig_dir, "dct_example.png"), dpi=300)
    plt.close(fig)

    # ======================= HÌNH: jpeg_qtable_scale.png ====================
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ax.plot(qs[Ss > 0], Ss[Ss > 0], color="black", lw=2.2, label="Hệ số tỉ lệ S")
    ax.axvline(50, color="black", ls="--", lw=1.8)
    ax.axhline(100, color="black", ls=":", lw=1.8)
    pos = {50: (56, 300), 75: (53, 24), 90: (57, 8)}
    for qq in (50, 75, 90):
        ax.plot(qq, ijg_scale(qq), "o", color="black", ms=7)
        ax.annotate(f"q={qq}, S={ijg_scale(qq)}", (qq, ijg_scale(qq)), xytext=pos[qq],
                    fontsize=10, va="center", arrowprops=dict(arrowstyle="-", lw=1.5, shrinkA=2, shrinkB=4))
    ax.set_yscale("log")
    ax.set_xlabel("Chất lượng quality q (1–100)", fontsize=10)
    ax.set_ylabel("Hệ số tỉ lệ S (%) – thang log", fontsize=10)
    ax.set_xlim(0, 101)
    ax.set_ylim(1.2, 9000)
    ax.grid(True, which="both", color="0.85", lw=0.8)
    ax.tick_params(labelsize=10)
    for s in ax.spines.values():
        s.set_linewidth(1.5)
    ax.text(52, 4500, "q<50: S=5000/q", fontsize=10, ha="left", va="center")
    ax.text(52, 2300, "q≥50: S=200−2q", fontsize=10, ha="left", va="center")
    ax.text(98, 2.0, "q=100: S=0", fontsize=10, ha="right", va="center")
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "jpeg_qtable_scale.png"), dpi=300)
    plt.close(fig)
    draw_pipeline(fig_dir)


if __name__ == "__main__":
    main()
