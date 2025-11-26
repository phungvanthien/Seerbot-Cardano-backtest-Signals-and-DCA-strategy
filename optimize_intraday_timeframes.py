"""
Optimize parameters for each pair and timeframe to maximize profit
"""

import pandas as pd
import numpy as np
from datetime import datetime
from backtest_fixed_amount import FixedAmountBacktestEngine, PAIRS
import os
from itertools import product

INITIAL_CAPITAL = 10000
POSITION_SIZE_FIXED = 500
TAKE_PROFIT_PCT = 5.0
STOP_LOSS_PCT = -2.5

# Parameter ranges to test
RSI_BUY_RANGE = [20, 22, 25, 28, 30]
RSI_SELL_RANGE = [70, 72, 75, 78, 80]
MAX_DCA_RANGE = [2, 3, 4, 5]

def backtest_with_params(pair, timeframe, rsi_buy, rsi_sell, max_dca):
    """Run backtest with specific parameters"""
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
        
        # Adjust RSI for shorter timeframes
        adjusted_rsi_buy = rsi_buy
        if timeframe in ['2H', '1H']:
            adjusted_rsi_buy = max(20, rsi_buy - 3)
        elif timeframe in ['4H', '6H']:
            adjusted_rsi_buy = max(20, rsi_buy - 2)
        
        engine_params = {
            'initial_capital': INITIAL_CAPITAL,
            'fixed_amount': POSITION_SIZE_FIXED,
            'rsi_period': rsi_period,
            'take_profit': TAKE_PROFIT_PCT / 100,
            'stop_loss': abs(STOP_LOSS_PCT) / 100,
            'rsi_buy': adjusted_rsi_buy,
            'rsi_sell': rsi_sell,
            'max_dca': max_dca,
            'use_trend_filter': False,
            'use_volume_filter': False
        }
        
        engine = FixedAmountBacktestEngine(**engine_params)
        engine.run(df)
        results = engine.get_results()
        
        if results:
            return {
                'total_profit_pct': results['total_profit_pct'],
                'win_rate': results['win_rate'],
                'total_trades': results['total_trades'],
                'avg_profit_pct': results['avg_profit_pct'],
                'final_capital': results['final_capital']
            }
        
        return None
        
    except Exception as e:
        return None

def optimize_pair_timeframe(pair, timeframe):
    """Find optimal parameters for a pair and timeframe"""
    print(f"  Optimizing {pair} {timeframe}...")
    
    best_params = None
    best_profit = float('-inf')
    best_result = None
    
    total_combinations = len(RSI_BUY_RANGE) * len(RSI_SELL_RANGE) * len(MAX_DCA_RANGE)
    tested = 0
    
    for rsi_buy, rsi_sell, max_dca in product(RSI_BUY_RANGE, RSI_SELL_RANGE, MAX_DCA_RANGE):
        tested += 1
        if tested % 20 == 0:
            print(f"    Tested {tested}/{total_combinations} combinations...")
        
        result = backtest_with_params(pair, timeframe, rsi_buy, rsi_sell, max_dca)
        
        if result and result['total_trades'] >= 10:  # At least 10 trades
            # Score based on profit and win rate
            score = result['total_profit_pct'] + (result['win_rate'] * 0.1)
            
            if score > best_profit:
                best_profit = score
                best_params = {
                    'rsi_buy': rsi_buy,
                    'rsi_sell': rsi_sell,
                    'max_dca': max_dca
                }
                best_result = result
    
    if best_params:
        print(f"    ✓ Best: RSI Buy={best_params['rsi_buy']}, RSI Sell={best_params['rsi_sell']}, Max DCA={best_params['max_dca']}")
        print(f"      Profit: {best_result['total_profit_pct']:.2f}%, Win Rate: {best_result['win_rate']:.2f}%, Trades: {best_result['total_trades']}")
        return {
            'pair': pair,
            'timeframe': timeframe,
            **best_params,
            **best_result
        }
    
    return None

def main():
    """Optimize parameters for all pairs and timeframes"""
    print("=" * 80)
    print("OPTIMIZE PARAMETERS FOR INTRADAY TIMEFRAMES")
    print("=" * 80)
    print(f"Testing combinations for {len(PAIRS)} pairs × 4 timeframes")
    print(f"RSI Buy: {RSI_BUY_RANGE}")
    print(f"RSI Sell: {RSI_SELL_RANGE}")
    print(f"Max DCA: {MAX_DCA_RANGE}")
    print("=" * 80)
    
    timeframes = ['6H', '4H', '2H', '1H']
    all_results = []
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Processing: {pair}")
        print(f"{'='*80}")
        
        for timeframe in timeframes:
            result = optimize_pair_timeframe(pair, timeframe)
            if result:
                all_results.append(result)
    
    # Save results
    if all_results:
        df_results = pd.DataFrame(all_results)
        filename = 'optimal_params_intraday_timeframes.csv'
        df_results.to_csv(filename, index=False)
        print(f"\n{'='*80}")
        print("✅ OPTIMIZATION COMPLETE!")
        print(f"{'='*80}")
        print(f"\nSaved results to: {filename}")
        print(f"\nTotal optimized: {len(all_results)} combinations")
        
        # Summary
        profitable = len([r for r in all_results if r['total_profit_pct'] > 0])
        print(f"Profitable combinations: {profitable}/{len(all_results)}")
        
        # Show best for each pair
        print(f"\n{'='*80}")
        print("BEST PARAMETERS BY PAIR AND TIMEFRAME")
        print(f"{'='*80}")
        for pair in PAIRS:
            print(f"\n{pair}:")
            pair_results = [r for r in all_results if r['pair'] == pair]
            for tf in timeframes:
                tf_results = [r for r in pair_results if r['timeframe'] == tf]
                if tf_results:
                    best = max(tf_results, key=lambda x: x['total_profit_pct'])
                    print(f"  {tf}: RSI Buy={best['rsi_buy']}, RSI Sell={best['rsi_sell']}, Max DCA={best['max_dca']} | "
                          f"Profit: {best['total_profit_pct']:.2f}%, Win Rate: {best['win_rate']:.2f}%")
    else:
        print("\n✗ No results found")

if __name__ == "__main__":
    main()

