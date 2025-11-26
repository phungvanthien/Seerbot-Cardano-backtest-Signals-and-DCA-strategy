"""
Script tối ưu hóa tham số cho từng cặp trên dữ liệu thực
Chỉ test trên các cặp có dữ liệu thực: iBTCUSDM, iETHUSDM, ADAUSDM
"""

import pandas as pd
import numpy as np
import os
from itertools import product
from backtest_improved import ImprovedBacktestEngine, PAIRS

# Chỉ test trên các cặp có dữ liệu thực
REAL_DATA_PAIRS = ['iBTCUSDM', 'iETHUSDM', 'ADAUSDM']

def test_parameter_combination_real(pair, params, start_date=None, end_date=None):
    """Test một combination tham số trên dữ liệu thực"""
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
        
        # Filter theo ngày nếu có
        if start_date:
            df = df[df['timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['timestamp'] <= pd.to_datetime(end_date)]
        
        if len(df) < 14:
            return None
        
        engine = ImprovedBacktestEngine(**params)
        engine.run(df)
        results = engine.get_results()
        
        return results
        
    except Exception as e:
        return None

def optimize_pair_real_data(pair):
    """
    Tối ưu hóa tham số cho một cặp token trên dữ liệu thực
    Test trên nhiều khoảng thời gian từ dữ liệu 2 năm
    """
    print(f"\n{'='*80}")
    print(f"Tối ưu hóa tham số cho: {pair} (Dữ liệu thực)")
    print(f"{'='*80}")
    
    # Định nghĩa các giá trị để test (giảm số lượng để nhanh hơn)
    take_profits = [0.08, 0.10, 0.12]
    stop_losses = [0.03, 0.04, 0.05]
    rsi_buys = [22, 25, 28]
    rsi_sells = [75, 77, 80]
    position_sizes = [0.05, 0.07]
    max_dcas = [2, 3]
    
    # Định nghĩa các khoảng thời gian để test (từ dữ liệu 2 năm)
    # Chia thành 4 quý để test
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    test_periods = [
        {
            'name': '6 tháng gần nhất',
            'start': (end_date - timedelta(days=180)).strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        },
        {
            'name': '3 tháng gần nhất',
            'start': (end_date - timedelta(days=90)).strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        },
        {
            'name': '1 năm gần nhất',
            'start': (end_date - timedelta(days=365)).strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        },
        {
            'name': 'Toàn bộ 2 năm',
            'start': None,  # Từ đầu dữ liệu
            'end': end_date.strftime('%Y-%m-%d')
        }
    ]
    
    best_params = None
    best_score = -float('inf')
    all_results = []
    
    total_combinations = (len(take_profits) * len(stop_losses) * 
                         len(rsi_buys) * len(rsi_sells) * 
                         len(position_sizes) * len(max_dcas))
    
    print(f"📊 Sẽ test {total_combinations} combinations...")
    print(f"📅 Test trên {len(test_periods)} khoảng thời gian")
    print(f"⏱️  Ước tính thời gian: {total_combinations * len(test_periods) * 2} giây")
    print()
    
    count = 0
    
    for tp, sl, rsi_b, rsi_s, pos_size, max_dca in product(
        take_profits, stop_losses, rsi_buys, rsi_sells, position_sizes, max_dcas
    ):
        count += 1
        if count % 20 == 0:
            print(f"  Đã test {count}/{total_combinations} combinations... ({count/total_combinations*100:.1f}%)")
        
        # Test trên tất cả các khoảng thời gian
        total_profit = 0
        total_trades = 0
        total_win_rate = 0
        period_count = 0
        period_results_detail = []
        
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
            
            results = test_parameter_combination_real(
                pair,
                params,
                period['start'],
                period['end']
            )
            
            if results and results['total_trades'] > 0:
                total_profit += results['total_profit_pct']
                total_trades += results['total_trades']
                total_win_rate += results['win_rate']
                period_count += 1
                
                period_results_detail.append({
                    'period': period['name'],
                    'profit': results['total_profit_pct'],
                    'trades': results['total_trades'],
                    'win_rate': results['win_rate']
                })
        
        if period_count > 0:
            avg_profit = total_profit / period_count
            avg_win_rate = total_win_rate / period_count
            avg_trades = total_trades / period_count
            
            # Tính score (có thể điều chỉnh)
            # Ưu tiên lợi nhuận 70%, win rate 20%, số lệnh 10%
            score = avg_profit * 0.7 + (avg_win_rate / 100) * 20 + min(avg_trades / 20, 1) * 10
            
            all_results.append({
                'take_profit': tp,
                'stop_loss': sl,
                'rsi_buy': rsi_b,
                'rsi_sell': rsi_s,
                'position_size': pos_size,
                'max_dca': max_dca,
                'avg_profit': avg_profit,
                'avg_win_rate': avg_win_rate,
                'avg_trades': avg_trades,
                'total_trades': total_trades,
                'period_count': period_count,
                'score': score,
                'period_details': period_results_detail
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
                    'avg_trades': avg_trades,
                    'score': score,
                    'period_details': period_results_detail
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
        print(f"\n  Kết quả trung bình:")
        print(f"    Lợi nhuận: {best_params['avg_profit']:.2f}%")
        print(f"    Win Rate: {best_params['avg_win_rate']:.1f}%")
        print(f"    Số lệnh trung bình: {best_params['avg_trades']:.1f}")
        print(f"    Score: {best_params['score']:.2f}")
        
        print(f"\n  Chi tiết theo khoảng thời gian:")
        for detail in best_params['period_details']:
            print(f"    {detail['period']:20s}: Profit {detail['profit']:>6.2f}% | "
                  f"Trades {detail['trades']:2d} | Win Rate {detail['win_rate']:>5.1f}%")
    
    # Lưu top 20
    if all_results:
        df_results = pd.DataFrame(all_results)
        df_results = df_results.sort_values('score', ascending=False).head(20)
        
        # Loại bỏ cột period_details (không thể serialize)
        df_results_clean = df_results.drop(columns=['period_details'])
        df_results_clean.to_csv(f'optimization_{pair}_real_data.csv', index=False)
        print(f"\n✓ Đã lưu top 20 results vào optimization_{pair}_real_data.csv")
    
    return best_params

def main():
    """Tối ưu hóa tham số cho các cặp có dữ liệu thực"""
    print("=" * 80)
    print("TỐI ƯU HÓA THAM SỐ CHO TỪNG CẶP - DỮ LIỆU THỰC")
    print("=" * 80)
    
    print(f"\n📊 Chỉ test trên các cặp có dữ liệu thực:")
    for pair in REAL_DATA_PAIRS:
        print(f"  - {pair}")
    
    print(f"\n⏱️  Quá trình này có thể mất vài phút...")
    print("=" * 80)
    
    optimal_params_all = {}
    
    for pair in REAL_DATA_PAIRS:
        optimal_params = optimize_pair_real_data(pair)
        if optimal_params:
            optimal_params_all[pair] = optimal_params
    
    # Tổng hợp
    print(f"\n{'='*80}")
    print("TỔNG HỢP THAM SỐ TỐI ƯU - DỮ LIỆU THỰC")
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
            'Avg Trades': params['avg_trades'],
            'Score': params['score']
        })
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_csv('optimal_params_real_data.csv', index=False)
        print(f"\n✓ Đã lưu tổng hợp vào optimal_params_real_data.csv")
        
        print(f"\n{'Pair':<12} {'Take Profit':>12} {'Stop Loss':>10} {'RSI Buy':>8} {'RSI Sell':>9} {'Pos Size':>9} {'Max DCA':>8} {'Avg Profit':>12} {'Win Rate':>10}")
        print("-" * 100)
        for row in summary_data:
            print(f"{row['Pair']:<12} {row['Take Profit %']:>10.0f}% "
                  f"{row['Stop Loss %']:>8.0f}% {row['RSI Buy']:>8} "
                  f"{row['RSI Sell']:>9} {row['Position Size %']:>7.0f}% "
                  f"{row['Max DCA']:>8} {row['Avg Profit %']:>10.2f}% "
                  f"{row['Avg Win Rate %']:>8.1f}%")
    
    print(f"\n{'='*80}")
    print("KHUYẾN NGHỊ")
    print(f"{'='*80}")
    print("""
1. Sử dụng tham số tối ưu cho từng cặp trong giao dịch thực
2. Test lại trên dữ liệu validation để xác nhận
3. Paper trading với tham số tối ưu trước khi giao dịch thực
4. Điều chỉnh tham số theo điều kiện thị trường thay đổi
5. Xem file optimization_*_real_data.csv để xem top 20 combinations
    """)

if __name__ == "__main__":
    main()


