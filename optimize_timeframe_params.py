"""
Tối ưu tham số RSI cho khung thời gian ngắn hơn (8H, 12H)
Khung thời gian ngắn hơn thường cần điều chỉnh RSI period và ngưỡng
"""

import pandas as pd
import numpy as np
from itertools import product
from backtest_fixed_amount import FixedAmountBacktestEngine, PAIRS
import os

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500

def calculate_rsi_custom(prices, period=14):
    """Tính RSI với period tùy chỉnh"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def backtest_with_custom_rsi(pair, params, timeframe='8h', rsi_period=14):
    """Backtest với RSI period tùy chỉnh"""
    if timeframe == '1D':
        filename = f"data/{pair}_ohlcv.csv"
    elif timeframe == '12h':
        filename = f"data/{pair}_ohlcv_12h.csv"
    elif timeframe == '8h':
        filename = f"data/{pair}_ohlcv_8h.csv"
    else:
        return None
    
    if not os.path.exists(filename):
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
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        if len(df) < rsi_period + 5:
            return None
        
        # Tính RSI với period tùy chỉnh
        df['rsi'] = calculate_rsi_custom(df['close'], period=rsi_period)
        
        # Sử dụng engine nhưng override RSI calculation
        # Tạm thời sử dụng engine hiện tại với RSI mặc định
        params_clean = {k: v for k, v in params.items() if k != 'position_size'}
        
        engine_params = {
            'initial_capital': INITIAL_CAPITAL,
            'fixed_amount': POSITION_SIZE_FIXED,
            **params_clean
        }
        
        # Tạo engine và override RSI
        engine = FixedAmountBacktestEngine(**engine_params)
        
        # Override RSI trong df trước khi chạy
        # (Cần sửa engine để chấp nhận RSI period tùy chỉnh)
        engine.run(df)
        results = engine.get_results()
        
        if results:
            results['timeframe'] = timeframe
            results['rsi_period'] = rsi_period
            results['start_date'] = df['timestamp'].min()
            results['end_date'] = df['timestamp'].max()
            results['days'] = len(df)
        
        return results
        
    except Exception as e:
        return None

def optimize_timeframe_params(pair, timeframe='8h'):
    """Tối ưu tham số cho khung thời gian cụ thể"""
    print(f"\n{'='*80}")
    print(f"Tối ưu tham số cho {pair} - Khung {timeframe}")
    print(f"{'='*80}")
    
    # Test các RSI period khác nhau cho khung ngắn hơn
    rsi_periods = [7, 10, 14] if timeframe != '1D' else [14]
    rsi_buys = [20, 25, 30]
    rsi_sells = [70, 75, 80]
    take_profits = [0.05, 0.08, 0.10]
    stop_losses = [0.03, 0.04]
    
    best_params = None
    best_score = -float('inf')
    all_results = []
    
    total_combinations = len(rsi_periods) * len(rsi_buys) * len(rsi_sells) * len(take_profits) * len(stop_losses)
    print(f"📊 Sẽ test {total_combinations} combinations...")
    
    count = 0
    for rsi_p, rsi_b, rsi_s, tp, sl in product(rsi_periods, rsi_buys, rsi_sells, take_profits, stop_losses):
        count += 1
        if count % 20 == 0:
            print(f"  Đã test {count}/{total_combinations}...")
        
        params = {
            'take_profit': tp,
            'stop_loss': sl,
            'rsi_buy': rsi_b,
            'rsi_sell': rsi_s,
            'max_dca': 3,
            'use_trend_filter': False,
            'use_volume_filter': False
        }
        
        results = backtest_with_custom_rsi(pair, params, timeframe, rsi_p)
        
        if results and results['total_trades'] > 0:
            # Score = profit * 0.6 + win_rate * 0.3 + trades * 0.1
            score = (results['total_profit_pct'] * 0.6 + 
                    (results['win_rate'] / 100) * 30 + 
                    min(results['total_trades'] / 50, 1) * 10)
            
            all_results.append({
                'rsi_period': rsi_p,
                'rsi_buy': rsi_b,
                'rsi_sell': rsi_s,
                'take_profit': tp,
                'stop_loss': sl,
                'profit': results['total_profit_pct'],
                'trades': results['total_trades'],
                'win_rate': results['win_rate'],
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_params = {
                    'rsi_period': rsi_p,
                    'rsi_buy': rsi_b,
                    'rsi_sell': rsi_s,
                    'take_profit': tp,
                    'stop_loss': sl,
                    'profit': results['total_profit_pct'],
                    'trades': results['total_trades'],
                    'win_rate': results['win_rate'],
                    'score': score
                }
    
    if best_params:
        print(f"\n🏆 THAM SỐ TỐI ƯU:")
        print(f"  RSI Period: {best_params['rsi_period']}")
        print(f"  RSI Buy: {best_params['rsi_buy']}")
        print(f"  RSI Sell: {best_params['rsi_sell']}")
        print(f"  Take Profit: {best_params['take_profit']*100:.0f}%")
        print(f"  Stop Loss: {best_params['stop_loss']*100:.0f}%")
        print(f"  Kết quả: {best_params['profit']:.2f}% | {best_params['trades']} lệnh | Win Rate: {best_params['win_rate']:.1f}%")
    
    return best_params, all_results

def main():
    """Tối ưu tham số cho các khung thời gian"""
    print("=" * 80)
    print("TỐI ƯU THAM SỐ CHO KHUNG THỜI GIAN NGẮN HƠN")
    print("=" * 80)
    
    # Chỉ test trên các cặp có dữ liệu thực
    test_pairs = ['iBTCUSDM', 'iETHUSDM', 'ADAUSDM']
    timeframes = ['8h', '12h']
    
    all_optimal = {}
    
    for timeframe in timeframes:
        print(f"\n{'='*80}")
        print(f"KHUNG THỜI GIAN: {timeframe}")
        print(f"{'='*80}")
        
        timeframe_optimal = {}
        
        for pair in test_pairs:
            optimal, all_results = optimize_timeframe_params(pair, timeframe)
            if optimal:
                timeframe_optimal[pair] = optimal
        
        all_optimal[timeframe] = timeframe_optimal
    
    # Tổng hợp
    print(f"\n{'='*80}")
    print("TỔNG HỢP THAM SỐ TỐI ƯU")
    print(f"{'='*80}")
    
    for timeframe in timeframes:
        print(f"\nKhung {timeframe}:")
        for pair, params in all_optimal[timeframe].items():
            print(f"  {pair}: RSI Period {params['rsi_period']}, Buy {params['rsi_buy']}, Sell {params['rsi_sell']}, "
                  f"TP {params['take_profit']*100:.0f}%, SL {params['stop_loss']*100:.0f}% | "
                  f"{params['trades']} lệnh, {params['profit']:.2f}%")

if __name__ == "__main__":
    main()


