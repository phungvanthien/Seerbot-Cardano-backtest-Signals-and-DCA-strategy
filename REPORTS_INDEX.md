# Danh Sách Báo Cáo PNG - Backtest Chiến Lược RSI + DCA

## 📊 Tổng Quan

Đã tạo **18 báo cáo PNG** riêng biệt cho:
- **6 cặp token**: iBTCUSDM, iETHUSDM, ADAUSDM, WMTXUSDM, IAGUSDM, SNEKUSDM
- **3 khung thời gian**: 1D (Daily), 12H (12 giờ), 8H (8 giờ)

Mỗi báo cáo chứa **100 lệnh gần ngày 26/11/2025 nhất** (hoặc tất cả lệnh nếu ít hơn 100).

## 📁 Danh Sách Báo Cáo

### iBTCUSDM

| Khung Thời Gian | File | Số Lệnh |
|-----------------|------|---------|
| 1D (Daily) | `Report_iBTCUSDM_1D_*.png` | 10 lệnh |
| 12H | `Report_iBTCUSDM_12H_*.png` | 54 lệnh |
| 8H | `Report_iBTCUSDM_8H_*.png` | 91 lệnh |

### iETHUSDM

| Khung Thời Gian | File | Số Lệnh |
|-----------------|------|---------|
| 1D (Daily) | `Report_iETHUSDM_1D_*.png` | 10 lệnh |
| 12H | `Report_iETHUSDM_12H_*.png` | 69 lệnh |
| 8H | `Report_iETHUSDM_8H_*.png` | 100 lệnh |

### ADAUSDM

| Khung Thời Gian | File | Số Lệnh |
|-----------------|------|---------|
| 1D (Daily) | `Report_ADAUSDM_1D_*.png` | 28 lệnh |
| 12H | `Report_ADAUSDM_12H_*.png` | 93 lệnh |
| 8H | `Report_ADAUSDM_8H_*.png` | 100 lệnh |

### WMTXUSDM

| Khung Thời Gian | File | Số Lệnh |
|-----------------|------|---------|
| 1D (Daily) | `Report_WMTXUSDM_1D_*.png` | 15 lệnh |
| 12H | `Report_WMTXUSDM_12H_*.png` | 57 lệnh |
| 8H | `Report_WMTXUSDM_8H_*.png` | 87 lệnh |

### IAGUSDM

| Khung Thời Gian | File | Số Lệnh |
|-----------------|------|---------|
| 1D (Daily) | `Report_IAGUSDM_1D_*.png` | 11 lệnh |
| 12H | `Report_IAGUSDM_12H_*.png` | 43 lệnh |
| 8H | `Report_IAGUSDM_8H_*.png` | 74 lệnh |

### SNEKUSDM

| Khung Thời Gian | File | Số Lệnh |
|-----------------|------|---------|
| 1D (Daily) | `Report_SNEKUSDM_1D_*.png` | 18 lệnh |
| 12H | `Report_SNEKUSDM_12H_*.png` | 48 lệnh |
| 8H | `Report_SNEKUSDM_8H_*.png` | 75 lệnh |

## 📋 Nội Dung Mỗi Báo Cáo

Mỗi báo cáo PNG bao gồm:

1. **Thông tin cơ bản**:
   - Cặp token và khung thời gian
   - Thời gian test
   - Vốn ban đầu và vốn cuối
   - Lợi nhuận tổng

2. **Tham số sử dụng**:
   - RSI Period (14 cho 1D, 10 cho 12H/8H)
   - Take Profit, Stop Loss
   - RSI Buy, RSI Sell
   - Max DCA

3. **Thống kê chi tiết**:
   - Số lệnh thắng/thua
   - Win Rate
   - Lợi nhuận trung bình/lệnh
   - Lý do bán

4. **Bảng chi tiết 100 lệnh**:
   - Tất cả lệnh mua (BUY/DCA) và bán (SELL)
   - Ngày giờ, giá, số lượng
   - Vốn đầu tư, lợi nhuận
   - RSI tại thời điểm giao dịch
   - Lý do bán

5. **Equity Curve**:
   - Biểu đồ giá trị portfolio theo thời gian
   - So sánh với vốn ban đầu

6. **Kết luận**:
   - Tổng kết kết quả
   - Đánh giá hiệu suất

## 🎯 Lưu Ý

- **Lệnh được lọc**: Mỗi báo cáo chứa 100 lệnh bán gần ngày 26/11/2025 nhất (hoặc tất cả nếu ít hơn 100)
- **Lệnh mua liên quan**: Tự động bao gồm tất cả lệnh mua (BUY/DCA) liên quan đến các lệnh bán được chọn
- **Tham số điều chỉnh**: Khung 12H và 8H có tham số được điều chỉnh (Take Profit giảm 20%, RSI Buy threshold tăng, Stop Loss giảm 10%)

## 📈 So Sánh Nhanh

### Số Lệnh Trung Bình

| Khung | Số Lệnh Trung Bình |
|-------|-------------------|
| 1D | 15.3 lệnh |
| 12H | 60.7 lệnh |
| 8H | 87.8 lệnh |

### Khung Thời Gian Nào Có Nhiều Lệnh Nhất?

- **8H**: iETHUSDM và ADAUSDM có đủ 100 lệnh
- **12H**: ADAUSDM có 93 lệnh (gần 100 nhất)
- **1D**: Tất cả đều có ít hơn 30 lệnh

## 🔍 Cách Sử Dụng

1. Mở file PNG bằng bất kỳ trình xem ảnh nào
2. Xem thông tin tổng quan ở phần đầu
3. Kiểm tra bảng chi tiết lệnh ở giữa
4. Xem equity curve để đánh giá xu hướng
5. Đọc kết luận ở cuối báo cáo

## 📝 Ghi Chú

- Tất cả báo cáo được tạo vào: 26/11/2025
- Vốn ban đầu: $10,000 cho mỗi cặp
- Số tiền mỗi lệnh: $500 (cố định)
- Dữ liệu: Từ CryptoCompare API (dữ liệu thực 2 năm)

---

**Tổng số báo cáo**: 18 files PNG


