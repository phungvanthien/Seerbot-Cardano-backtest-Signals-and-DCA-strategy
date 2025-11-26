"""
Analyze backtest results and remove loss-making reports
Then suggest improvements for profitable backtesting on real data
"""

import pandas as pd
import numpy as np
from datetime import datetime
from backtest_improved_strategy import ImprovedStrategyBacktestEngine, PAIRS
import os
import glob

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500
TARGET_DATE = datetime(2025, 11, 26)
MAX_TRADES = 100

TAKE_PROFIT_PCT = 5.0
STOP_LOSS_PCT = -2.5

def backtest_timeframe_quick(pair, timeframe='6H'):
    """Quick backtest to check profitability"""
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
        
        if len(df) < max(200, rsi_period + 5):
            return None
        
        engine = ImprovedStrategyBacktestEngine(
            initial_capital=INITIAL_CAPITAL,
            fixed_amount=POSITION_SIZE_FIXED,
            take_profit=TAKE_PROFIT_PCT / 100,
            stop_loss=abs(STOP_LOSS_PCT) / 100,
            rsi_buy=25,
            rsi_sell=75,
            max_dca=2,
            rsi_period=rsi_period,
            timeframe=timeframe
        )
        
        engine.run(df)
        results = engine.get_results()
        
        if results:
            return {
                'pair': pair,
                'timeframe': timeframe,
                'profit_pct': results['total_profit_pct'],
                'win_rate': results['win_rate'],
                'total_trades': results['total_trades']
            }
        
        return None
        
    except Exception as e:
        return None

def analyze_all_reports():
    """Analyze all backtest results and identify loss-making reports"""
    print("=" * 80)
    print("ANALYZING BACKTEST RESULTS")
    print("=" * 80)
    
    timeframes = ['6H', '4H', '2H', '1H']
    results = []
    
    for pair in PAIRS:
        for timeframe in timeframes:
            result = backtest_timeframe_quick(pair, timeframe)
            if result:
                results.append(result)
    
    return results

def remove_loss_reports(loss_reports):
    """Remove PNG reports that are making losses"""
    removed_count = 0
    
    for report in loss_reports:
        pair = report['pair']
        timeframe = report['timeframe']
        safe_pair = pair.replace('/', '_')
        
        # Remove Improved reports with losses
        pattern_improved = f"Report_RSI14_Signals_and_DCA_Strategy/Report_{safe_pair}_{timeframe}_RSI14_DCA_EN_Improved.png"
        if os.path.exists(pattern_improved):
            os.remove(pattern_improved)
            removed_count += 1
            print(f"  ✗ Removed: {pattern_improved} (Loss: {report['profit_pct']:.2f}%)")
    
    return removed_count

def suggest_improvements(loss_reports, profitable_reports):
    """Suggest improvements based on analysis"""
    print("\n" + "=" * 80)
    print("SUGGESTED IMPROVEMENTS FOR PROFITABLE BACKTESTING")
    print("=" * 80)
    
    suggestions = []
    
    # Analyze patterns in loss-making reports
    loss_timeframes = [r['timeframe'] for r in loss_reports]
    loss_pairs = [r['pair'] for r in loss_reports]
    
    # Suggestion 1: Avoid very short timeframes
    if '1H' in loss_timeframes:
        suggestions.append({
            'priority': 'HIGH',
            'title': 'Avoid 1H Timeframe',
            'description': '1H timeframe shows high losses. Consider focusing on 4H and 6H timeframes which tend to be more stable.',
            'action': 'Focus on 4H and 6H timeframes only'
        })
    
    # Suggestion 2: Stricter trend filter
    suggestions.append({
        'priority': 'HIGH',
        'title': 'Stricter Trend Filter',
        'description': 'Add additional confirmation: require price to be above EMA50 for at least 3-5 candles before entering.',
        'action': 'Add trend confirmation period (3-5 candles)'
    })
    
    # Suggestion 3: Dynamic position sizing
    suggestions.append({
        'priority': 'MEDIUM',
        'title': 'Dynamic Position Sizing',
        'description': 'Reduce position size in choppy markets. Use smaller positions (e.g., $300) when volatility is high.',
        'action': 'Implement volatility-based position sizing'
    })
    
    # Suggestion 4: Better entry timing
    suggestions.append({
        'priority': 'HIGH',
        'title': 'Better Entry Timing',
        'description': 'Only enter when RSI is oversold AND price is near support (e.g., recent low or EMA support).',
        'action': 'Add support level confirmation before entry'
    })
    
    # Suggestion 5: Trailing stop loss
    suggestions.append({
        'priority': 'MEDIUM',
        'title': 'Trailing Stop Loss',
        'description': 'Use trailing stop loss: when profit reaches 3%, move stop loss to break-even. When profit reaches 5%, use trailing stop of 2%.',
        'action': 'Implement trailing stop loss mechanism'
    })
    
    # Suggestion 6: Market condition filter
    suggestions.append({
        'priority': 'HIGH',
        'title': 'Market Condition Filter',
        'description': 'Avoid trading in strong downtrends. Only trade when market is in consolidation or uptrend.',
        'action': 'Add market condition assessment (trending vs ranging)'
    })
    
    # Suggestion 7: Volume confirmation
    suggestions.append({
        'priority': 'MEDIUM',
        'title': 'Volume Confirmation',
        'description': 'Require volume to be above average (1.2x MA) for entry signals to avoid false breakouts.',
        'action': 'Increase volume threshold from 0.8x to 1.2x MA'
    })
    
    # Suggestion 8: RSI divergence
    suggestions.append({
        'priority': 'LOW',
        'title': 'RSI Divergence',
        'description': 'Look for bullish RSI divergence (price makes lower low but RSI makes higher low) before entering.',
        'action': 'Add RSI divergence detection'
    })
    
    # Suggestion 9: Time-based filters
    suggestions.append({
        'priority': 'LOW',
        'title': 'Time-based Filters',
        'description': 'Avoid trading during low liquidity periods. Focus on active trading hours.',
        'action': 'Add time-of-day filter for entry signals'
    })
    
    # Suggestion 10: Multiple timeframe confirmation
    suggestions.append({
        'priority': 'HIGH',
        'title': 'Multiple Timeframe Confirmation',
        'description': 'Require higher timeframe (e.g., 4H) to also show uptrend before entering on lower timeframe (e.g., 1H).',
        'action': 'Add multi-timeframe trend alignment check'
    })
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. [{suggestion['priority']}] {suggestion['title']}")
        print(f"   Description: {suggestion['description']}")
        print(f"   Action: {suggestion['action']}")
    
    return suggestions

