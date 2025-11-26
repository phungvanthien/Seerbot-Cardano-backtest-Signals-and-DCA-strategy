"""
Script tạo báo cáo PNG đầy đủ với tất cả các cặp và chi tiết lệnh
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from datetime import datetime
from backtest_fixed_amount import FixedAmountBacktestEngine, PAIRS
import os

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500

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

def create_full_png_report():
    """Tạo báo cáo PNG đầy đủ"""
    print("=" * 80)
    print("TẠO BÁO CÁO PNG ĐẦY ĐỦ")
    print("=" * 80)
    
    optimal_params = load_optimal_params()
    print("\n📊 Đang chạy backtest...")
    all_results = {}
    
    for pair in PAIRS:
        print(f"  Đang xử lý {pair}...")
        if pair in optimal_params:
            params = optimal_params[pair]
        else:
            params = {
                'take_profit': 0.10, 'stop_loss': 0.04, 'rsi_buy': 25,
                'rsi_sell': 75, 'max_dca': 3, 'use_trend_filter': False, 'use_volume_filter': False
            }
        results = backtest_with_fixed_amount(pair, params)
        all_results[pair] = results
    
    # Tính toán tổng hợp
    total_initial = sum(r['initial_capital'] for r in all_results.values() if r)
    total_final = sum(r['final_capital'] for r in all_results.values() if r)
    total_profit = total_final - total_initial
    total_profit_pct = (total_profit / total_initial * 100) if total_initial > 0 else 0
    
    # Tạo figure lớn
    fig = plt.figure(figsize=(20, 30))
    fig.suptitle('BÁO CÁO BACKTEST CHIẾN LƯỢC RSI14 + DCA\nCardano DEX Trading Strategy - Dữ Liệu Thực', 
                 fontsize=22, fontweight='bold', y=0.998)
    fig.text(0.5, 0.995, f"Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Vốn: ${INITIAL_CAPITAL:,} | Mỗi lệnh: ${POSITION_SIZE_FIXED:,}", 
             ha='center', fontsize=11, style='italic')
    
    y_pos = 0.97
    
    # 1. Phương pháp
    ax1 = fig.add_axes([0.05, y_pos - 0.06, 0.9, 0.06])
    ax1.axis('off')
    method_text = """PHƯƠNG PHÁP BACKTEST: Nguồn dữ liệu thực từ CryptoCompare API (2 năm) cho iBTCUSDM, iETHUSDM, ADAUSDM | 
    Chiến lược: Mua khi RSI14 ≤ ngưỡng mua (tối ưu), DCA tại nến đỏ (tối đa 2-3 lần), Bán khi RSI14 ≥ ngưỡng bán hoặc Take Profit/Stop Loss | 
    Quản lý rủi ro: Stop Loss 3-4%, Trailing Stop 3%, Tham số được tối ưu riêng cho từng cặp token"""
    ax1.text(0.02, 0.5, method_text, fontsize=11, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='#E8F4F8', alpha=0.5), wrap=True)
    y_pos -= 0.08
    
    # 2. Tổng hợp
    ax2 = fig.add_axes([0.05, y_pos - 0.1, 0.9, 0.1])
    ax2.axis('off')
    ax2.set_title('TỔNG HỢP KẾT QUẢ', fontsize=16, fontweight='bold', pad=15)
    
    summary_data = []
    for pair in PAIRS:
        if all_results.get(pair) and all_results[pair]:
            r = all_results[pair]
            summary_data.append([
                pair, f"${r['initial_capital']:,.0f}", f"${r['final_capital']:,.0f}",
                f"${r['total_profit']:,.2f}", f"{r['total_profit_pct']:+.2f}%",
                str(r['total_trades']), f"{r['win_rate']:.1f}%"
            ])
    
    summary_data.append([
        'TỔNG', f"${total_initial:,.0f}", f"${total_final:,.0f}",
        f"${total_profit:,.2f}", f"{total_profit_pct:+.2f}%", '', ''
    ])
    
    table2 = ax2.table(cellText=summary_data,
                      colLabels=['Cặp Token', 'Vốn Ban Đầu', 'Vốn Cuối', 'Lợi Nhuận', 'Lợi Nhuận %', 'Số Lệnh', 'Win Rate'],
                      cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
    table2.auto_set_font_size(False)
    table2.set_fontsize(10)
    table2.scale(1, 2.2)
    for i in range(7):
        table2[(0, i)].set_facecolor('#2C3E50')
        table2[(0, i)].set_text_props(weight='bold', color='white')
    if summary_data:
        for i in range(7):
            table2[(len(summary_data), i)].set_facecolor('#FFD700')
            table2[(len(summary_data), i)].set_text_props(weight='bold')
    y_pos -= 0.12
    
    # 3. Chi tiết từng cặp
    for idx, pair in enumerate(PAIRS):
        if not all_results.get(pair) or not all_results[pair]:
            continue
        
        results = all_results[pair]
        
        # Thông tin cơ bản
        ax_info = fig.add_axes([0.05, y_pos - 0.08, 0.9, 0.08])
        ax_info.axis('off')
        ax_info.set_title(f'{idx+1}. CHI TIẾT CẶP: {pair}', fontsize=14, fontweight='bold', pad=10)
        
        info_lines = [
            f"Thời gian: {results['start_date'].strftime('%d/%m/%Y')} → {results['end_date'].strftime('%d/%m/%Y')} ({results['days']} ngày)",
            f"Vốn: ${results['initial_capital']:,.2f} → ${results['final_capital']:,.2f} | Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%)",
            f"Lệnh: {results['total_trades']} (Thắng: {results['winning_trades']}, Thua: {results['losing_trades']}) | Win Rate: {results['win_rate']:.2f}% | Avg Profit: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)"
        ]
        
        if pair in optimal_params:
            p = optimal_params[pair]
            params_text = f"Tham số: TP {p['take_profit']*100:.0f}% | SL {p['stop_loss']*100:.0f}% | RSI Buy {p['rsi_buy']} | RSI Sell {p['rsi_sell']} | Max DCA {p['max_dca']} | Mỗi lệnh: ${POSITION_SIZE_FIXED:,.0f}"
        else:
            params_text = f"Tham số mặc định | Mỗi lệnh: ${POSITION_SIZE_FIXED:,.0f}"
        
        ax_info.text(0.02, 0.6, '\n'.join(info_lines), fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='#E3F2FD', alpha=0.5))
        ax_info.text(0.02, 0.1, params_text, fontsize=9, style='italic',
                    bbox=dict(boxstyle='round', facecolor='#FFF9C4', alpha=0.5))
        y_pos -= 0.1
        
        # Bảng lệnh (tất cả lệnh)
        trades = results['trades']
        if trades:
            sell_trades = sorted([t for t in trades if t['type'] == 'SELL'], 
                                key=lambda x: pd.to_datetime(x['timestamp']))
            
            if sell_trades:
                num_trades = len(sell_trades)
                rows_per_page = 15
                pages = (num_trades + rows_per_page - 1) // rows_per_page
                
                for page in range(min(pages, 2)):  # Tối đa 2 trang
                    start_idx = page * rows_per_page
                    end_idx = min(start_idx + rows_per_page, num_trades)
                    page_trades = sell_trades[start_idx:end_idx]
                    
                    ax_trades = fig.add_axes([0.05, y_pos - 0.15, 0.9, 0.15])
                    ax_trades.axis('off')
                    title = f'Bảng Chi Tiết Lệnh - {pair}'
                    if pages > 1:
                        title += f' (Trang {page+1}/{pages})'
                    ax_trades.set_title(title, fontsize=11, fontweight='bold', pad=5)
                    
                    trades_data = []
                    for i, sell in enumerate(page_trades):
                        trades_data.append([
                            str(start_idx + i + 1),
                            pd.to_datetime(sell['timestamp']).strftime('%d/%m/%Y'),
                            f"${sell['price']:.4f}",
                            f"${sell.get('proceeds', 0):,.2f}",
                            f"${sell.get('total_invested', 0):,.2f}",
                            f"${sell.get('profit', 0):,.2f}",
                            f"{sell.get('profit_pct', 0):+.2f}%",
                            f"{sell.get('rsi', 0):.1f}",
                            sell.get('reason', '')[:15]
                        ])
                    
                    if trades_data:
                        table_trades = ax_trades.table(cellText=trades_data,
                                                      colLabels=['STT', 'Ngày', 'Giá Bán', 'Doanh Thu', 'Vốn Đầu Tư', 'Lợi Nhuận', 'Lợi Nhuận %', 'RSI', 'Lý Do'],
                                                      cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
                        table_trades.auto_set_font_size(False)
                        table_trades.set_fontsize(8)
                        table_trades.scale(1, 1.8)
                        
                        for i in range(9):
                            table_trades[(0, i)].set_facecolor('#1A237E')
                            table_trades[(0, i)].set_text_props(weight='bold', color='white')
                        
                        for i in range(1, len(trades_data) + 1):
                            profit = float(trades_data[i-1][5].replace('$', '').replace(',', ''))
                            if profit > 0:
                                table_trades[(i, 5)].set_facecolor('#C8E6C9')
                                table_trades[(i, 6)].set_facecolor('#C8E6C9')
                            else:
                                table_trades[(i, 5)].set_facecolor('#FFCDD2')
                                table_trades[(i, 6)].set_facecolor('#FFCDD2')
                    
                    y_pos -= 0.17
        
        # Equity curve
        if results.get('equity_curve'):
            ax_equity = fig.add_axes([0.05, y_pos - 0.1, 0.9, 0.1])
            equity = results['equity_curve']
            ax_equity.plot(equity, linewidth=2.5, color='#1976D2', label='Equity Curve')
            ax_equity.axhline(y=results['initial_capital'], color='red', linestyle='--', 
                             linewidth=2, label='Vốn ban đầu', alpha=0.7)
            ax_equity.fill_between(range(len(equity)), results['initial_capital'], equity, 
                                  where=np.array(equity) >= results['initial_capital'],
                                  alpha=0.3, color='green', label='Lợi nhuận')
            ax_equity.fill_between(range(len(equity)), results['initial_capital'], equity,
                                  where=np.array(equity) < results['initial_capital'],
                                  alpha=0.3, color='red', label='Lỗ')
            ax_equity.set_title(f'Equity Curve - {pair}', fontsize=11, fontweight='bold')
            ax_equity.set_xlabel('Thời gian (Nến)', fontsize=9)
            ax_equity.set_ylabel('Giá trị Portfolio ($)', fontsize=9)
            ax_equity.legend(fontsize=8, loc='best')
            ax_equity.grid(True, alpha=0.3)
            y_pos -= 0.12
    
    # Kết luận
    ax_conclusion = fig.add_axes([0.05, y_pos - 0.08, 0.9, 0.08])
    ax_conclusion.axis('off')
    ax_conclusion.set_title('KẾT LUẬN VÀ KHUYẾN NGHỊ', fontsize=16, fontweight='bold', pad=15)
    
    profitable = len([p for p in PAIRS if all_results.get(p) and all_results[p] and all_results[p]['total_profit_pct'] > 0])
    total_pairs = len([p for p in PAIRS if all_results.get(p) and all_results[p]])
    
    conclusion_text = f"""
    TỔNG KẾT: Vốn ban đầu ${total_initial:,.2f} → Vốn cuối ${total_final:,.2f} | Lợi nhuận tổng: ${total_profit:,.2f} ({total_profit_pct:+.2f}%) | 
    Số cặp có lợi nhuận: {profitable}/{total_pairs} | 
    KHUYẾN NGHỊ: Ưu tiên giao dịch các cặp có dữ liệu thực (ADAUSDM, iBTCUSDM, iETHUSDM) với tham số tối ưu. 
    Paper trading ít nhất 2-3 tháng trước khi giao dịch thực. Luôn quản lý rủi ro và không đầu tư quá mức.
    LƯU Ý: Kết quả backtest không đảm bảo hiệu suất tương lai. Chưa tính phí giao dịch và slippage.
    """
    
    ax_conclusion.text(0.02, 0.5, conclusion_text, fontsize=11, verticalalignment='center',
                      bbox=dict(boxstyle='round', facecolor='#E8F5E9', alpha=0.5))
    
    filename = f"Backtest_Report_Full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"\n✓ Đã tạo báo cáo PNG đầy đủ: {filename}")
    plt.close()
    
    return filename

if __name__ == "__main__":
    try:
        filename = create_full_png_report()
        print(f"\n{'='*80}")
        print(f"✅ HOÀN THÀNH!")
        print(f"📄 File PNG: {filename}")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        import traceback
        traceback.print_exc()


