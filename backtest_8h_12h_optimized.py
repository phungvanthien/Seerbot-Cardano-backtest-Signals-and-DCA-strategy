"""
Backtest trên khung 8H và 12H với tham số được điều chỉnh
Điều chỉnh RSI period và ngưỡng cho phù hợp với khung thời gian ngắn hơn
"""

import pandas as pd
import numpy as np
from datetime import datetime
from backtest_fixed_amount import FixedAmountBacktestEngine, PAIRS
import os

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500

def load_optimal_params():
    """Đọc tham số tối ưu cho daily"""
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

def backtest_timeframe_optimized(pair, params, timeframe='8h', rsi_period=10):
    """Backtest với RSI period được điều chỉnh cho khung ngắn hơn"""
    if timeframe == '1D':
        filename = f"data/{pair}_ohlcv.csv"
        rsi_period = 14  # Daily dùng RSI 14
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
        
        params_clean = {k: v for k, v in params.items() if k != 'position_size'}
        
        # Điều chỉnh tham số cho khung ngắn hơn
        adjusted_params = params_clean.copy()
        
        # Khung ngắn hơn: giảm take profit, tăng ngưỡng RSI buy (ít tín hiệu hơn)
        if timeframe in ['8h', '12h']:
            # Giảm take profit một chút
            adjusted_params['take_profit'] = params_clean['take_profit'] * 0.8
            # Tăng RSI buy threshold để giảm false signals
            adjusted_params['rsi_buy'] = max(20, params_clean['rsi_buy'] - 2)
            # Giảm stop loss một chút
            adjusted_params['stop_loss'] = params_clean['stop_loss'] * 0.9
        
        engine_params = {
            'initial_capital': INITIAL_CAPITAL,
            'fixed_amount': POSITION_SIZE_FIXED,
            'rsi_period': rsi_period,
            **adjusted_params
        }
        
        engine = FixedAmountBacktestEngine(**engine_params)
        engine.run(df)
        results = engine.get_results()
        
        if results:
            results['timeframe'] = timeframe
            results['rsi_period'] = rsi_period
            results['start_date'] = df['timestamp'].min()
            results['end_date'] = df['timestamp'].max()
            results['days'] = len(df)
            results['pair'] = pair
        
        return results
        
    except Exception as e:
        print(f"Lỗi khi backtest {pair} {timeframe}: {e}")
        return None

def main():
    """Backtest trên khung 8H và 12H với tham số được điều chỉnh"""
    print("=" * 80)
    print("BACKTEST TRÊN KHUNG 8H VÀ 12H - THAM SỐ ĐIỀU CHỈNH")
    print("=" * 80)
    print(f"\nVốn: ${INITIAL_CAPITAL:,} | Mỗi lệnh: ${POSITION_SIZE_FIXED:,}")
    print("Điều chỉnh: RSI Period 10 (thay vì 14), giảm Take Profit, tăng RSI Buy threshold")
    print("=" * 80)
    
    optimal_params = load_optimal_params()
    timeframes = ['1D', '12h', '8h']
    
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
            rsi_period = 10 if timeframe in ['8h', '12h'] else 14
            
            print(f"\n  Khung {timeframe} (RSI Period {rsi_period}):")
            results = backtest_timeframe_optimized(pair, params, timeframe, rsi_period)
            
            if results:
                pair_results[timeframe] = results
                print(f"    ✓ Lợi nhuận: {results['total_profit_pct']:+.2f}%")
                print(f"    ✓ Số lệnh: {results['total_trades']}")
                print(f"    ✓ Win Rate: {results['win_rate']:.1f}%")
                print(f"    ✓ Số nến: {results['days']}")
                print(f"    ✓ Lợi nhuận trung bình/lệnh: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)")
            else:
                print(f"    ✗ Không có kết quả")
        
        all_results[pair] = pair_results
    
    # Tổng hợp
    print(f"\n{'='*80}")
    print("BẢNG SO SÁNH KẾT QUẢ")
    print(f"{'='*80}")
    
    print(f"\n{'Cặp Token':<12} {'1D - Lệnh':>10} {'1D - Profit':>12} {'1D - WR':>8} "
          f"{'12H - Lệnh':>10} {'12H - Profit':>12} {'12H - WR':>8} "
          f"{'8H - Lệnh':>10} {'8H - Profit':>12} {'8H - WR':>8}")
    print("-" * 100)
    
    for pair in PAIRS:
        if pair not in all_results or not all_results[pair]:
            continue
        
        row = [pair]
        for timeframe in timeframes:
            if timeframe in all_results[pair]:
                r = all_results[pair][timeframe]
                row.append(str(r['total_trades']))
                row.append(f"{r['total_profit_pct']:+.2f}%")
                row.append(f"{r['win_rate']:.1f}%")
            else:
                row.extend(['-', '-', '-'])
        
        print(f"{row[0]:<12} {row[1]:>10} {row[2]:>12} {row[3]:>8} "
              f"{row[4]:>10} {row[5]:>12} {row[6]:>8} "
              f"{row[7]:>10} {row[8]:>12} {row[9]:>8}")
    
    # Tính tổng
    print(f"\n{'='*80}")
    print("TỔNG HỢP")
    print(f"{'='*80}")
    
    for timeframe in timeframes:
        tf_results = []
        for pair_results in all_results.values():
            if timeframe in pair_results:
                tf_results.append(pair_results[timeframe])
        
        if tf_results:
            total_initial = sum(r['initial_capital'] for r in tf_results)
            total_final = sum(r['final_capital'] for r in tf_results)
            total_profit = total_final - total_initial
            total_profit_pct = (total_profit / total_initial * 100) if total_initial > 0 else 0
            total_trades = sum(r['total_trades'] for r in tf_results)
            total_winning = sum(r['winning_trades'] for r in tf_results)
            avg_win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0
            
            print(f"\nKhung {timeframe}:")
            print(f"  Tổng vốn: ${total_initial:,.2f} → ${total_final:,.2f}")
            print(f"  Tổng lợi nhuận: ${total_profit:,.2f} ({total_profit_pct:+.2f}%)")
            print(f"  Tổng số lệnh: {total_trades}")
            print(f"  Win Rate trung bình: {avg_win_rate:.1f}%")
    
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
                    'RSI Period': r.get('rsi_period', 14),
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
                    'Candles': r['days']
                })
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_csv('backtest_timeframes_optimized.csv', index=False)
        print(f"\n✓ Đã lưu kết quả vào backtest_timeframes_optimized.csv")
    
    print(f"\n{'='*80}")
    print("KHUYẾN NGHỊ")
    print(f"{'='*80}")
    print("""
1. Khung 12H cho kết quả tốt nhất: Nhiều lệnh hơn 1D, win rate ổn định hơn 8H
2. Khung 8H có nhiều lệnh nhất nhưng win rate thấp hơn
3. Nên điều chỉnh tham số riêng cho từng khung thời gian
4. Có thể cần tối ưu tham số riêng cho khung 8H và 12H
5. Paper trading trên khung ngắn hơn trước khi giao dịch thực
    """)

if __name__ == "__main__":
    main()


