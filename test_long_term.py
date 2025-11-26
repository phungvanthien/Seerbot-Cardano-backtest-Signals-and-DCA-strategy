"""
Script test chiến lược trên dữ liệu dài hạn (1-2 năm)
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from backtest_improved import ImprovedBacktestEngine, PAIRS

def test_long_term_backtest(pair, params, years=2):
    """Test backtest dài hạn cho một cặp"""
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
        
        # Filter theo số năm
        if len(df) > 0:
            end_date = df['timestamp'].max()
            start_date = end_date - timedelta(days=years * 365)
            mask = df['timestamp'] >= start_date
            df = df[mask].copy()
        
        if len(df) < 14:
            return None
        
        engine = ImprovedBacktestEngine(**params)
        engine.run(df)
        results = engine.get_results()
        
        if results:
            results['start_date'] = df['timestamp'].min()
            results['end_date'] = df['timestamp'].max()
            results['days'] = len(df)
            results['years'] = years
        
        return results
        
    except Exception as e:
        print(f"Lỗi khi test {pair}: {e}")
        return None

def analyze_long_term_results(all_results):
    """Phân tích kết quả dài hạn"""
    analysis = {
        'total_pairs': len([r for r in all_results.values() if r is not None]),
        'profitable_pairs': len([r for r in all_results.values() if r and r['total_profit_pct'] > 0]),
        'total_trades': sum(r['total_trades'] for r in all_results.values() if r),
        'total_profit_pct': 0,
        'avg_win_rate': 0,
        'best_pair': None,
        'worst_pair': None
    }
    
    if analysis['total_pairs'] > 0:
        profits = [r['total_profit_pct'] for r in all_results.values() if r]
        analysis['total_profit_pct'] = np.mean(profits)
        
        win_rates = [r['win_rate'] for r in all_results.values() if r and r['total_trades'] > 0]
        if win_rates:
            analysis['avg_win_rate'] = np.mean(win_rates)
        
        best = max([(pair, r) for pair, r in all_results.items() if r], 
                   key=lambda x: x[1]['total_profit_pct'], default=None)
        if best:
            analysis['best_pair'] = best[0]
        
        worst = min([(pair, r) for pair, r in all_results.items() if r], 
                    key=lambda x: x[1]['total_profit_pct'], default=None)
        if worst:
            analysis['worst_pair'] = worst[0]
    
    return analysis

def main():
    """Test chiến lược trên dữ liệu dài hạn"""
    print("=" * 80)
    print("TEST CHIẾN LƯỢC TRÊN DỮ LIỆU DÀI HẠN (1-2 NĂM)")
    print("=" * 80)
    
    # Tham số tối ưu
    optimal_params = {
        'initial_capital': 10000,
        'position_size': 0.07,
        'take_profit': 0.10,
        'stop_loss': 0.04,
        'rsi_buy': 25,
        'rsi_sell': 75,
        'max_dca': 3,
        'use_trend_filter': False,
        'use_volume_filter': False
    }
    
    years = 2  # Test trên 2 năm
    
    print(f"\n📊 Test trên {years} năm dữ liệu")
    print(f"Tham số: Position Size {optimal_params['position_size']*100}%, "
          f"Take Profit {optimal_params['take_profit']*100}%, "
          f"Stop Loss {optimal_params['stop_loss']*100}%")
    print("=" * 80)
    
    all_results = {}
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Testing: {pair}")
        print(f"{'='*80}")
        
        results = test_long_term_backtest(pair, optimal_params, years)
        all_results[pair] = results
        
        if results:
            print(f"✓ Kết quả:")
            print(f"  Thời gian: {results['start_date']} đến {results['end_date']}")
            print(f"  Số ngày: {results['days']}")
            print(f"  Lợi nhuận: {results['total_profit_pct']:.2f}%")
            print(f"  Số lệnh: {results['total_trades']}")
            print(f"  Win Rate: {results['win_rate']:.1f}%")
            print(f"  Lợi nhuận trung bình/lệnh: {results['avg_profit_pct']:.2f}%")
        else:
            print("✗ Không có kết quả")
    
    # Phân tích tổng hợp
    print(f"\n{'='*80}")
    print("PHÂN TÍCH TỔNG HỢP")
    print(f"{'='*80}")
    
    analysis = analyze_long_term_results(all_results)
    
    print(f"\n📊 Thống kê:")
    print(f"  Số cặp test: {analysis['total_pairs']}")
    print(f"  Số cặp có lợi nhuận: {analysis['profitable_pairs']}")
    print(f"  Tỷ lệ thành công: {analysis['profitable_pairs']/analysis['total_pairs']*100:.1f}%" if analysis['total_pairs'] > 0 else "N/A")
    print(f"  Tổng số lệnh: {analysis['total_trades']}")
    print(f"  Lợi nhuận trung bình: {analysis['total_profit_pct']:.2f}%")
    print(f"  Win Rate trung bình: {analysis['avg_win_rate']:.1f}%")
    
    if analysis['best_pair']:
        best_result = all_results[analysis['best_pair']]
        print(f"\n🏆 Cặp tốt nhất: {analysis['best_pair']}")
        print(f"  Lợi nhuận: {best_result['total_profit_pct']:.2f}%")
        print(f"  Win Rate: {best_result['win_rate']:.1f}%")
    
    if analysis['worst_pair']:
        worst_result = all_results[analysis['worst_pair']]
        print(f"\n📉 Cặp kém nhất: {analysis['worst_pair']}")
        print(f"  Lợi nhuận: {worst_result['total_profit_pct']:.2f}%")
        print(f"  Win Rate: {worst_result['win_rate']:.1f}%")
    
    # Lưu kết quả
    summary_data = []
    for pair, results in all_results.items():
        if results:
            summary_data.append({
                'Pair': pair,
                'Start Date': results['start_date'],
                'End Date': results['end_date'],
                'Days': results['days'],
                'Years': results['years'],
                'Initial Capital': results['initial_capital'],
                'Final Capital': results['final_capital'],
                'Total Profit': results['total_profit'],
                'Total Profit %': results['total_profit_pct'],
                'Total Trades': results['total_trades'],
                'Winning Trades': results['winning_trades'],
                'Losing Trades': results['losing_trades'],
                'Win Rate %': results['win_rate'],
                'Avg Profit': results['avg_profit'],
                'Avg Profit %': results['avg_profit_pct'],
                'Max Equity': results['max_equity'],
                'Min Equity': results['min_equity']
            })
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_csv('long_term_test_results.csv', index=False)
        print(f"\n✓ Đã lưu kết quả vào long_term_test_results.csv")
    
    # Tính toán lợi nhuận hàng năm
    if summary_data:
        print(f"\n{'='*80}")
        print("DỰ BÁO LỢI NHUẬN")
        print(f"{'='*80}")
        
        avg_annual_return = analysis['total_profit_pct'] / years
        print(f"  Lợi nhuận trung bình/năm: {avg_annual_return:.2f}%")
        print(f"  Lợi nhuận ước tính 2 năm: {analysis['total_profit_pct']:.2f}%")
        
        if avg_annual_return > 0:
            print(f"\n💡 Kết luận:")
            print(f"  Chiến lược cho thấy tiềm năng với lợi nhuận trung bình {avg_annual_return:.2f}%/năm")
            print(f"  Tuy nhiên, cần lưu ý:")
            print(f"    - Kết quả dựa trên backtest, không đảm bảo tương lai")
            print(f"    - Chưa tính phí giao dịch và slippage")
            print(f"    - Cần paper trading để xác nhận")

if __name__ == "__main__":
    main()


