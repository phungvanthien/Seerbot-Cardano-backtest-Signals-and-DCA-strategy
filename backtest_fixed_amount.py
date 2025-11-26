"""
Backtest Engine với số tiền cố định mỗi lệnh ($500)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Danh sách các cặp token
PAIRS = [
    'iBTCUSDM',
    'iETHUSDM', 
    'ADAUSDM',
    'WMTXUSDM',
    'IAGUSDM',
    'SNEKUSDM'
]

def calculate_rsi(prices, period=14):
    """Tính toán RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(prices, period=20):
    """Tính toán EMA"""
    return prices.ewm(span=period, adjust=False).mean()

def is_red_candle(row):
    """Kiểm tra nến đỏ"""
    return row['close'] < row['open']

class FixedAmountBacktestEngine:
    def __init__(self, initial_capital=10000, fixed_amount=500, 
                 take_profit=0.08, stop_loss=0.04, 
                 rsi_buy=25, rsi_sell=75, max_dca=3,
                 use_trend_filter=True, use_volume_filter=True,
                 rsi_period=14):
        """
        Engine với số tiền cố định mỗi lệnh
        
        Parameters:
        - initial_capital: Vốn ban đầu
        - fixed_amount: Số tiền cố định mỗi lệnh ($500)
        - take_profit: Mục tiêu lợi nhuận
        - stop_loss: Stop loss
        - rsi_buy: Ngưỡng RSI để mua
        - rsi_sell: Ngưỡng RSI để bán
        - max_dca: Số lần DCA tối đa
        """
        self.initial_capital = initial_capital
        self.fixed_amount = fixed_amount
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell
        self.max_dca = max_dca
        self.use_trend_filter = use_trend_filter
        self.use_volume_filter = use_volume_filter
        self.rsi_period = rsi_period
        
        self.reset()
    
    def reset(self):
        """Reset trạng thái"""
        self.cash = self.initial_capital
        self.position = 0
        self.entry_prices = []
        self.entry_amounts = []
        self.entry_capital = []
        self.in_position = False
        self.dca_count = 0
        self.highest_price = 0
        self.entry_timestamp = None
        self.trades = []
        self.equity_curve = []
    
    def get_average_entry_price(self):
        """Tính giá mua trung bình"""
        if len(self.entry_prices) == 0:
            return 0
        total_amount = sum(self.entry_amounts)
        if total_amount == 0:
            return 0
        weighted_sum = sum(price * amount for price, amount in zip(self.entry_prices, self.entry_amounts))
        return weighted_sum / total_amount
    
    def get_total_invested(self):
        """Tính tổng vốn đã đầu tư"""
        return sum(self.entry_capital)
    
    def buy(self, price, timestamp, rsi, is_dca=False):
        """Mua với số tiền cố định"""
        # Luôn dùng $500 (hoặc số tiền còn lại nếu ít hơn)
        capital_to_use = min(self.fixed_amount, self.cash)
        
        if capital_to_use < 10:  # Tối thiểu $10
            return False
        
        amount = capital_to_use / price
        if amount <= 0:
            return False
        
        self.cash -= capital_to_use
        self.position += amount
        self.entry_prices.append(price)
        self.entry_amounts.append(amount)
        self.entry_capital.append(capital_to_use)
        self.in_position = True
        
        if is_dca:
            self.dca_count += 1
        else:
            self.dca_count = 0
            self.entry_timestamp = timestamp
            self.highest_price = price
        
        trade_type = "DCA" if is_dca else "BUY"
        self.trades.append({
            'timestamp': timestamp,
            'type': trade_type,
            'price': price,
            'amount': amount,
            'capital': capital_to_use,
            'rsi': rsi,
            'position': self.position,
            'avg_entry_price': self.get_average_entry_price(),
            'cash': self.cash
        })
        
        return True
    
    def sell(self, price, timestamp, rsi, reason):
        """Bán position"""
        if self.position <= 0:
            return False
        
        proceeds = self.position * price
        total_invested = self.get_total_invested()
        profit = proceeds - total_invested
        profit_pct = (profit / total_invested * 100) if total_invested > 0 else 0
        
        self.cash += proceeds
        
        self.trades.append({
            'timestamp': timestamp,
            'type': 'SELL',
            'price': price,
            'amount': self.position,
            'proceeds': proceeds,
            'total_invested': total_invested,
            'profit': profit,
            'profit_pct': profit_pct,
            'rsi': rsi,
            'reason': reason,
            'cash': self.cash
        })
        
        # Reset
        self.position = 0
        self.entry_prices = []
        self.entry_amounts = []
        self.entry_capital = []
        self.in_position = False
        self.dca_count = 0
        self.highest_price = 0
        self.entry_timestamp = None
        
        return True
    
    def get_current_value(self, current_price):
        """Tính giá trị hiện tại"""
        return self.cash + (self.position * current_price)
    
    def get_current_profit_pct(self, current_price):
        """Tính lợi nhuận hiện tại"""
        if not self.in_position:
            return 0
        total_invested = self.get_total_invested()
        if total_invested == 0:
            return 0
        current_value = self.position * current_price
        profit = current_value - total_invested
        return (profit / total_invested) * 100
    
    def run(self, df):
        """Chạy backtest"""
        self.reset()
        
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
        
        df['rsi14'] = calculate_rsi(df['close'], period=self.rsi_period)
        df['ema20'] = calculate_ema(df['close'], period=20)
        df['is_red'] = df.apply(is_red_candle, axis=1)
        
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
        else:
            df['volume_ma'] = 1
            df['volume'] = 1
        
        for idx, row in df.iterrows():
            timestamp = row.get('timestamp', idx)
            close_price = row['close']
            rsi = row['rsi14']
            is_red = row['is_red']
            ema20 = row['ema20']
            volume = row['volume']
            volume_ma = row['volume_ma']
            
            if pd.isna(rsi) or pd.isna(ema20):
                self.equity_curve.append(self.get_current_value(close_price))
                continue
            
            # Logic bán
            if self.in_position:
                if close_price > self.highest_price:
                    self.highest_price = close_price
                
                trailing_stop_price = self.highest_price * (1 - 0.03)
                if close_price < trailing_stop_price and close_price < self.get_average_entry_price():
                    self.sell(close_price, timestamp, rsi, 'TRAILING_STOP')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Kiểm tra lợi nhuận/lỗ trước
                profit_pct = self.get_current_profit_pct(close_price)
                
                # Cắt lỗ khi -2.5%
                if profit_pct <= -2.5:
                    self.sell(close_price, timestamp, rsi, 'STOP_LOSS_2.5%')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Chốt lãi khi +5%
                if profit_pct >= 5.0:
                    self.sell(close_price, timestamp, rsi, 'TAKE_PROFIT_5%')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Stop loss cũ (nếu có)
                avg_entry = self.get_average_entry_price()
                stop_loss_price = avg_entry * (1 - self.stop_loss)
                if close_price <= stop_loss_price:
                    self.sell(close_price, timestamp, rsi, 'STOP_LOSS')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                if rsi >= self.rsi_sell:
                    self.sell(close_price, timestamp, rsi, 'RSI_SELL')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Take profit cũ (nếu có)
                if profit_pct >= (self.take_profit * 100):
                    self.sell(close_price, timestamp, rsi, 'TAKE_PROFIT')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
            
            # Logic mua
            can_buy = False
            
            if rsi <= self.rsi_buy:
                can_buy = True
                
                if self.use_trend_filter:
                    if close_price < ema20 * 0.95:
                        can_buy = False
                
                if self.use_volume_filter and can_buy:
                    if volume < volume_ma * 0.8:
                        can_buy = False
            
            if can_buy:
                if not self.in_position:
                    self.buy(close_price, timestamp, rsi, is_dca=False)
                else:
                    if is_red and self.dca_count < self.max_dca:
                        avg_entry = self.get_average_entry_price()
                        if close_price < avg_entry:
                            self.buy(close_price, timestamp, rsi, is_dca=True)
            
            self.equity_curve.append(self.get_current_value(close_price))
        
        # Bán hết nếu còn position
        if self.in_position:
            last_row = df.iloc[-1]
            last_price = last_row['close']
            last_rsi = last_row['rsi14']
            last_timestamp = last_row.get('timestamp', df.index[-1])
            self.sell(last_price, last_timestamp, last_rsi, 'END_OF_DATA')
    
    def get_results(self):
        """Tính toán kết quả"""
        if len(self.trades) == 0:
            return None
        
        buys = [t for t in self.trades if t['type'] in ['BUY', 'DCA']]
        sells = [t for t in self.trades if t['type'] == 'SELL']
        
        total_profit = sum(s['profit'] for s in sells)
        total_profit_pct = ((self.cash - self.initial_capital) / self.initial_capital) * 100
        
        winning_trades = [s for s in sells if s['profit'] > 0]
        losing_trades = [s for s in sells if s['profit'] < 0]
        
        win_rate = (len(winning_trades) / len(sells) * 100) if len(sells) > 0 else 0
        
        avg_profit = np.mean([s['profit'] for s in sells]) if len(sells) > 0 else 0
        avg_profit_pct = np.mean([s['profit_pct'] for s in sells]) if len(sells) > 0 else 0
        
        sell_reasons = {}
        for s in sells:
            reason = s.get('reason', 'UNKNOWN')
            sell_reasons[reason] = sell_reasons.get(reason, 0) + 1
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.cash,
            'total_profit': total_profit,
            'total_profit_pct': total_profit_pct,
            'total_trades': len(sells),
            'total_buys': len(buys),
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

