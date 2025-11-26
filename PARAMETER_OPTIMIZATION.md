# Hướng Dẫn Tối Ưu Hóa Tham Số

## Các Tham Số Quan Trọng Cần Tối Ưu

### 1. Take Profit (8% - 15%)
- **Giá trị thấp (5-8%)**: Bán sớm, an toàn nhưng bỏ lỡ cơ hội
- **Giá trị trung bình (8-12%)**: Cân bằng giữa lợi nhuận và rủi ro
- **Giá trị cao (12-15%)**: Lợi nhuận cao nhưng rủi ro bỏ lỡ cơ hội bán

**Đề xuất**: Bắt đầu với 8-10%, điều chỉnh theo từng cặp token

### 2. Stop Loss (3% - 6%)
- **Giá trị thấp (2-3%)**: Cắt lỗ sớm, nhưng có thể bán trong biến động ngắn hạn
- **Giá trị trung bình (4-5%)**: Cân bằng giữa bảo vệ vốn và cho phép biến động
- **Giá trị cao (5-6%)**: Cho phép biến động nhiều hơn, nhưng rủi ro cao hơn

**Đề xuất**: 4% cho thị trường biến động, 3% cho thị trường ổn định

### 3. RSI Buy Threshold (20 - 30)
- **Giá trị thấp (20-22)**: Mua ở oversold rất sâu, ít tín hiệu nhưng chất lượng cao
- **Giá trị trung bình (25-27)**: Cân bằng giữa số lượng và chất lượng tín hiệu
- **Giá trị cao (28-30)**: Nhiều tín hiệu nhưng có thể có false signals

**Đề xuất**: 25 cho thị trường biến động, 22-23 cho thị trường ổn định

### 4. RSI Sell Threshold (70 - 80)
- **Giá trị thấp (70-72)**: Bán sớm, an toàn nhưng bỏ lỡ cơ hội
- **Giá trị trung bình (75-77)**: Cân bằng
- **Giá trị cao (78-80)**: Giữ lâu hơn, lợi nhuận cao nhưng rủi ro

**Đề xuất**: 75 cho thị trường biến động, 77-78 cho thị trường tăng mạnh

### 5. Max DCA (2 - 5)
- **Giá trị thấp (2)**: Bảo thủ, ít DCA
- **Giá trị trung bình (3)**: Cân bằng
- **Giá trị cao (4-5)**: DCA nhiều, rủi ro cao hơn

**Đề xuất**: 3 cho hầu hết trường hợp, 2 cho thị trường rất biến động

### 6. Trailing Stop (2% - 5%)
- **Giá trị thấp (2-3%)**: Bảo vệ lợi nhuận sớm
- **Giá trị trung bình (3-4%)**: Cân bằng
- **Giá trị cao (4-5%)**: Cho phép biến động nhiều hơn

**Đề xuất**: 3% cho thị trường biến động, 4% cho thị trường ổn định

## Quy Trình Tối Ưu Hóa

### Bước 1: Backtest Cơ Bản
```bash
python3 backtest_improved.py
```

### Bước 2: Phân Tích Kết Quả
- Xem file `backtest_improved_summary.csv`
- Phân tích win rate, avg profit, max drawdown
- Xem lý do bán trong báo cáo chi tiết

### Bước 3: Điều Chỉnh Tham Số
Sửa trong file `backtest_improved.py`:
```python
TAKE_PROFIT = 0.10      # Thử 10%
STOP_LOSS = 0.03        # Thử 3%
RSI_BUY = 22            # Thử 22
RSI_SELL = 77           # Thử 77
MAX_DCA = 2             # Thử 2
```

### Bước 4: So Sánh Kết Quả
Chạy lại và so sánh:
- Lợi nhuận tổng
- Win rate
- Avg profit per trade
- Max drawdown

### Bước 5: Lặp Lại
Thử các combination khác nhau cho đến khi tìm được tham số tối ưu

## Grid Search (Tự Động)

Bạn có thể tạo script để tự động test nhiều combination:

```python
# Ví dụ grid search
take_profits = [0.08, 0.10, 0.12]
stop_losses = [0.03, 0.04, 0.05]
rsi_buys = [22, 25, 28]

best_params = None
best_profit = -float('inf')

for tp in take_profits:
    for sl in stop_losses:
        for rsi_b in rsi_buys:
            # Chạy backtest với tham số này
            # So sánh kết quả
            # Lưu tham số tốt nhất
```

## Tham Số Theo Từng Cặp Token

Mỗi token có thể cần tham số khác nhau:

| Token | Take Profit | Stop Loss | RSI Buy | RSI Sell | Lý Do |
|-------|-------------|-----------|---------|----------|-------|
| iBTCUSDM | 10% | 4% | 25 | 75 | Biến động cao |
| iETHUSDM | 8% | 3% | 22 | 77 | Ổn định hơn |
| ADAUSDM | 12% | 5% | 25 | 75 | Xu hướng rõ |
| WMTXUSDM | 8% | 4% | 25 | 75 | Trung bình |
| IAGUSDM | 10% | 4% | 25 | 75 | Biến động |
| SNEKUSDM | 8% | 3% | 22 | 77 | Ổn định |

## Lưu Ý Quan Trọng

⚠️ **Overfitting**: 
- Không tối ưu quá mức trên một khoảng thời gian
- Test trên nhiều khoảng thời gian khác nhau
- Kết quả backtest không đảm bảo hiệu suất tương lai

⚠️ **Market Conditions**:
- Tham số tốt trong bull market có thể không tốt trong bear market
- Nên có nhiều bộ tham số cho các điều kiện thị trường khác nhau

⚠️ **Transaction Costs**:
- Backtest không tính phí giao dịch
- Trong thực tế, cần trừ phí để có kết quả chính xác

## Công Cụ Hỗ Trợ

1. **Backtest trên nhiều khung thời gian**: 1D, 4H, 1H
2. **Walk-forward analysis**: Test trên nhiều period
3. **Monte Carlo simulation**: Mô phỏng nhiều kịch bản
4. **Paper trading**: Test trên tài khoản demo


