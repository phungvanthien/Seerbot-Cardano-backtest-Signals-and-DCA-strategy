"""
Fixed amount backtest engine for short-selling strategy (RSI14 + DCA)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(prices, period=20):
    return prices.ewm(span=period, adjust=False).mean()

def is_green_candle(row):
    return row['close'] > row['open']

class FixedAmountShortBacktestEngine:
    def __init__(self, initial_capital=10000, fixed_amount=500,
                 take_profit=0.05, stop_loss=0.025,
                 rsi_short_entry=80, rsi_cover=30, max_dca=3,
                 use_trend_filter=False, use_volume_filter=False,
                 rsi_period=14):
        self.initial_capital = initial_capital
        self.fixed_amount = fixed_amount
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.rsi_short_entry = rsi_short_entry
        self.rsi_cover = rsi_cover
        self.max_dca = max_dca
        self.use_trend_filter = use_trend_filter
        self.use_volume_filter = use_volume_filter
        self.rsi_period = rsi_period
        self.reset()

    def reset(self):
        self.cash = self.initial_capital
        self.short_position = 0
        self.entry_prices = []
        self.entry_amounts = []
        self.entry_capital = []
        self.in_short = False
        self.dca_count = 0
        self.short_highest_price = 0
        self.entry_timestamp = None
        self.trades = []
        self.equity_curve = []

    def get_average_entry_price(self):
        if len(self.entry_prices) == 0:
            return 0
        total_amount = sum(self.entry_amounts)
        if total_amount == 0:
            return 0
        weighted_sum = sum(price * amount for price, amount in zip(self.entry_prices, self.entry_amounts))
        return weighted_sum / total_amount

    def get_total_invested(self):
        return sum(self.entry_capital)

    def short_sell(self, price, timestamp, rsi, is_dca=False):
        capital_to_use = min(self.fixed_amount, self.cash)
        if capital_to_use < 10:
            return False
        amount = capital_to_use / price
        if amount <= 0:
            return False
        self.cash -= capital_to_use
        self.short_position += amount
        self.entry_prices.append(price)
        self.entry_amounts.append(amount)
        self.entry_capital.append(capital_to_use)
        self.in_short = True

        if is_dca:
            self.dca_count += 1
        else:
            self.dca_count = 0
            self.entry_timestamp = timestamp
            self.short_highest_price = price

        trade_type = "SHORT_DCA" if is_dca else "SHORT"
        self.trades.append({
            'timestamp': timestamp,
            'type': trade_type,
            'price': price,
            'amount': amount,
            'capital': capital_to_use,
            'rsi': rsi,
            'position': self.short_position,
            'avg_entry_price': self.get_average_entry_price(),
            'cash': self.cash
        })
        return True

    def cover(self, price, timestamp, rsi, reason):
        if self.short_position <= 0:
            return False

        short_value = self.short_position * price
        total_invested = self.get_total_invested()
        profit = total_invested - short_value
        profit_pct = (profit / total_invested * 100) if total_invested > 0 else 0

        self.cash += total_invested + profit

        self.trades.append({
            'timestamp': timestamp,
            'type': 'COVER',
            'price': price,
            'amount': self.short_position,
            'proceeds': total_invested,
            'total_invested': total_invested,
            'profit': profit,
            'profit_pct': profit_pct,
            'rsi': rsi,
            'reason': reason,
            'cash': self.cash
        })

        self.short_position = 0
        self.entry_prices = []
        self.entry_amounts = []
        self.entry_capital = []
        self.in_short = False
        self.dca_count = 0
        self.short_highest_price = 0
        self.entry_timestamp = None
        return True

    def get_current_short_profit_pct(self, current_price):
        if not self.in_short:
            return 0
        total_invested = self.get_total_invested()
        if total_invested == 0:
            return 0
        short_value = self.short_position * current_price
        profit = total_invested - short_value
        return (profit / total_invested) * 100

    def run(self, df):
        self.reset()
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()

        df['rsi14'] = calculate_rsi(df['close'], period=self.rsi_period)
        df['ema20'] = calculate_ema(df['close'], period=20)
        df['is_green'] = df.apply(is_green_candle, axis=1)

        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
        else:
            df['volume_ma'] = 1
            df['volume'] = 1

        for idx, row in df.iterrows():
            timestamp = row.get('timestamp', idx)
            close_price = row['close']
            rsi = row['rsi14']
            is_green = row['is_green']
            ema20 = row['ema20']
            volume = row['volume']
            volume_ma = row['volume_ma']

            if pd.isna(rsi) or pd.isna(ema20):
                equity = self.cash + self.get_total_invested()
                if self.in_short:
                    short_value = self.short_position * close_price
                    equity += (self.get_total_invested() - short_value)
                self.equity_curve.append(equity)
                continue

            if self.in_short:
                if close_price > self.short_highest_price:
                    self.short_highest_price = close_price

                profit_pct = self.get_current_short_profit_pct(close_price)

                if profit_pct <= -abs(self.stop_loss) * 100:
                    self.cover(close_price, timestamp, rsi, 'SHORT_STOP_LOSS')
                    equity = self.cash
                    self.equity_curve.append(equity)
                    continue

                if profit_pct >= self.take_profit * 100:
                    self.cover(close_price, timestamp, rsi, 'SHORT_TAKE_PROFIT')
                    equity = self.cash
                    self.equity_curve.append(equity)
                    continue

                if rsi <= self.rsi_cover:
                    self.cover(close_price, timestamp, rsi, 'SHORT_RSI_EXIT')
                    equity = self.cash
                    self.equity_curve.append(equity)
                    continue

            can_short = False
            if rsi >= self.rsi_short_entry:
                can_short = True
                if self.use_trend_filter:
                    if close_price < ema20 * 1.05:
                        can_short = False
                if self.use_volume_filter and can_short:
                    if volume < volume_ma * 0.8:
                        can_short = False

            if can_short:
                if not self.in_short:
                    self.short_sell(close_price, timestamp, rsi, is_dca=False)
                else:
                    avg_entry = self.get_average_entry_price()
                    if is_green and close_price > avg_entry and self.dca_count < self.max_dca:
                        self.short_sell(close_price, timestamp, rsi, is_dca=True)

            equity = self.cash + self.get_total_invested()
            if self.in_short:
                short_value = self.short_position * close_price
                equity += (self.get_total_invested() - short_value)
            self.equity_curve.append(equity)

        if self.in_short:
            last_row = df.iloc[-1]
            last_price = last_row['close']
            last_rsi = last_row['rsi14']
            last_timestamp = last_row.get('timestamp', df.index[-1])
            self.cover(last_price, last_timestamp, last_rsi, 'SHORT_END_OF_DATA')

    def get_results(self):
        if len(self.trades) == 0:
            return None

        shorts = [t for t in self.trades if t['type'] in ['SHORT', 'SHORT_DCA']]
        covers = [t for t in self.trades if t['type'] == 'COVER']

        total_profit = sum(s['profit'] for s in covers)
        total_profit_pct = ((self.cash - self.initial_capital) / self.initial_capital) * 100
        winning_trades = [s for s in covers if s['profit'] > 0]
        losing_trades = [s for s in covers if s['profit'] < 0]
        win_rate = (len(winning_trades) / len(covers) * 100) if len(covers) > 0 else 0
        avg_profit = np.mean([s['profit'] for s in covers]) if len(covers) > 0 else 0
        avg_profit_pct = np.mean([s['profit_pct'] for s in covers]) if len(covers) > 0 else 0

        sell_reasons = {}
        for s in covers:
            reason = s.get('reason', 'UNKNOWN')
            sell_reasons[reason] = sell_reasons.get(reason, 0) + 1

        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.cash,
            'total_profit': total_profit,
            'total_profit_pct': total_profit_pct,
            'total_trades': len(covers),
            'total_shorts': len(shorts),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_profit_pct': avg_profit_pct,
            'max_equity': max(self.equity_curve) if self.equity_curve else self.initial_capital,
            'min_equity': min(self.equity_curve) if self.equity_curve else self.initial_capital,
            'sell_reasons': sell_reasons,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        return results

