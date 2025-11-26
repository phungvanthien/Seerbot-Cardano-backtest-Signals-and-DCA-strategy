"""
Script chuyển đổi dữ liệu OHLCV từ daily sang khung thời gian ngắn hơn (8h, 12h)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def resample_ohlcv(df, timeframe='8H'):
    """
    Chuyển đổi dữ liệu OHLCV sang khung thời gian mới
    
    Parameters:
    - df: DataFrame với cột timestamp, open, high, low, close, volume
    - timeframe: '8H' hoặc '12H'
    """
    if 'timestamp' not in df.columns:
        return None
    
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    df = df.sort_index()
    
    # Resample OHLCV
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    
    resampled = df.resample(timeframe).agg(ohlc_dict)
    resampled = resampled.dropna()
    resampled = resampled.reset_index()
    resampled = resampled.rename(columns={'timestamp': 'timestamp'})
    
    return resampled

def convert_pair_to_timeframe(pair, timeframe='8H'):
    """Chuyển đổi một cặp token sang khung thời gian mới"""
    filename = f"data/{pair}_ohlcv.csv"
    
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
        
        print(f"  → Đang chuyển đổi {pair} từ daily sang {timeframe}...")
        print(f"    Số nến ban đầu: {len(df)}")
        
        resampled = resample_ohlcv(df, timeframe)
        
        if resampled is None or len(resampled) == 0:
            print(f"  ✗ Không thể chuyển đổi {pair}")
            return None
        
        print(f"    Số nến sau khi chuyển đổi: {len(resampled)}")
        print(f"    Từ: {resampled['timestamp'].min()} đến {resampled['timestamp'].max()}")
        
        # Lưu file mới
        output_filename = f"data/{pair}_ohlcv_{timeframe.replace('H', 'h')}.csv"
        resampled.to_csv(output_filename, index=False)
        print(f"  ✓ Đã lưu vào {output_filename}")
        
        return output_filename
        
    except Exception as e:
        print(f"  ✗ Lỗi khi chuyển đổi {pair}: {e}")
        return None

def main():
    """Chuyển đổi tất cả các cặp sang khung 8h và 12h"""
    print("=" * 80)
    print("CHUYỂN ĐỔI DỮ LIỆU SANG KHUNG THỜI GIAN NGẮN HƠN")
    print("=" * 80)
    
    from backtest_fixed_amount import PAIRS
    
    timeframes = ['8H', '12H']
    
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
    print("  - data/*_ohlcv_8h.csv (khung 8 giờ)")
    print("  - data/*_ohlcv_12h.csv (khung 12 giờ)")

if __name__ == "__main__":
    main()


