"""
Generate Parabolic SAR + DCA Strategy Reports
- Entry/Exit: Open price when SAR signal appears
- DCA: When price moves 5% higher or lower than first entry
- Take Profit: 5%
- All timeframes with real data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from backtest_psar_dca_strategy import PSARDCABacktestEngine, PAIRS
import os

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500
TARGET_DATE = datetime(2025, 11, 26)
MAX_TRADES = 100

TAKE_PROFIT_PCT = 5.0
DCA_THRESHOLD_PCT = 5.0

def select_trades_near_target(trades):
    """Return trades & sells closest to TARGET_DATE (max MAX_TRADES)"""
    if not trades:
        return None
    
    trades_sorted = sorted(trades, key=lambda x: pd.to_datetime(x['timestamp']))
    sell_trades = [t for t in trades_sorted if t['type'] == 'SELL']
    if not sell_trades:
        return None
    
    for trade in sell_trades:
        trade_time = pd.to_datetime(trade['timestamp'])
        trade['days_from_target'] = abs((trade_time - TARGET_DATE).total_seconds() / 86400)
        trade['is_before'] = trade_time <= TARGET_DATE
    
    sell_trades_sorted = sorted(
        sell_trades,
        key=lambda x: (not x['is_before'], x['days_from_target'])
    )
    selected_sells = sell_trades_sorted[:MAX_TRADES]
    if not selected_sells:
        return None
    
    selected_sell_times = [pd.to_datetime(t['timestamp']) for t in selected_sells]
    min_time = min(selected_sell_times)
    max_time = max(selected_sell_times)
    
    buffer_before = timedelta(hours=48)
    buffer_after = timedelta(hours=24)
    time_start = min_time - buffer_before
    time_end = max_time + buffer_after
    
    selected_trades = [
        t for t in trades_sorted
        if time_start <= pd.to_datetime(t['timestamp']) <= time_end
    ]
    
    return {
        'selected_trades': selected_trades,
        'selected_sells': selected_sells,
        'time_start': time_start,
        'time_end': time_end
    }

def summarize_results_with_selection(results, selection):
    """Update stats so report only reflects selected trades"""
    selected_trades = selection['selected_trades']
    selected_sells = [t for t in selected_trades if t['type'] == 'SELL']
    if not selected_sells:
        return None
    
    total_profit = sum(s.get('profit', 0) for s in selected_sells)
    total_profit_pct = (total_profit / results['initial_capital']) * 100 if results['initial_capital'] else 0
    winning = len([s for s in selected_sells if s.get('profit', 0) > 0])
    losing = len([s for s in selected_sells if s.get('profit', 0) < 0])
    win_rate = (winning / len(selected_sells) * 100) if selected_sells else 0
    avg_profit = total_profit / len(selected_sells) if selected_sells else 0
    avg_profit_pct = (
        sum(s.get('profit_pct', 0) for s in selected_sells) / len(selected_sells)
        if selected_sells else 0
    )
    
    sell_reasons = {}
    for sell in selected_sells:
        reason = sell.get('reason', 'UNKNOWN')
        sell_reasons[reason] = sell_reasons.get(reason, 0) + 1
    
    results['trades'] = selected_trades
    results['total_trades'] = len(selected_sells)
    results['selected_trades_count'] = len(selected_trades)
    results['winning_trades'] = winning
    results['losing_trades'] = losing
    results['win_rate'] = win_rate
    results['total_profit'] = total_profit
    results['total_profit_pct'] = total_profit_pct
    results['avg_profit'] = avg_profit
    results['avg_profit_pct'] = avg_profit_pct
    results['sell_reasons'] = sell_reasons
    results['start_date'] = selection['time_start']
    results['end_date'] = selection['time_end']
    
    return results

def backtest_timeframe(pair, timeframe='1D'):
    """Backtest on a specific timeframe with Parabolic SAR + DCA strategy"""
    timeframe_map = {
        '1D': ('', 14),
        '12H': ('12h', 14),
        '8H': ('8h', 14),
        '6H': ('6h', 14),
        '4H': ('4h', 14),
        '2H': ('2h', 14),
        '1H': ('1h', 14),
    }
    
    if timeframe not in timeframe_map:
        return None
    
    file_suffix, _ = timeframe_map[timeframe]
    if file_suffix:
        filename = f"data/{pair}_ohlcv_{file_suffix}.csv"
    else:
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
        
        if len(df) < 50:
            return None
        
        engine = PSARDCABacktestEngine(
            initial_capital=INITIAL_CAPITAL,
            fixed_amount=POSITION_SIZE_FIXED,
            take_profit=TAKE_PROFIT_PCT / 100,
            dca_threshold=DCA_THRESHOLD_PCT / 100,
            psar_af_start=0.02,
            psar_af_increment=0.02,
            psar_af_max=0.2
        )
        
        engine.run(df)
        results = engine.get_results()
        
        if not results:
            return None
        
        results['pair'] = pair
        results['timeframe'] = timeframe
        results['days'] = len(df)
        
        # Select trades near target date
        selection = select_trades_near_target(results['trades'])
        if not selection:
            return None
        
        # Update results with selected trades
        results = summarize_results_with_selection(results, selection)
        
        return results
        
    except Exception as e:
        print(f"Error backtesting {pair} {timeframe}: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_png_report(pair, timeframe, results, output_dir='Report_PSAR_And_DCA'):
    """Generate PNG report"""
    if not results or not results.get('trades'):
        return None
    
    # Create output directory if not exists
    os.makedirs(output_dir, exist_ok=True)
    
    fig = plt.figure(figsize=(24, 40))
    fig.subplots_adjust(top=0.96)
    
    y_pos = 0.97
    
    # Header
    ax_header = fig.add_axes([0.05, y_pos - 0.10, 0.9, 0.10])
    ax_header.axis('off')
    
    ax_header.text(0.5, 0.75, f'BACKTEST REPORT - {pair}', 
                   fontsize=24, fontweight='bold', ha='center', va='center',
                   transform=ax_header.transAxes)
    
    ax_header.text(0.5, 0.45, f'Strategy: Parabolic SAR + DCA | Entry/Exit: Open Price | Timeframe: {timeframe}', 
                   fontsize=16, fontweight='bold', ha='center', va='center',
                   transform=ax_header.transAxes)
    
    ax_header.text(0.5, 0.15, 
                   f"Generated: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')} | "
                   f"Capital: ${INITIAL_CAPITAL:,} | Per Trade: ${POSITION_SIZE_FIXED:,} | "
                   f"Take Profit: +{TAKE_PROFIT_PCT}% | DCA Threshold: ±{DCA_THRESHOLD_PCT}% | 100 trades closest to 11/26/2025", 
                   fontsize=11, style='italic', ha='center', va='center',
                   transform=ax_header.transAxes)
    
    y_pos -= 0.12
    
    # Basic info
    ax_info = fig.add_axes([0.05, y_pos - 0.05, 0.9, 0.05])
    ax_info.axis('off')
    
    profit_color = '#C8E6C9' if results['total_profit'] > 0 else '#FFCDD2'
    info_text = f"""
    Test Period: {results['start_date'].strftime('%m/%d/%Y')} → {results['end_date'].strftime('%m/%d/%Y')} | 
    Candles: {results['days']} | 
    Initial Capital: ${results['initial_capital']:,.2f} | 
    Final Capital: ${results['final_capital']:,.2f} | 
    Profit: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%) | 
    Total Trades: {results.get('selected_trades_count', results['total_trades'])} | 
    Sell Trades: {results['total_trades']} | 
    Win Rate: {results['win_rate']:.2f}%
    """
    ax_info.text(0.02, 0.5, info_text, fontsize=10, verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor=profit_color, alpha=0.7))
    y_pos -= 0.07
    
    # Parameters
    ax_params = fig.add_axes([0.05, y_pos - 0.04, 0.9, 0.04])
    ax_params.axis('off')
    
    params_text = f"""
    Strategy: Parabolic SAR (Stop and Reverse) + DCA (Dollar Cost Averaging) | 
    Entry Signal: SAR trend changes from downtrend (-1) to uptrend (+1) | 
    Exit Signal: SAR trend changes from uptrend (+1) to downtrend (-1) OR Take Profit 5% | 
    Entry/Exit Price: Open Price of Candle | 
    DCA: When price moves ±{DCA_THRESHOLD_PCT}% from first entry (higher or lower) | 
    Take Profit: +{TAKE_PROFIT_PCT}% | Per Trade: ${POSITION_SIZE_FIXED:,} | 
    SAR Parameters: AF Start=0.02, AF Increment=0.02, AF Max=0.2
    """
    ax_params.text(0.02, 0.5, params_text, fontsize=10, verticalalignment='center',
                  bbox=dict(boxstyle='round', facecolor='#FFF3E0', alpha=0.7))
    y_pos -= 0.06
    
    # Statistics
    ax_stats = fig.add_axes([0.05, y_pos - 0.06, 0.9, 0.06])
    ax_stats.axis('off')
    ax_stats.set_title('DETAILED STATISTICS', fontsize=14, fontweight='bold', pad=10)
    
    stats_data = [
        ['Metric', 'Value'],
        ['Winning Trades', f"{results['winning_trades']}"],
        ['Losing Trades', f"{results['losing_trades']}"],
        ['Win Rate', f"{results['win_rate']:.2f}%"],
        ['Avg Profit/Trade', f"${results['avg_profit']:,.2f}"],
        ['Avg Profit %', f"{results['avg_profit_pct']:+.2f}%"],
    ]
    
    if results.get('sell_reasons'):
        for reason, count in list(results['sell_reasons'].items())[:3]:
            stats_data.append([f"Reason: {reason}", f"{count} times"])
    
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
    
    # Trades table
    trades = results['trades']
    if trades:
        sell_trades = sorted([t for t in trades if t['type'] == 'SELL'],
                            key=lambda x: pd.to_datetime(x['timestamp']))
        
        trades_data = []
        trade_num = 1
        for sell in sell_trades[:MAX_TRADES]:
            trades_data.append([
                str(trade_num), pd.to_datetime(sell['timestamp']).strftime('%m/%d/%Y\n%H:%M'),
                'SELL', f"${sell['price']:.4f}", f"{sell['amount']:.4f}",
                f"${sell.get('proceeds', 0):,.2f}", f"${sell.get('total_invested', 0):,.2f}",
                f"${sell.get('profit', 0):,.2f}", f"{sell.get('profit_pct', 0):+.2f}%",
                sell.get('reason', '')[:25]
            ])
            trade_num += 1
        
        if trades_data:
            table_height = min(0.75, 0.03 + len(trades_data) * 0.012)
            ax_trades = fig.add_axes([0.03, y_pos - table_height, 0.94, table_height])
            ax_trades.axis('off')
            ax_trades.set_title(f'DETAILED TRADES TABLE - 100 NEAREST TRADES ({len(sell_trades[:MAX_TRADES])} sell trades)', 
                              fontsize=13, fontweight='bold', pad=12)
            
            font_size = 8
            scale_y = 1.2
            col_widths = [0.04, 0.12, 0.06, 0.08, 0.08, 0.10, 0.10, 0.10, 0.10, 0.22]
            
            table_trades = ax_trades.table(
                cellText=trades_data,
                colLabels=['#', 'Date Time', 'Type', 'Price', 'Amount', 'Proceeds ($)', 
                          'Invested ($)', 'Profit ($)', 'Profit %', 'Reason'],
                cellLoc='center', loc='center', bbox=[0, 0, 1, 1],
                colWidths=col_widths
            )
            table_trades.auto_set_font_size(False)
            table_trades.set_fontsize(font_size)
            table_trades.scale(1, scale_y)
            
            for i in range(10):
                table_trades[(0, i)].set_facecolor('#1A237E')
                table_trades[(0, i)].set_text_props(weight='bold', color='white', size=font_size+1)
            
            for i in range(1, len(trades_data) + 1):
                row = trades_data[i-1]
                if row[2] == 'SELL':
                    try:
                        profit_str = row[7] if len(row) > 7 else '0'
                        profit = float(profit_str.replace('$', '').replace(',', '').replace(' ', '')) if profit_str else 0
                        if profit > 0:
                            for j in [5, 6, 7, 8]:
                                if j < len(row):
                                    table_trades[(i, j)].set_facecolor('#C8E6C9')
                        else:
                            for j in [5, 6, 7, 8]:
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
                         linewidth=2, label='Initial Capital', alpha=0.7)
        ax_equity.fill_between(range(len(equity)), results['initial_capital'], equity,
                              where=np.array(equity) >= results['initial_capital'],
                              alpha=0.3, color='green')
        ax_equity.fill_between(range(len(equity)), results['initial_capital'], equity,
                              where=np.array(equity) < results['initial_capital'],
                              alpha=0.3, color='red')
        ax_equity.set_title(f'Equity Curve - {pair} ({timeframe})', fontsize=12, fontweight='bold')
        ax_equity.set_xlabel('Time (Candles)', fontsize=10)
        ax_equity.set_ylabel('Portfolio Value ($)', fontsize=10)
        ax_equity.legend(fontsize=9)
        ax_equity.grid(True, alpha=0.3)
        y_pos -= 0.14
    
    # Conclusion
    ax_conclusion = fig.add_axes([0.05, y_pos - 0.05, 0.9, 0.05])
    ax_conclusion.axis('off')
    
    conclusion_text = f"""
    CONCLUSION: {pair} - Parabolic SAR + DCA Strategy on {timeframe} timeframe | 
    Entry/Exit: Open Price | Take Profit: +{TAKE_PROFIT_PCT}% | DCA: ±{DCA_THRESHOLD_PCT}% | 
    Profit: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%) | 
    {results['total_trades']} sell trades | 
    Win Rate: {results['win_rate']:.2f}% | 
    Avg Profit: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)
    """
    
    conclusion_color = '#E8F5E9' if results['total_profit'] > 0 else '#FFEBEE'
    ax_conclusion.text(0.02, 0.5, conclusion_text, fontsize=11, verticalalignment='center',
                      bbox=dict(boxstyle='round', facecolor=conclusion_color, alpha=0.7), weight='bold')
    y_pos -= 0.06
    
    # SeerBOT Team credit
    ax_credit = fig.add_axes([0.05, y_pos - 0.03, 0.9, 0.03])
    ax_credit.axis('off')
    credit_text = "Backtest by SeerBOT Team"
    ax_credit.text(0.5, 0.5, credit_text, fontsize=12, verticalalignment='center',
                  horizontalalignment='center', weight='bold', 
                  bbox=dict(boxstyle='round', facecolor='#F5F5F5', alpha=0.8, edgecolor='#1976D2', linewidth=2),
                  color='#1976D2')
    
    safe_pair = pair.replace('/', '_')
    filename = os.path.join(output_dir, f"Report_{safe_pair}_{timeframe}_PSAR_DCA.png")
    
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return filename

def main():
    """Generate Parabolic SAR + DCA strategy reports for all pairs and timeframes"""
    print("=" * 80)
    print("PARABOLIC SAR + DCA STRATEGY BACKTEST REPORTS")
    print("=" * 80)
    print("Strategy Details:")
    print("  - Entry/Exit: Open price when SAR signal appears")
    print("  - DCA: When price moves ±5% from first entry (higher or lower)")
    print("  - Take Profit: +5%")
    print("  - All timeframes with real data")
    print("=" * 80)
    
    timeframes = ['1D', '12H', '8H', '6H', '4H', '2H', '1H']
    generated_files = []
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Processing: {pair}")
        print(f"{'='*80}")
        
        for timeframe in timeframes:
            print(f"\n  → Timeframe {timeframe}...")
            results = backtest_timeframe(pair, timeframe)
            
            if results and results.get('trades'):
                sell_count = len([t for t in results['trades'] if t['type'] == 'SELL'])
                profit_pct = results['total_profit_pct']
                status = "✓" if profit_pct > 0 else "✗"
                print(f"    {status} Found {sell_count} sell trades | Profit: {profit_pct:+.2f}%")
                filename = generate_png_report(pair, timeframe, results)
                if filename:
                    generated_files.append((filename, profit_pct))
                    print(f"    ✓ Created: {filename}")
                else:
                    print(f"    ✗ Could not create report")
            else:
                print(f"    ✗ No data or no trades")
    
    print(f"\n{'='*80}")
    print("✅ COMPLETED!")
    print(f"{'='*80}")
    print(f"\nGenerated {len(generated_files)} PNG reports in Report_PSAR_And_DCA/")
    
    profitable = [f for f, p in generated_files if p > 0]
    loss_making = [f for f, p in generated_files if p <= 0]
    
    if profitable:
        print(f"\n✅ Profitable reports ({len(profitable)}):")
        for f, p in sorted([x for x in generated_files if x[1] > 0], key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {os.path.basename(f)} (+{p:.2f}%)")
    
    if loss_making:
        print(f"\n❌ Loss-making reports ({len(loss_making)}):")
        for f, p in sorted([x for x in generated_files if x[1] <= 0], key=lambda x: x[1])[:10]:
            print(f"  - {os.path.basename(f)} ({p:.2f}%)")
    
    print(f"\n{'='*80}")

if __name__ == "__main__":
    main()

