# Thời gian nén/giải nén, tác động tới trang web và chương trình demo (t10)

## 1. Mục tiêu

Phần này đo **chi phí tính toán** của việc nén: thời gian mã hoá (xảy ra một lần, ở máy chủ khi tải ảnh lên) và thời gian giải mã (xảy ra ở mỗi lượt xem, trên thiết bị người dùng), quy đổi thông lượng megapixel/giây, rồi đặt các con số đó cạnh thời gian truyền qua mạng để xem yếu tố nào thực sự quyết định tốc độ trang danh mục 40 ảnh. Phần cuối mô tả chương trình demo trực tiếp `src/demo.py`.

## 2. Phương pháp và tham số

Tám cấu hình, mã hoá/giải mã hoàn toàn trong bộ nhớ bằng Pillow (cùng hàm `encode/decode` của `common.py`) trên cả 20 ảnh:

| Cấu hình | Tham số Pillow | Lý do |
|---|---|---|
| JPEG q50 / q75 / q90 | `quality=q` (4:2:0 mặc định, không `optimize`) | Ba mức baseline của đề bài |
| PNG L9 | `compress_level=9` | Mức nén tối đa của zlib: cận trên chi phí mã hoá của PNG |
| WebP q50 / q75 / q90 | `quality=q, method=4` | `method=4` là mặc định của libwebp (thang 0–6), cân bằng tốc độ và hiệu quả |
| WebP lossless | `lossless=True, quality=100, method=4` | Với WebP không mất mát, `quality` là mức nỗ lực nén (100 = tối đa), không phải độ trung thực |

Mỗi cặp (ảnh, cấu hình) được chạy **1 lần khởi động và bỏ đi** (nạp thư viện, làm nóng cache, cấp phát bộ nhớ lần đầu), sau đó đo **9 lần** và lấy **trung vị** (`common.time_ms`): trung vị bền vững trước các lần đo bị tiến trình khác chen vào, và số lần lẻ cho một giá trị đo thực. Thông lượng gộp = tổng megapixel / tổng thời gian. Thời gian giải mã gồm cả `load()` và đổi sang RGB như một trình xem ảnh. Bên cạnh thời gian tường còn ghi thời gian CPU của tiến trình (`time.process_time`, cùng các lần chạy) để đối chiếu độ nhiễu. Máy đo: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel, 12 lõi, Pillow 12.3.0 (libjpeg-turbo 3.1.4.1, libwebp 1.6.0, zlib 1.3.1.zlib-ng).

**Lưu ý độ tin cậy.** Windows không cung cấp load average, nên độ bận của máy được đánh giá bằng phép đo tham chiếu JPEG q75: IQR/trung vị 12% trước và 20% sau; tổng thời gian tường mã hoá / CPU = 1.01. Chạy lại khi máy rảnh nếu IQR lớn hoặc tỉ số wall/CPU xa 1.

## 3. Kết quả đo

**Bảng 1.** Thời gian mã hoá và giải mã (trung vị, ms/ảnh) theo nhóm: P = ảnh chụp nhiều chi tiết (7 ảnh, 500 px), T = ảnh có chữ (3 ảnh 500 px + 4 ảnh 1000 px), G = gradient/nền trơn (3 + 3 ảnh).

| Cấu hình | Mã hoá P | Mã hoá T | Mã hoá G | Giải mã P | Giải mã T | Giải mã G |
|---|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 1.92 | 7.53 | 2.04 | 2.27 | 8.99 | 2.54 |
| JPEG q75 | 2.32 | 7.24 | 1.67 | 2.50 | 8.83 | 2.41 |
| JPEG q90 | 2.47 | 6.92 | 2.08 | 2.77 | 9.27 | 3.64 |
| PNG L9 | 190.8 | 158.6 | 202.7 | 12.7 | 13.3 | 8.75 |
| WebP q50 | 76.9 | 197.3 | 107.0 | 11.4 | 27.4 | 15.7 |
| WebP q75 | 82.0 | 202.3 | 109.6 | 11.8 | 28.9 | 14.8 |
| WebP q90 | 92.0 | 210.4 | 100.8 | 13.3 | 30.2 | 13.7 |
| WebP lossless | 707.0 | 671.5 | 506.8 | 17.4 | 29.4 | 17.9 |

