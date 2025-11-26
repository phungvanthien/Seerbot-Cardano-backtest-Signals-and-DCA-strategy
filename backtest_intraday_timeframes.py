"""
Backtest và tạo báo cáo PNG cho các khung thời gian ngắn: 6h, 4h, 2h, 1h
Với take profit 5% và stop loss -2.5%
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from datetime import datetime, timedelta
from backtest_fixed_amount import FixedAmountBacktestEngine, PAIRS
import os

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500
TARGET_DATE = datetime(2025, 11, 26)  # Ngày mục tiêu
MAX_TRADES = 100  # Số lệnh tối đa trong mỗi báo cáo

# Cấu hình take profit và stop loss
TAKE_PROFIT_PCT = 5.0  # 5%
STOP_LOSS_PCT = -2.5   # -2.5%

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
                'take_profit': TAKE_PROFIT_PCT / 100,  # Override với 5%
                'stop_loss': abs(STOP_LOSS_PCT) / 100,  # Override với 2.5%
                'rsi_buy': int(row['RSI Buy']),
                'rsi_sell': int(row['RSI Sell']),
                'max_dca': int(row['Max DCA']),
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        return params_dict
    except:
        return {}

def backtest_timeframe(pair, params, timeframe='6H'):
    """Backtest trên một khung thời gian cụ thể"""
    # Map timeframe to filename
    timeframe_map = {
        '6H': ('6h', 8),
        '4H': ('4h', 8),
        '2H': ('2h', 7),
        '1H': ('1h', 7)
    }
    
    if timeframe not in timeframe_map:
        return None
    
    file_suffix, rsi_period = timeframe_map[timeframe]
    filename = f"data/{pair}_ohlcv_{file_suffix}.csv"
    
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
        
        # Điều chỉnh tham số cho khung ngắn hơn
        adjusted_params = params.copy()
        adjusted_params['take_profit'] = TAKE_PROFIT_PCT / 100  # Đảm bảo 5%
        adjusted_params['stop_loss'] = abs(STOP_LOSS_PCT) / 100  # Đảm bảo 2.5%
        
        # Điều chỉnh RSI cho khung ngắn hơn
        if timeframe in ['2H', '1H']:
            adjusted_params['rsi_buy'] = max(20, params['rsi_buy'] - 3)
        elif timeframe in ['4H', '6H']:
            adjusted_params['rsi_buy'] = max(20, params['rsi_buy'] - 2)
        
        params_clean = {k: v for k, v in adjusted_params.items() if k != 'position_size'}
        
        engine_params = {
            'initial_capital': INITIAL_CAPITAL,
            'fixed_amount': POSITION_SIZE_FIXED,
            'rsi_period': rsi_period,
            **params_clean
        }
        
        engine = FixedAmountBacktestEngine(**engine_params)
        engine.run(df)
        results = engine.get_results()
        
        if results:
            results['start_date'] = df['timestamp'].min()
            results['end_date'] = df['timestamp'].max()
            results['days'] = len(df)
            results['pair'] = pair
            results['timeframe'] = timeframe
            
            # Lọc lấy 100 lệnh gần nhất (gần TARGET_DATE)
            trades = results.get('trades', [])
            if trades:
                # Sắp xếp theo thời gian
                trades_sorted = sorted(trades, key=lambda x: pd.to_datetime(x['timestamp']))
                
                # Lấy các lệnh bán (SELL) gần TARGET_DATE nhất
                sell_trades = [t for t in trades_sorted if t['type'] == 'SELL']
                
                if sell_trades:
                    # Tính khoảng cách từ TARGET_DATE
                    for trade in sell_trades:
                        trade_time = pd.to_datetime(trade['timestamp'])
                        trade['days_from_target'] = abs((trade_time - TARGET_DATE).total_seconds() / 86400)
                        trade['is_before'] = trade_time <= TARGET_DATE
                    
                    # Sắp xếp: ưu tiên lệnh trước TARGET_DATE, sau đó theo khoảng cách
                    sell_trades_sorted = sorted(sell_trades, 
                                               key=lambda x: (not x['is_before'], x['days_from_target']))
                    
                    # Lấy 100 lệnh gần nhất
                    selected_sells = sell_trades_sorted[:MAX_TRADES]
                    
                    # Lấy tất cả lệnh mua liên quan đến các lệnh bán này
                    selected_sell_times = [pd.to_datetime(t['timestamp']) for t in selected_sells]
                    if selected_sell_times:
                        min_time = min(selected_sell_times)
                        max_time = max(selected_sell_times)
                        
                        # Lấy tất cả lệnh trong khoảng thời gian này
                        selected_trades = []
                        for trade in trades_sorted:
                            trade_time = pd.to_datetime(trade['timestamp'])
                            if trade_time <= max_time + timedelta(days=1):
                                selected_trades.append(trade)
                        
                        # Sắp xếp lại selected_trades theo thời gian
                        selected_trades = sorted(selected_trades, key=lambda x: pd.to_datetime(x['timestamp']))
                        
                        # Cập nhật results với trades đã lọc
                        results['trades'] = selected_trades
                        results['total_trades'] = len(selected_sells)
                        results['selected_trades_count'] = len(selected_trades)
                        results['target_date'] = TARGET_DATE.strftime('%Y-%m-%d')
        
        return results
        
    except Exception as e:
        print(f"Lỗi khi backtest {pair} {timeframe}: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_png_report(pair, timeframe, results):
    """Tạo báo cáo PNG cho một cặp token trên một khung thời gian"""
    if not results or not results.get('trades'):
        return None
    
    # Điều chỉnh kích thước figure dựa trên khung thời gian
    if timeframe in ['1H', '2H']:
        fig_height = 45
    elif timeframe in ['4H', '6H']:
        fig_height = 40
    else:
        fig_height = 35
    
    fig = plt.figure(figsize=(24, fig_height))
    fig.suptitle(f'BÁO CÁO BACKTEST - {pair}\nChiến Lược: RSI & DCA\nKhung Thời Gian: {timeframe}', 
                 fontsize=22, fontweight='bold', y=0.998)
    fig.text(0.5, 0.995, 
             f"Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | "
             f"Vốn: ${INITIAL_CAPITAL:,} | Mỗi lệnh: ${POSITION_SIZE_FIXED:,} | "
             f"Cắt lỗ: {STOP_LOSS_PCT}% | Chốt lãi: +{TAKE_PROFIT_PCT}% | 100 lệnh gần ngày 26/11/2025 nhất", 
             ha='center', fontsize=11, style='italic')
    
    y_pos = 0.97
    
    # Thông tin cơ bản
    ax_info = fig.add_axes([0.05, y_pos - 0.05, 0.9, 0.05])
    ax_info.axis('off')
    
    info_text = f"""
    Thời gian test: {results['start_date'].strftime('%d/%m/%Y')} → {results['end_date'].strftime('%d/%m/%Y')} | 
    Số nến: {results['days']} | 
    Vốn ban đầu: ${results['initial_capital']:,.2f} | 
    Vốn cuối: ${results['final_capital']:,.2f} | 
    Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%) | 
    Tổng lệnh: {results.get('selected_trades_count', results['total_trades'])} | 
    Lệnh bán: {results['total_trades']} | 
    Win Rate: {results['win_rate']:.2f}%
    """
    ax_info.text(0.02, 0.5, info_text, fontsize=10, verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='#E3F2FD', alpha=0.7))
    y_pos -= 0.07
    
    # Tham số sử dụng
    ax_params = fig.add_axes([0.05, y_pos - 0.04, 0.9, 0.04])
    ax_params.axis('off')
    
    rsi_period = 8 if timeframe in ['6H', '4H'] else 7
    params_text = f"""
    Chiến lược: RSI & DCA | 
    RSI Period: {rsi_period} | 
    Cắt lỗ: {STOP_LOSS_PCT}% | Chốt lãi: +{TAKE_PROFIT_PCT}% | 
    RSI Buy: {results.get('rsi_buy', 25)} | 
    RSI Sell: {results.get('rsi_sell', 75)} | 
    Max DCA: {results.get('max_dca', 3)} | 
    Mỗi lệnh: ${POSITION_SIZE_FIXED:,}
    """
    ax_params.text(0.02, 0.5, params_text, fontsize=10, verticalalignment='center',
                  bbox=dict(boxstyle='round', facecolor='#FFF3E0', alpha=0.7))
    y_pos -= 0.06
    
    # Thống kê
    ax_stats = fig.add_axes([0.05, y_pos - 0.06, 0.9, 0.06])
    ax_stats.axis('off')
    ax_stats.set_title('THỐNG KÊ CHI TIẾT', fontsize=14, fontweight='bold', pad=10)
    
    stats_data = [
        ['Chỉ Số', 'Giá Trị'],
        ['Lệnh thắng', f"{results['winning_trades']}"],
        ['Lệnh thua', f"{results['losing_trades']}"],
        ['Tỷ lệ thắng', f"{results['win_rate']:.2f}%"],
        ['Lợi nhuận trung bình/lệnh', f"${results['avg_profit']:,.2f}"],
        ['Lợi nhuận % trung bình', f"{results['avg_profit_pct']:+.2f}%"],
    ]
    
    if results.get('sell_reasons'):
        for reason, count in list(results['sell_reasons'].items())[:3]:
            stats_data.append([f"Lý do: {reason}", f"{count} lần"])
    
    table_stats = ax_stats.table(cellText=stats_data, cellLoc='left', loc='center', 
                                 bbox=[0, 0, 1, 1])
    table_stats.auto_set_font_size(False)
    table_stats.set_fontsize(10)
    table_stats.scale(1, 2.5)
    table_stats[(0, 0)].set_facecolor('#2C3E50')
    table_stats[(0, 1)].set_facecolor('#2C3E50')
    table_stats[(0, 0)].set_text_props(weight='bold', color='white')
    table_stats[(0, 1)].set_text_props(weight='bold', color='white')
    y_pos -= 0.08
    
    # Bảng lệnh chi tiết
    trades = results['trades']
    if trades:
        sell_trades = sorted([t for t in trades if t['type'] == 'SELL'],
                            key=lambda x: pd.to_datetime(x['timestamp']))
        
        # Hiển thị chỉ lệnh bán để bảng gọn
        trades_data = []
        trade_num = 1
        for sell in sell_trades[:MAX_TRADES]:
            trades_data.append([
                str(trade_num), pd.to_datetime(sell['timestamp']).strftime('%d/%m/%Y\n%H:%M'),
                'BÁN', f"${sell['price']:.4f}", f"{sell['amount']:.4f}",
                f"${sell.get('proceeds', 0):,.2f}", f"{sell.get('rsi', 0):.1f}",
                f"${sell.get('total_invested', 0):,.2f}", f"${sell.get('profit', 0):,.2f}",
                f"{sell.get('profit_pct', 0):+.2f}%", sell.get('reason', '')[:20]
            ])
            trade_num += 1
        
        if trades_data:
            table_height = min(0.75, 0.03 + len(trades_data) * 0.012)
            ax_trades = fig.add_axes([0.03, y_pos - table_height, 0.94, table_height])
            ax_trades.axis('off')
            ax_trades.set_title(f'BẢNG CHI TIẾT 100 LỆNH GẦN NHẤT ({len(sell_trades[:MAX_TRADES])} lệnh bán)', 
                              fontsize=13, fontweight='bold', pad=12)
            
            font_size = 8
            scale_y = 1.2
            col_widths = [0.04, 0.12, 0.06, 0.08, 0.08, 0.10, 0.06, 0.10, 0.10, 0.10, 0.16]
            
            table_trades = ax_trades.table(
                cellText=trades_data,
                colLabels=['STT', 'Ngày Giờ', 'Loại', 'Giá', 'Số Lượng', 'Vốn/Doanh Thu ($)', 
                          'RSI', 'Vốn Đầu Tư', 'Lợi Nhuận ($)', 'Lợi Nhuận %', 'Lý Do'],
                cellLoc='center', loc='center', bbox=[0, 0, 1, 1],
                colWidths=col_widths
            )
            table_trades.auto_set_font_size(False)
            table_trades.set_fontsize(font_size)
            table_trades.scale(1, scale_y)
            
            # Header
            for i in range(11):
                table_trades[(0, i)].set_facecolor('#1A237E')
                table_trades[(0, i)].set_text_props(weight='bold', color='white', size=font_size+1)
            
            # Color code rows
            for i in range(1, len(trades_data) + 1):
                row = trades_data[i-1]
                if row[2] == 'BÁN':
                    try:
                        profit_str = row[8] if len(row) > 8 else '0'
                        profit = float(profit_str.replace('$', '').replace(',', '').replace(' ', '')) if profit_str else 0
                        if profit > 0:
                            for j in [6, 7, 8, 9]:
                                if j < len(row):
                                    table_trades[(i, j)].set_facecolor('#C8E6C9')
                        else:
                            for j in [6, 7, 8, 9]:
                                if j < len(row):
                                    table_trades[(i, j)].set_facecolor('#FFCDD2')
                    except:
                        pass
            
            y_pos -= (table_height + 0.02)
    
    # Equity curve
    if results.get('equity_curve'):
        ax_equity = fig.add_axes([0.05, y_pos - 0.12, 0.9, 0.12])
        equity = results['equity_curve']
        ax_equity.plot(equity, linewidth=2.5, color='#1976D2', label='Equity Curve')
        ax_equity.axhline(y=results['initial_capital'], color='red', linestyle='--',
                         linewidth=2, label='Vốn ban đầu', alpha=0.7)
        ax_equity.fill_between(range(len(equity)), results['initial_capital'], equity,
                              where=np.array(equity) >= results['initial_capital'],
                              alpha=0.3, color='green')
        ax_equity.fill_between(range(len(equity)), results['initial_capital'], equity,
                              where=np.array(equity) < results['initial_capital'],
                              alpha=0.3, color='red')
        ax_equity.set_title(f'Equity Curve - {pair} ({timeframe})', fontsize=12, fontweight='bold')
        ax_equity.set_xlabel('Thời gian (Nến)', fontsize=10)
        ax_equity.set_ylabel('Giá trị Portfolio ($)', fontsize=10)
        ax_equity.legend(fontsize=9)
        ax_equity.grid(True, alpha=0.3)
        y_pos -= 0.14
    
    # Kết luận
    ax_conclusion = fig.add_axes([0.05, y_pos - 0.05, 0.9, 0.05])
    ax_conclusion.axis('off')
    
    conclusion_text = f"""
    KẾT LUẬN: {pair} - Chiến lược RSI & DCA trên khung {timeframe} | 
    Cắt lỗ: {STOP_LOSS_PCT}% | Chốt lãi: +{TAKE_PROFIT_PCT}% | 
    Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%) | 
    {results['total_trades']} lệnh bán | 
    Win Rate: {results['win_rate']:.2f}% | 
    Lợi nhuận trung bình: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)
    """
    
    ax_conclusion.text(0.02, 0.5, conclusion_text, fontsize=11, verticalalignment='center',
                      bbox=dict(boxstyle='round', facecolor='#E8F5E9', alpha=0.7), weight='bold')
    
    # Lưu file
    safe_pair = pair.replace('/', '_')
    filename = f"Report_{safe_pair}_{timeframe}.png"
    
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return filename

def main():
    """Tạo báo cáo PNG cho tất cả các cặp và khung thời gian"""
    print("=" * 80)
    print("BACKTEST VÀ TẠO BÁO CÁO PNG - KHUNG THỜI GIAN NGẮN")
    print("=" * 80)
    print(f"Khung thời gian: 6H, 4H, 2H, 1H")
    print(f"Take Profit: +{TAKE_PROFIT_PCT}% | Stop Loss: {STOP_LOSS_PCT}%")
    print(f"Mỗi báo cáo chứa 100 lệnh gần ngày {TARGET_DATE.strftime('%d/%m/%Y')} nhất")
    print("=" * 80)
    
    optimal_params = load_optimal_params()
    timeframes = ['6H', '4H', '2H', '1H']
    
    generated_files = []
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Đang xử lý: {pair}")
        print(f"{'='*80}")
        
        if pair in optimal_params:
            params = optimal_params[pair]
        else:
            params = {
                'take_profit': TAKE_PROFIT_PCT / 100,
                'stop_loss': abs(STOP_LOSS_PCT) / 100,
                'rsi_buy': 25,
                'rsi_sell': 75,
                'max_dca': 3,
                'use_trend_filter': False,
                'use_volume_filter': False
            }
        
        for timeframe in timeframes:
            print(f"\n  → Khung {timeframe}...")
            results = backtest_timeframe(pair, params, timeframe)
            
            if results and results.get('trades'):
                sell_count = len([t for t in results['trades'] if t['type'] == 'SELL'])
                print(f"    ✓ Có {sell_count} lệnh bán")
                filename = generate_png_report(pair, timeframe, results)
                if filename:
                    generated_files.append(filename)
                    print(f"    ✓ Đã tạo: {filename}")
                else:
                    print(f"    ✗ Không thể tạo báo cáo")
            else:
                print(f"    ✗ Không có dữ liệu")
    
    print(f"\n{'='*80}")
    print("✅ HOÀN THÀNH!")
    print(f"{'='*80}")
    print(f"\nĐã tạo {len(generated_files)} báo cáo PNG:")
    for f in generated_files:
        print(f"  - {f}")
    print(f"\n{'='*80}")

if __name__ == "__main__":
    main()

