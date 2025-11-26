"""
Generate PNG reports for short-selling strategy across intraday timeframes.
Short logic: RSI14 >= 80 triggers short entry, DCA $500 per add, TP +5%, SL -2.5%.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from backtest_fixed_amount_short import FixedAmountShortBacktestEngine
from backtest_fixed_amount import PAIRS
import os

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500
TARGET_DATE = datetime(2025, 11, 26)
MAX_TRADES = 100

TAKE_PROFIT_PCT = 5.0
STOP_LOSS_PCT = -2.5

def run_backtest_on_df(df, rsi_period):
    engine_params = {
        'initial_capital': INITIAL_CAPITAL,
        'fixed_amount': POSITION_SIZE_FIXED,
        'rsi_period': rsi_period,
        'take_profit': TAKE_PROFIT_PCT / 100,
        'stop_loss': abs(STOP_LOSS_PCT) / 100,
        'rsi_short_entry': 80,
        'rsi_cover': 30,
        'max_dca': 3,
        'use_trend_filter': False,
        'use_volume_filter': False
    }
    engine = FixedAmountShortBacktestEngine(**engine_params)
    engine.run(df)
    return engine.get_results()

def select_trades_near_target(trades):
    if not trades:
        return None
    trades_sorted = sorted(trades, key=lambda x: pd.to_datetime(x['timestamp']))
    sell_trades = [t for t in trades_sorted if t['type'] == 'COVER']
    if not sell_trades:
        return None
    for trade in sell_trades:
        trade_time = pd.to_datetime(trade['timestamp'])
        trade['days_from_target'] = abs((trade_time - TARGET_DATE).total_seconds() / 86400)
        trade['is_before'] = trade_time <= TARGET_DATE
    sell_trades_sorted = sorted(sell_trades, key=lambda x: (not x['is_before'], x['days_from_target']))
    selected_sells = sell_trades_sorted[:MAX_TRADES]
    selected_sell_times = [pd.to_datetime(t['timestamp']) for t in selected_sells]
    if not selected_sell_times:
        return None
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
    selected_trades = selection['selected_trades']
    selected_sells = [t for t in selected_trades if t['type'] == 'COVER']
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
    results['final_capital'] = results['initial_capital'] + total_profit
    results['sell_reasons'] = sell_reasons
    results['start_date'] = selection['time_start']
    results['end_date'] = selection['time_end']
    results['days'] = (selection['time_end'] - selection['time_start']).days + 1
    results['target_date'] = TARGET_DATE.strftime('%Y-%m-%d')
    return results

def backtest_timeframe_short(pair, timeframe='6H'):
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

        initial_results = run_backtest_on_df(df, rsi_period)
        if not initial_results:
            return None
        selection = select_trades_near_target(initial_results.get('trades', []))
        if not selection:
            return None
        window_start = max(selection['time_start'], df['timestamp'].min())
        window_end = min(selection['time_end'], df['timestamp'].max())
        df_window = df[(df['timestamp'] >= window_start) & (df['timestamp'] <= window_end)]
        if len(df_window) < rsi_period + 5:
            return None
        window_results = run_backtest_on_df(df_window, rsi_period)
        if not window_results:
            return None
        window_selection = select_trades_near_target(window_results.get('trades', []))
        if not window_selection:
            return None
        summarized = summarize_results_with_selection(window_results, window_selection)
        if not summarized:
            return None
        summarized['pair'] = pair
        summarized['timeframe'] = timeframe
        return summarized
    except Exception as e:
        print(f"Error short backtesting {pair} {timeframe}: {e}")
        return None

def generate_png_report_short(pair, timeframe, results):
    if not results or not results.get('trades'):
        return None
    fig = plt.figure(figsize=(24, 40))
    fig.suptitle(f'BACKTEST REPORT - {pair}\nStrategy: RSI14 Short Indicator & DCA Method | Timeframe: {timeframe}',
                 fontsize=22, fontweight='bold', y=0.995)
    fig.text(0.5, 0.985,
             f"Generated: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')} | "
             f"Capital: ${INITIAL_CAPITAL:,} | Per Short: ${POSITION_SIZE_FIXED:,} | "
             f"Stop Loss: {STOP_LOSS_PCT}% | Take Profit: +{TAKE_PROFIT_PCT}% | 100 trades closest to 11/26/2025",
             ha='center', fontsize=11, style='italic')
    y_pos = 0.97

    info_text = f"""
    Test Period: {results['start_date'].strftime('%m/%d/%Y')} → {results['end_date'].strftime('%m/%d/%Y')} |
    Candles: {results['days']} |
    Initial Capital: ${results['initial_capital']:,.2f} |
    Final Capital: ${results['final_capital']:,.2f} |
    Profit: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%) |
    Total Shorts: {results.get('total_shorts', 0)} |
    Covers: {results['total_trades']} |
    Win Rate: {results['win_rate']:.2f}%
    """
    ax_info = fig.add_axes([0.05, y_pos - 0.05, 0.9, 0.05])
    ax_info.axis('off')
    ax_info.text(0.02, 0.5, info_text, fontsize=10,
                 bbox=dict(boxstyle='round', facecolor='#E3F2FD', alpha=0.7))
    y_pos -= 0.07

    params_text = f"""
    Short Strategy: RSI14 >= 80 | DCA Short ${POSITION_SIZE_FIXED:,} |
    Stop Loss: {STOP_LOSS_PCT}% | Take Profit: +{TAKE_PROFIT_PCT}% |
    RSI Cover: 30 | Max DCA: 3 | Leverage: 1x
    """
    ax_params = fig.add_axes([0.05, y_pos - 0.04, 0.9, 0.04])
    ax_params.axis('off')
    ax_params.text(0.02, 0.5, params_text, fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='#FFF3E0', alpha=0.7))
    y_pos -= 0.06

    ax_stats = fig.add_axes([0.05, y_pos - 0.06, 0.9, 0.06])
    ax_stats.axis('off')
    ax_stats.set_title('DETAILED STATISTICS (Short)', fontsize=14, fontweight='bold', pad=10)
    stats_data = [
        ['Metric', 'Value'],
        ['Winning Covers', f"{results['winning_trades']}"],
        ['Losing Covers', f"{results['losing_trades']}"],
        ['Win Rate', f"{results['win_rate']:.2f}%"],
        ['Avg Profit/Cover', f"${results['avg_profit']:,.2f}"],
        ['Avg Profit %', f"{results['avg_profit_pct']:+.2f}%"],
    ]
    if results.get('sell_reasons'):
        for reason, count in list(results['sell_reasons'].items())[:3]:
            stats_data.append([f"Reason: {reason}", f"{count} times"])
    table_stats = ax_stats.table(cellText=stats_data, cellLoc='left', loc='center', bbox=[0, 0, 1, 1])
    table_stats.auto_set_font_size(False)
    table_stats.set_fontsize(10)
    table_stats.scale(1, 2.5)
    table_stats[(0, 0)].set_facecolor('#2C3E50')
    table_stats[(0, 1)].set_facecolor('#2C3E50')
    table_stats[(0, 0)].set_text_props(weight='bold', color='white')
    table_stats[(0, 1)].set_text_props(weight='bold', color='white')
    y_pos -= 0.08

    trades = results['trades']
    if trades:
        covers = sorted([t for t in trades if t['type'] == 'COVER'],
                        key=lambda x: pd.to_datetime(x['timestamp']))
        trades_data = []
        trade_num = 1
        for cover in covers[:MAX_TRADES]:
            trades_data.append([
                str(trade_num), pd.to_datetime(cover['timestamp']).strftime('%m/%d/%Y\n%H:%M'),
                'COVER', f"${cover['price']:.4f}", f"{cover['amount']:.4f}",
                f"${cover.get('total_invested', 0):,.2f}", f"{cover.get('rsi', 0):.1f}",
                f"${cover.get('total_invested', 0):,.2f}", f"${cover.get('profit', 0):,.2f}",
                f"{cover.get('profit_pct', 0):+.2f}%", cover.get('reason', '')[:20]
            ])
            trade_num += 1

        if trades_data:
            table_height = min(0.75, 0.03 + len(trades_data) * 0.012)
            ax_trades = fig.add_axes([0.03, y_pos - table_height, 0.94, table_height])
            ax_trades.axis('off')
            ax_trades.set_title(f'DETAILED TRADES TABLE - 100 NEAREST COVERS ({len(trades_data)} trades)',
                                fontsize=13, fontweight='bold', pad=12)
            font_size = 8
            col_widths = [0.04, 0.12, 0.06, 0.08, 0.08, 0.10, 0.06, 0.10, 0.10, 0.10, 0.16]
            table_trades = ax_trades.table(
                cellText=trades_data,
                colLabels=['#', 'Date Time', 'Type', 'Price', 'Amount', 'Margin ($)',
                          'RSI', 'Total Invested', 'Profit ($)', 'Profit %', 'Reason'],
                cellLoc='center', loc='center', bbox=[0, 0, 1, 1],
                colWidths=col_widths
            )
            table_trades.auto_set_font_size(False)
            table_trades.set_fontsize(font_size)
            table_trades.scale(1, 1.2)
            for i in range(11):
                table_trades[(0, i)].set_facecolor('#4A148C')
                table_trades[(0, i)].set_text_props(weight='bold', color='white', size=font_size+1)
            for i in range(1, len(trades_data) + 1):
                row = trades_data[i-1]
                profit_str = row[8]
                profit = float(profit_str.replace('$', '').replace(',', '')) if profit_str else 0
                color = '#C8E6C9' if profit > 0 else '#FFCDD2'
                for j in range(7, 10):
                    table_trades[(i, j)].set_facecolor(color)
            y_pos -= (table_height + 0.02)

    if results.get('equity_curve'):
        ax_equity = fig.add_axes([0.05, y_pos - 0.12, 0.9, 0.12])
        equity = results['equity_curve']
        ax_equity.plot(equity, linewidth=2.5, color='#D32F2F', label='Equity Curve (Short)')
        ax_equity.axhline(y=results['initial_capital'], color='gray', linestyle='--',
                         linewidth=2, label='Initial Capital', alpha=0.7)
        ax_equity.set_title(f'Equity Curve - {pair} ({timeframe})', fontsize=12, fontweight='bold')
        ax_equity.set_xlabel('Time (Candles)', fontsize=10)
        ax_equity.set_ylabel('Portfolio Value ($)', fontsize=10)
        ax_equity.legend(fontsize=9)
        ax_equity.grid(True, alpha=0.3)
        y_pos -= 0.14

    ax_conclusion = fig.add_axes([0.05, y_pos - 0.05, 0.9, 0.05])
    ax_conclusion.axis('off')
    conclusion_text = f"""
    CONCLUSION (SHORT): {pair} - RSI14 Short DCA on {timeframe} |
    Stop Loss: {STOP_LOSS_PCT}% | Take Profit: +{TAKE_PROFIT_PCT}% |
    Profit: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%) |
    Covers: {results['total_trades']} | Win Rate: {results['win_rate']:.2f}% |
    Avg Profit: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)
    """
    ax_conclusion.text(0.02, 0.5, conclusion_text, fontsize=11,
                      bbox=dict(boxstyle='round', facecolor='#FCE4EC', alpha=0.7), weight='bold')

    ax_credit = fig.add_axes([0.05, y_pos - 0.03, 0.9, 0.03])
    ax_credit.axis('off')
    ax_credit.text(0.5, 0.5, "Backtest by SeerBOT Team (Short Strategy)",
                   fontsize=12, weight='bold', ha='center',
                   bbox=dict(boxstyle='round', facecolor='#F5F5F5', edgecolor='#D32F2F', linewidth=2),
                   color='#D32F2F')

    safe_pair = pair.replace('/', '_')
    filename = f"Report_{safe_pair}_{timeframe}_RSI14_DCA_EN_Short.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    return filename

def main():
    print("=" * 80)
    print("BACKTEST SHORT STRATEGY - RSI14 DCA SHORT")
    print("=" * 80)
    print("Conditions: RSI14 >= 80 triggers short, DCA $500, TP +5%, SL -2.5%")
    print(f"Reports use trades closest to {TARGET_DATE.strftime('%m/%d/%Y')}")
    print("=" * 80)

    timeframes = ['6H', '4H', '2H', '1H']
    generated_files = []

    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Processing Short Strategy: {pair}")
        print(f"{'='*80}")

        for timeframe in timeframes:
            print(f"\n  → Timeframe {timeframe} (Short)...")
            results = backtest_timeframe_short(pair, timeframe)
            if results and results.get('trades'):
                sell_count = len([t for t in results['trades'] if t['type'] == 'COVER'])
                print(f"    ✓ Found {sell_count} cover trades")
                filename = generate_png_report_short(pair, timeframe, results)
                if filename:
                    generated_files.append(filename)
                    print(f"    ✓ Created: {filename}")
                else:
                    print(f"    ✗ Could not create report")
            else:
                print(f"    ✗ No data for short strategy")

    print(f"\n{'='*80}")
    print("✅ SHORT STRATEGY REPORTS COMPLETE")
    print(f"{'='*80}")
    print(f"\nGenerated {len(generated_files)} short PNG reports:")
    for f in generated_files:
        print(f"  - {f}")
    print(f"\n{'='*80}")

if __name__ == "__main__":
    main()

