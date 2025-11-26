"""
Script test nhiều bộ tham số khác nhau để tìm tối ưu
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from backtest_improved import ImprovedBacktestEngine, filter_data_by_date, PAIRS

def test_parameter_set(pair, params, filter_year=2025, filter_month=11, filter_days=25):
    """Test một bộ tham số cho một cặp token"""
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
        
        if len(df) < 14:  # Cần ít nhất 14 nến để tính RSI
            return None
        
        engine = ImprovedBacktestEngine(**params)
        engine.run(df)
        results = engine.get_results()
        
        return results
        
    except Exception as e:
        return None

def main():
    """Test nhiều bộ tham số"""
    print("=" * 80)
    print("TEST NHIỀU BỘ THAM SỐ - TÌM TỐI ƯU")
    print("=" * 80)
    
    # Định nghĩa các bộ tham số để test
    parameter_sets = [
        {
            'name': 'Bảo Thủ (Take Profit 8%, Stop Loss 4%)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.08,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': True,
                'use_volume_filter': True
            }
        },
        {
            'name': 'Tích Cực (Take Profit 10%, Stop Loss 3%)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.10,
                'stop_loss': 0.03,
                'rsi_buy': 22,
                'rsi_sell': 77,
                'max_dca': 3,
                'use_trend_filter': True,
                'use_volume_filter': True
            }
        },
        {
            'name': 'Aggressive (Take Profit 12%, Stop Loss 5%)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.12,
                'stop_loss': 0.05,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 4,
                'use_trend_filter': True,
                'use_volume_filter': False
            }
        },
        {
            'name': 'Cân Bằng (Take Profit 9%, Stop Loss 4%, RSI 23/76)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.09,
                'stop_loss': 0.04,
                'rsi_buy': 23,
                'rsi_sell': 76,
                'max_dca': 3,
                'use_trend_filter': True,
                'use_volume_filter': True
            }
        },
        {
            'name': 'Oversold Sâu (RSI Buy 20, Take Profit 10%)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.10,
                'stop_loss': 0.04,
                'rsi_buy': 20,
                'rsi_sell': 75,
                'max_dca': 2,
                'use_trend_filter': True,
                'use_volume_filter': True
            }
        },
        {
            'name': 'Giữ Lâu (RSI Sell 80, Take Profit 12%)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.12,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 80,
                'max_dca': 3,
                'use_trend_filter': True,
                'use_volume_filter': True
            }
        },
        {
            'name': 'DCA Nhiều (Max DCA 5, Take Profit 8%)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.08,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 5,
                'use_trend_filter': True,
                'use_volume_filter': True
            }
        },
        {
            'name': 'Không Filter (No Trend/Volume Filter)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.08,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        }
    ]
    
    filter_year = 2025
    filter_month = 11
    filter_days = 25
    
    print(f"\n📅 Filter dữ liệu: {filter_days} ngày gần nhất của tháng {filter_month}/{filter_year}")
    print(f"📊 Test {len(parameter_sets)} bộ tham số cho {len(PAIRS)} cặp token\n")
    
    all_results = []
    
    for param_set in parameter_sets:
        print(f"\n{'='*80}")
        print(f"Testing: {param_set['name']}")
        print(f"{'='*80}")
        
        set_results = {
            'param_set': param_set['name'],
            'pairs': {},
            'total_initial': 0,
            'total_final': 0,
            'total_profit': 0,
            'total_profit_pct': 0,
            'total_trades': 0,
            'total_winning': 0,
            'total_losing': 0,
            'avg_win_rate': 0
        }
        
        for pair in PAIRS:
            results = test_parameter_set(
                pair, 
                param_set['params'],
                filter_year, 
                filter_month, 
                filter_days
            )
            
            if results:
                set_results['pairs'][pair] = results
                set_results['total_initial'] += results['initial_capital']
                set_results['total_final'] += results['final_capital']
                set_results['total_trades'] += results['total_trades']
                set_results['total_winning'] += results['winning_trades']
                set_results['total_losing'] += results['losing_trades']
                
                print(f"  {pair:12s}: Profit {results['total_profit_pct']:>7.2f}% | "
                      f"Trades: {results['total_trades']:2d} | "
                      f"Win Rate: {results['win_rate']:>5.1f}%")
        
        if set_results['total_initial'] > 0:
            set_results['total_profit'] = set_results['total_final'] - set_results['total_initial']
            set_results['total_profit_pct'] = (set_results['total_profit'] / set_results['total_initial']) * 100
            
            if set_results['total_trades'] > 0:
                set_results['avg_win_rate'] = (set_results['total_winning'] / set_results['total_trades']) * 100
        
        all_results.append(set_results)
        
        print(f"\n  📊 Tổng hợp: Profit {set_results['total_profit_pct']:>7.2f}% | "
              f"Trades: {set_results['total_trades']:2d} | "
              f"Win Rate: {set_results['avg_win_rate']:>5.1f}%")
    
    # So sánh kết quả
    print(f"\n{'='*80}")
    print("BẢNG SO SÁNH KẾT QUẢ")
    print(f"{'='*80}")
    
    print(f"\n{'Bộ Tham Số':<50} {'Profit %':>12} {'Trades':>8} {'Win Rate':>10}")
    print("-" * 80)
    
    # Sắp xếp theo profit
    sorted_results = sorted(all_results, key=lambda x: x['total_profit_pct'], reverse=True)
    
    for i, result in enumerate(sorted_results, 1):
        print(f"{i}. {result['param_set']:<48} "
              f"{result['total_profit_pct']:>10.2f}% "
              f"{result['total_trades']:>8} "
              f"{result['avg_win_rate']:>8.1f}%")
    
    # Tìm bộ tham số tốt nhất
    best = sorted_results[0]
    print(f"\n{'='*80}")
    print("🏆 BỘ THAM SỐ TỐT NHẤT")
    print(f"{'='*80}")
    print(f"Tên: {best['param_set']}")
    print(f"Lợi nhuận: {best['total_profit_pct']:.2f}%")
    print(f"Tổng số lệnh: {best['total_trades']}")
    print(f"Win Rate: {best['avg_win_rate']:.1f}%")
    
    # Lưu kết quả vào CSV
    summary_data = []
    for result in sorted_results:
        summary_data.append({
            'Parameter Set': result['param_set'],
            'Total Profit %': result['total_profit_pct'],
            'Total Trades': result['total_trades'],
            'Winning Trades': result['total_winning'],
            'Losing Trades': result['total_losing'],
            'Win Rate %': result['avg_win_rate'],
            'Total Initial': result['total_initial'],
            'Total Final': result['total_final']
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_csv('parameter_test_results.csv', index=False)
    print(f"\n✓ Đã lưu kết quả vào parameter_test_results.csv")
    
    # Lưu chi tiết cho từng cặp
    detailed_data = []
    for result in all_results:
        for pair, pair_results in result['pairs'].items():
            detailed_data.append({
                'Parameter Set': result['param_set'],
                'Pair': pair,
                'Profit %': pair_results['total_profit_pct'],
                'Trades': pair_results['total_trades'],
                'Win Rate %': pair_results['win_rate'],
                'Avg Profit %': pair_results['avg_profit_pct']
            })
    
    if detailed_data:
        df_detailed = pd.DataFrame(detailed_data)
        df_detailed.to_csv('parameter_test_detailed.csv', index=False)
        print(f"✓ Đã lưu chi tiết vào parameter_test_detailed.csv")
    
    print(f"\n{'='*80}")
    print("KHUYẾN NGHỊ")
    print(f"{'='*80}")
    print(f"""
Dựa trên kết quả test, bộ tham số tốt nhất là:
{best['param_set']}

Bạn có thể sử dụng các tham số này trong file backtest_improved.py:

TAKE_PROFIT = {[p['params']['take_profit'] for p in parameter_sets if p['name'] == best['param_set']][0]}
STOP_LOSS = {[p['params']['stop_loss'] for p in parameter_sets if p['name'] == best['param_set']][0]}
RSI_BUY = {[p['params']['rsi_buy'] for p in parameter_sets if p['name'] == best['param_set']][0]}
RSI_SELL = {[p['params']['rsi_sell'] for p in parameter_sets if p['name'] == best['param_set']][0]}
MAX_DCA = {[p['params']['max_dca'] for p in parameter_sets if p['name'] == best['param_set']][0]}

Lưu ý: Kết quả có thể khác nhau tùy vào:
- Chất lượng dữ liệu
- Khung thời gian backtest
- Điều kiện thị trường cụ thể
    """)

if __name__ == "__main__":
    main()