def main():
    """Main function"""
    print("=" * 80)
    print("ANALYZE AND CLEAN LOSS-MAKING REPORTS")
    print("=" * 80)
    
    # Analyze all reports
    print("\n📊 Analyzing backtest results...")
    all_results = analyze_all_reports()
    
    if not all_results:
        print("✗ No results found")
        return
    
    # Separate profitable and loss-making
    profitable = [r for r in all_results if r['profit_pct'] > 0]
    loss_making = [r for r in all_results if r['profit_pct'] <= 0]
    
    print(f"\n📈 Profitable reports: {len(profitable)}")
    print(f"📉 Loss-making reports: {len(loss_making)}")
    
    # Show profitable reports
    if profitable:
        print(f"\n✅ PROFITABLE REPORTS:")
        for r in sorted(profitable, key=lambda x: x['profit_pct'], reverse=True):
            print(f"  {r['pair']} {r['timeframe']}: +{r['profit_pct']:.2f}% (Win Rate: {r['win_rate']:.1f}%, Trades: {r['total_trades']})")
    
    # Show loss-making reports
    if loss_making:
        print(f"\n❌ LOSS-MAKING REPORTS:")
        for r in sorted(loss_making, key=lambda x: x['profit_pct']):
            print(f"  {r['pair']} {r['timeframe']}: {r['profit_pct']:.2f}% (Win Rate: {r['win_rate']:.1f}%, Trades: {r['total_trades']})")
    
    # Remove loss-making reports
    if loss_making:
        print(f"\n🗑️  Removing loss-making reports...")
        removed = remove_loss_reports(loss_making)
        print(f"✓ Removed {removed} loss-making reports")
    else:
        print("\n✓ No loss-making reports to remove")
    
    # Suggest improvements
    suggestions = suggest_improvements(loss_making, profitable)
    
    # Save suggestions to file
    with open('STRATEGY_IMPROVEMENT_SUGGESTIONS.md', 'w') as f:
        f.write("# Strategy Improvement Suggestions\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Profitable reports: {len(profitable)}\n")
        f.write(f"- Loss-making reports: {len(loss_making)}\n\n")
        f.write("## Suggested Improvements\n\n")
        for i, suggestion in enumerate(suggestions, 1):
            f.write(f"### {i}. {suggestion['title']} [{suggestion['priority']}]\n\n")
            f.write(f"**Description:** {suggestion['description']}\n\n")
            f.write(f"**Action:** {suggestion['action']}\n\n")
    
    print(f"\n{'='*80}")
    print("✅ ANALYSIS COMPLETE!")
    print(f"{'='*80}")
    print(f"\nSuggestions saved to: STRATEGY_IMPROVEMENT_SUGGESTIONS.md")

if __name__ == "__main__":
    main()