**Bảng 2.** Theo kích thước ảnh (trung vị ms/ảnh; 13 ảnh 500 px, 7 ảnh 1000 px) và thông lượng gộp trên cả 20 ảnh (megapixel/giây).

| Cấu hình | Mã hoá 500 px | Mã hoá 1000 px | Mã hoá MP/s | Giải mã 500 px | Giải mã 1000 px | Giải mã MP/s |
|---|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 2.14 | 7.55 | 139.5 | 2.10 | 9.05 | 120.7 |
| JPEG q75 | 2.09 | 7.33 | 143.0 | 2.28 | 8.88 | 113.2 |
| JPEG q90 | 2.42 | 6.92 | 140.2 | 2.68 | 9.27 | 107.7 |
| PNG L9 | 151.0 | 190.5 | 2.79 | 10.3 | 15.9 | 46.8 |
| WebP q50 | 71.5 | 197.3 | 4.68 | 10.0 | 27.4 | 31.9 |
| WebP q75 | 73.7 | 202.3 | 4.46 | 11.1 | 28.9 | 30.8 |
| WebP q90 | 78.7 | 219.4 | 4.05 | 12.0 | 30.2 | 29.8 |
| WebP lossless | 468.1 | 698.8 | 0.88 | 13.2 | 29.4 | 27.8 |

Hình: `figures/t10/enc_dec_time.png` — (a) thời gian mã hoá và (b) thời gian giải mã (ms, thang log) của 8 cấu hình theo ba nhóm ảnh P, T, G.

Trên trung vị cả 20 ảnh (thời gian tường), mã hoá PNG L9 chậm hơn JPEG q75 khoảng 77.5 lần (176.0 so với 2.27 ms); WebP q75 chậm hơn JPEG q75 khoảng 36.4 lần (82.7 ms); WebP lossless là cấu hình chậm nhất (655.1 ms, chậm hơn PNG L9 3.7 lần). Theo thời gian CPU, các tỉ số tương ứng là 74.1, 33.7 và 3.5 lần. Ở phía giải mã, mọi cấu hình đều nhanh: tối đa 17.6 ms/ảnh (trung vị toàn bộ), JPEG q75 2.74 ms, WebP q75 12.4 ms (4.5 lần JPEG), PNG L9 12.3 ms; chênh lệch giữa các codec nhỏ hơn rất nhiều so với phía mã hoá.

## 4. Giải thích cơ chế

**JPEG mã hoá nhanh nhất** vì mọi bước là phép tính cố định trên từng khối 8×8: đổi màu sang YCbCr, giảm mẫu sắc độ (4:2:0), DCT, lượng tử hoá bằng bảng cố định theo quality và mã hoá Huffman. Không có vòng lặp tìm kiếm, và libjpeg-turbo viết bằng SIMD cho các bước nặng nên đạt hàng trăm MP/s (thông lượng gộp 143.0 MP/s ở q75); đổi quality chỉ đổi bảng lượng tử nên thời gian ít đổi (2.44 ms ở q50 và 2.46 ms ở q90).

