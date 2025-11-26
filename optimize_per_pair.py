"""
Script tối ưu hóa tham số cho từng cặp token riêng biệt
"""

import pandas as pd
import numpy as np
import os
from itertools import product
from backtest_improved import ImprovedBacktestEngine, filter_data_by_date, PAIRS

def test_parameter_combination(pair, params, filter_year=2025, filter_month=11, filter_days=25):
    """Test một combination tham số"""
    filename = f"data/{pair}_ohlcv.csv"
    
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
        
        if filter_year and filter_month and filter_days:
            df = filter_data_by_date(df, filter_year, filter_month, filter_days)
        
        if len(df) < 14:
            return None
        
        engine = ImprovedBacktestEngine(**params)
        engine.run(df)
        results = engine.get_results()
        
        return results
        
    except Exception as e:
        return None

def optimize_pair(pair, test_periods=None):
    """
    Tối ưu hóa tham số cho một cặp token
    
    Parameters:
    - pair: Tên cặp token
    - test_periods: List các khoảng thời gian để test
    """
    print(f"\n{'='*80}")
    print(f"Tối ưu hóa tham số cho: {pair}")
    print(f"{'='*80}")
    
    # Định nghĩa các giá trị để test
    take_profits = [0.08, 0.10, 0.12]
    stop_losses = [0.03, 0.04, 0.05]
    rsi_buys = [22, 25, 28]
    rsi_sells = [75, 77, 80]
    position_sizes = [0.05, 0.07]
    max_dcas = [2, 3]
    
    # Sử dụng test periods mặc định nếu không có
    if test_periods is None:
        test_periods = [
            {'year': 2025, 'month': 11, 'days': 25},
            {'year': 2025, 'month': 10, 'days': 30},
        ]
    
    best_params = None
    best_score = -float('inf')
    all_results = []
    
    total_combinations = (len(take_profits) * len(stop_losses) * 
                         len(rsi_buys) * len(rsi_sells) * 
                         len(position_sizes) * len(max_dcas))
    
    print(f"📊 Sẽ test {total_combinations} combinations...")
    print(f"📅 Test trên {len(test_periods)} khoảng thời gian")
    
    count = 0
    
    for tp, sl, rsi_b, rsi_s, pos_size, max_dca in product(
        take_profits, stop_losses, rsi_buys, rsi_sells, position_sizes, max_dcas
    ):
        count += 1
        if count % 10 == 0:
            print(f"  Đã test {count}/{total_combinations} combinations...")
        
        # Test trên tất cả các khoảng thời gian
        total_profit = 0
        total_trades = 0
        total_win_rate = 0
        period_count = 0
        
        for period in test_periods:
            params = {
                'initial_capital': 10000,
                'position_size': pos_size,
                'take_profit': tp,
                'stop_loss': sl,
                'rsi_buy': rsi_b,
                'rsi_sell': rsi_s,
                'max_dca': max_dca,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
            
            results = test_parameter_combination(
                pair,
                params,
                period['year'],
                period['month'],
                period['days']
            )
            
            if results and results['total_trades'] > 0:
                total_profit += results['total_profit_pct']
                total_trades += results['total_trades']
                total_win_rate += results['win_rate']
                period_count += 1
        
        if period_count > 0:
            avg_profit = total_profit / period_count
            avg_win_rate = total_win_rate / period_count
            
            # Tính score (có thể điều chỉnh)
            score = avg_profit * 0.7 + avg_win_rate * 0.3
            
            all_results.append({
                'take_profit': tp,
                'stop_loss': sl,
                'rsi_buy': rsi_b,
                'rsi_sell': rsi_s,
                'position_size': pos_size,
                'max_dca': max_dca,
                'avg_profit': avg_profit,
                'avg_win_rate': avg_win_rate,
                'total_trades': total_trades,
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_params = {
                    'take_profit': tp,
                    'stop_loss': sl,
                    'rsi_buy': rsi_b,
                    'rsi_sell': rsi_s,
                    'position_size': pos_size,
                    'max_dca': max_dca,
                    'avg_profit': avg_profit,
                    'avg_win_rate': avg_win_rate,
                    'score': score
                }
    
    # Hiển thị kết quả
    if best_params:
        print(f"\n{'='*80}")
        print(f"🏆 THAM SỐ TỐI ƯU CHO {pair}")
        print(f"{'='*80}")
        print(f"  Take Profit: {best_params['take_profit']*100:.0f}%")
        print(f"  Stop Loss: {best_params['stop_loss']*100:.0f}%")
        print(f"  RSI Buy: {best_params['rsi_buy']}")
        print(f"  RSI Sell: {best_params['rsi_sell']}")
        print(f"  Position Size: {best_params['position_size']*100:.0f}%")
        print(f"  Max DCA: {best_params['max_dca']}")
        print(f"\n  Kết quả:")
        print(f"    Lợi nhuận trung bình: {best_params['avg_profit']:.2f}%")
        print(f"    Win Rate trung bình: {best_params['avg_win_rate']:.1f}%")
        print(f"    Score: {best_params['score']:.2f}")
    
    # Lưu top 10
    if all_results:
        df_results = pd.DataFrame(all_results)
        df_results = df_results.sort_values('score', ascending=False)
        df_results.to_csv(f'optimization_{pair}.csv', index=False)
        print(f"\n✓ Đã lưu top results vào optimization_{pair}.csv")
    
    return best_params

def main():
    """Tối ưu hóa tham số cho tất cả các cặp"""
    print("=" * 80)
    print("TỐI ƯU HÓA THAM SỐ CHO TỪNG CẶP TOKEN")
    print("=" * 80)
    
    # Định nghĩa các khoảng thời gian để test
    test_periods = [
        {'year': 2025, 'month': 11, 'days': 25},
        {'year': 2025, 'month': 10, 'days': 30},
        {'year': 2025, 'month': 9, 'days': 30},
    ]
    
    print(f"\n📅 Test trên {len(test_periods)} khoảng thời gian")
    print("=" * 80)
    
    optimal_params_all = {}
    
    for pair in PAIRS:
        optimal_params = optimize_pair(pair, test_periods)
        if optimal_params:
            optimal_params_all[pair] = optimal_params
    
    # Tổng hợp
    print(f"\n{'='*80}")
    print("TỔNG HỢP THAM SỐ TỐI ƯU")
    print(f"{'='*80}")
    
    summary_data = []
    for pair, params in optimal_params_all.items():
        summary_data.append({
            'Pair': pair,
            'Take Profit %': params['take_profit'] * 100,
            'Stop Loss %': params['stop_loss'] * 100,
            'RSI Buy': params['rsi_buy'],
            'RSI Sell': params['rsi_sell'],
            'Position Size %': params['position_size'] * 100,
            'Max DCA': params['max_dca'],
            'Avg Profit %': params['avg_profit'],
            'Avg Win Rate %': params['avg_win_rate'],
            'Score': params['score']
        })
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_csv('optimal_params_per_pair.csv', index=False)
        print(f"\n✓ Đã lưu tổng hợp vào optimal_params_per_pair.csv")
        
        print(f"\n{'Pair':<12} {'Take Profit':>12} {'Stop Loss':>10} {'RSI Buy':>8} {'RSI Sell':>9} {'Pos Size':>9} {'Max DCA':>8}")
        print("-" * 80)
        for row in summary_data:
            print(f"{row['Pair']:<12} {row['Take Profit %']:>10.0f}% "
                  f"{row['Stop Loss %']:>8.0f}% {row['RSI Buy']:>8} "
                  f"{row['RSI Sell']:>9} {row['Position Size %']:>7.0f}% "
                  f"{row['Max DCA']:>8}")
    
    print(f"\n{'='*80}")
    print("KHUYẾN NGHỊ")
    print(f"{'='*80}")
    print("""
1. Sử dụng tham số tối ưu cho từng cặp trong giao dịch thực
2. Test lại trên dữ liệu validation để xác nhận
3. Paper trading với tham số tối ưu trước khi giao dịch thực
4. Điều chỉnh tham số theo điều kiện thị trường thay đổi
    """)

if __name__ == "__main__":
    main()


