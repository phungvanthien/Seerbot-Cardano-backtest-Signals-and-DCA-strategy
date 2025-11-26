# Hướng Dẫn Sử Dụng Backtest Với Tham Số Tối Ưu

## 📋 Tổng Quan

Script `backtest_optimized.py` tự động đọc tham số tối ưu từ file `optimal_params_real_data.csv` và áp dụng cho từng cặp token trong backtest.

## 🚀 Cách Sử Dụng

### Chạy Script

```bash
python3 backtest_optimized.py
```

### Chọn Khoảng Thời Gian

Script sẽ hỏi bạn chọn khoảng thời gian test:

1. **6 tháng gần nhất** - Test trên 6 tháng dữ liệu
2. **1 năm gần nhất** - Test trên 1 năm dữ liệu
3. **2 năm (toàn bộ)** - Test trên toàn bộ dữ liệu (mặc định)
4. **Tùy chỉnh** - Nhập ngày bắt đầu và kết thúc

### Kết Quả

Script sẽ:
- ✅ Tự động đọc tham số tối ưu cho từng cặp
- ✅ Chạy backtest với tham số tối ưu
- ✅ Hiển thị kết quả chi tiết cho từng cặp
- ✅ Tổng hợp kết quả tổng thể
- ✅ Lưu kết quả vào file CSV
- ✅ Tạo biểu đồ equity curve

## 📊 Kết Quả Mẫu (2 Năm)

### Với Tham Số Tối Ưu

| Cặp Token | Lợi Nhuận | Số Lệnh | Win Rate | Avg Profit |
|-----------|-----------|---------|----------|------------|
| **ADAUSDM** | **15.12%** | 28 | 39.3% | 3.91% |
| **iBTCUSDM** | **3.68%** | 10 | **70.0%** | 5.41% |
| **iETHUSDM** | **1.42%** | 10 | 50.0% | 2.83% |

### Tổng Hợp

- **Tổng lợi nhuận**: +3.14% (2 năm)
- **Win Rate tổng thể**: 34.8%
- **Số cặp có lợi nhuận**: 4/6

## 📁 Files Được Tạo

1. **backtest_optimized_YYYYMMDD_HHMMSS.csv**: Kết quả chi tiết
2. **backtest_optimized_YYYYMMDD_HHMMSS.png**: Biểu đồ equity curve

## 🔍 Phân Tích Kết Quả

### Điểm Mạnh

1. ✅ **ADAUSDM xuất sắc**: 15.12% lợi nhuận với tham số tối ưu
2. ✅ **iBTCUSDM ổn định**: 3.68% với win rate cao (70%)
3. ✅ **iETHUSDM ổn định**: 1.42% với win rate 50%

### Điểm Cần Lưu Ý

1. ⚠️ **Win Rate tổng thể thấp**: 34.8% (do ADAUSDM có nhiều lệnh nhưng win rate thấp)
2. ⚠️ **Các cặp không có tham số tối ưu**: Sử dụng tham số mặc định, kết quả kém hơn

## 💡 So Sánh Với Tham Số Cũ

### Trước Khi Tối Ưu (Tham Số Chung)
- ADAUSDM: 5.06% (2 năm)
- iBTCUSDM: 3.15% (2 năm)
- iETHUSDM: 1.20% (2 năm)

### Sau Khi Tối Ưu (Tham Số Riêng)
- ADAUSDM: **15.12%** ⬆️ +10.06%
- iBTCUSDM: **3.68%** ⬆️ +0.53%
- iETHUSDM: **1.42%** ⬆️ +0.22%

**Cải thiện rõ rệt**, đặc biệt là ADAUSDM!

## 🎯 Khuyến Nghị

### 1. Sử Dụng Tham Số Tối Ưu

Luôn sử dụng tham số tối ưu cho từng cặp thay vì dùng chung:
- **ADAUSDM**: RSI Buy 28, Max DCA 3 (nhiều cơ hội)
- **iBTCUSDM**: RSI Buy 25, Max DCA 2 (an toàn)
- **iETHUSDM**: Take Profit 10%, RSI Sell 77 (tận dụng xu hướng)

### 2. Paper Trading

Test với tham số tối ưu trên paper trading trước khi giao dịch thực:
```bash
# Sửa paper_trading_simulator.py để dùng tham số tối ưu
python3 paper_trading_simulator.py
```

### 3. Monitoring

Theo dõi kết quả và điều chỉnh nếu cần:
- Win rate < 40%: Xem xét điều chỉnh tham số
- Lỗ liên tiếp > 5 lệnh: Tạm dừng và phân tích

## 🔧 Tùy Chỉnh

### Thay Đổi Tham Số Mặc Định

Sửa trong file `backtest_optimized.py`:

```python
# Tham số mặc định cho các cặp không có tham số tối ưu
params = {
    'position_size': 0.07,
    'take_profit': 0.10,
    'stop_loss': 0.04,
    'rsi_buy': 25,
    'rsi_sell': 75,
    'max_dca': 3,
    'use_trend_filter': False,
    'use_volume_filter': False
}
```

### Thêm Cặp Mới

1. Chạy `optimize_real_data.py` để tối ưu tham số cho cặp mới
2. File `optimal_params_real_data.csv` sẽ được cập nhật
3. Script `backtest_optimized.py` sẽ tự động đọc tham số mới

## 📈 Kết Luận

Script `backtest_optimized.py` giúp:
- ✅ Tự động áp dụng tham số tối ưu cho từng cặp
- ✅ So sánh kết quả với tham số cũ
- ✅ Phân tích chi tiết từng cặp
- ✅ Lưu kết quả để theo dõi

**Kết quả cho thấy việc tối ưu tham số riêng cho từng cặp đã cải thiện đáng kể lợi nhuận, đặc biệt là ADAUSDM (+10.06%)!**


