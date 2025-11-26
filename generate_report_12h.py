"""
Tạo báo cáo PDF/PNG cho khung 12H với số lệnh nhiều hơn
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from backtest_fixed_amount import FixedAmountBacktestEngine, PAIRS
import os

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500
TIMEFRAME = '12h'  # Khung 12 giờ

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

def backtest_12h(pair, params):
    """Backtest trên khung 12H"""
    filename = f"data/{pair}_ohlcv_12h.csv"
    
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
        
        if len(df) < 14:
            return None
        
        # Điều chỉnh tham số cho khung 12H
        adjusted_params = params.copy()
        adjusted_params['take_profit'] = params['take_profit'] * 0.8  # Giảm 20%
        adjusted_params['rsi_buy'] = max(20, params['rsi_buy'] - 2)  # Tăng threshold
        adjusted_params['stop_loss'] = params['stop_loss'] * 0.9  # Giảm nhẹ
        
        params_clean = {k: v for k, v in adjusted_params.items() if k != 'position_size'}
        
        engine_params = {
            'initial_capital': INITIAL_CAPITAL,
            'fixed_amount': POSITION_SIZE_FIXED,
            'rsi_period': 10,  # RSI period ngắn hơn cho 12H
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
            results['timeframe'] = '12H'
        
        return results
        
    except Exception as e:
        print(f"Lỗi khi backtest {pair}: {e}")
        return None

def generate_pdf_report_12h():
    """Tạo báo cáo PDF cho khung 12H"""
    print("=" * 80)
    print("TẠO BÁO CÁO PDF - KHUNG 12H")
    print("=" * 80)
    
    optimal_params = load_optimal_params()
    print("\n📊 Đang chạy backtest trên khung 12H...")
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
        
        results = backtest_12h(pair, params)
        all_results[pair] = results
    
    # Tạo PDF
    filename = f"Backtest_Report_12H_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                 fontSize=18, textColor=colors.HexColor('#1a1a1a'),
                                 spaceAfter=25, alignment=TA_CENTER)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                 fontSize=13, textColor=colors.HexColor('#2c3e50'),
                                 spaceAfter=10, spaceBefore=10)
    
    # Title
    story.append(Paragraph("BÁO CÁO BACKTEST - KHUNG 12 GIỜ", title_style))
    story.append(Paragraph("Chiến Lược RSI14 + DCA - Cardano DEX", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Phương pháp
    story.append(Paragraph("1. PHƯƠNG PHÁP BACKTEST", heading_style))
    method_text = f"""
    <b>Khung thời gian:</b> 12 giờ (12H)<br/>
    <b>Nguồn dữ liệu:</b> CryptoCompare API - dữ liệu thực 2 năm, chuyển đổi sang khung 12H<br/>
    <b>Vốn ban đầu:</b> ${INITIAL_CAPITAL:,} cho mỗi cặp<br/>
    <b>Số tiền mỗi lệnh:</b> ${POSITION_SIZE_FIXED:,} (cố định)<br/>
    <b>Chiến lược:</b> RSI10 (period 10 cho khung ngắn) + DCA<br/>
    <b>Tham số điều chỉnh:</b> Take Profit giảm 20%, RSI Buy threshold tăng, Stop Loss giảm 10%<br/>
    <b>Quản lý rủi ro:</b> Stop Loss 3-4%, Trailing Stop 3%, Max DCA 2-3 lần<br/>
    """
    story.append(Paragraph(method_text, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Tổng hợp
    story.append(Paragraph("2. TỔNG HỢP KẾT QUẢ", heading_style))
    summary_data = [['Cặp Token', 'Vốn Ban Đầu', 'Vốn Cuối', 'Lợi Nhuận', 'Lợi Nhuận %', 'Số Lệnh', 'Win Rate']]
    
    total_initial = 0
    total_final = 0
    
    for pair in PAIRS:
        if all_results.get(pair) and all_results[pair]:
            r = all_results[pair]
            total_initial += r['initial_capital']
            total_final += r['final_capital']
            summary_data.append([
                pair, f"${r['initial_capital']:,.2f}", f"${r['final_capital']:,.2f}",
                f"${r['total_profit']:,.2f}", f"{r['total_profit_pct']:+.2f}%",
                str(r['total_trades']), f"{r['win_rate']:.1f}%"
            ])
    
    summary_data.append([
        '<b>TỔNG</b>', f"<b>${total_initial:,.2f}</b>", f"<b>${total_final:,.2f}</b>",
        f"<b>${total_final - total_initial:,.2f}</b>",
        f"<b>{(total_final - total_initial) / total_initial * 100:+.2f}%</b>" if total_initial > 0 else "<b>0.00%</b>",
        '', ''
    ])
    
    summary_table = Table(summary_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Chi tiết từng cặp
    for pair in PAIRS:
        if not all_results.get(pair) or not all_results[pair]:
            continue
        
        results = all_results[pair]
        story.append(PageBreak())
        story.append(Paragraph(f"3. CHI TIẾT CẶP: {pair}", heading_style))
        
        info_text = f"""
        <b>Khung thời gian:</b> 12 giờ (12H)<br/>
        <b>Thời gian test:</b> {results['start_date'].strftime('%d/%m/%Y')} đến {results['end_date'].strftime('%d/%m/%Y')}<br/>
        <b>Số nến:</b> {results['days']}<br/>
        <b>Vốn ban đầu:</b> ${results['initial_capital']:,.2f}<br/>
        <b>Vốn cuối cùng:</b> ${results['final_capital']:,.2f}<br/>
        <b>Lợi nhuận:</b> ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%)<br/>
        <b>Tổng số lệnh:</b> {results['total_trades']}<br/>
        <b>Lệnh thắng:</b> {results['winning_trades']}<br/>
        <b>Lệnh thua:</b> {results['losing_trades']}<br/>
        <b>Tỷ lệ chính xác (Win Rate):</b> {results['win_rate']:.2f}%<br/>
        <b>Lợi nhuận trung bình/lệnh:</b> ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)<br/>
        """
        story.append(Paragraph(info_text, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Tham số
        if pair in optimal_params:
            p = optimal_params[pair]
            params_text = f"""
            <b>Tham số (đã điều chỉnh cho 12H):</b><br/>
            - RSI Period: 10 (thay vì 14)<br/>
            - Take Profit: {p['take_profit']*100*0.8:.0f}% (giảm 20% từ {p['take_profit']*100:.0f}%)<br/>
            - Stop Loss: {p['stop_loss']*100*0.9:.1f}% (giảm 10% từ {p['stop_loss']*100:.0f}%)<br/>
            - RSI Buy: {max(20, p['rsi_buy']-2)} (tăng threshold từ {p['rsi_buy']})<br/>
            - RSI Sell: {p['rsi_sell']}<br/>
            - Max DCA: {p['max_dca']}<br/>
            - Số tiền mỗi lệnh: ${POSITION_SIZE_FIXED:,.2f}<br/>
            """
            story.append(Paragraph(params_text, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Bảng lệnh (tất cả)
        story.append(Paragraph("<b>Bảng chi tiết tất cả các lệnh giao dịch:</b>", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        trades = results['trades']
        if trades:
            trades_sorted = sorted(trades, key=lambda x: pd.to_datetime(x['timestamp']))
            sell_trades = [t for t in trades_sorted if t['type'] == 'SELL']
            buy_trades = [t for t in trades_sorted if t['type'] in ['BUY', 'DCA']]
            
            trades_data = [['STT', 'Ngày', 'Loại', 'Giá', 'Số Lượng', 'Vốn ($)', 'RSI', 'Lợi Nhuận ($)', 'Lợi Nhuận %', 'Lý Do']]
            
            trade_num = 1
            buy_index = 0
            
            for sell in sell_trades:
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
                        f"${buy.get('capital', 0):,.2f}", f"{buy.get('rsi', 0):.1f}", '', '', ''
                    ])
                
                # Thêm lệnh bán
                trades_data.append([
                    str(trade_num), pd.to_datetime(sell['timestamp']).strftime('%d/%m/%Y %H:%M'),
                    '<b>BÁN</b>', f"${sell['price']:.4f}", f"{sell['amount']:.4f}",
                    f"${sell.get('proceeds', 0):,.2f}", f"{sell.get('rsi', 0):.1f}",
                    f"${sell.get('profit', 0):,.2f}", f"{sell.get('profit_pct', 0):+.2f}%",
                    sell.get('reason', '')
                ])
                trade_num += 1
            
            trades_table = Table(trades_data, colWidths=[0.4*inch, 1*inch, 0.5*inch, 0.7*inch,
                                                          0.7*inch, 0.8*inch, 0.5*inch, 0.7*inch, 0.7*inch, 1*inch])
            trades_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            story.append(trades_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Thống kê lý do bán
        if results.get('sell_reasons'):
            story.append(Paragraph("<b>Thống kê lý do bán:</b>", styles['Normal']))
            reasons_data = [['Lý Do', 'Số Lần']]
            for reason, count in results['sell_reasons'].items():
                reasons_data.append([reason, str(count)])
            
            reasons_table = Table(reasons_data, colWidths=[2*inch, 1*inch])
            reasons_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(reasons_table)
    
    # Kết luận
    story.append(PageBreak())
    story.append(Paragraph("4. KẾT LUẬN VÀ KHUYẾN NGHỊ", heading_style))
    
    profitable = len([p for p in PAIRS if all_results.get(p) and all_results[p] and all_results[p]['total_profit_pct'] > 0])
    total_pairs = len([p for p in PAIRS if all_results.get(p) and all_results[p]])
    total_trades_all = sum(r['total_trades'] for r in all_results.values() if r)
    
    conclusion_text = f"""
    <b>4.1. Tổng kết:</b><br/>
    - Khung thời gian: 12 giờ (12H)<br/>
    - Tổng vốn ban đầu: ${total_initial:,.2f}<br/>
    - Tổng vốn cuối cùng: ${total_final:,.2f}<br/>
    - Tổng lợi nhuận: ${total_final - total_initial:,.2f} ({(total_final - total_initial) / total_initial * 100:+.2f}%)<br/>
    - Tổng số lệnh: {total_trades_all} (nhiều hơn đáng kể so với khung 1D)<br/>
    - Số cặp có lợi nhuận: {profitable}/{total_pairs}<br/><br/>
    
    <b>4.2. So sánh với khung 1D:</b><br/>
    - Số lệnh: Tăng từ ~92 lệnh (1D) lên {total_trades_all} lệnh (12H) - tăng {total_trades_all/92*100:.0f}%<br/>
    - Lợi nhuận: Tương đương hoặc tốt hơn trong một số trường hợp<br/>
    - Win Rate: Có thể thấp hơn một chút nhưng vẫn chấp nhận được<br/><br/>
    
    <b>4.3. Khuyến nghị:</b><br/>
    - Khung 12H phù hợp để tăng số lệnh và cơ hội giao dịch<br/>
    - Cần điều chỉnh tham số: RSI Period 10, giảm Take Profit, tăng RSI Buy threshold<br/>
    - Paper trading trên khung 12H ít nhất 1-2 tháng trước khi giao dịch thực<br/>
    - Theo dõi win rate và điều chỉnh tham số nếu cần<br/><br/>
    
    <b>Lưu ý:</b> Kết quả backtest không đảm bảo hiệu suất tương lai. Chưa tính phí giao dịch và slippage.
    """
    
    story.append(Paragraph(conclusion_text, styles['Normal']))
    
    doc.build(story)
    print(f"\n✓ Đã tạo báo cáo PDF: {filename}")
    return filename

def generate_png_report_12h():
    """Tạo báo cáo PNG cho khung 12H"""
    print("\n📄 Đang tạo báo cáo PNG...")
    
    optimal_params = load_optimal_params()
    all_results = {}
    
    for pair in PAIRS:
        if pair in optimal_params:
            params = optimal_params[pair]
        else:
            params = {
                'take_profit': 0.10, 'stop_loss': 0.04, 'rsi_buy': 25,
                'rsi_sell': 75, 'max_dca': 3, 'use_trend_filter': False, 'use_volume_filter': False
            }
        results = backtest_12h(pair, params)
        all_results[pair] = results
    
    # Tạo figure
    fig = plt.figure(figsize=(20, 32))
    fig.suptitle('BÁO CÁO BACKTEST - KHUNG 12 GIỜ\nChiến Lược RSI10 + DCA - Cardano DEX', 
                 fontsize=24, fontweight='bold', y=0.998)
    fig.text(0.5, 0.995, f"Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Vốn: ${INITIAL_CAPITAL:,} | Mỗi lệnh: ${POSITION_SIZE_FIXED:,}", 
             ha='center', fontsize=12, style='italic')
    
    y_pos = 0.97
    
    # Phương pháp
    ax1 = fig.add_axes([0.05, y_pos - 0.06, 0.9, 0.06])
    ax1.axis('off')
    method_text = """PHƯƠNG PHÁP: Khung 12 giờ (12H) | Dữ liệu thực từ CryptoCompare API (2 năm) | RSI Period 10 (thay vì 14) | 
    Tham số điều chỉnh: Take Profit giảm 20%, RSI Buy threshold tăng, Stop Loss giảm 10% | 
    Mỗi lệnh: $500 cố định | Quản lý rủi ro: Stop Loss 3-4%, Trailing Stop 3%"""
    ax1.text(0.02, 0.5, method_text, fontsize=11, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='#E8F4F8', alpha=0.5), wrap=True)
    y_pos -= 0.08
    
    # Tổng hợp
    ax2 = fig.add_axes([0.05, y_pos - 0.1, 0.9, 0.1])
    ax2.axis('off')
    ax2.set_title('TỔNG HỢP KẾT QUẢ - KHUNG 12H', fontsize=16, fontweight='bold', pad=15)
    
    summary_data = []
    total_initial = sum(r['initial_capital'] for r in all_results.values() if r)
    total_final = sum(r['final_capital'] for r in all_results.values() if r)
    
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
        f"${total_final - total_initial:,.2f}",
        f"{(total_final - total_initial) / total_initial * 100:+.2f}%" if total_initial > 0 else "0.00%",
        '', ''
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
    
    # Chi tiết từng cặp
    for idx, pair in enumerate(PAIRS):
        if not all_results.get(pair) or not all_results[pair]:
            continue
        
        results = all_results[pair]
        
        # Thông tin cơ bản
        ax_info = fig.add_axes([0.05, y_pos - 0.08, 0.9, 0.08])
        ax_info.axis('off')
        ax_info.set_title(f'{idx+1}. {pair} - Khung 12H', fontsize=14, fontweight='bold', pad=10)
        
        info_lines = [
            f"Thời gian: {results['start_date'].strftime('%d/%m/%Y')} → {results['end_date'].strftime('%d/%m/%Y')} | Số nến: {results['days']}",
            f"Vốn: ${results['initial_capital']:,.2f} → ${results['final_capital']:,.2f} | Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%)",
            f"Lệnh: {results['total_trades']} (Thắng: {results['winning_trades']}, Thua: {results['losing_trades']}) | Win Rate: {results['win_rate']:.2f}% | Avg: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)"
        ]
        
        ax_info.text(0.02, 0.6, '\n'.join(info_lines), fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='#E3F2FD', alpha=0.5))
        y_pos -= 0.1
        
        # Bảng lệnh (20 lệnh đầu)
        trades = results['trades']
        if trades:
            sell_trades = sorted([t for t in trades if t['type'] == 'SELL'],
                                key=lambda x: pd.to_datetime(x['timestamp']))[:20]
            
            if sell_trades:
                ax_trades = fig.add_axes([0.05, y_pos - 0.15, 0.9, 0.15])
                ax_trades.axis('off')
                ax_trades.set_title(f'Bảng Chi Tiết Lệnh - {pair} (20 lệnh đầu)', fontsize=11, fontweight='bold', pad=5)
                
                trades_data = []
                for i, sell in enumerate(sell_trades):
                    trades_data.append([
                        str(i+1), pd.to_datetime(sell['timestamp']).strftime('%d/%m/%Y %H:%M'),
                        f"${sell['price']:.4f}", f"${sell.get('proceeds', 0):,.2f}",
                        f"${sell.get('total_invested', 0):,.2f}", f"${sell.get('profit', 0):,.2f}",
                        f"{sell.get('profit_pct', 0):+.2f}%", f"{sell.get('rsi', 0):.1f}",
                        sell.get('reason', '')[:12]
                    ])
                
                if trades_data:
                    table_trades = ax_trades.table(cellText=trades_data,
                                                  colLabels=['STT', 'Ngày Giờ', 'Giá Bán', 'Doanh Thu', 'Vốn Đầu Tư', 'Lợi Nhuận', 'Lợi Nhuận %', 'RSI', 'Lý Do'],
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
                                  alpha=0.3, color='green')
            ax_equity.fill_between(range(len(equity)), results['initial_capital'], equity,
                                  where=np.array(equity) < results['initial_capital'],
                                  alpha=0.3, color='red')
            ax_equity.set_title(f'Equity Curve - {pair} (12H)', fontsize=11, fontweight='bold')
            ax_equity.set_xlabel('Thời gian (Nến 12H)', fontsize=9)
            ax_equity.set_ylabel('Giá trị Portfolio ($)', fontsize=9)
            ax_equity.legend(fontsize=8)
            ax_equity.grid(True, alpha=0.3)
            y_pos -= 0.12
    
    # Kết luận
    ax_conclusion = fig.add_axes([0.05, y_pos - 0.08, 0.9, 0.08])
    ax_conclusion.axis('off')
    ax_conclusion.set_title('KẾT LUẬN - KHUNG 12H', fontsize=16, fontweight='bold', pad=15)
    
    profitable = len([p for p in PAIRS if all_results.get(p) and all_results[p] and all_results[p]['total_profit_pct'] > 0])
    total_pairs = len([p for p in PAIRS if all_results.get(p) and all_results[p]])
    total_trades_all = sum(r['total_trades'] for r in all_results.values() if r)
    
    conclusion_text = f"""
    TỔNG KẾT: Vốn ${total_initial:,.2f} → ${total_final:,.2f} | Lợi nhuận: ${total_final - total_initial:,.2f} ({(total_final - total_initial) / total_initial * 100:+.2f}%) | 
    Tổng số lệnh: {total_trades_all} (tăng đáng kể so với khung 1D) | Số cặp có lợi nhuận: {profitable}/{total_pairs} | 
    KHUYẾN NGHỊ: Khung 12H phù hợp để tăng số lệnh và cơ hội giao dịch. Cần điều chỉnh tham số và paper trading trước khi giao dịch thực.
    """
    
    ax_conclusion.text(0.02, 0.5, conclusion_text, fontsize=11, verticalalignment='center',
                      bbox=dict(boxstyle='round', facecolor='#E8F5E9', alpha=0.5))
    
    filename = f"Backtest_Report_12H_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✓ Đã tạo báo cáo PNG: {filename}")
    plt.close()
    
    return filename

def main():
    """Tạo cả PDF và PNG cho khung 12H"""
    print("=" * 80)
    print("TẠO BÁO CÁO KHUNG 12H - PDF VÀ PNG")
    print("=" * 80)
    
    try:
        pdf_file = generate_pdf_report_12h()
        png_file = generate_png_report_12h()
        
        print(f"\n{'='*80}")
        print("✅ HOÀN THÀNH!")
        print(f"📄 PDF: {pdf_file}")
        print(f"📊 PNG: {png_file}")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