**WebP lossy mã hoá chậm hơn JPEG** vì bộ mã hoá VP8 phải *quyết định* nhiều hơn: với mỗi macroblock 16×16 nó thử các chế độ dự đoán nội ảnh (intra 16×16, intra 4×4, chế độ cho sắc độ), chọn chế độ theo hàm chi phí tỉ lệ–méo (RDO), nghĩa là phải biến đổi, lượng tử và tái dựng từng ứng viên; sau đó dùng bộ mã hoá số học nhị phân thích nghi theo ngữ cảnh (chậm hơn Huffman tĩnh vì từng bit đi qua mô hình xác suất) và bộ lọc khử khối trong vòng lặp. Đổi lại dung lượng nhỏ hơn (trung bình 21.7 KB/ảnh ở q75 so với 40.1 KB của JPEG q75; hai mức q không tương đương về chất lượng). `method` càng cao thì thử càng nhiều ứng viên; q cao hơn có nhiều hệ số khác không hơn nên thời gian cũng tăng (77.8 ms ở q50, 94.6 ms ở q90).

**PNG L9 chậm do tìm kiếm LZ77.** PNG trước hết áp bộ lọc dự đoán theo từng hàng rồi nén bằng deflate; ở mức 9 zlib duyệt chuỗi băm rất dài và so khớp “lười” (lazy matching) để tìm chuỗi lặp dài nhất, tức là đánh đổi thời gian lấy vài phần trăm dung lượng. Chi phí phụ thuộc vào số vị trí phải thử chứ không chỉ vào số điểm ảnh. Lưu ý bản Pillow đo ở đây liên kết với zlib-ng, có chiến lược cho từng mức khác zlib cổ điển, nên con số tuyệt đối có thể khác trên môi trường dùng zlib chuẩn.

**WebP lossless chậm nhất khi mã hoá, nhưng gọn hơn PNG.** Nó kết hợp biến đổi dự đoán theo ô, biến đổi tương quan màu, trừ kênh lục, LZ77 với bộ nhớ đệm màu và nhiều bảng Huffman theo vùng; ở `quality=100` bộ mã hoá thử nhiều tổ hợp tham số để chọn cái tốt nhất. Kết quả: dung lượng trung bình 198.6 KB/ảnh so với 258.8 KB của PNG L9, nhưng thời gian mã hoá cao hơn.

**Giải mã cả ba đều nhanh** vì giải mã không phải tìm kiếm: JPEG chỉ giải Huffman rồi IDCT (SIMD); WebP lossy giải số học, dựng lại dự đoán nội ảnh từ các khối lân cận (phụ thuộc tuần tự, khó SIMD hơn) và lọc khử khối nên thường chậm hơn JPEG vài lần; PNG chỉ inflate rồi đảo bộ lọc, thời gian tỉ lệ với lượng dữ liệu phải giải nén, và WebP lossless giải Huffman/LZ77 rồi đảo các phép biến đổi. Tỉ số thời gian mã hoá/giải mã (trung vị toàn bộ) là 0.8 với JPEG q75, 6.7 với WebP q75, 14.3 với PNG L9 và 37.2 với WebP lossless: nén có tìm kiếm (PNG L9, WebP) bất đối xứng mạnh, mã hoá tốn hơn giải mã nhiều lần.

## 5. Ý nghĩa đối với website

Quy trình thực tế là **mã hoá một lần ở máy chủ** (khi tải ảnh lên hoặc trong bước build), còn **giải mã ở mỗi lượt xem**. Vì vậy chi phí mã hoá được chia cho mọi lượt xem, còn thời gian giải mã cộng thẳng vào độ trễ người dùng, nhưng so với thời gian truyền qua mạng thì chỉ chiếm phần nhỏ. Ước tính trang danh mục 40 ảnh (dung lượng bằng trung bình 20 ảnh của bộ dữ liệu; thời gian = tổng KB×8/băng thông + 40 × thời gian giải mã trung bình; tải tuần tự, bỏ qua độ trễ TCP/TLS):

**Bảng 3.** Thời gian tải trang 40 ảnh (s).

