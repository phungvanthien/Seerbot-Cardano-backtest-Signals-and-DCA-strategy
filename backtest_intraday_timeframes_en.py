"""
Backtest and generate PNG reports for short timeframes: 6h, 4h, 2h, 1h
With take profit 5% and stop loss -2.5%
English version
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
TARGET_DATE = datetime(2025, 11, 26)  # Target date
MAX_TRADES = 100  # Maximum trades in each report

# Take profit and stop loss configuration
TAKE_PROFIT_PCT = 5.0  # 5%
STOP_LOSS_PCT = -2.5   # -2.5%

def load_optimal_params():
    """Load optimal parameters"""
    filename = 'optimal_params_real_data.csv'
    if not os.path.exists(filename):
        return {}
    try:
        df = pd.read_csv(filename)
        params_dict = {}
        for _, row in df.iterrows():
            pair = row['Pair']
            params_dict[pair] = {
                'take_profit': TAKE_PROFIT_PCT / 100,  # Override with 5%
                'stop_loss': abs(STOP_LOSS_PCT) / 100,  # Override with 2.5%
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
    """Backtest on a specific timeframe"""
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
        
        # Adjust parameters for shorter timeframes
        adjusted_params = params.copy()
        adjusted_params['take_profit'] = TAKE_PROFIT_PCT / 100  # Ensure 5%
        adjusted_params['stop_loss'] = abs(STOP_LOSS_PCT) / 100  # Ensure 2.5%
        
        # Adjust RSI for shorter timeframes
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
            
            # Filter to get 100 nearest trades (closest to TARGET_DATE)
            trades = results.get('trades', [])
            if trades:
                # Sort by time
                trades_sorted = sorted(trades, key=lambda x: pd.to_datetime(x['timestamp']))
                
                # Get SELL trades closest to TARGET_DATE
                sell_trades = [t for t in trades_sorted if t['type'] == 'SELL']
                
                if sell_trades:
                    # Calculate distance from TARGET_DATE
                    for trade in sell_trades:
                        trade_time = pd.to_datetime(trade['timestamp'])
                        trade['days_from_target'] = abs((trade_time - TARGET_DATE).total_seconds() / 86400)
                        trade['is_before'] = trade_time <= TARGET_DATE
                    
                    # Sort: prioritize trades before TARGET_DATE, then by distance
                    sell_trades_sorted = sorted(sell_trades, 
                                               key=lambda x: (not x['is_before'], x['days_from_target']))
                    
                    # Get 100 nearest trades
                    selected_sells = sell_trades_sorted[:MAX_TRADES]
                    
                    # Get all related buy trades for these sell trades
                    selected_sell_times = [pd.to_datetime(t['timestamp']) for t in selected_sells]
                    if selected_sell_times:
                        min_time = min(selected_sell_times)
                        max_time = max(selected_sell_times)
                        
                        # Get all trades in this time range
                        selected_trades = []
                        for trade in trades_sorted:
                            trade_time = pd.to_datetime(trade['timestamp'])
                            if trade_time <= max_time + timedelta(days=1):
                                selected_trades.append(trade)
                        
                        # Re-sort selected_trades by time
                        selected_trades = sorted(selected_trades, key=lambda x: pd.to_datetime(x['timestamp']))
                        
                        # Update results with filtered trades
                        results['trades'] = selected_trades
                        results['total_trades'] = len(selected_sells)
                        results['selected_trades_count'] = len(selected_trades)
                        results['target_date'] = TARGET_DATE.strftime('%Y-%m-%d')
        
        return results
        
    except Exception as e:
        print(f"Error backtesting {pair} {timeframe}: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_png_report(pair, timeframe, results):
    """Generate PNG report for a token pair on a specific timeframe"""
    if not results or not results.get('trades'):
        return None
    
    # Adjust figure size based on timeframe
    if timeframe in ['1H', '2H']:
        fig_height = 45
    elif timeframe in ['4H', '6H']:
        fig_height = 40
    else:
        fig_height = 35
    
    fig = plt.figure(figsize=(24, fig_height))
    # Add padding at top
    fig.subplots_adjust(top=0.96)
    
    y_pos = 0.97
    
    # Header box with title and info - placed in the white space area
    ax_header = fig.add_axes([0.05, y_pos - 0.10, 0.9, 0.10])
    ax_header.axis('off')
    
    # Main title
    ax_header.text(0.5, 0.75, f'BACKTEST REPORT - {pair}', 
                   fontsize=24, fontweight='bold', ha='center', va='center',
                   transform=ax_header.transAxes)
    
    # Strategy and timeframe
    ax_header.text(0.5, 0.55, f'Strategy: RSI14 Indicator & DCA Trading Method | Timeframe: {timeframe}', 
                   fontsize=16, fontweight='bold', ha='center', va='center',
                   transform=ax_header.transAxes)
    
    # Additional strategy info
    ax_header.text(0.5, 0.35, 
                   'Using RSI14 (Relative Strength Index 14-period) indicator and DCA (Dollar Cost Averaging) trading approach', 
                   fontsize=12, ha='center', va='center', style='italic',
                   transform=ax_header.transAxes)
    
    # Date and info
    ax_header.text(0.5, 0.10, 
                   f"Generated: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')} | "
                   f"Capital: ${INITIAL_CAPITAL:,} | Per Trade: ${POSITION_SIZE_FIXED:,} | "
                   f"Stop Loss: {STOP_LOSS_PCT}% | Take Profit: +{TAKE_PROFIT_PCT}% | 100 trades closest to 11/26/2025", 
                   fontsize=11, style='italic', ha='center', va='center',
                   transform=ax_header.transAxes)
    
    y_pos -= 0.12
    
    # Basic information
    ax_info = fig.add_axes([0.05, y_pos - 0.05, 0.9, 0.05])
    ax_info.axis('off')
    
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
                bbox=dict(boxstyle='round', facecolor='#E3F2FD', alpha=0.7))
    y_pos -= 0.07
    
    # Parameters used
    ax_params = fig.add_axes([0.05, y_pos - 0.04, 0.9, 0.04])
    ax_params.axis('off')
    
    rsi_period = 8 if timeframe in ['6H', '4H'] else 7
    params_text = f"""
    Strategy: RSI14 Indicator & DCA Trading Method | 
    RSI Period: {rsi_period} (RSI14) | 
    Stop Loss: {STOP_LOSS_PCT}% | Take Profit: +{TAKE_PROFIT_PCT}% | 
    RSI Buy Threshold: {results.get('rsi_buy', 25)} | 
    RSI Sell Threshold: {results.get('rsi_sell', 75)} | 
    Max DCA Levels: {results.get('max_dca', 3)} | 
    Per Trade: ${POSITION_SIZE_FIXED:,}
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
    
    # Detailed trades table
    trades = results['trades']
    if trades:
        sell_trades = sorted([t for t in trades if t['type'] == 'SELL'],
                            key=lambda x: pd.to_datetime(x['timestamp']))
        
        # Display only sell trades for cleaner table
        trades_data = []
        trade_num = 1
        for sell in sell_trades[:MAX_TRADES]:
            trades_data.append([
                str(trade_num), pd.to_datetime(sell['timestamp']).strftime('%m/%d/%Y\n%H:%M'),
                'SELL', f"${sell['price']:.4f}", f"{sell['amount']:.4f}",
                f"${sell.get('proceeds', 0):,.2f}", f"{sell.get('rsi', 0):.1f}",
                f"${sell.get('total_invested', 0):,.2f}", f"${sell.get('profit', 0):,.2f}",
                f"{sell.get('profit_pct', 0):+.2f}%", sell.get('reason', '')[:20]
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
            col_widths = [0.04, 0.12, 0.06, 0.08, 0.08, 0.10, 0.06, 0.10, 0.10, 0.10, 0.16]
            
            table_trades = ax_trades.table(
                cellText=trades_data,
                colLabels=['#', 'Date Time', 'Type', 'Price', 'Amount', 'Capital/Proceeds ($)', 
                          'RSI', 'Invested', 'Profit ($)', 'Profit %', 'Reason'],
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
                if row[2] == 'SELL':
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
    CONCLUSION: {pair} - RSI14 Indicator & DCA Trading Method on {timeframe} timeframe | 
    Stop Loss: {STOP_LOSS_PCT}% | Take Profit: +{TAKE_PROFIT_PCT}% | 
    Profit: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%) | 
    {results['total_trades']} sell trades | 
    Win Rate: {results['win_rate']:.2f}% | 
    Avg Profit: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)
    """
    
    ax_conclusion.text(0.02, 0.5, conclusion_text, fontsize=11, verticalalignment='center',
                      bbox=dict(boxstyle='round', facecolor='#E8F5E9', alpha=0.7), weight='bold')
    y_pos -= 0.06
    
    # SeerBOT Team credit
    ax_credit = fig.add_axes([0.05, y_pos - 0.03, 0.9, 0.03])
    ax_credit.axis('off')
    credit_text = "Backtest by SeerBOT Team"
    ax_credit.text(0.5, 0.5, credit_text, fontsize=12, verticalalignment='center',
                  horizontalalignment='center', weight='bold', 
                  bbox=dict(boxstyle='round', facecolor='#F5F5F5', alpha=0.8, edgecolor='#1976D2', linewidth=2),
                  color='#1976D2')
    
    # Save file
    safe_pair = pair.replace('/', '_')
    filename = f"Report_{safe_pair}_{timeframe}_RSI14_DCA_EN.png"
    
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return filename

def main():
    """Generate PNG reports for all pairs and timeframes"""
    print("=" * 80)
    print("BACKTEST AND GENERATE PNG REPORTS - SHORT TIMEFRAMES")
    print("=" * 80)
    print(f"Timeframes: 6H, 4H, 2H, 1H")
    print(f"Take Profit: +{TAKE_PROFIT_PCT}% | Stop Loss: {STOP_LOSS_PCT}%")
    print(f"Each report contains 100 trades closest to {TARGET_DATE.strftime('%m/%d/%Y')}")
    print("=" * 80)
    
    optimal_params = load_optimal_params()
    timeframes = ['6H', '4H', '2H', '1H']
    
    generated_files = []
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Processing: {pair}")
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
            print(f"\n  → Timeframe {timeframe}...")
            results = backtest_timeframe(pair, params, timeframe)
            
            if results and results.get('trades'):
                sell_count = len([t for t in results['trades'] if t['type'] == 'SELL'])
                print(f"    ✓ Found {sell_count} sell trades")
                filename = generate_png_report(pair, timeframe, results)
                if filename:
                    generated_files.append(filename)
                    print(f"    ✓ Created: {filename}")
                else:
                    print(f"    ✗ Could not create report")
            else:
                print(f"    ✗ No data")
    
    print(f"\n{'='*80}")
    print("✅ COMPLETED!")
    print(f"{'='*80}")
    print(f"\nGenerated {len(generated_files)} PNG reports:")
    for f in generated_files:
        print(f"  - {f}")
    print(f"\n{'='*80}")

if __name__ == "__main__":
    main()

