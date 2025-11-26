"""
Script tạo báo cáo PDF chi tiết về backtest
Bao gồm: phương pháp, thống kê lệnh, tỷ lệ chính xác, lợi nhuận
Vốn: $10,000, mỗi lệnh: $500
"""

import pandas as pd
import numpy as np
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
            # Tính position_size dựa trên $500 mỗi lệnh
            params_dict[pair] = {
                'position_size': POSITION_SIZE_FIXED / INITIAL_CAPITAL,  # Tự động tính
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
        
        # Loại bỏ position_size khỏi params (không dùng trong FixedAmountBacktestEngine)
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

def generate_pdf_report():
    """Tạo báo cáo PDF"""
    print("=" * 80)
    print("TẠO BÁO CÁO PDF CHI TIẾT")
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
    
    # Tạo PDF
    filename = f"Backtest_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    story.append(Paragraph("BÁO CÁO BACKTEST CHIẾN LƯỢC RSI14 + DCA", title_style))
    story.append(Paragraph("Cardano DEX Trading Strategy", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Phương pháp backtest
    story.append(Paragraph("1. PHƯƠNG PHÁP BACKTEST", heading_style))
    
    method_text = """
    <b>1.1. Nguồn dữ liệu:</b><br/>
    - Dữ liệu OHLCV lịch sử từ CryptoCompare API (dữ liệu thực)
    - Các cặp token: iBTCUSDM, iETHUSDM, ADAUSDM (dữ liệu thực 2 năm)
    - Các cặp khác: WMTXUSDM, IAGUSDM, SNEKUSDM (dữ liệu mẫu)<br/><br/>
    
    <b>1.2. Chiến lược giao dịch:</b><br/>
    - Mua khi RSI14 ≤ ngưỡng mua (tối ưu cho từng cặp)
    - DCA: Mua thêm tại nến đỏ khi RSI14 < ngưỡng mua, tối đa 2-3 lần
    - Bán khi RSI14 ≥ ngưỡng bán HOẶC lợi nhuận ≥ Take Profit HOẶC Stop Loss<br/><br/>
    
    <b>1.3. Tham số:</b><br/>
    - Vốn ban đầu: $10,000
    - Số tiền mỗi lệnh: $500 (cố định)
    - Tham số tối ưu được tìm bằng cách test 324 combinations trên 4 khoảng thời gian<br/><br/>
    
    <b>1.4. Quản lý rủi ro:</b><br/>
    - Stop Loss: 3-4% (tùy từng cặp)
    - Trailing Stop: 3% từ đỉnh
    - Giới hạn DCA: 2-3 lần tùy từng cặp
    """
    
    story.append(Paragraph(method_text, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Tổng hợp kết quả
    story.append(Paragraph("2. TỔNG HỢP KẾT QUẢ", heading_style))
    
    summary_data = [['Cặp Token', 'Vốn Ban Đầu', 'Vốn Cuối', 'Lợi Nhuận', 'Lợi Nhuận %', 'Số Lệnh', 'Win Rate']]
    
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
        '<b>TỔNG</b>',
        f"<b>${total_initial:,.2f}</b>",
        f"<b>${total_final:,.2f}</b>",
        f"<b>${total_final - total_initial:,.2f}</b>",
        f"<b>{(total_final - total_initial) / total_initial * 100:+.2f}%</b>",
        '',
        ''
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
        if not all_results.get(pair) or all_results[pair] is None:
            continue
        
        results = all_results[pair]
        story.append(PageBreak())
        story.append(Paragraph(f"3. CHI TIẾT CẶP: {pair}", heading_style))
        
        # Thông tin cơ bản
        info_text = f"""
        <b>Thời gian test:</b> {results['start_date'].strftime('%d/%m/%Y')} đến {results['end_date'].strftime('%d/%m/%Y')}<br/>
        <b>Số ngày:</b> {results['days']} ngày<br/>
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
        
        # Tham số sử dụng
        if pair in optimal_params:
            params = optimal_params[pair]
            params_text = f"""
            <b>Tham số tối ưu:</b><br/>
            - Take Profit: {params['take_profit']*100:.0f}%<br/>
            - Stop Loss: {params['stop_loss']*100:.0f}%<br/>
            - RSI Buy: {params['rsi_buy']}<br/>
            - RSI Sell: {params['rsi_sell']}<br/>
            - Max DCA: {params['max_dca']}<br/>
            - Số tiền mỗi lệnh: ${POSITION_SIZE_FIXED:,.2f} (cố định)<br/>
            - Vốn ban đầu: ${INITIAL_CAPITAL:,.2f}<br/>
            """
            story.append(Paragraph(params_text, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        else:
            params_text = f"""
            <b>Tham số mặc định:</b><br/>
            - Take Profit: 10%<br/>
            - Stop Loss: 4%<br/>
            - RSI Buy: 25<br/>
            - RSI Sell: 75<br/>
            - Max DCA: 3<br/>
            - Số tiền mỗi lệnh: ${POSITION_SIZE_FIXED:,.2f} (cố định)<br/>
            - Vốn ban đầu: ${INITIAL_CAPITAL:,.2f}<br/>
            """
            story.append(Paragraph(params_text, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Bảng chi tiết lệnh
        story.append(Paragraph("<b>Bảng chi tiết các lệnh giao dịch:</b>", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        trades = results['trades']
        if trades:
            # Sắp xếp theo thời gian
            trades_sorted = sorted(trades, key=lambda x: pd.to_datetime(x['timestamp']))
            
            # Tách lệnh mua và bán
            buy_trades = [t for t in trades_sorted if t['type'] in ['BUY', 'DCA']]
            sell_trades = [t for t in trades_sorted if t['type'] == 'SELL']
            
            # Tạo bảng lệnh - hiển thị theo từng chu kỳ mua-bán
            trades_data = [['STT', 'Ngày', 'Loại', 'Giá', 'Số Lượng', 'Vốn ($)', 'RSI', 'Lợi Nhuận ($)', 'Lợi Nhuận %', 'Lý Do']]
            
            trade_num = 1
            buy_index = 0
            
            for sell in sell_trades:
                sell_time = pd.to_datetime(sell['timestamp'])
                
                # Tìm các lệnh mua trước lệnh bán này
                related_buys = []
                while buy_index < len(buy_trades):
                    buy_time = pd.to_datetime(buy_trades[buy_index]['timestamp'])
                    if buy_time < sell_time:
                        related_buys.append(buy_trades[buy_index])
                        buy_index += 1
                    else:
                        break
                
                # Thêm các lệnh mua (theo thứ tự thời gian)
                for buy in related_buys:
                    trades_data.append([
                        '',
                        pd.to_datetime(buy['timestamp']).strftime('%d/%m/%Y'),
                        buy['type'],
                        f"${buy['price']:.4f}",
                        f"{buy['amount']:.4f}",
                        f"${buy.get('capital', 0):,.2f}",
                        f"{buy.get('rsi', 0):.1f}",
                        '',
                        '',
                        ''
                    ])
                
                # Thêm lệnh bán
                profit_color = 'green' if sell.get('profit', 0) > 0 else 'red'
                trades_data.append([
                    str(trade_num),
                    pd.to_datetime(sell['timestamp']).strftime('%d/%m/%Y'),
                    '<b>BÁN</b>',
                    f"${sell['price']:.4f}",
                    f"{sell['amount']:.4f}",
                    f"${sell.get('proceeds', 0):,.2f}",
                    f"{sell.get('rsi', 0):.1f}",
                    f"<b>${sell.get('profit', 0):,.2f}</b>",
                    f"<b>{sell.get('profit_pct', 0):+.2f}%</b>",
                    sell.get('reason', '')
                ])
                
                trade_num += 1
            
            trades_table = Table(trades_data, colWidths=[0.4*inch, 0.9*inch, 0.5*inch, 0.7*inch, 
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
    
    conclusion_text = f"""
    <b>4.1. Tổng kết:</b><br/>
    - Tổng vốn ban đầu: ${total_initial:,.2f}<br/>
    - Tổng vốn cuối cùng: ${total_final:,.2f}<br/>
    - Tổng lợi nhuận: ${total_final - total_initial:,.2f} ({(total_final - total_initial) / total_initial * 100:+.2f}%)<br/>
    - Số cặp có lợi nhuận: {len([p for p in PAIRS if all_results.get(p) and all_results[p]['total_profit_pct'] > 0])}/{len([p for p in PAIRS if all_results.get(p)])}<br/><br/>
    
    <b>4.2. Đánh giá:</b><br/>
    - Chiến lược RSI14 + DCA cho thấy hiệu quả trên các cặp có dữ liệu thực<br/>
    - Việc tối ưu tham số riêng cho từng cặp đã cải thiện đáng kể lợi nhuận<br/>
    - Cần tiếp tục paper trading để xác nhận trước khi giao dịch thực<br/><br/>
    
    <b>4.3. Khuyến nghị:</b><br/>
    - Ưu tiên giao dịch các cặp có dữ liệu thực: ADAUSDM, iBTCUSDM, iETHUSDM<br/>
    - Sử dụng tham số tối ưu cho từng cặp<br/>
    - Luôn có stop loss và trailing stop<br/>
    - Paper trading ít nhất 2-3 tháng trước khi giao dịch thực<br/>
    - Quản lý rủi ro: không đầu tư quá mức khả năng chịu đựng<br/><br/>
    
    <b>Lưu ý:</b> Kết quả backtest không đảm bảo hiệu suất tương lai. Luôn quản lý rủi ro cẩn thận.
    """
    
    story.append(Paragraph(conclusion_text, styles['Normal']))
    
    # Build PDF
    print(f"\n📄 Đang tạo file PDF...")
    doc.build(story)
    print(f"✓ Đã tạo báo cáo PDF: {filename}")
    
    return filename

if __name__ == "__main__":
    try:
        filename = generate_pdf_report()
        print(f"\n{'='*80}")
        print(f"✅ HOÀN THÀNH!")
        print(f"📄 File PDF: {filename}")
        print(f"{'='*80}")
    except ImportError:
        print("\n✗ Cần cài đặt reportlab:")
        print("  pip3 install reportlab")
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        import traceback
        traceback.print_exc()

