"""
Script backtest trên nhiều khung thời gian (1D, 12H, 8H)
So sánh số lệnh và lợi nhuận
"""

import pandas as pd
import numpy as np
from datetime import datetime
from backtest_fixed_amount import FixedAmountBacktestEngine, PAIRS
import os

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500

def load_optimal_params():
    """Đọc tham số tối ưu"""
    filename = 'optimal_params_real_data.csv'
    if not os.path.exists(filename):
        return {}
    try:
        df = pd.read_csv(filename)
        params_dict = {}
        for _, row in df.iterrows():
            pair = row['Pair']
            params_dict[pair] = {
                'take_profit': row['Take Profit %'] / 100,
                'stop_loss': row['Stop Loss %'] / 100,
                'rsi_buy': int(row['RSI Buy']),
                'rsi_sell': int(row['RSI Sell']),
                'max_dca': int(row['Max DCA']),
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        return params_dict
    except:
        return {}

def backtest_timeframe(pair, params, timeframe='1D'):
    """Backtest trên một khung thời gian cụ thể"""
    if timeframe == '1D':
        filename = f"data/{pair}_ohlcv.csv"
    elif timeframe == '12H':
        filename = f"data/{pair}_ohlcv_12h.csv"
    elif timeframe == '8H':
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
        
        if len(df) < 14:
            return None
        
        params_clean = {k: v for k, v in params.items() if k != 'position_size'}
        
        engine_params = {
            'initial_capital': INITIAL_CAPITAL,
            'fixed_amount': POSITION_SIZE_FIXED,
            **params_clean
        }
        
        engine = FixedAmountBacktestEngine(**engine_params)
        engine.run(df)
        results = engine.get_results()
        
        if results:
            results['timeframe'] = timeframe
            results['start_date'] = df['timestamp'].min()
            results['end_date'] = df['timestamp'].max()
            results['days'] = len(df)
            results['pair'] = pair
        
        return results
        
    except Exception as e:
        return None

def main():
    """So sánh backtest trên các khung thời gian khác nhau"""
    print("=" * 80)
    print("BACKTEST TRÊN NHIỀU KHUNG THỜI GIAN")
    print("=" * 80)
    print("\nSo sánh: 1D (Daily), 12H, 8H")
    print(f"Vốn: ${INITIAL_CAPITAL:,} | Mỗi lệnh: ${POSITION_SIZE_FIXED:,}")
    print("=" * 80)
    
    optimal_params = load_optimal_params()
    timeframes = ['1D', '12H', '8H']
    
    all_results = {}
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Testing: {pair}")
        print(f"{'='*80}")
        
        if pair in optimal_params:
            params = optimal_params[pair]
        else:
            params = {
                'take_profit': 0.10,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        
        pair_results = {}
        
        for timeframe in timeframes:
            print(f"\n  Khung {timeframe}:")
            results = backtest_timeframe(pair, params, timeframe)
            
            if results:
                pair_results[timeframe] = results
                print(f"    ✓ Lợi nhuận: {results['total_profit_pct']:+.2f}%")
                print(f"    ✓ Số lệnh: {results['total_trades']}")
                print(f"    ✓ Win Rate: {results['win_rate']:.1f}%")
                print(f"    ✓ Số nến: {results['days']}")
            else:
                print(f"    ✗ Không có kết quả")
        
        all_results[pair] = pair_results
    
    # Tổng hợp và so sánh
    print(f"\n{'='*80}")
    print("BẢNG SO SÁNH KẾT QUẢ")
    print(f"{'='*80}")
    
    comparison_data = []
    
    for pair in PAIRS:
        if pair not in all_results or not all_results[pair]:
            continue
        
        row = [pair]
        for timeframe in timeframes:
            if timeframe in all_results[pair]:
                r = all_results[pair][timeframe]
                row.append(f"{r['total_trades']} lệnh")
                row.append(f"{r['total_profit_pct']:+.2f}%")
                row.append(f"{r['win_rate']:.1f}%")
            else:
                row.extend(['-', '-', '-'])
        
        comparison_data.append(row)
    
    # In bảng
    print(f"\n{'Cặp Token':<12} {'1D - Lệnh':>12} {'1D - Profit':>14} {'1D - WR':>10} "
          f"{'12H - Lệnh':>12} {'12H - Profit':>14} {'12H - WR':>10} "
          f"{'8H - Lệnh':>12} {'8H - Profit':>14} {'8H - WR':>10}")
    print("-" * 120)
    
    for row in comparison_data:
        print(f"{row[0]:<12} {row[1]:>12} {row[2]:>14} {row[3]:>10} "
              f"{row[4]:>12} {row[5]:>14} {row[6]:>10} "
              f"{row[7]:>12} {row[8]:>14} {row[9]:>10}")
    
    # Lưu kết quả
    summary_data = []
    for pair in PAIRS:
        if pair not in all_results or not all_results[pair]:
            continue
        
        for timeframe in timeframes:
            if timeframe in all_results[pair]:
                r = all_results[pair][timeframe]
                summary_data.append({
                    'Pair': pair,
                    'Timeframe': timeframe,
                    'Initial Capital': r['initial_capital'],
                    'Final Capital': r['final_capital'],
                    'Total Profit': r['total_profit'],
                    'Total Profit %': r['total_profit_pct'],
                    'Total Trades': r['total_trades'],
                    'Winning Trades': r['winning_trades'],
                    'Losing Trades': r['losing_trades'],
                    'Win Rate %': r['win_rate'],
                    'Avg Profit': r['avg_profit'],
                    'Avg Profit %': r['avg_profit_pct'],
                    'Days': r['days']
                })
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_csv('backtest_timeframes_comparison.csv', index=False)
        print(f"\n✓ Đã lưu kết quả vào backtest_timeframes_comparison.csv")
    
    # Phân tích
    print(f"\n{'='*80}")
    print("PHÂN TÍCH")
    print(f"{'='*80}")
    
    for timeframe in timeframes:
        tf_results = [r for pair_results in all_results.values() 
                     for tf, r in pair_results.items() if tf == timeframe and r]
        
        if tf_results:
            total_trades = sum(r['total_trades'] for r in tf_results)
            total_profit_pct = np.mean([r['total_profit_pct'] for r in tf_results])
            avg_win_rate = np.mean([r['win_rate'] for r in tf_results])
            
            print(f"\nKhung {timeframe}:")
            print(f"  Tổng số lệnh: {total_trades}")
            print(f"  Lợi nhuận trung bình: {total_profit_pct:+.2f}%")
            print(f"  Win Rate trung bình: {avg_win_rate:.1f}%")
    
    print(f"\n{'='*80}")
    print("KHUYẾN NGHỊ")
    print(f"{'='*80}")
    print("""
1. Khung thời gian ngắn hơn (8H, 12H) sẽ tạo nhiều cơ hội giao dịch hơn
2. Tuy nhiên, cần điều chỉnh tham số RSI cho phù hợp với khung thời gian ngắn hơn
3. Nên test trên paper trading trước khi áp dụng
4. Có thể cần điều chỉnh take profit và stop loss cho khung thời gian ngắn hơn
    """)

if __name__ == "__main__":
    main()


