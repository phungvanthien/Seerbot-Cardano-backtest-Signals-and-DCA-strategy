# Hướng Dẫn Sử Dụng Nhanh

## 🚀 Bắt Đầu Nhanh

### 1. Tải Dữ Liệu

```bash
# Tải dữ liệu dài hạn (2 năm)
python3 download_long_term_data.py

# Hoặc tải dữ liệu ngắn hạn
python3 download_real_data.py
```

### 2. Chạy Backtest

```bash
# Backtest với tham số tối ưu
python3 backtest_improved.py

# Test trên nhiều khoảng thời gian
python3 test_multiple_periods.py

# Test dài hạn (1-2 năm)
python3 test_long_term.py
```

### 3. Paper Trading

```bash
# Chạy paper trading simulator
python3 paper_trading_simulator.py
```

### 4. Tối Ưu Hóa

```bash
# Tối ưu tham số cho từng cặp
python3 optimize_per_pair.py
```

## 📊 Xem Kết Quả

### Files CSV
- `long_term_test_results.csv`: Kết quả test dài hạn
- `multiple_periods_test_results.csv`: Kết quả nhiều khoảng thời gian
- `paper_trading_trades.csv`: Chi tiết lệnh paper trading
- `optimal_params_per_pair.csv`: Tham số tối ưu

### Files JSON
- `paper_trading_log.json`: Log đầy đủ paper trading

## ⚙️ Điều Chỉnh Tham Số

Sửa trong file `backtest_improved.py` hoặc `paper_trading_simulator.py`:

```python
optimal_params = {
    'position_size': 0.07,      # 7%
    'take_profit': 0.10,        # 10%
    'stop_loss': 0.04,          # 4%
    'rsi_buy': 25,
    'rsi_sell': 75,
    'max_dca': 3,
    'use_trend_filter': False,
    'use_volume_filter': False
}
```

## 📈 Kết Quả Hiện Tại

### Test Dài Hạn (2 Năm)
- **ADAUSDM**: 5.06% (19 lệnh, 47.4% win rate)
- **iBTCUSDM**: 3.15% (10 lệnh, 60% win rate)
- **iETHUSDM**: 1.20% (10 lệnh, 50% win rate)

### Paper Trading (30 Ngày)
- **Win Rate**: 80%
- **Lợi nhuận**: $144.38

## ⚠️ Lưu Ý

1. Dữ liệu mẫu chỉ để test, không dùng cho giao dịch thực
2. Luôn paper trading trước khi giao dịch thực
3. Quản lý rủi ro và không đầu tư quá mức
4. Kết quả backtest không đảm bảo hiệu suất tương lai

## 📚 Tài Liệu

- `FINAL_RECOMMENDATIONS.md`: Khuyến nghị cuối cùng
- `PERIOD_TEST_ANALYSIS.md`: Phân tích test nhiều khoảng thời gian
- `COMPREHENSIVE_RESULTS.md`: Tổng hợp kết quả toàn diện
- `STRATEGY_IMPROVEMENTS.md`: Giải thích các cải tiến
- `PARAMETER_OPTIMIZATION.md`: Hướng dẫn tối ưu hóa


