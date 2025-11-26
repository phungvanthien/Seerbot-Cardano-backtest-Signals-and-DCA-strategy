"""
Script cải tiến để tải dữ liệu thực từ nhiều nguồn
Hỗ trợ: CoinGecko, CryptoCompare, và các nguồn khác
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os

PAIRS = [
    'iBTCUSDM',
    'iETHUSDM', 
    'ADAUSDM',
    'WMTXUSDM',
    'IAGUSDM',
    'SNEKUSDM'
]

# Mapping cho các nguồn dữ liệu
COINGECKO_MAPPING = {
    'ADAUSDM': 'cardano',
    'iBTCUSDM': 'bitcoin',  # Có thể dùng BTC làm proxy
    'iETHUSDM': 'ethereum',  # Có thể dùng ETH làm proxy
}

CRYPTOCOMPARE_MAPPING = {
    'ADAUSDM': 'ADA',
    'iBTCUSDM': 'BTC',
    'iETHUSDM': 'ETH',
}

def download_from_coingecko_improved(pair, days=365):
    """Tải dữ liệu từ CoinGecko với nhiều thông tin hơn"""
    coin_id = COINGECKO_MAPPING.get(pair)
    if not coin_id:
        return None
    
    try:
        # Sử dụng market_chart endpoint để có volume
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily'
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Chuyển đổi dữ liệu
        if 'prices' in data and len(data['prices']) > 0:
            prices = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
            prices['timestamp'] = pd.to_datetime(prices['timestamp'], unit='ms')
            
            # Lấy volume nếu có
            volumes = pd.DataFrame(data.get('total_volumes', []), columns=['timestamp', 'volume'])
            if len(volumes) > 0:
                volumes['timestamp'] = pd.to_datetime(volumes['timestamp'], unit='ms')
                prices = prices.merge(volumes, on='timestamp', how='left')
            else:
                prices['volume'] = 0
            
            # Tính open, high, low từ close (xấp xỉ)
            prices['open'] = prices['close'].shift(1).fillna(prices['close'])
            prices['high'] = prices['close'] * 1.02  # Xấp xỉ
            prices['low'] = prices['close'] * 0.98   # Xấp xỉ
            
            # Sắp xếp lại cột
            df = prices[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            return df
        
        return None
    except Exception as e:
        print(f"Lỗi khi tải từ CoinGecko cho {pair}: {e}")
        return None

def download_from_cryptocompare(pair, days=365):
    """Tải dữ liệu từ CryptoCompare API"""
    symbol = CRYPTOCOMPARE_MAPPING.get(pair)
    if not symbol:
        return None
    
    try:
        url = "https://min-api.cryptocompare.com/data/v2/histoday"
        params = {
            'fsym': symbol,
            'tsym': 'USD',
            'limit': min(days, 2000)  # CryptoCompare giới hạn 2000
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('Response') == 'Success' and 'Data' in data:
            df = pd.DataFrame(data['Data']['Data'])
            
            # Chuẩn hóa tên cột
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volumefrom': 'volume'
            })
            
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
        
        return None
    except Exception as e:
        print(f"Lỗi khi tải từ CryptoCompare cho {pair}: {e}")
        return None

def download_pair_data_improved(pair, days=365, prefer_real=True):
    """
    Tải dữ liệu với thứ tự ưu tiên:
    1. CryptoCompare (nếu có)
    2. CoinGecko (nếu có)
    3. Dữ liệu mẫu (nếu không tải được)
    """
    print(f"\nĐang tải dữ liệu cho {pair}...")
    
    df = None
    
    # Thử CryptoCompare trước
    if prefer_real:
        df = download_from_cryptocompare(pair, days)
        if df is not None and len(df) > 0:
            print(f"✓ Tải thành công từ CryptoCompare ({len(df)} nến)")
            return df
    
    # Thử CoinGecko
    if df is None and prefer_real:
        df = download_from_coingecko_improved(pair, days)
        if df is not None and len(df) > 0:
            print(f"✓ Tải thành công từ CoinGecko ({len(df)} nến)")
            return df
    
    # Nếu không tải được, tạo dữ liệu mẫu
    if df is None:
        print(f"⚠ Không thể tải dữ liệu thực, tạo dữ liệu mẫu...")
        df = create_sample_data_extended(pair, days)
    
    return df

def create_sample_data_extended(pair, days=365):
    """Tạo dữ liệu mẫu mở rộng với nhiều khoảng thời gian"""
    print(f"Tạo dữ liệu mẫu cho {pair} (CẢNH BÁO: Đây là dữ liệu giả)")
    
    # Tạo dữ liệu từ 1 năm trước đến hiện tại
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='1D')
    
    import numpy as np
    np.random.seed(hash(pair) % 1000)
    
    base_price = np.random.uniform(0.5, 2.0)
    prices = []
    current_price = base_price
    
    # Tạo xu hướng và biến động thực tế hơn
    trend = np.random.choice([-0.001, 0, 0.001])  # Xu hướng nhẹ
    
    for i, date in enumerate(dates):
        # Thêm xu hướng
        change = trend + np.random.normal(0, 0.02)
        current_price *= (1 + change)
        current_price = max(0.01, current_price)
        
        # Tạo OHLC
        daily_volatility = np.random.uniform(0.01, 0.03)
        high = current_price * (1 + abs(np.random.normal(0, daily_volatility)))
        low = current_price * (1 - abs(np.random.normal(0, daily_volatility)))
        open_price = current_price * (1 + np.random.normal(0, daily_volatility * 0.5))
        close_price = current_price
        volume = np.random.uniform(10000, 100000)
        
        prices.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(prices)
    return df

def main():
    """Hàm chính để tải dữ liệu cho tất cả các cặp"""
    print("=" * 60)
    print("Tải Dữ Liệu Thực Cho Cardano DEX Pairs")
    print("=" * 60)
    print("\nLưu ý: Script sẽ thử tải từ các API thực.")
    print("Nếu không tải được, sẽ tạo dữ liệu mẫu để test.")
    print("=" * 60)
    
    downloaded_files = []
    
    for pair in PAIRS:
        try:
            # Thử tải dữ liệu thực (ít nhất 365 ngày)
            df = download_pair_data_improved(pair, days=365, prefer_real=True)
            
            if df is not None and len(df) > 0:
                # Lưu vào file
                os.makedirs('data', exist_ok=True)
                filename = f"data/{pair}_ohlcv.csv"
                df.to_csv(filename, index=False)
                print(f"✓ Đã lưu vào {filename} ({len(df)} nến)")
                downloaded_files.append(filename)
            
            time.sleep(1)  # Tránh rate limit
            
        except Exception as e:
            print(f"✗ Lỗi khi xử lý {pair}: {e}")
            continue
    
    print("\n" + "=" * 60)
    print(f"Hoàn thành! Đã tải/lưu {len(downloaded_files)} file")
    print("=" * 60)
    
    return downloaded_files

if __name__ == "__main__":
    main()


