#!/usr/bin/env bash
# Chạy toàn bộ pipeline: tạo dữ liệu rồi lần lượt mọi script src/t01_*.py ... src/t10_*.py.
# Dùng glob nên không phụ thuộc tên cụ thể của từng task. Các script chạy TUẦN TỰ (không song song)
# để các phép đo thời gian (t08, t10) không bị nhiễu bởi tác vụ khác. Hãy để máy rảnh khi chạy.
#   ./run_all.sh                 # tạo lại dữ liệu (seed 2026) rồi chạy t01..t10
#   SKIP_DATASET=1 ./run_all.sh  # giữ nguyên data/ hiện có
set -u
cd "$(dirname "$0")"
PY="${PYTHON:-python}"
failed=()
if [ "${SKIP_DATASET:-0}" != "1" ]; then
  echo "=== make_dataset ==="
  "$PY" src/make_dataset.py || { echo "make_dataset THẤT BẠI" >&2; exit 1; }
fi
for f in src/t[0-9][0-9]_*.py; do
  [ -e "$f" ] || continue
  echo "=== $f ==="
  "$PY" "$f" || failed+=("$f")
done
if [ "${#failed[@]}" -gt 0 ]; then
  echo "Các script lỗi: ${failed[*]}" >&2
  exit 1
fi
echo "Hoàn tất: mọi script chạy thành công."
