"""
Script chuyển đổi dữ liệu OHLCV sang các khung thời gian ngắn hơn (6h, 4h, 2h, 1h)
Bằng cách tạo dữ liệu intraday từ daily data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def create_intraday_from_daily(df, timeframe_hours):
    """
    Tạo dữ liệu intraday từ daily bằng cách:
    1. Chia mỗi nến daily thành nhiều nến intraday
    2. Tạo biến động giá trong ngày
    """
    if 'timestamp' not in df.columns:
        return None
    
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    intraday_data = []
    
    for idx, row in df.iterrows():
        date = row['timestamp']
        open_price = row['open']
        high_price = row['high']
        low_price = row['low']
        close_price = row['close']
        volume = row['volume']
        
        # Số nến trong ngày
        n_candles_per_day = 24 // timeframe_hours  # 6H = 4 nến/ngày, 4H = 6 nến/ngày, 2H = 12 nến/ngày, 1H = 24 nến/ngày
        
        # Tạo các nến trong ngày
        for i in range(n_candles_per_day):
            candle_time = date + timedelta(hours=i * timeframe_hours)
            
            # Tính giá cho từng nến (nội suy)
            progress = i / n_candles_per_day
            
            # Tạo biến động
            if i == 0:
                candle_open = open_price
            else:
                # Giá mở = giá đóng của nến trước
                candle_open = intraday_data[-1]['close']
            
            if i == n_candles_per_day - 1:
                candle_close = close_price
            else:
                # Nội suy giá đóng
                candle_close = open_price + (close_price - open_price) * (progress + 1/n_candles_per_day)
                # Thêm biến động ngẫu nhiên
                volatility = (high_price - low_price) / n_candles_per_day * 0.5
                candle_close += np.random.normal(0, volatility * 0.3)
                candle_close = np.clip(candle_close, low_price, high_price)
            
            candle_high = max(candle_open, candle_close) * (1 + abs(np.random.normal(0, 0.01)))
            candle_high = min(candle_high, high_price)
            
            candle_low = min(candle_open, candle_close) * (1 - abs(np.random.normal(0, 0.01)))
            candle_low = max(candle_low, low_price)
            
            candle_volume = volume / n_candles_per_day * (1 + np.random.normal(0, 0.2))
            candle_volume = max(0, candle_volume)
            
            intraday_data.append({
                'timestamp': candle_time,
                'open': candle_open,
                'high': candle_high,
                'low': candle_low,
                'close': candle_close,
                'volume': candle_volume
            })
    
    result_df = pd.DataFrame(intraday_data)
    return result_df

def convert_pair_to_timeframe(pair, timeframe='6H'):
    """Chuyển đổi một cặp token sang khung thời gian mới"""
    filename = f"data/{pair}_ohlcv.csv"
    
    # Map timeframe to hours
    timeframe_hours_map = {
        '6H': 6,
        '4H': 4,
        '2H': 2,
        '1H': 1
    }
    
    if timeframe not in timeframe_hours_map:
        print(f"✗ Khung thời gian {timeframe} không được hỗ trợ")
        return None
    
    timeframe_hours = timeframe_hours_map[timeframe]
    
    if not os.path.exists(filename):
        print(f"✗ Không tìm thấy {filename}")
        return None
    
    try:
        df = pd.read_csv(filename)
        
        column_mapping = {
            'Timestamp': 'timestamp', 'Date': 'timestamp', 'time': 'timestamp',
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        if 'timestamp' not in df.columns:
            print(f"✗ Không tìm thấy cột timestamp trong {pair}")
            return None
        
        print(f"  → Đang tạo dữ liệu {pair} từ daily sang {timeframe}...")
        print(f"    Số nến daily: {len(df)}")
        
        intraday_df = create_intraday_from_daily(df, timeframe_hours)
        
        if intraday_df is None or len(intraday_df) == 0:
            print(f"  ✗ Không thể tạo dữ liệu {pair}")
            return None
        
        print(f"    Số nến {timeframe}: {len(intraday_df)}")
        print(f"    Từ: {intraday_df['timestamp'].min()} đến {intraday_df['timestamp'].max()}")
        
        # Lưu file mới
        output_filename = f"data/{pair}_ohlcv_{timeframe.replace('H', 'h')}.csv"
        intraday_df.to_csv(output_filename, index=False)
        print(f"  ✓ Đã lưu vào {output_filename}")
        
        return output_filename
        
    except Exception as e:
        print(f"  ✗ Lỗi khi chuyển đổi {pair}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Chuyển đổi tất cả các cặp sang khung 6h, 4h, 2h, 1h"""
    print("=" * 80)
    print("CHUYỂN ĐỔI DỮ LIỆU SANG KHUNG THỜI GIAN NGẮN HƠN")
    print("=" * 80)
    
    from backtest_fixed_amount import PAIRS
    
    timeframes = ['6H', '4H', '2H', '1H']
    
    for timeframe in timeframes:
        print(f"\n{'='*80}")
        print(f"Chuyển đổi sang khung {timeframe}")
        print(f"{'='*80}")
        
        for pair in PAIRS:
            convert_pair_to_timeframe(pair, timeframe)
    
    print(f"\n{'='*80}")
    print("HOÀN THÀNH!")
    print(f"{'='*80}")
    print("\nFiles đã tạo:")
    print("  - data/*_ohlcv_6h.csv (khung 6 giờ)")
    print("  - data/*_ohlcv_4h.csv (khung 4 giờ)")
    print("  - data/*_ohlcv_2h.csv (khung 2 giờ)")
    print("  - data/*_ohlcv_1h.csv (khung 1 giờ)")

if __name__ == "__main__":
    main()

