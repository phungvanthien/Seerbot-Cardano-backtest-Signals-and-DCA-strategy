"""
Script tải dữ liệu dài hạn (1-2 năm) cho tất cả các cặp token
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
    'iBTCUSDM': 'bitcoin',
    'iETHUSDM': 'ethereum',
}

CRYPTOCOMPARE_MAPPING = {
    'ADAUSDM': 'ADA',
    'iBTCUSDM': 'BTC',
    'iETHUSDM': 'ETH',
}

def download_from_cryptocompare_long(pair, days=730):
    """Tải dữ liệu dài hạn từ CryptoCompare"""
    symbol = CRYPTOCOMPARE_MAPPING.get(pair)
    if not symbol:
        return None
    
    try:
        # CryptoCompare giới hạn 2000 ngày, chia nhỏ request
        all_data = []
        remaining_days = days
        limit = 2000
        
        while remaining_days > 0:
            url = "https://min-api.cryptocompare.com/data/v2/histoday"
            params = {
                'fsym': symbol,
                'tsym': 'USD',
                'limit': min(limit, remaining_days),
                'toTs': int((datetime.now() - timedelta(days=days-remaining_days)).timestamp())
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('Response') == 'Success' and 'Data' in data:
                batch_data = data['Data']['Data']
                if not batch_data:
                    break
                all_data.extend(batch_data)
                remaining_days -= len(batch_data)
                
                if len(batch_data) < limit:
                    break
            else:
                break
            
            time.sleep(0.5)  # Tránh rate limit
        
        if not all_data:
            return None
        
        df = pd.DataFrame(all_data)
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
        df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
        
        return df
        
    except Exception as e:
        print(f"Lỗi khi tải từ CryptoCompare cho {pair}: {e}")
        return None

def download_from_coingecko_long(pair, days=730):
    """Tải dữ liệu dài hạn từ CoinGecko"""
    coin_id = COINGECKO_MAPPING.get(pair)
    if not coin_id:
        return None
    
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': min(days, 365),  # CoinGecko free tier giới hạn 365 ngày
            'interval': 'daily'
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'prices' in data and len(data['prices']) > 0:
            prices = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
            prices['timestamp'] = pd.to_datetime(prices['timestamp'], unit='ms')
            
            volumes = pd.DataFrame(data.get('total_volumes', []), columns=['timestamp', 'volume'])
            if len(volumes) > 0:
                volumes['timestamp'] = pd.to_datetime(volumes['timestamp'], unit='ms')
                prices = prices.merge(volumes, on='timestamp', how='left')
            else:
                prices['volume'] = 0
            
            prices['open'] = prices['close'].shift(1).fillna(prices['close'])
            prices['high'] = prices['close'] * 1.02
            prices['low'] = prices['close'] * 0.98
            
            df = prices[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            return df
        
        return None
    except Exception as e:
        print(f"Lỗi khi tải từ CoinGecko cho {pair}: {e}")
        return None

def create_extended_sample_data(pair, days=730):
    """Tạo dữ liệu mẫu mở rộng với nhiều pattern"""
    import numpy as np
    np.random.seed(hash(pair) % 1000)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='1D')
    
    base_price = np.random.uniform(0.5, 2.0)
    prices = []
    current_price = base_price
    
    # Tạo nhiều pattern khác nhau
    for i, date in enumerate(dates):
        # Thay đổi trend theo thời gian
        if i < len(dates) * 0.3:
            trend = 0.001  # Uptrend đầu
        elif i < len(dates) * 0.6:
            trend = -0.0005  # Downtrend giữa
        else:
            trend = 0.0005  # Sideways cuối
        
        change = trend + np.random.normal(0, 0.02)
        current_price *= (1 + change)
        current_price = max(0.01, current_price)
        
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
    
    return pd.DataFrame(prices)

def main():
    """Tải dữ liệu dài hạn cho tất cả các cặp"""
    print("=" * 80)
    print("Tải Dữ Liệu Dài Hạn (1-2 Năm) Cho Cardano DEX Pairs")
    print("=" * 80)
    
    days = 730  # 2 năm
    
    print(f"\n📅 Tải dữ liệu cho {days} ngày (2 năm)")
    print("=" * 80)
    
    downloaded_files = []
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Đang xử lý: {pair}")
        print(f"{'='*80}")
        
        df = None
        
        # Thử CryptoCompare trước (hỗ trợ dài hạn tốt hơn)
        print("  → Thử tải từ CryptoCompare...")
        df = download_from_cryptocompare_long(pair, days)
        if df is not None and len(df) > 0:
            print(f"  ✓ Tải thành công từ CryptoCompare: {len(df)} nến")
            print(f"    Từ: {df['timestamp'].min()} đến {df['timestamp'].max()}")
        else:
            # Thử CoinGecko
            print("  → Thử tải từ CoinGecko...")
            df = download_from_coingecko_long(pair, days)
            if df is not None and len(df) > 0:
                print(f"  ✓ Tải thành công từ CoinGecko: {len(df)} nến")
                print(f"    Từ: {df['timestamp'].min()} đến {df['timestamp'].max()}")
            else:
                # Tạo dữ liệu mẫu
                print("  → Tạo dữ liệu mẫu...")
                df = create_extended_sample_data(pair, days)
                print(f"  ⚠ Đã tạo dữ liệu mẫu: {len(df)} nến")
        
        if df is not None and len(df) > 0:
            os.makedirs('data', exist_ok=True)
            filename = f"data/{pair}_ohlcv.csv"
            df.to_csv(filename, index=False)
            print(f"  ✓ Đã lưu vào {filename}")
            downloaded_files.append(filename)
        
        time.sleep(1)  # Tránh rate limit
    
    print(f"\n{'='*80}")
    print(f"Hoàn thành! Đã tải/lưu {len(downloaded_files)} file")
    print(f"{'='*80}")
    
    return downloaded_files

if __name__ == "__main__":
    main()


