"""
Script tạo báo cáo PNG chi tiết về backtest
Bao gồm: phương pháp, thống kê lệnh, tỷ lệ chính xác, lợi nhuận
Vốn: $10,000, mỗi lệnh: $500
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_agg import FigureCanvasAgg
from datetime import datetime
from backtest_fixed_amount import FixedAmountBacktestEngine, PAIRS
import os

# Tham số
INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500  # $500 mỗi lệnh

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

def backtest_with_fixed_amount(pair, params, start_date=None, end_date=None):
    """Backtest với số tiền cố định $500 mỗi lệnh"""
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
        
        if start_date:
            df = df[df['timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['timestamp'] <= pd.to_datetime(end_date)]
        
        if len(df) < 14:
            return None
        
        # Loại bỏ position_size khỏi params
        params_clean = {k: v for k, v in params.items() if k != 'position_size'}
        
        engine_params = {
            'initial_capital': INITIAL_CAPITAL,
            'fixed_amount': POSITION_SIZE_FIXED,
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
        
        return results
        
    except Exception as e:
        print(f"Lỗi khi backtest {pair}: {e}")
        return None

def create_png_report():
    """Tạo báo cáo PNG"""
    print("=" * 80)
    print("TẠO BÁO CÁO PNG CHI TIẾT")
    print("=" * 80)
    
    # Đọc tham số tối ưu
    optimal_params = load_optimal_params()
    
    # Chạy backtest cho tất cả các cặp
    print("\n📊 Đang chạy backtest cho tất cả các cặp...")
    all_results = {}
    
    for pair in PAIRS:
        print(f"  Đang xử lý {pair}...")
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
        
        results = backtest_with_fixed_amount(pair, params)
        all_results[pair] = results
    
    # Tạo figure lớn cho toàn bộ báo cáo
    fig = plt.figure(figsize=(16, 24))
    fig.suptitle('BÁO CÁO BACKTEST CHIẾN LƯỢC RSI14 + DCA\nCardano DEX Trading Strategy', 
                 fontsize=20, fontweight='bold', y=0.995)
    
    # Thêm thông tin ngày tạo
    fig.text(0.5, 0.98, f"Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 
             ha='center', fontsize=10, style='italic')
    
    current_y = 0.96
    
    # 1. Phương pháp backtest
    ax1 = fig.add_axes([0.1, current_y - 0.08, 0.8, 0.08])
    ax1.axis('off')
    method_text = """
    PHƯƠNG PHÁP BACKTEST:
    • Nguồn dữ liệu: CryptoCompare API (dữ liệu thực) cho iBTCUSDM, iETHUSDM, ADAUSDM (2 năm)
    • Chiến lược: Mua khi RSI14 ≤ ngưỡng mua, DCA tại nến đỏ, Bán khi RSI14 ≥ ngưỡng bán hoặc Take Profit/Stop Loss
    • Vốn ban đầu: $10,000 | Số tiền mỗi lệnh: $500 (cố định) | Tham số tối ưu cho từng cặp
    • Quản lý rủi ro: Stop Loss 3-4%, Trailing Stop 3%, Giới hạn DCA 2-3 lần
    """
    ax1.text(0, 0.5, method_text, fontsize=11, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    current_y -= 0.1
    
    # 2. Tổng hợp kết quả
    ax2 = fig.add_axes([0.1, current_y - 0.12, 0.8, 0.12])
    ax2.axis('off')
    ax2.set_title('TỔNG HỢP KẾT QUẢ', fontsize=14, fontweight='bold', pad=10)
    
    summary_data = []
    total_initial = 0
    total_final = 0
    
    for pair in PAIRS:
        if all_results.get(pair) and all_results[pair] is not None:
            r = all_results[pair]
            total_initial += r['initial_capital']
            total_final += r['final_capital']
            summary_data.append([
                pair,
                f"${r['initial_capital']:,.2f}",
                f"${r['final_capital']:,.2f}",
                f"${r['total_profit']:,.2f}",
                f"{r['total_profit_pct']:+.2f}%",
                str(r['total_trades']),
                f"{r['win_rate']:.1f}%"
            ])
    
    summary_data.append([
        'TỔNG',
        f"${total_initial:,.2f}",
        f"${total_final:,.2f}",
        f"${total_final - total_initial:,.2f}",
        f"{(total_final - total_initial) / total_initial * 100:+.2f}%" if total_initial > 0 else "0.00%",
        '',
        ''
    ])
    
    table = ax2.table(cellText=summary_data,
                     colLabels=['Cặp Token', 'Vốn Ban Đầu', 'Vốn Cuối', 'Lợi Nhuận', 'Lợi Nhuận %', 'Số Lệnh', 'Win Rate'],
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # Style cho header
    for i in range(7):
        table[(0, i)].set_facecolor('#4A90E2')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Style cho hàng tổng
    if summary_data:
        for i in range(7):
            table[(len(summary_data), i)].set_facecolor('#E8F4F8')
            table[(len(summary_data), i)].set_text_props(weight='bold')
    
    current_y -= 0.14
    
    # 3. Chi tiết từng cặp
    pair_count = 0
    for pair in PAIRS:
        if not all_results.get(pair) or all_results[pair] is None:
            continue
        
        if pair_count >= 3:  # Chỉ hiển thị 3 cặp đầu tiên để tránh quá dài
            break
        
        results = all_results[pair]
        
        # Thông tin cơ bản
        ax_info = fig.add_axes([0.1, current_y - 0.15, 0.8, 0.15])
        ax_info.axis('off')
        ax_info.set_title(f'CHI TIẾT CẶP: {pair}', fontsize=12, fontweight='bold', pad=10)
        
        info_text = f"""
        Thời gian: {results['start_date'].strftime('%d/%m/%Y')} đến {results['end_date'].strftime('%d/%m/%Y')} ({results['days']} ngày)
        Vốn ban đầu: ${results['initial_capital']:,.2f} | Vốn cuối: ${results['final_capital']:,.2f} | Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%)
        Số lệnh: {results['total_trades']} | Lệnh thắng: {results['winning_trades']} | Lệnh thua: {results['losing_trades']} | Win Rate: {results['win_rate']:.2f}%
        Lợi nhuận trung bình/lệnh: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)
        """
        
        if pair in optimal_params:
            params = optimal_params[pair]
            params_text = f"Tham số: Take Profit {params['take_profit']*100:.0f}% | Stop Loss {params['stop_loss']*100:.0f}% | RSI Buy {params['rsi_buy']} | RSI Sell {params['rsi_sell']} | Max DCA {params['max_dca']} | Mỗi lệnh: ${POSITION_SIZE_FIXED:,.2f}"
        else:
            params_text = f"Tham số mặc định | Mỗi lệnh: ${POSITION_SIZE_FIXED:,.2f}"
        
        ax_info.text(0.05, 0.7, info_text, fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
        ax_info.text(0.05, 0.2, params_text, fontsize=9, style='italic',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.3))
        
        current_y -= 0.17
        
        # Bảng chi tiết lệnh (chỉ hiển thị 10 lệnh đầu)
        trades = results['trades']
        if trades:
            sell_trades = [t for t in trades if t['type'] == 'SELL']
            
            if sell_trades:
                ax_trades = fig.add_axes([0.1, current_y - 0.2, 0.8, 0.2])
                ax_trades.axis('off')
                ax_trades.set_title(f'Bảng Chi Tiết Lệnh Giao Dịch - {pair} (Hiển thị 10 lệnh đầu)', 
                                   fontsize=10, fontweight='bold', pad=5)
                
                trades_data = []
                for i, sell in enumerate(sell_trades[:10]):  # Chỉ 10 lệnh đầu
                    trades_data.append([
                        str(i+1),
                        pd.to_datetime(sell['timestamp']).strftime('%d/%m/%Y'),
                        f"${sell['price']:.4f}",
                        f"${sell.get('proceeds', 0):,.2f}",
                        f"${sell.get('profit', 0):,.2f}",
                        f"{sell.get('profit_pct', 0):+.2f}%",
                        f"{sell.get('rsi', 0):.1f}",
                        sell.get('reason', '')
                    ])
                
                if trades_data:
                    table_trades = ax_trades.table(cellText=trades_data,
                                                  colLabels=['STT', 'Ngày', 'Giá Bán', 'Doanh Thu', 'Lợi Nhuận', 'Lợi Nhuận %', 'RSI', 'Lý Do'],
                                                  cellLoc='center',
                                                  loc='center',
                                                  bbox=[0, 0, 1, 1])
                    table_trades.auto_set_font_size(False)
                    table_trades.set_fontsize(8)
                    table_trades.scale(1, 1.5)
                    
                    # Style
                    for i in range(8):
                        table_trades[(0, i)].set_facecolor('#2C3E50')
                        table_trades[(0, i)].set_text_props(weight='bold', color='white')
                    
                    # Màu cho lợi nhuận
                    for i in range(1, len(trades_data) + 1):
                        profit = float(trades_data[i-1][4].replace('$', '').replace(',', ''))
                        if profit > 0:
                            table_trades[(i, 4)].set_facecolor('#90EE90')
                            table_trades[(i, 5)].set_facecolor('#90EE90')
                        else:
                            table_trades[(i, 4)].set_facecolor('#FFB6C1')
                            table_trades[(i, 5)].set_facecolor('#FFB6C1')
                
                current_y -= 0.22
        
        # Biểu đồ equity curve
        if results.get('equity_curve'):
            ax_equity = fig.add_axes([0.1, current_y - 0.12, 0.8, 0.12])
            equity = results['equity_curve']
            ax_equity.plot(equity, linewidth=2, color='#2E86AB', label='Equity Curve')
            ax_equity.axhline(y=results['initial_capital'], color='r', linestyle='--', 
                             label='Vốn ban đầu', alpha=0.7)
            ax_equity.set_title(f'Equity Curve - {pair}', fontsize=10, fontweight='bold')
            ax_equity.set_xlabel('Thời gian (Nến)')
            ax_equity.set_ylabel('Giá trị Portfolio ($)')
            ax_equity.legend()
            ax_equity.grid(True, alpha=0.3)
            current_y -= 0.14
        
        pair_count += 1
    
    # 4. Kết luận
    ax_conclusion = fig.add_axes([0.1, current_y - 0.1, 0.8, 0.1])
    ax_conclusion.axis('off')
    ax_conclusion.set_title('KẾT LUẬN VÀ KHUYẾN NGHỊ', fontsize=14, fontweight='bold', pad=10)
    
    conclusion_text = f"""
    Tổng vốn ban đầu: ${total_initial:,.2f} | Tổng vốn cuối: ${total_final:,.2f} | Tổng lợi nhuận: ${total_final - total_initial:,.2f} ({(total_final - total_initial) / total_initial * 100:+.2f}%)
    Số cặp có lợi nhuận: {len([p for p in PAIRS if all_results.get(p) and all_results[p] and all_results[p]['total_profit_pct'] > 0])}/{len([p for p in PAIRS if all_results.get(p) and all_results[p]])}
    Khuyến nghị: Ưu tiên giao dịch các cặp có dữ liệu thực (ADAUSDM, iBTCUSDM, iETHUSDM), sử dụng tham số tối ưu, paper trading trước khi giao dịch thực.
    Lưu ý: Kết quả backtest không đảm bảo hiệu suất tương lai. Luôn quản lý rủi ro cẩn thận.
    """
    
    ax_conclusion.text(0.05, 0.5, conclusion_text, fontsize=10, verticalalignment='center',
                      bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
    
    # Lưu file
    filename = f"Backtest_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✓ Đã tạo báo cáo PNG: {filename}")
    plt.close()
    
    return filename

if __name__ == "__main__":
    try:
        filename = create_png_report()
        print(f"\n{'='*80}")
        print(f"✅ HOÀN THÀNH!")
        print(f"📄 File PNG: {filename}")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        import traceback
        traceback.print_exc()


