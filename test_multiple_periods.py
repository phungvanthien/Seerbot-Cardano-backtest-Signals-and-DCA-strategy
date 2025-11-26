"""
Script test chiến lược trên nhiều khoảng thời gian khác nhau
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from backtest_improved import ImprovedBacktestEngine, filter_data_by_date, PAIRS

def test_period(pair, params, start_date, end_date, period_name):
    """Test chiến lược trên một khoảng thời gian cụ thể"""
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
        
        # Filter theo khoảng thời gian
        mask = (df['timestamp'] >= pd.to_datetime(start_date)) & (df['timestamp'] <= pd.to_datetime(end_date))
        df_filtered = df[mask].copy()
        
        if len(df_filtered) < 14:  # Cần ít nhất 14 nến để tính RSI
            return None
        
        engine = ImprovedBacktestEngine(**params)
        engine.run(df_filtered)
        results = engine.get_results()
        
        if results:
            results['period_name'] = period_name
            results['start_date'] = start_date
            results['end_date'] = end_date
            results['days'] = len(df_filtered)
        
        return results
        
    except Exception as e:
        return None

def get_periods():
    """Định nghĩa các khoảng thời gian để test"""
    periods = []
    
    # Lấy ngày hiện tại
    today = datetime.now()
    
    # 1. 25 ngày gần nhất
    end_date = today
    start_date = end_date - timedelta(days=25)
    periods.append({
        'name': '25 ngày gần nhất',
        'start': start_date.strftime('%Y-%m-%d'),
        'end': end_date.strftime('%Y-%m-%d')
    })
    
    # 2. 1 tháng gần nhất
    start_date = end_date - timedelta(days=30)
    periods.append({
        'name': '1 tháng gần nhất',
        'start': start_date.strftime('%Y-%m-%d'),
        'end': end_date.strftime('%Y-%m-%d')
    })
    
    # 3. 3 tháng gần nhất
    start_date = end_date - timedelta(days=90)
    periods.append({
        'name': '3 tháng gần nhất',
        'start': start_date.strftime('%Y-%m-%d'),
        'end': end_date.strftime('%Y-%m-%d')
    })
    
    # 4. 6 tháng gần nhất
    start_date = end_date - timedelta(days=180)
    periods.append({
        'name': '6 tháng gần nhất',
        'start': start_date.strftime('%Y-%m-%d'),
        'end': end_date.strftime('%Y-%m-%d')
    })
    
    # 5. Tháng 11/2025 (25 ngày)
    periods.append({
        'name': 'Tháng 11/2025 (25 ngày)',
        'start': '2025-11-06',
        'end': '2025-11-30'
    })
    
    # 6. Tháng 10/2025
    periods.append({
        'name': 'Tháng 10/2025',
        'start': '2025-10-01',
        'end': '2025-10-31'
    })
    
    # 7. Tháng 9/2025
    periods.append({
        'name': 'Tháng 9/2025',
        'start': '2025-09-01',
        'end': '2025-09-30'
    })
    
    # 8. Q4/2025 (3 tháng cuối)
    periods.append({
        'name': 'Q4/2025 (Oct-Dec)',
        'start': '2025-10-01',
        'end': '2025-12-31'
    })
    
    return periods

def main():
    """Test chiến lược trên nhiều khoảng thời gian"""
    print("=" * 80)
    print("TEST CHIẾN LƯỢC TRÊN NHIỀU KHOẢNG THỜI GIAN")
    print("=" * 80)
    
    # Tham số tối ưu từ kết quả test trước
    optimal_params = {
        'initial_capital': 10000,
        'position_size': 0.07,  # 7%
        'take_profit': 0.10,     # 10%
        'stop_loss': 0.04,       # 4%
        'rsi_buy': 25,
        'rsi_sell': 75,
        'max_dca': 3,
        'use_trend_filter': False,
        'use_volume_filter': False
    }
    
    periods = get_periods()
    
    print(f"\n📊 Test {len(periods)} khoảng thời gian cho {len(PAIRS)} cặp token")
    print(f"Tham số: Position Size {optimal_params['position_size']*100}%, "
          f"Take Profit {optimal_params['take_profit']*100}%, "
          f"Stop Loss {optimal_params['stop_loss']*100}%")
    print("=" * 80)
    
    all_results = []
    
    for period in periods:
        print(f"\n{'='*80}")
        print(f"Testing: {period['name']}")
        print(f"Từ {period['start']} đến {period['end']}")
        print(f"{'='*80}")
        
        period_results = {
            'period_name': period['name'],
            'start_date': period['start'],
            'end_date': period['end'],
            'pairs': {},
            'total_initial': 0,
            'total_final': 0,
            'total_profit': 0,
            'total_profit_pct': 0,
            'total_trades': 0,
            'total_winning': 0,
            'total_losing': 0,
            'avg_win_rate': 0,
            'avg_profit_per_trade': 0,
            'total_days': 0
        }
        
        for pair in PAIRS:
            results = test_period(
                pair,
                optimal_params,
                period['start'],
                period['end'],
                period['name']
            )
            
            if results:
                period_results['pairs'][pair] = results
                period_results['total_initial'] += results['initial_capital']
                period_results['total_final'] += results['final_capital']
                period_results['total_trades'] += results['total_trades']
                period_results['total_winning'] += results['winning_trades']
                period_results['total_losing'] += results['losing_trades']
                period_results['total_days'] = results.get('days', 0)
                
                print(f"  {pair:12s}: Profit {results['total_profit_pct']:>7.2f}% | "
                      f"Trades: {results['total_trades']:2d} | "
                      f"Win Rate: {results['win_rate']:>5.1f}% | "
                      f"Days: {results.get('days', 0):3d}")
        
        if period_results['total_initial'] > 0:
            period_results['total_profit'] = period_results['total_final'] - period_results['total_initial']
            period_results['total_profit_pct'] = (period_results['total_profit'] / period_results['total_initial']) * 100
            
            if period_results['total_trades'] > 0:
                period_results['avg_win_rate'] = (period_results['total_winning'] / period_results['total_trades']) * 100
                total_avg_profit = sum(r['avg_profit_pct'] for r in period_results['pairs'].values() if r['total_trades'] > 0)
                count = sum(1 for r in period_results['pairs'].values() if r['total_trades'] > 0)
                period_results['avg_profit_per_trade'] = total_avg_profit / count if count > 0 else 0
        
        all_results.append(period_results)
        
        print(f"\n  📊 Tổng hợp: Profit {period_results['total_profit_pct']:>7.2f}% | "
              f"Trades: {period_results['total_trades']:2d} | "
              f"Win Rate: {period_results['avg_win_rate']:>5.1f}% | "
              f"Days: {period_results['total_days']:3d}")
    
    # Tổng hợp kết quả
    print(f"\n{'='*80}")
    print("BẢNG TỔNG HỢP KẾT QUẢ THEO KHOẢNG THỜI GIAN")
    print(f"{'='*80}")
    
    print(f"\n{'Khoảng Thời Gian':<30} {'Profit %':>12} {'Trades':>8} {'Win Rate':>10} {'Days':>8}")
    print("-" * 80)
    
    sorted_results = sorted(all_results, key=lambda x: x['total_profit_pct'], reverse=True)
    
    for result in sorted_results:
        print(f"{result['period_name']:<30} "
              f"{result['total_profit_pct']:>10.2f}% "
              f"{result['total_trades']:>8} "
              f"{result['avg_win_rate']:>8.1f}% "
              f"{result['total_days']:>8}")
    
    # Phân tích
    print(f"\n{'='*80}")
    print("PHÂN TÍCH KẾT QUẢ")
    print(f"{'='*80}")
    
    profitable_periods = [r for r in all_results if r['total_profit_pct'] > 0]
    losing_periods = [r for r in all_results if r['total_profit_pct'] <= 0]
    
    print(f"\n📈 Khoảng thời gian có lợi nhuận: {len(profitable_periods)}/{len(all_results)}")
    if profitable_periods:
        avg_profit = np.mean([r['total_profit_pct'] for r in profitable_periods])
        print(f"   Lợi nhuận trung bình: {avg_profit:.2f}%")
    
    print(f"\n📉 Khoảng thời gian lỗ: {len(losing_periods)}/{len(all_results)}")
    if losing_periods:
        avg_loss = np.mean([r['total_profit_pct'] for r in losing_periods])
        print(f"   Lỗ trung bình: {avg_loss:.2f}%")
    
    # Tính toán các chỉ số
    all_profits = [r['total_profit_pct'] for r in all_results if r['total_trades'] > 0]
    if all_profits:
        print(f"\n📊 Thống kê tổng thể:")
        print(f"   Lợi nhuận trung bình: {np.mean(all_profits):.2f}%")
        print(f"   Lợi nhuận tốt nhất: {max(all_profits):.2f}%")
        print(f"   Lỗ lớn nhất: {min(all_profits):.2f}%")
        print(f"   Độ lệch chuẩn: {np.std(all_profits):.2f}%")
    
    # Lưu kết quả
    summary_data = []
    for result in sorted_results:
        summary_data.append({
            'Period': result['period_name'],
            'Start Date': result['start_date'],
            'End Date': result['end_date'],
            'Days': result['total_days'],
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
    df_summary.to_csv('multiple_periods_test_results.csv', index=False)
    print(f"\n✓ Đã lưu kết quả vào multiple_periods_test_results.csv")
    
    # Lưu chi tiết cho từng cặp
    detailed_data = []
    for result in all_results:
        for pair, pair_results in result['pairs'].items():
            detailed_data.append({
                'Period': result['period_name'],
                'Pair': pair,
                'Profit %': pair_results['total_profit_pct'],
                'Trades': pair_results['total_trades'],
                'Win Rate %': pair_results['win_rate'],
                'Avg Profit %': pair_results['avg_profit_pct'],
                'Days': pair_results.get('days', 0)
            })
    
    if detailed_data:
        df_detailed = pd.DataFrame(detailed_data)
        df_detailed.to_csv('multiple_periods_detailed.csv', index=False)
        print(f"✓ Đã lưu chi tiết vào multiple_periods_detailed.csv")
    
    print(f"\n{'='*80}")
    print("KHUYẾN NGHỊ")
    print(f"{'='*80}")
    print(f"""
Dựa trên kết quả test trên {len(periods)} khoảng thời gian:

1. Chiến lược hoạt động tốt nhất trong khoảng thời gian: {sorted_results[0]['period_name']}
   - Lợi nhuận: {sorted_results[0]['total_profit_pct']:.2f}%
   - Win Rate: {sorted_results[0]['avg_win_rate']:.1f}%

2. Tỷ lệ thành công: {len(profitable_periods)}/{len(all_results)} khoảng thời gian có lợi nhuận

3. Độ ổn định: {'Tốt' if np.std(all_profits) < 1.0 else 'Trung bình' if np.std(all_profits) < 2.0 else 'Thấp'} 
   (Độ lệch chuẩn: {np.std(all_profits):.2f}%)

4. Khuyến nghị:
   - Nên test trên dữ liệu thực từ API
   - Test trên nhiều năm dữ liệu để có kết quả đáng tin cậy hơn
   - Điều chỉnh tham số theo từng điều kiện thị trường
    """)

if __name__ == "__main__":
    main()


