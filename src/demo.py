"""Demo trực tiếp: nén ảnh với JPEG / WebP / PNG và xem ngay chất lượng, dung lượng, thời gian.

CÁCH DÙNG
    # Cửa sổ tương tác (cần màn hình / backend có GUI, ví dụ TkAgg, QtAgg, MacOSX):
    python src/demo.py                          # ảnh mặc định data/images/T01_card1000.png
    python src/demo.py duong/dan/anh_bat_ky.jpg # ảnh bất kỳ Pillow đọc được
    # Không giao diện (kiểm thử, backend Agg): ghi thẳng một hình PNG rồi thoát
    python src/demo.py data/images/P01_coffee.png --save out.png --codec "WebP" --quality 40 \
        --center 250 250 --zoom-size 48

GIAO DIỆN
    - Hai ô lớn: ảnh gốc (trái) và ảnh sau nén-giải nén (phải).
    - Slider "Quality" 5-100 (không có tác dụng với PNG và WebP lossless vì chúng không mất mát;
      khi đó slider bị khoá).
    - RadioButtons chọn codec: JPEG 4:2:0, JPEG 4:4:4, WebP, PNG, WebP lossless.
    - Click chuột (hoặc nhấn giữ và kéo) lên một trong hai ảnh lớn để chọn TÂM vùng phóng to;
      hai ô bên phải hiển thị vùng đó của ảnh gốc và ảnh nén (nội suy 'nearest' để thấy rõ
      từng điểm ảnh, lỗi khối 8x8 của JPEG, vết nhoè của WebP...). Phím '+' / '-' đổi kích
      thước vùng phóng to.
    - Bảng số liệu: dung lượng KB, bpp, tỉ lệ nén so với RGB thô, PSNR, SSIM (toàn ảnh, định
      nghĩa của common.py), PSNR cục bộ của vùng phóng to, thời gian mã hoá và giải mã (ms).

THAM SỐ CODEC (đồng nhất với các thí nghiệm khác, dùng common.encode/decode/psnr/ssim)
    JPEG 4:2:0 : quality=q, subsampling=2 (mặc định của libjpeg: chroma giảm một nửa mỗi chiều)
    JPEG 4:4:4 : quality=q, subsampling=0 (giữ nguyên độ phân giải màu; tốt cho chữ màu/cạnh)
    WebP       : quality=q, method=4
    PNG        : compress_level=9 (không mất mát)
    WebP lossless: lossless=True, quality=100, method=4 (không mất mát)
Thời gian mã hoá/giải mã là trung vị của 3 lần chạy (đủ để thấy xu hướng khi tương tác;
phép đo chính xác nằm ở src/t10_timing.py).
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import IMG_DIR, decode, encode, psnr, ssim, time_ms  # noqa: E402

import matplotlib  # noqa: E402

CODECS = {
    "JPEG 4:2:0": ("JPEG", lambda q: dict(quality=q, subsampling=2), True),
    "JPEG 4:4:4": ("JPEG", lambda q: dict(quality=q, subsampling=0), True),
    "WebP": ("WEBP", lambda q: dict(quality=q, method=4), True),
    "PNG": ("PNG", lambda q: dict(compress_level=9), False),
    "WebP lossless": ("WEBP", lambda q: dict(lossless=True, quality=100, method=4), False),
}
CODEC_LIST = list(CODECS)
DEFAULT_IMAGE = os.path.join(IMG_DIR, "T01_card1000.png")


def compress_eval(img, ref, codec, q, timing_repeats=3):
    """Nén + giải nén + đo chỉ số. Trả về dict gồm cả ảnh sau giải nén (mảng uint8)."""
    fmt, mk, uses_q = CODECS[codec]
    params = mk(q)
    data = encode(img, fmt, **params)
    rec = decode(data)
    out = np.asarray(rec)
    W, H = img.size
    return {
        "codec": codec, "quality": q if uses_q else None, "size_kb": len(data) / 1024,
        "bpp": 8 * len(data) / (W * H), "ratio": (W * H * 3) / len(data),
        "psnr": psnr(ref, out), "ssim": ssim(ref, out), "rec": out,
        "enc_ms": time_ms(lambda: encode(img, fmt, **params), timing_repeats),
        "dec_ms": time_ms(lambda: decode(data), timing_repeats),
    }


def auto_center(ref, size):
    """Tâm vùng size×size có độ biến thiên (độ lớn gradient) lớn nhất: nơi nén lộ lỗi rõ nhất
    (cạnh chữ, viền vật thể). Dùng làm tâm phóng to mặc định thay vì giữa ảnh (thường là nền trơn)."""
    g = ref.astype(np.float64).mean(axis=2)
    mag = np.abs(np.diff(g, axis=0, prepend=g[:1]))[:, :] + np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    ii = np.cumsum(np.cumsum(np.pad(mag, ((1, 0), (1, 0))), axis=0), axis=1)   # ảnh tích phân
    s = min(size, *g.shape)
    box = ii[s:, s:] - ii[:-s, s:] - ii[s:, :-s] + ii[:-s, :-s]
    y, x = np.unravel_index(np.argmax(box), box.shape)
    return int(x + s // 2), int(y + s // 2)


def fmt_psnr(v):
    return "∞ (không mất mát)" if np.isinf(v) else f"{v:.2f} dB"


class Demo:
    def __init__(self, img, name, codec="JPEG 4:2:0", quality=75, center=None, zoom=48):
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        from matplotlib.widgets import RadioButtons, Slider
        plt.rcParams["font.family"] = "DejaVu Sans"
        self.plt = plt
        self.img, self.name = img, name
        self.ref = np.asarray(img)
        self.W, self.H = img.size
        self.codec, self.q = codec, int(quality)
        self.zoom = int(max(8, min(zoom, min(self.W, self.H))))
        self.cx, self.cy = center if center else auto_center(self.ref, self.zoom)
        self.cache = {}
        self.res = None

        self.fig = plt.figure(figsize=(14, 8.4))
        self.fig.canvas.manager.set_window_title(f"Demo nén ảnh — {name}") \
            if getattr(self.fig.canvas, "manager", None) else None
        self.ax_o = self.fig.add_axes([0.03, 0.34, 0.36, 0.60])
        self.ax_c = self.fig.add_axes([0.40, 0.34, 0.36, 0.60])
        self.ax_zo = self.fig.add_axes([0.80, 0.64, 0.17, 0.30])
        self.ax_zc = self.fig.add_axes([0.80, 0.34, 0.17, 0.26])
        self.ax_sl = self.fig.add_axes([0.12, 0.255, 0.45, 0.03])
        self.ax_rb = self.fig.add_axes([0.03, 0.02, 0.16, 0.20])
        self.ax_tx = self.fig.add_axes([0.22, 0.02, 0.55, 0.20])
        self.ax_hp = self.fig.add_axes([0.79, 0.02, 0.20, 0.25])
        for ax in (self.ax_tx, self.ax_hp):
            ax.axis("off")

        self.im_o = self.ax_o.imshow(self.ref)
        self.ax_o.set_title(f"Ảnh gốc ({self.W}×{self.H})", fontsize=11)
        self.im_c = self.ax_c.imshow(self.ref)
        for ax in (self.ax_o, self.ax_c):
            ax.set_xticks([])
            ax.set_yticks([])
        self.rect_o = Rectangle((0, 0), 1, 1, fill=False, ec="red", lw=1.6)
        self.rect_c = Rectangle((0, 0), 1, 1, fill=False, ec="red", lw=1.6)
        self.ax_o.add_patch(self.rect_o)
        self.ax_c.add_patch(self.rect_c)
        self.im_zo = self.ax_zo.imshow(self.ref[:2, :2], interpolation="nearest")
        self.im_zc = self.ax_zc.imshow(self.ref[:2, :2], interpolation="nearest")
        for ax in (self.ax_zo, self.ax_zc):
            ax.set_xticks([])
            ax.set_yticks([])

        self.slider = Slider(self.ax_sl, "Quality", 5, 100, valinit=self.q, valstep=1)
        self.radio = RadioButtons(self.ax_rb, CODEC_LIST, active=CODEC_LIST.index(codec))
        try:
            self.radio.set_label_props({"fontsize": [11] * len(CODEC_LIST)})
        except Exception:
            pass
        self.ax_rb.set_title("Codec", fontsize=11, loc="left")
        self.txt = self.ax_tx.text(0.0, 1.0, "", va="top", ha="left", fontsize=11.5,
                                   family="DejaVu Sans Mono")
        self.ax_hp.text(0.0, 1.0,
                        "Hướng dẫn\n• Click / kéo chuột trên ảnh\n  lớn: chọn tâm vùng phóng to\n"
                        "• Slider: quality 5–100\n  (khoá với PNG, WebP lossless)\n"
                        "• Phím + / −: đổi cỡ vùng phóng to",
                        va="top", ha="left", fontsize=10.5)

        self.slider.on_changed(self._on_quality)
        self.radio.on_clicked(self._on_codec)
        self.fig.canvas.mpl_connect("button_press_event", self._on_mouse)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_mouse)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)
        self.refresh_codec()

    # ---- tính toán ----
    def _uses_q(self):
        return CODECS[self.codec][2]

    def refresh_codec(self):
        key = (self.codec, self.q if self._uses_q() else None)
        if key not in self.cache:
            self.cache[key] = compress_eval(self.img, self.ref, self.codec, self.q)
        self.res = self.cache[key]
        self.slider.set_active(self._uses_q())
        self.slider.poly.set_alpha(1.0 if self._uses_q() else 0.25)
        self.im_c.set_data(self.res["rec"])
        lab = self.codec + (f", quality {self.q}" if self._uses_q() else "")
        self.ax_c.set_title(f"Ảnh nén: {lab}", fontsize=11)
        self.refresh_zoom(draw=False)
        self.draw()

    def _region(self):
        s = self.zoom
        x0 = int(min(max(self.cx - s // 2, 0), self.W - s))
        y0 = int(min(max(self.cy - s // 2, 0), self.H - s))
        return x0, y0, s

    def refresh_zoom(self, draw=True):
        x0, y0, s = self._region()
        sl = (slice(y0, y0 + s), slice(x0, x0 + s))
        self.im_zo.set_data(self.ref[sl])
        self.im_zc.set_data(self.res["rec"][sl])
        for im in (self.im_zo, self.im_zc):
            im.set_extent((-0.5, s - 0.5, s - 0.5, -0.5))
        for ax in (self.ax_zo, self.ax_zc):
            ax.set_xlim(-0.5, s - 0.5)
            ax.set_ylim(s - 0.5, -0.5)
        self.rect_o.set_bounds(x0 - 0.5, y0 - 0.5, s, s)
        self.rect_c.set_bounds(x0 - 0.5, y0 - 0.5, s, s)
        local = psnr(self.ref[sl], self.res["rec"][sl])
        self.ax_zo.set_title(f"Phóng to: gốc\n({s}×{s} px)", fontsize=10)
        self.ax_zc.set_title("Phóng to: nén\nPSNR vùng " + ("∞" if np.isinf(local) else f"{local:.1f} dB"),
                             fontsize=10)
        self._local_psnr = local
        self._update_text()
        if draw:
            self.draw()

    def _update_text(self):
        r = self.res
        qs = f"{r['quality']}" if r["quality"] is not None else "không áp dụng"
        self.txt.set_text(
            f"Codec         : {r['codec']}   (quality: {qs})\n"
            f"Dung lượng    : {r['size_kb']:.1f} KB   |   {r['bpp']:.3f} bpp   |   "
            f"nén {r['ratio']:.1f}× so với RGB thô\n"
            f"PSNR (cả ảnh) : {fmt_psnr(r['psnr'])}\n"
            f"SSIM (cả ảnh) : {r['ssim']:.4f}\n"
            f"Thời gian     : mã hoá {r['enc_ms']:.1f} ms   |   giải mã {r['dec_ms']:.1f} ms\n"
            f"Tâm vùng zoom : ({self.cx}, {self.cy})   |   PSNR vùng: {fmt_psnr(self._local_psnr)}")

    def draw(self):
        self.fig.canvas.draw_idle()

    # ---- sự kiện ----
    def _on_quality(self, val):
        self.q = int(val)
        self.refresh_codec()

    def _on_codec(self, label):
        self.codec = label
        self.refresh_codec()

    def _on_mouse(self, event):
        if event.inaxes not in (self.ax_o, self.ax_c) or event.xdata is None:
            return
        if event.name == "motion_notify_event" and event.button != 1:
            return
        self.cx = int(np.clip(round(event.xdata), 0, self.W - 1))
        self.cy = int(np.clip(round(event.ydata), 0, self.H - 1))
        self.refresh_zoom()

    def _on_key(self, event):
        if event.key in ("+", "="):
            self.zoom = int(min(min(self.W, self.H), self.zoom * 1.25 + 1))
        elif event.key in ("-", "_"):
            self.zoom = int(max(8, self.zoom / 1.25))
        else:
            return
        self.refresh_zoom()

    # ---- đặt trạng thái bằng mã (dùng cho --save) ----
    def set_state(self, codec, quality):
        self.codec, self.q = codec, int(quality)
        self.radio.eventson = False
        self.radio.set_active(CODEC_LIST.index(codec))
        self.radio.eventson = True
        self.slider.eventson = False
        self.slider.set_val(self.q)
        self.slider.eventson = True
        self.refresh_codec()


def parse_args():
    ap = argparse.ArgumentParser(description="Demo tương tác so sánh nén ảnh JPEG / WebP / PNG.")
    ap.add_argument("image", nargs="?", default=DEFAULT_IMAGE,
                    help="đường dẫn ảnh (mặc định: data/images/T01_card1000.png)")
    ap.add_argument("--codec", choices=CODEC_LIST, default="JPEG 4:2:0", help="codec ban đầu")
    ap.add_argument("--quality", type=int, default=75, help="quality ban đầu (5-100)")
    ap.add_argument("--center", type=int, nargs=2, metavar=("X", "Y"), default=None,
                    help="tâm vùng phóng to ban đầu (mặc định: vùng nhiều chi tiết nhất)")
    ap.add_argument("--zoom-size", type=int, default=48, help="cạnh vùng phóng to, điểm ảnh (mặc định 48)")
    ap.add_argument("--save", metavar="OUT.png", default=None,
                    help="chạy không giao diện (Agg), lưu hình giao diện ra file rồi thoát")
    ap.add_argument("--dpi", type=int, default=120, help="dpi khi --save (mặc định 120)")
    a = ap.parse_args()
    if not 5 <= a.quality <= 100:
        ap.error("--quality phải nằm trong [5, 100]")
    return a


def main():
    a = parse_args()
    if a.save:
        matplotlib.use("Agg")
    if not os.path.isfile(a.image):
        sys.exit(f"Không tìm thấy ảnh: {a.image}")
    img = Image.open(a.image).convert("RGB")
    img.load()
    demo = Demo(img, os.path.basename(a.image), a.codec, a.quality, tuple(a.center) if a.center else None,
                a.zoom_size)
    if a.save:
        demo.fig.savefig(a.save, dpi=a.dpi)
        r = demo.res
        print(f"[headless] {demo.name} | {r['codec']} q={r['quality']} | {r['size_kb']:.2f} KB | "
              f"{r['bpp']:.3f} bpp | PSNR {r['psnr']:.2f} dB | SSIM {r['ssim']:.4f} | "
              f"enc {r['enc_ms']:.1f} ms | dec {r['dec_ms']:.1f} ms -> {a.save}")
        return
    if matplotlib.get_backend().lower() == "agg":
        sys.exit("Không có backend giao diện (đang là Agg). Dùng --save out.png để chạy không giao diện, "
                 "hoặc cài tkinter/PyQt và chạy trên máy có màn hình.")
    demo.plt.show()


if __name__ == "__main__":
    main()
