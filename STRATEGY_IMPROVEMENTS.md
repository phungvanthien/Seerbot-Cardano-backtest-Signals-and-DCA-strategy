# Đề Xuất Cải Tiến Chiến Lược RSI14 + DCA

## Vấn Đề Của Chiến Lược Hiện Tại

1. **Take Profit quá thấp (5%)**: Bán quá sớm, bỏ lỡ cơ hội tăng giá tiếp
2. **Không có Stop Loss**: Giữ position lỗ quá lâu, rủi ro cao
3. **RSI ngưỡng chưa tối ưu**: Mua ở RSI 30 có thể chưa đủ oversold
4. **DCA không giới hạn**: Có thể DCA quá nhiều khi giá tiếp tục giảm
5. **Không có filter xu hướng**: Có thể mua trong downtrend mạnh
6. **Không có điều kiện volume**: Mua khi thanh khoản thấp

## Các Cải Tiến Đề Xuất

### 1. Tăng Take Profit: 5% → 8-10%
- **Lý do**: Cho phép position tăng giá nhiều hơn trước khi bán
- **Lợi ích**: Tăng lợi nhuận trung bình mỗi lệnh
- **Rủi ro**: Có thể bỏ lỡ cơ hội bán nếu giá quay đầu

### 2. Thêm Stop Loss: 4%
- **Lý do**: Giới hạn thua lỗ, bảo vệ vốn
- **Lợi ích**: Giảm rủi ro, cắt lỗ sớm khi thị trường đi ngược
- **Rủi ro**: Có thể bán sớm trong biến động ngắn hạn

### 3. Trailing Stop Loss: 3% từ đỉnh
- **Lý do**: Bảo vệ lợi nhuận khi giá đã tăng
- **Lợi ích**: Tự động điều chỉnh stop loss theo giá tăng
- **Cách hoạt động**: Khi giá tăng, stop loss tự động nâng lên

### 4. Điều chỉnh RSI Ngưỡng
- **Mua**: RSI <= 25 (thay vì 30) - mua ở oversold sâu hơn
- **Bán**: RSI >= 75 (thay vì 70) - bán ở overbought cao hơn
- **Lợi ích**: Tăng tỷ lệ thắng, giảm false signals

### 5. Giới hạn DCA: Tối đa 3 lần
- **Lý do**: Tránh DCA quá nhiều khi giá tiếp tục giảm
- **Lợi ích**: Quản lý rủi ro tốt hơn, không "catch falling knife"
- **Logic**: Chỉ DCA khi giá thấp hơn giá mua trung bình

### 6. Filter Xu Hướng (EMA20)
- **Lý do**: Chỉ mua khi có xu hướng tăng hoặc sideways
- **Điều kiện**: Giá không thấp hơn EMA20 quá 5%
- **Lợi ích**: Tránh mua trong downtrend mạnh

### 7. Filter Volume
- **Lý do**: Chỉ mua khi có thanh khoản tốt
- **Điều kiện**: Volume >= 80% volume trung bình 20 ngày
- **Lợi ích**: Tránh mua ở thị trường thanh khoản thấp

## So Sánh Chiến Lược

| Tham Số | Chiến Lược Cũ | Chiến Lược Mới | Cải Thiện |
|---------|---------------|----------------|-----------|
| Take Profit | 5% | 8% | +60% |
| Stop Loss | Không có | 4% | Giảm rủi ro |
| Trailing Stop | Không có | 3% | Bảo vệ lợi nhuận |
| RSI Mua | <= 30 | <= 25 | Tín hiệu tốt hơn |
| RSI Bán | >= 70 | >= 75 | Giữ lâu hơn |
| Max DCA | Không giới hạn | 3 lần | Quản lý rủi ro |
| Trend Filter | Không có | EMA20 | Tránh downtrend |
| Volume Filter | Không có | Volume MA | Thanh khoản tốt |

## Cách Sử Dụng

### Chạy Chiến Lược Cải Tiến
```bash
python3 backtest_improved.py
```

### Tùy Chỉnh Tham Số
Bạn có thể điều chỉnh các tham số trong file `backtest_improved.py`:

```python
TAKE_PROFIT = 0.08      # 8% (có thể tăng lên 0.10 = 10%)
STOP_LOSS = 0.04        # 4% (có thể giảm xuống 0.03 = 3%)
RSI_BUY = 25           # Có thể giảm xuống 20 cho oversold sâu hơn
RSI_SELL = 75          # Có thể tăng lên 80 cho overbought cao hơn
MAX_DCA = 3            # Có thể tăng lên 4-5 nếu muốn DCA nhiều hơn
```

## Kết Quả Mong Đợi

Với các cải tiến này, bạn có thể mong đợi:
- **Tăng lợi nhuận trung bình**: Do take profit cao hơn
- **Giảm số lệnh thua**: Do stop loss và filter tốt hơn
- **Tăng tỷ lệ thắng**: Do RSI ngưỡng tối ưu và filter xu hướng
- **Giảm drawdown**: Do stop loss và trailing stop

## Lưu Ý

⚠️ **Quan trọng**:
- Các cải tiến này dựa trên backtest, kết quả thực tế có thể khác
- Nên test trên nhiều khoảng thời gian khác nhau
- Có thể cần điều chỉnh tham số cho từng cặp token cụ thể
- Luôn quản lý rủi ro và không đầu tư quá mức

## Đề Xuất Thêm

1. **Backtest trên nhiều khung thời gian**: 1D, 4H, 1H
2. **Tối ưu hóa tham số**: Sử dụng grid search để tìm tham số tối ưu
3. **Phân tích theo từng cặp**: Mỗi token có thể cần tham số khác nhau
4. **Thêm chỉ báo khác**: MACD, Bollinger Bands để xác nhận tín hiệu
5. **Paper trading**: Test trên tài khoản demo trước khi giao dịch thực