| Cấu hình | KB/ảnh | 4G: truyền | 4G: giải mã | 4G: tổng | 3G: truyền | 3G: tổng |
|---|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 29.2 | 0.96 | 0.17 | 1.13 | 4.78 | 4.95 |
| JPEG q75 | 40.1 | 1.31 | 0.18 | 1.49 | 6.56 | 6.75 |
| JPEG q90 | 63.0 | 2.06 | 0.19 | 2.25 | 10.3 | 10.5 |
| PNG L9 | 258.8 | 8.48 | 0.44 | 8.92 | 42.4 | 42.8 |
| WebP q50 | 16.9 | 0.56 | 0.64 | 1.20 | 2.78 | 3.42 |
| WebP q75 | 21.7 | 0.71 | 0.67 | 1.38 | 3.56 | 4.22 |
| WebP q90 | 38.6 | 1.26 | 0.69 | 1.95 | 6.32 | 7.01 |
| WebP lossless | 198.6 | 6.51 | 0.74 | 7.25 | 32.5 | 33.3 |

Hình: `figures/t10/page_load.png` — thời gian tải trang 40 ảnh (cột xếp chồng: truyền + giải mã) trên (a) 4G 10 Mbit/s và (b) 3G 2 Mbit/s.

Truyền 1 KB mất 0.82 ms trên 4G và 4.10 ms trên 3G, nên 1 ms giải mã chỉ đáng bằng 1.22 KB (4G) hoặc 0.24 KB (3G) dung lượng. Thời gian giải mã chiếm tối đa 54% tổng thời gian trên 4G (cấu hình WebP q50) và 19% trên 3G (cấu hình WebP q50); trên 3G thời gian truyền chiếm ưu thế ở mọi cấu hình, còn trên 4G các cấu hình rất nhẹ (WebP) có phần giải mã đáng kể, nên mạng càng nhanh thì chi phí giải mã càng đáng cân nhắc. Ví dụ so sánh danh nghĩa WebP q75 với JPEG q75: dung lượng chênh 18.3 KB/ảnh, tương ứng 15.0 ms (4G) hoặc 75.1 ms (3G) truyền, trong khi giải mã tốn thêm 9.66 ms/ảnh; chênh lệch ròng là 5.36 ms/ảnh trên 4G và 65.5 ms/ảnh trên 3G (dương = WebP có lợi). Cần nhớ q75 của hai codec không cho cùng chất lượng; so sánh công bằng theo PSNR/SSIM nằm ở các phần đánh giá chất lượng của báo cáo. Ngược lại, PNG L9 và WebP lossless nặng gấp 6.5 và 5.0 lần JPEG q75 (tải trang 8.92 s và 7.25 s trên 4G; 42.8 s và 33.3 s trên 3G), nên chỉ phù hợp cho ảnh phải giữ nguyên từng điểm ảnh.

**Bảng 4.** Chi phí mã hoá 10.000 ảnh, một luồng (lõi-phút; chia cho số lõi khi chạy song song).

| Cấu hình | ms/ảnh (trung bình 20 ảnh) | Lõi-phút, ảnh trộn | Lõi-phút, ảnh 500 px | Lõi-phút, ảnh 1000 px |
|---|---:|---:|---:|---:|
| JPEG q50 | 3.67 | 0.61 | 0.34 | 1.12 |
| JPEG q75 | 3.58 | 0.60 | 0.34 | 1.08 |
| JPEG q90 | 3.66 | 0.61 | 0.37 | 1.05 |
| PNG L9 | 183.4 | 30.6 | 28.3 | 34.7 |
| WebP q50 | 109.4 | 18.2 | 11.1 | 31.6 |
| WebP q75 | 115.0 | 19.2 | 11.9 | 32.7 |
| WebP q90 | 126.6 | 21.1 | 13.6 | 35.1 |
| WebP lossless | 584.6 | 97.4 | 86.6 | 117.5 |

