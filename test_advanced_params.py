"""
Script test các bộ tham số nâng cao dựa trên kết quả ban đầu
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
        
        if len(df) < 14:
            return None
        
        engine = ImprovedBacktestEngine(**params)
        engine.run(df)
        results = engine.get_results()
        
        return results
        
    except Exception as e:
        return None

def main():
    """Test các bộ tham số nâng cao"""
    print("=" * 80)
    print("TEST CÁC BỘ THAM SỐ NÂNG CAO")
    print("=" * 80)
    
    # Dựa trên kết quả trước, test các biến thể của "Không Filter"
    parameter_sets = [
        {
            'name': 'Không Filter - Take Profit 10%',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.10,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        },
        {
            'name': 'Không Filter - Take Profit 12%',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.12,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        },
        {
            'name': 'Không Filter - RSI 22/77',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.08,
                'stop_loss': 0.04,
                'rsi_buy': 22,
                'rsi_sell': 77,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        },
        {
            'name': 'Không Filter - Stop Loss 3%',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.08,
                'stop_loss': 0.03,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        },
        {
            'name': 'Chỉ Filter Volume (No Trend)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.08,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': True
            }
        },
        {
            'name': 'Chỉ Filter Trend (No Volume)',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.08,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': True,
                'use_volume_filter': False
            }
        },
        {
            'name': 'Không Filter - Max DCA 2',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.05,
                'take_profit': 0.08,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 2,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        },
        {
            'name': 'Không Filter - Position Size 7%',
            'params': {
                'initial_capital': 10000,
                'position_size': 0.07,
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
    print(f"📊 Test {len(parameter_sets)} bộ tham số nâng cao\n")
    
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
            'avg_win_rate': 0,
            'avg_profit_per_trade': 0
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
                      f"Win Rate: {results['win_rate']:>5.1f}% | "
                      f"Avg Profit: {results['avg_profit_pct']:>6.2f}%")
        
        if set_results['total_initial'] > 0:
            set_results['total_profit'] = set_results['total_final'] - set_results['total_initial']
            set_results['total_profit_pct'] = (set_results['total_profit'] / set_results['total_initial']) * 100
            
            if set_results['total_trades'] > 0:
                set_results['avg_win_rate'] = (set_results['total_winning'] / set_results['total_trades']) * 100
                # Tính avg profit per trade
                total_avg_profit = sum(r['avg_profit_pct'] for r in set_results['pairs'].values() if r['total_trades'] > 0)
                count = sum(1 for r in set_results['pairs'].values() if r['total_trades'] > 0)
                set_results['avg_profit_per_trade'] = total_avg_profit / count if count > 0 else 0
        
        all_results.append(set_results)
        
        print(f"\n  📊 Tổng hợp: Profit {set_results['total_profit_pct']:>7.2f}% | "
              f"Trades: {set_results['total_trades']:2d} | "
              f"Win Rate: {set_results['avg_win_rate']:>5.1f}% | "
              f"Avg Profit/Trade: {set_results['avg_profit_per_trade']:>6.2f}%")
    
    # So sánh kết quả
    print(f"\n{'='*80}")
    print("BẢNG SO SÁNH KẾT QUẢ NÂNG CAO")
    print(f"{'='*80}")
    
    print(f"\n{'Bộ Tham Số':<50} {'Profit %':>12} {'Trades':>8} {'Win Rate':>10} {'Avg Profit':>12}")
    print("-" * 92)
    
    sorted_results = sorted(all_results, key=lambda x: x['total_profit_pct'], reverse=True)
    
    for i, result in enumerate(sorted_results, 1):
        print(f"{i}. {result['param_set']:<48} "
              f"{result['total_profit_pct']:>10.2f}% "
              f"{result['total_trades']:>8} "
              f"{result['avg_win_rate']:>8.1f}% "
              f"{result['avg_profit_per_trade']:>10.2f}%")
    
    # Top 3
    print(f"\n{'='*80}")
    print("🏆 TOP 3 BỘ THAM SỐ TỐT NHẤT")
    print(f"{'='*80}")
    
    for i, result in enumerate(sorted_results[:3], 1):
        print(f"\n{i}. {result['param_set']}")
        print(f"   Lợi nhuận: {result['total_profit_pct']:.2f}%")
        print(f"   Tổng số lệnh: {result['total_trades']}")
        print(f"   Win Rate: {result['avg_win_rate']:.1f}%")
        print(f"   Avg Profit/Trade: {result['avg_profit_per_trade']:.2f}%")
    
    # Lưu kết quả
    summary_data = []
    for result in sorted_results:
        summary_data.append({
            'Parameter Set': result['param_set'],
            'Total Profit %': result['total_profit_pct'],
            'Total Trades': result['total_trades'],
            'Winning Trades': result['total_winning'],
            'Losing Trades': result['total_losing'],
            'Win Rate %': result['avg_win_rate'],
            'Avg Profit Per Trade %': result['avg_profit_per_trade'],
            'Total Initial': result['total_initial'],
            'Total Final': result['total_final']
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_csv('parameter_test_advanced_results.csv', index=False)
    print(f"\n✓ Đã lưu kết quả vào parameter_test_advanced_results.csv")
    
    # Phân tích
    print(f"\n{'='*80}")
    print("PHÂN TÍCH VÀ KHUYẾN NGHỊ")
    print(f"{'='*80}")
    
    best = sorted_results[0]
    print(f"""
📊 Kết quả tốt nhất: {best['param_set']}
   - Lợi nhuận: {best['total_profit_pct']:.2f}%
   - Win Rate: {best['avg_win_rate']:.1f}%
   - Avg Profit/Trade: {best['avg_profit_per_trade']:.2f}%

💡 Nhận xét:
   - Bộ tham số không filter xu hướng/volume cho nhiều cơ hội giao dịch hơn
   - Tuy nhiên, trong thực tế, filter có thể giúp tránh false signals
   - Nên test trên nhiều khoảng thời gian khác nhau để xác nhận
   - Có thể kết hợp: không filter trend nhưng vẫn filter volume

🔧 Đề xuất tham số tối ưu:
   TAKE_PROFIT = 0.08 - 0.10
   STOP_LOSS = 0.03 - 0.04
   RSI_BUY = 22 - 25
   RSI_SELL = 75 - 77
   MAX_DCA = 2 - 3
   USE_TREND_FILTER = False (hoặc True với điều kiện lỏng hơn)
   USE_VOLUME_FILTER = False (hoặc True với ngưỡng thấp hơn)
    """)

if __name__ == "__main__":
    main()


