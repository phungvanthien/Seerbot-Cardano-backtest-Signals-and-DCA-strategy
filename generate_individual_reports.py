"""
Tạo báo cáo PNG riêng cho từng cặp token trên từng khung thời gian
Mỗi báo cáo chứa 100 lệnh gần nhất (gần ngày 26/11/2025)
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
        rsi_period = 14
    elif timeframe == '12H':
        filename = f"data/{pair}_ohlcv_12h.csv"
        rsi_period = 10
    elif timeframe == '8H':
        filename = f"data/{pair}_ohlcv_8h.csv"
        rsi_period = 10
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
        
        # Điều chỉnh tham số cho khung ngắn hơn
        adjusted_params = params.copy()
        if timeframe in ['12H', '8H']:
            adjusted_params['take_profit'] = params['take_profit'] * 0.8
            adjusted_params['rsi_buy'] = max(20, params['rsi_buy'] - 2)
            adjusted_params['stop_loss'] = params['stop_loss'] * 0.9
        
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
                    # Tính khoảng cách từ TARGET_DATE (chỉ tính lệnh trước TARGET_DATE)
                    for trade in sell_trades:
                        trade_time = pd.to_datetime(trade['timestamp'])
                        # Ưu tiên lệnh gần TARGET_DATE nhất (có thể trước hoặc sau)
                        trade['days_from_target'] = abs((trade_time - TARGET_DATE).total_seconds() / 86400)
                        trade['is_before'] = trade_time <= TARGET_DATE
                    
                    # Sắp xếp: ưu tiên lệnh trước TARGET_DATE, sau đó theo khoảng cách
                    sell_trades_sorted = sorted(sell_trades, 
                                               key=lambda x: (not x['is_before'], x['days_from_target']))
                    
                    # Lấy 100 lệnh gần nhất (hoặc tất cả nếu ít hơn 100)
                    selected_sells = sell_trades_sorted[:MAX_TRADES]
                    
                    # Lấy tất cả lệnh mua liên quan đến các lệnh bán này
                    selected_sell_times = [pd.to_datetime(t['timestamp']) for t in selected_sells]
                    if selected_sell_times:
                        min_time = min(selected_sell_times)
                        max_time = max(selected_sell_times)
                        
                        # Lấy tất cả lệnh trong khoảng thời gian này (bao gồm cả lệnh mua trước lệnh bán đầu tiên)
                        selected_trades = []
                        for trade in trades_sorted:
                            trade_time = pd.to_datetime(trade['timestamp'])
                            # Lấy lệnh từ trước lệnh bán đầu tiên một chút đến lệnh bán cuối cùng
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
    if timeframe in ['8H', '12H']:
        # Khung ngắn hơn có nhiều lệnh hơn, cần figure lớn hơn
        fig_height = 40 if timeframe == '8H' else 35
        fig = plt.figure(figsize=(24, fig_height))
    else:
        fig = plt.figure(figsize=(20, 28))
    
    fig.suptitle(f'BÁO CÁO BACKTEST - {pair}\nChiến Lược: RSI14 & DCA\nKhung Thời Gian: {timeframe}', 
                 fontsize=22, fontweight='bold', y=0.998)
    fig.text(0.5, 0.995, 
             f"Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | "
             f"Vốn: ${INITIAL_CAPITAL:,} | Mỗi lệnh: ${POSITION_SIZE_FIXED:,} | "
             f"Cắt lỗ: -2.5% | Chốt lãi: +5% | 100 lệnh gần ngày 26/11/2025 nhất", 
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
    
    params_text = f"""
    Chiến lược: RSI14 & DCA | 
    RSI Period: {14 if timeframe == '1D' else 10} | 
    Cắt lỗ: -2.5% | Chốt lãi: +5% | 
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
    
    # Bảng lệnh chi tiết (100 lệnh)
    trades = results['trades']
    if trades:
        sell_trades = sorted([t for t in trades if t['type'] == 'SELL'],
                            key=lambda x: pd.to_datetime(x['timestamp']))
        buy_trades = sorted([t for t in trades if t['type'] in ['BUY', 'DCA']],
                           key=lambda x: pd.to_datetime(x['timestamp']))
        
        # Tạo bảng với 100 lệnh bán gần nhất
        # Với khung 8H và 12H: chỉ hiển thị lệnh bán để bảng gọn và dễ đọc
        if timeframe in ['8H', '12H']:
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
        else:
            # Khung 1D: hiển thị cả lệnh mua và bán
            trades_data = []
            trade_num = 1
            buy_index = 0
            
            for sell in sell_trades[:MAX_TRADES]:
                sell_time = pd.to_datetime(sell['timestamp'])
                
                # Tìm lệnh mua tương ứng
                related_buys = []
                while buy_index < len(buy_trades):
                    buy_time = pd.to_datetime(buy_trades[buy_index]['timestamp'])
                    if buy_time < sell_time:
                        related_buys.append(buy_trades[buy_index])
                        buy_index += 1
                    else:
                        break
                
                # Thêm lệnh mua
                for buy in related_buys:
                    trades_data.append([
                        '', pd.to_datetime(buy['timestamp']).strftime('%d/%m/%Y %H:%M'),
                        buy['type'], f"${buy['price']:.4f}", f"{buy['amount']:.4f}",
                        f"${buy.get('capital', 0):,.2f}", f"{buy.get('rsi', 0):.1f}", 
                        '', '', '', ''
                    ])
                
                # Thêm lệnh bán
                trades_data.append([
                    str(trade_num), pd.to_datetime(sell['timestamp']).strftime('%d/%m/%Y %H:%M'),
                    '<b>BÁN</b>', f"${sell['price']:.4f}", f"{sell['amount']:.4f}",
                    f"${sell.get('proceeds', 0):,.2f}", f"{sell.get('rsi', 0):.1f}",
                    f"${sell.get('total_invested', 0):,.2f}", f"${sell.get('profit', 0):,.2f}",
                    f"{sell.get('profit_pct', 0):+.2f}%", sell.get('reason', '')[:15]
                ])
                trade_num += 1
        
        if trades_data:
            # Điều chỉnh kích thước bảng dựa trên số lượng lệnh
            num_sell_trades = len(sell_trades[:MAX_TRADES])
            if timeframe in ['8H', '12H']:
                # Khung ngắn hơn: bảng đã được tạo chỉ với lệnh bán
                # Tính toán chiều cao bảng dựa trên số dòng
                table_height = min(0.75, 0.03 + len(trades_data) * 0.012)  # Điều chỉnh theo số dòng
            else:
                # Khung 1D: giữ nguyên cách hiển thị cũ
                table_height = 0.5
            
            ax_trades = fig.add_axes([0.03, y_pos - table_height, 0.94, table_height])
            ax_trades.axis('off')
            ax_trades.set_title(f'BẢNG CHI TIẾT 100 LỆNH GẦN NHẤT ({num_sell_trades} lệnh bán)', 
                              fontsize=13, fontweight='bold', pad=12)
            
            # Điều chỉnh font size và scale dựa trên khung thời gian
            if timeframe in ['8H', '12H']:
                font_size = 8
                scale_y = 1.2
                col_widths = [0.04, 0.12, 0.06, 0.08, 0.08, 0.10, 0.06, 0.10, 0.10, 0.10, 0.16]
            else:
                font_size = 7
                scale_y = 1.5
                col_widths = None
            
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
                if row[2] == 'BÁN' or row[2] == '<b>BÁN</b>':
                    try:
                        profit_str = row[8] if len(row) > 8 else '0'
                        profit = float(profit_str.replace('$', '').replace(',', '').replace(' ', '')) if profit_str else 0
                        if profit > 0:
                            for j in [6, 7, 8, 9]:  # Vốn đầu tư, Lợi nhuận, Lợi nhuận %
                                if j < len(row):
                                    table_trades[(i, j)].set_facecolor('#C8E6C9')
                        else:
                            for j in [6, 7, 8, 9]:
                                if j < len(row):
                                    table_trades[(i, j)].set_facecolor('#FFCDD2')
                    except:
                        pass
                else:
                    # Lệnh mua (nếu có)
                    for j in range(11):
                        if j < len(row):
                            table_trades[(i, j)].set_facecolor('#F5F5F5')
            
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
    KẾT LUẬN: {pair} - Chiến lược RSI14 & DCA trên khung {timeframe} | 
    Cắt lỗ: -2.5% | Chốt lãi: +5% | 
    Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%) | 
    {results['total_trades']} lệnh bán | 
    Win Rate: {results['win_rate']:.2f}% | 
    Lợi nhuận trung bình: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)
    """
    
    ax_conclusion.text(0.02, 0.5, conclusion_text, fontsize=11, verticalalignment='center',
                      bbox=dict(boxstyle='round', facecolor='#E8F5E9', alpha=0.7), weight='bold')
    
    # Lưu file - ghi đè lên file cũ cho khung 8H và 12H
    safe_pair = pair.replace('/', '_')
    if timeframe in ['8H', '12H']:
        # Tìm và xóa file cũ cùng tên (không có timestamp)
        old_pattern = f"Report_{safe_pair}_{timeframe}_*.png"
        import glob
        old_files = glob.glob(old_pattern)
        for old_file in old_files:
            try:
                os.remove(old_file)
            except:
                pass
        # Tạo file mới với tên cố định (không có timestamp)
        filename = f"Report_{safe_pair}_{timeframe}.png"
    else:
        # Khung 1D: giữ timestamp
        filename = f"Report_{safe_pair}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return filename

def main():
    """Tạo báo cáo PNG cho tất cả các cặp và khung thời gian"""
    print("=" * 80)
    print("TẠO BÁO CÁO PNG - MỖI CẶP, MỖI KHUNG THỜI GIAN")
    print("=" * 80)
    print(f"Mỗi báo cáo chứa 100 lệnh gần ngày {TARGET_DATE.strftime('%d/%m/%Y')} nhất")
    print("=" * 80)
    
    optimal_params = load_optimal_params()
    timeframes = ['1D', '12H', '8H']
    
    generated_files = []
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Đang xử lý: {pair}")
        print(f"{'='*80}")
        
        if pair in optimal_params:
            params = optimal_params[pair]
        else:
            params = {
                'take_profit': 0.10, 'stop_loss': 0.04, 'rsi_buy': 25,
                'rsi_sell': 75, 'max_dca': 3, 'use_trend_filter': False, 'use_volume_filter': False
            }
        
        for timeframe in timeframes:
            print(f"\n  → Khung {timeframe}...")
            results = backtest_timeframe(pair, params, timeframe)
            
            if results and results.get('trades'):
                print(f"    ✓ Có {len([t for t in results['trades'] if t['type'] == 'SELL'])} lệnh bán")
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