Mã hoá hàng loạt 10.000 ảnh bằng WebP q75 tốn khoảng 19.2 lõi-phút, bằng JPEG q75 khoảng 0.60 lõi-phút, còn cấu hình tốn nhất (WebP lossless) khoảng 1.62 lõi-giờ. Đó là chi phí một lần, song song hoá dễ dàng theo ảnh; so với việc phục vụ hàng triệu lượt xem, phần chênh lệch chi phí mã hoá của WebP là không đáng kể và được bù bằng dung lượng truyền giảm ở mỗi lượt xem. Mã hoá chậm chỉ thành vấn đề khi phải nén theo yêu cầu (on the fly) cho từng lượt truy cập, khi đó nên dùng mức nỗ lực thấp hơn hoặc lưu đệm kết quả.

## 6. Chương trình demo (`src/demo.py`)

Demo chạy cục bộ, nhận đường dẫn ảnh bất kỳ làm tham số dòng lệnh (mặc định `data/images/T01_card1000.png`) và mở cửa sổ matplotlib tương tác gồm: ảnh gốc và ảnh sau nén–giải nén cạnh nhau; **Slider Quality (5–100)**; **RadioButtons** chọn codec (JPEG 4:2:0, JPEG 4:4:4, WebP, PNG, WebP lossless); bảng số liệu gồm KB, bpp, tỉ lệ nén, PSNR, SSIM của cả ảnh, PSNR cục bộ của vùng chọn, thời gian mã hoá/giải mã; và hai ô **phóng to** (gốc và nén) quanh tâm do người dùng **click/kéo chuột** chọn trên ảnh (phím +/− đổi cỡ vùng). Tâm mặc định được chọn tự động tại vùng có gradient lớn nhất để lỗi nén hiện rõ ngay. Slider bị khoá với PNG và WebP lossless vì hai codec này không mất mát. Chế độ `--save out.png` chạy không giao diện (backend Agg), lưu ảnh chụp giao diện và in chỉ số ra màn hình, dùng để kiểm thử trong môi trường không có màn hình:

```
python src/demo.py                                    # cửa sổ tương tác
python src/demo.py anh.jpg --codec WebP --quality 40   # chọn trạng thái ban đầu
python src/demo.py --save out.png --codec "JPEG 4:2:0" --quality 30 --center 480 300
```

Hình: `figures/t10/demo_headless.png` — ảnh chụp giao diện demo ở chế độ không giao diện (ảnh T01, WebP quality 30; hình này được sinh khi kiểm thử demo, không do `t10_timing.py` tạo ra). Đây là công cụ minh hoạ: kéo slider xuống thấp trên ảnh có chữ sẽ thấy ngay vết nhoè quanh nét chữ và lỗi khối ở JPEG.

## 7. Hạn chế

- Đo trên một máy chủ (Xeon, không GPU, Pillow đơn luồng), không phải điện thoại; thiết bị yếu có thể giải mã chậm hơn vài lần nên phần giải mã trong Bảng 3 là cận dưới đối với thiết bị di động. Mức độ chậm đi chưa được đo.
- Mô hình tải trang đơn giản: tải tuần tự, bỏ qua RTT, TLS, HTTP/2 song song, tải lười và hiển thị lũy tiến; ảnh trong bộ dữ liệu (500/1000 px) lớn hơn thumbnail danh mục thông thường, nên số giây chỉ để so sánh tương đối giữa các cấu hình.
- Thời gian JPEG chỉ vài mili-giây nên rất nhạy với nhiễu hệ thống; các tỉ số giữa 500 px và 1000 px lẫn ảnh hưởng của nội dung (ảnh 1000 px chỉ thuộc nhóm T, G) và của nhiễu, không nên suy ra quy luật tỉ lệ diện tích từ bảng này.
- Kết quả PNG phụ thuộc bản zlib (ở đây là zlib-ng) và bộ lọc dòng mà Pillow chọn; kết quả WebP phụ thuộc `method` (chỉ đo `method=4`). Chất lượng ảnh (PSNR/SSIM) không đo ở phần này.
