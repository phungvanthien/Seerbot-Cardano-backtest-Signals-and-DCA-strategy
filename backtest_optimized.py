"""
Script backtest tự động với tham số tối ưu cho từng cặp token
Đọc tham số từ optimal_params_real_data.csv và áp dụng cho từng cặp
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from backtest_improved import ImprovedBacktestEngine, PAIRS

def load_optimal_params():
    """Đọc tham số tối ưu từ file CSV"""
    filename = 'optimal_params_real_data.csv'
    
    if not os.path.exists(filename):
        print(f"✗ Không tìm thấy file {filename}")
        print("  Vui lòng chạy optimize_real_data.py trước")
        return None
    
    try:
        df = pd.read_csv(filename)
        params_dict = {}
        
        for _, row in df.iterrows():
            pair = row['Pair']
            params_dict[pair] = {
                'position_size': row['Position Size %'] / 100,
                'take_profit': row['Take Profit %'] / 100,
                'stop_loss': row['Stop Loss %'] / 100,
                'rsi_buy': int(row['RSI Buy']),
                'rsi_sell': int(row['RSI Sell']),
                'max_dca': int(row['Max DCA']),
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        
        return params_dict
    except Exception as e:
        print(f"✗ Lỗi khi đọc file {filename}: {e}")
        return None

def backtest_pair_optimized(pair, params, start_date=None, end_date=None):
    """Backtest một cặp với tham số tối ưu"""
    filename = f"data/{pair}_ohlcv.csv"
    
    if not os.path.exists(filename):
        print(f"  ✗ Không tìm thấy file {filename}")
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
            print(f"  ✗ Không đủ dữ liệu (cần ít nhất 14 nến)")
            return None
        
        # Thêm initial_capital vào params
        engine_params = {
            'initial_capital': 10000,
            **params
        }
        
        engine = ImprovedBacktestEngine(**engine_params)
        engine.run(df)
        results = engine.get_results()
        
        if results:
            results['start_date'] = df['timestamp'].min()
            results['end_date'] = df['timestamp'].max()
            results['days'] = len(df)
        
        return results
        
    except Exception as e:
        print(f"  ✗ Lỗi khi backtest {pair}: {e}")
        return None

def main():
    """Chạy backtest với tham số tối ưu cho từng cặp"""
    print("=" * 80)
    print("BACKTEST VỚI THAM SỐ TỐI ƯU CHO TỪNG CẶP")
    print("=" * 80)
    
    # Đọc tham số tối ưu
    print("\n📖 Đang đọc tham số tối ưu...")
    optimal_params = load_optimal_params()
    
    if optimal_params is None:
        return
    
    print(f"✓ Đã đọc tham số tối ưu cho {len(optimal_params)} cặp")
    
    # Chọn khoảng thời gian test
    print("\n📅 Chọn khoảng thời gian test:")
    print("  1. 6 tháng gần nhất")
    print("  2. 1 năm gần nhất")
    print("  3. 2 năm (toàn bộ dữ liệu)")
    print("  4. Tùy chỉnh")
    
    choice = input("\nChọn (1-4, mặc định 3): ").strip() or "3"
    
    end_date = datetime.now()
    
    if choice == "1":
        start_date = end_date - timedelta(days=180)
        period_name = "6 tháng gần nhất"
    elif choice == "2":
        start_date = end_date - timedelta(days=365)
        period_name = "1 năm gần nhất"
    elif choice == "3":
        start_date = None
        period_name = "2 năm (toàn bộ)"
    else:
        start_date_str = input("Nhập ngày bắt đầu (YYYY-MM-DD): ").strip()
        end_date_str = input("Nhập ngày kết thúc (YYYY-MM-DD, Enter để dùng hôm nay): ").strip()
        start_date = pd.to_datetime(start_date_str) if start_date_str else None
        end_date = pd.to_datetime(end_date_str) if end_date_str else datetime.now()
        period_name = f"Từ {start_date_str} đến {end_date_str if end_date_str else 'hiện tại'}"
    
    print(f"\n📊 Test trên: {period_name}")
    print("=" * 80)
    
    # Chạy backtest cho từng cặp
    all_results = {}
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Backtest: {pair}")
        print(f"{'='*80}")
        
        # Kiểm tra xem có tham số tối ưu không
        if pair not in optimal_params:
            print(f"  ⚠ Không có tham số tối ưu cho {pair}, sử dụng tham số mặc định")
            params = {
                'position_size': 0.07,
                'take_profit': 0.10,
                'stop_loss': 0.04,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        else:
            params = optimal_params[pair]
            print(f"  ✓ Sử dụng tham số tối ưu:")
            print(f"    Take Profit: {params['take_profit']*100:.0f}%")
            print(f"    Stop Loss: {params['stop_loss']*100:.0f}%")
            print(f"    RSI Buy: {params['rsi_buy']}")
            print(f"    RSI Sell: {params['rsi_sell']}")
            print(f"    Position Size: {params['position_size']*100:.0f}%")
            print(f"    Max DCA: {params['max_dca']}")
        
        # Chạy backtest
        start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        results = backtest_pair_optimized(pair, params, start_date_str, end_date_str)
        all_results[pair] = results
        
        if results:
            print(f"\n  📊 KẾT QUẢ:")
            print(f"    Thời gian: {results['start_date']} đến {results['end_date']}")
            print(f"    Số ngày: {results['days']}")
            print(f"    Vốn ban đầu: ${results['initial_capital']:,.2f}")
            print(f"    Vốn cuối cùng: ${results['final_capital']:,.2f}")
            print(f"    Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%)")
            print(f"    Số lệnh: {results['total_trades']}")
            print(f"    Lệnh thắng: {results['winning_trades']}")
            print(f"    Lệnh thua: {results['losing_trades']}")
            print(f"    Win Rate: {results['win_rate']:.1f}%")
            print(f"    Lợi nhuận trung bình/lệnh: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)")
            
            if results.get('sell_reasons'):
                print(f"    Lý do bán:")
                for reason, count in results['sell_reasons'].items():
                    print(f"      {reason}: {count} lần")
        else:
            print(f"  ✗ Không có kết quả")
    
    # Tổng hợp
    print(f"\n{'='*80}")
    print("TỔNG HỢP KẾT QUẢ")
    print(f"{'='*80}")
    
    profitable_pairs = [pair for pair, r in all_results.items() if r and r['total_profit_pct'] > 0]
    losing_pairs = [pair for pair, r in all_results.items() if r and r['total_profit_pct'] <= 0]
    
    total_initial = sum(r['initial_capital'] for r in all_results.values() if r)
    total_final = sum(r['final_capital'] for r in all_results.values() if r)
    total_profit = total_final - total_initial
    total_profit_pct = (total_profit / total_initial * 100) if total_initial > 0 else 0
    total_trades = sum(r['total_trades'] for r in all_results.values() if r)
    total_winning = sum(r['winning_trades'] for r in all_results.values() if r)
    total_losing = sum(r['losing_trades'] for r in all_results.values() if r)
    overall_win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0
    
    print(f"\n📊 Thống kê tổng thể:")
    print(f"  Khoảng thời gian: {period_name}")
    print(f"  Tổng vốn ban đầu: ${total_initial:,.2f}")
    print(f"  Tổng vốn cuối cùng: ${total_final:,.2f}")
    print(f"  Tổng lợi nhuận: ${total_profit:,.2f} ({total_profit_pct:+.2f}%)")
    print(f"  Tổng số lệnh: {total_trades}")
    print(f"  Lệnh thắng: {total_winning}")
    print(f"  Lệnh thua: {total_losing}")
    print(f"  Win Rate tổng thể: {overall_win_rate:.1f}%")
    print(f"  Số cặp có lợi nhuận: {len(profitable_pairs)}/{len([r for r in all_results.values() if r])}")
    
    # Bảng so sánh
    print(f"\n{'Cặp Token':<12} {'Lợi Nhuận':>12} {'Số Lệnh':>10} {'Win Rate':>10} {'Avg Profit':>12}")
    print("-" * 70)
    
    sorted_results = sorted(
        [(pair, r) for pair, r in all_results.items() if r],
        key=lambda x: x[1]['total_profit_pct'],
        reverse=True
    )
    
    for pair, results in sorted_results:
        print(f"{pair:<12} {results['total_profit_pct']:>10.2f}% "
              f"{results['total_trades']:>10} {results['win_rate']:>8.1f}% "
              f"{results['avg_profit_pct']:>10.2f}%")
    
    # Lưu kết quả
    summary_data = []
    for pair, results in all_results.items():
        if results:
            summary_data.append({
                'Pair': pair,
                'Period': period_name,
                'Start Date': results['start_date'],
                'End Date': results['end_date'],
                'Days': results['days'],
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
                'Min Equity': results['min_equity'],
                'Take Profit': optimal_params.get(pair, {}).get('take_profit', 0) * 100 if optimal_params else 0,
                'Stop Loss': optimal_params.get(pair, {}).get('stop_loss', 0) * 100 if optimal_params else 0,
                'RSI Buy': optimal_params.get(pair, {}).get('rsi_buy', 0) if optimal_params else 0,
                'RSI Sell': optimal_params.get(pair, {}).get('rsi_sell', 0) if optimal_params else 0,
            })
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        filename = f'backtest_optimized_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df_summary.to_csv(filename, index=False)
        print(f"\n✓ Đã lưu kết quả vào {filename}")
    
    # Vẽ biểu đồ
    try:
        fig, axes = plt.subplots(len([r for r in all_results.values() if r]), 1, 
                                figsize=(14, 4 * len([r for r in all_results.values() if r])))
        
        if len([r for r in all_results.values() if r]) == 1:
            axes = [axes]
        
        for idx, (pair, results) in enumerate([(p, r) for p, r in all_results.items() if r]):
            ax = axes[idx]
            equity = results['equity_curve']
            
            ax.plot(equity, label=f'{pair} Equity Curve', linewidth=2)
            ax.axhline(y=results['initial_capital'], color='r', linestyle='--', 
                      label='Initial Capital', alpha=0.7)
            ax.set_title(f'{pair} - Final: ${results["final_capital"]:,.2f} '
                        f'({results["total_profit_pct"]:+.2f}%)', 
                        fontsize=12, fontweight='bold')
            ax.set_xlabel('Time (Candles)')
            ax.set_ylabel('Portfolio Value ($)')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_filename = f'backtest_optimized_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
        print(f"✓ Đã lưu biểu đồ vào {plot_filename}")
        plt.close()
    except Exception as e:
        print(f"\n⚠ Không thể vẽ biểu đồ: {e}")
    
    print(f"\n{'='*80}")
    print("HOÀN THÀNH")
    print(f"{'='*80}")
    print(f"""
✅ Đã chạy backtest với tham số tối ưu cho từng cặp
✅ Tổng lợi nhuận: {total_profit_pct:+.2f}%
✅ Win Rate tổng thể: {overall_win_rate:.1f}%

💡 Khuyến nghị:
   - Xem file CSV để phân tích chi tiết
   - So sánh với kết quả trước khi tối ưu
   - Paper trading với tham số này trước khi giao dịch thực
    """)

if __name__ == "__main__":
    main()


