# Chiến Lược RSI14 & DCA - Báo Cáo Backtest

## 📊 Tổng Quan Chiến Lược

**Tên chiến lược**: RSI14 & DCA (Dollar-Cost Averaging)

### Điều Kiện Giao Dịch

#### Điều Kiện Mua:
- **RSI14 <= 30**: Mua lần đầu khi RSI14 <= 30
- **DCA**: Mua thêm khi:
  - Nến đỏ (close < open)
  - RSI14 < 30
  - Sau lệnh mua đầu tiên
  - Tối đa 3 lần DCA

#### Điều Kiện Bán:
1. **Chốt lãi: +5%** (ưu tiên cao nhất)
2. **Cắt lỗ: -2.5%** (ưu tiên cao nhất)
3. **RSI >= 70**: Bán khi RSI đạt ngưỡng bán
4. **Stop Loss**: 4% từ giá mua trung bình (nếu có)
5. **Trailing Stop**: 3% từ đỉnh cao nhất

### Tham Số

- **Vốn ban đầu**: $10,000 cho mỗi cặp
- **Số tiền mỗi lệnh**: $500 (cố định)
- **RSI Period**: 
  - Khung 1D: 14
  - Khung 12H: 10
  - Khung 8H: 10
- **RSI Buy**: 25-30
- **RSI Sell**: 70-75
- **Max DCA**: 3 lần

## 📁 Danh Sách Báo Cáo

### Khung 1D (Daily) - 6 báo cáo

1. `Report_iBTCUSDM_1D_*.png`
2. `Report_iETHUSDM_1D_*.png`
3. `Report_ADAUSDM_1D_*.png`
4. `Report_WMTXUSDM_1D_*.png`
5. `Report_IAGUSDM_1D_*.png`
6. `Report_SNEKUSDM_1D_*.png`

### Khung 12H - 6 báo cáo

1. `Report_iBTCUSDM_12H.png`
2. `Report_iETHUSDM_12H.png`
3. `Report_ADAUSDM_12H.png`
4. `Report_WMTXUSDM_12H.png`
5. `Report_IAGUSDM_12H.png`
6. `Report_SNEKUSDM_12H.png`

### Khung 8H - 6 báo cáo

1. `Report_iBTCUSDM_8H.png`
2. `Report_iETHUSDM_8H.png`
3. `Report_ADAUSDM_8H.png`
4. `Report_WMTXUSDM_8H.png`
5. `Report_IAGUSDM_8H.png`
6. `Report_SNEKUSDM_8H.png`

## 📋 Nội Dung Mỗi Báo Cáo

Mỗi báo cáo PNG bao gồm:

1. **Tiêu đề**: 
   - Tên cặp token
   - Chiến lược: RSI14 & DCA
   - Khung thời gian
   - Thông tin: Cắt lỗ -2.5%, Chốt lãi +5%

2. **Thông tin cơ bản**:
   - Thời gian test
   - Vốn ban đầu và vốn cuối
   - Lợi nhuận tổng
   - Số lệnh

3. **Tham số sử dụng**:
   - Chiến lược: RSI14 & DCA
   - RSI Period
   - Cắt lỗ: -2.5%
   - Chốt lãi: +5%
   - RSI Buy/Sell
   - Max DCA

4. **Thống kê chi tiết**:
   - Lệnh thắng/thua
   - Win Rate
   - Lợi nhuận trung bình/lệnh
   - Lý do bán

5. **Bảng chi tiết 100 lệnh**:
   - STT, Ngày Giờ, Loại, Giá, Số Lượng
   - Vốn/Doanh Thu, RSI, Vốn Đầu Tư
   - Lợi Nhuận ($), Lợi Nhuận %, Lý Do
   - Màu sắc phân biệt lệnh thắng/thua

6. **Equity Curve**: 
   - Biểu đồ giá trị portfolio theo thời gian

7. **Kết luận**:
   - Tổng kết kết quả với chiến lược RSI14 & DCA

## 🎯 Điểm Nổi Bật

### Ưu Điểm:
- ✅ **Cắt lỗ nhanh**: -2.5% giúp giảm thiểu thua lỗ
- ✅ **Chốt lãi sớm**: +5% giúp bảo vệ lợi nhuận
- ✅ **DCA**: Giảm giá mua trung bình khi giá giảm
- ✅ **RSI14**: Chỉ báo momentum đáng tin cậy

### Lưu Ý:
- ⚠️ Cắt lỗ -2.5% có thể dẫn đến nhiều lệnh thua nhỏ
- ⚠️ Chốt lãi +5% có thể bỏ lỡ các đợt tăng giá lớn
- ⚠️ Cần điều chỉnh tham số cho từng cặp token

## 📊 Kết Quả

Tất cả 18 báo cáo PNG đã được tạo với:
- ✅ Chiến lược RSI14 & DCA
- ✅ Cắt lỗ: -2.5%
- ✅ Chốt lãi: +5%
- ✅ 100 lệnh gần ngày 26/11/2025 nhất
- ✅ Thông tin đầy đủ và dễ đọc

---

**Ngày tạo**: 26/11/2025
**Tổng số báo cáo**: 18 files PNG


