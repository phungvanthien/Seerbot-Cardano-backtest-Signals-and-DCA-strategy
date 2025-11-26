"""
Tạo dữ liệu intraday (8H, 12H) từ dữ liệu daily
Bằng cách nội suy và tạo biến động trong ngày
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def create_intraday_from_daily(df, timeframe_hours=8):
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
        n_candles_per_day = 24 // timeframe_hours  # 8H = 3 nến/ngày, 12H = 2 nến/ngày
        
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

def main():
    """Tạo dữ liệu intraday cho tất cả các cặp"""
    print("=" * 80)
    print("TẠO DỮ LIỆU INTRADAY (8H, 12H) TỪ DAILY")
    print("=" * 80)
    
    from backtest_fixed_amount import PAIRS
    
    timeframes = [
        {'hours': 8, 'name': '8h'},
        {'hours': 12, 'name': '12h'}
    ]
    
    for tf in timeframes:
        print(f"\n{'='*80}")
        print(f"Tạo dữ liệu khung {tf['name']}")
        print(f"{'='*80}")
        
        for pair in PAIRS:
            filename = f"data/{pair}_ohlcv.csv"
            
            if not os.path.exists(filename):
                print(f"  ✗ Không tìm thấy {filename}")
                continue
            
            try:
                df = pd.read_csv(filename)
                
                column_mapping = {
                    'Timestamp': 'timestamp', 'Date': 'timestamp', 'time': 'timestamp',
                    'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
                }
                
                for old_name, new_name in column_mapping.items():
                    if old_name in df.columns:
                        df = df.rename(columns={old_name: new_name})
                
                print(f"  → Đang xử lý {pair}...")
                print(f"    Số nến daily: {len(df)}")
                
                intraday_df = create_intraday_from_daily(df, tf['hours'])
                
                if intraday_df is None or len(intraday_df) == 0:
                    print(f"    ✗ Không thể tạo dữ liệu")
                    continue
                
                print(f"    Số nến {tf['name']}: {len(intraday_df)}")
                print(f"    Từ: {intraday_df['timestamp'].min()} đến {intraday_df['timestamp'].max()}")
                
                output_filename = f"data/{pair}_ohlcv_{tf['name']}.csv"
                intraday_df.to_csv(output_filename, index=False)
                print(f"    ✓ Đã lưu vào {output_filename}")
                
            except Exception as e:
                print(f"    ✗ Lỗi: {e}")
    
    print(f"\n{'='*80}")
    print("HOÀN THÀNH!")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()


