"""
ADX + DCA Strategy Backtest Engine
- Entry: Close price when ADX signal appears
- DCA: When price moves 5% higher or lower than first entry
- Take Profit: 5%
- Uses real data on all timeframes
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

def calculate_adx(high, low, close, period=14):
    """
    Calculate ADX (Average Directional Index)
    Returns: ADX, +DI, -DI
    """
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # Calculate smoothed TR and DM
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # Calculate DX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # Calculate ADX
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di

def calculate_ema(prices, period=20):
    """Tính toán EMA"""
    return prices.ewm(span=period, adjust=False).mean()

def is_red_candle(row):
    """Kiểm tra nến đỏ"""
    return row['close'] < row['open']

class ADXDCABacktestEngine:
    def __init__(self, initial_capital=10000, fixed_amount=500, 
                 take_profit=0.05, dca_threshold=0.05,
                 adx_period=14, adx_threshold=25,
                 rsi_period=14, rsi_oversold=30, rsi_overbought=70):
        """
        ADX + DCA Strategy Engine
        
        Parameters:
        - initial_capital: Vốn ban đầu
        - fixed_amount: Số tiền cố định mỗi lệnh ($500)
        - take_profit: Mục tiêu lợi nhuận (5%)
        - dca_threshold: Ngưỡng DCA (5% - giá lệch 5% so với entry đầu tiên)
        - adx_period: Chu kỳ ADX
        - adx_threshold: Ngưỡng ADX để xác định xu hướng mạnh
        - rsi_period: Chu kỳ RSI (dùng kết hợp với ADX)
        - rsi_oversold: RSI oversold level
        - rsi_overbought: RSI overbought level
        """
        self.initial_capital = initial_capital
        self.fixed_amount = fixed_amount
        self.take_profit = take_profit
        self.dca_threshold = dca_threshold
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        
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
        self.first_entry_price = 0  # Giá entry đầu tiên để tính DCA
        self.entry_timestamp = None
        self.trades = []
        self.equity_curve = []
        self.last_dca_direction = None  # 'up' or 'down' - hướng DCA cuối cùng
    
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
    
    def buy(self, price, timestamp, is_dca=False, reason=""):
        """Mua với số tiền cố định - Entry tại close price"""
        capital_to_use = min(self.fixed_amount, self.cash)
        
        if capital_to_use < 10:
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
        
        if not is_dca:
            # Entry đầu tiên
            self.first_entry_price = price
            self.entry_timestamp = timestamp
            self.dca_count = 0
            self.last_dca_direction = None
        else:
            self.dca_count += 1
        
        trade_type = "DCA" if is_dca else "BUY"
        self.trades.append({
            'timestamp': timestamp,
            'type': trade_type,
            'price': price,
            'amount': amount,
            'capital': capital_to_use,
            'position': self.position,
            'avg_entry_price': self.get_average_entry_price(),
            'cash': self.cash,
            'reason': reason
        })
        
        return True
    
    def sell(self, price, timestamp, reason):
        """Bán position - Exit tại close price"""
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
        self.first_entry_price = 0
        self.entry_timestamp = None
        self.last_dca_direction = None
        
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
    
    def calculate_rsi(self, prices, period=14):
        """Tính toán RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def check_buy_signal(self, row):
        """
        Kiểm tra tín hiệu mua dựa trên ADX
        - ADX > threshold (xu hướng mạnh)
        - +DI > -DI (xu hướng tăng)
        - RSI < overbought (chưa quá mua)
        """
        adx = row.get('adx', 0)
        plus_di = row.get('plus_di', 0)
        minus_di = row.get('minus_di', 0)
        rsi = row.get('rsi', 50)
        
        if pd.isna(adx) or pd.isna(plus_di) or pd.isna(minus_di) or pd.isna(rsi):
            return False
        
        # ADX cho thấy xu hướng mạnh
        if adx < self.adx_threshold:
            return False
        
        # +DI > -DI: xu hướng tăng
        if plus_di <= minus_di:
            return False
        
        # RSI không quá mua
        if rsi >= self.rsi_overbought:
            return False
        
        return True
    
    def check_sell_signal(self, row):
        """
        Kiểm tra tín hiệu bán dựa trên ADX
        - ADX > threshold (xu hướng mạnh)
        - -DI > +DI (xu hướng giảm)
        - RSI > oversold (chưa quá bán)
        """
        adx = row.get('adx', 0)
        plus_di = row.get('plus_di', 0)
        minus_di = row.get('minus_di', 0)
        rsi = row.get('rsi', 50)
        
        if pd.isna(adx) or pd.isna(plus_di) or pd.isna(minus_di) or pd.isna(rsi):
            return False
        
        # ADX cho thấy xu hướng mạnh
        if adx < self.adx_threshold:
            return False
        
        # -DI > +DI: xu hướng giảm
        if minus_di <= plus_di:
            return False
        
        # RSI không quá bán
        if rsi <= self.rsi_oversold:
            return False
        
        return True
    
    def check_dca_condition(self, current_price):
        """
        Kiểm tra điều kiện DCA
        DCA khi giá lệch 5% so với entry đầu tiên (cao hơn hoặc thấp hơn)
        """
        if self.first_entry_price == 0:
            return False, None
        
        price_change_pct = ((current_price - self.first_entry_price) / self.first_entry_price) * 100
        
        # DCA khi giá cao hơn 5%
        if price_change_pct >= (self.dca_threshold * 100):
            # Chỉ DCA nếu chưa DCA theo hướng này
            if self.last_dca_direction != 'up':
                return True, 'up'
        
        # DCA khi giá thấp hơn 5%
        if price_change_pct <= -(self.dca_threshold * 100):
            # Chỉ DCA nếu chưa DCA theo hướng này
            if self.last_dca_direction != 'down':
                return True, 'down'
        
        return False, None
    
    def run(self, df):
        """Chạy backtest với chiến lược ADX + DCA"""
        self.reset()
        
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
        
        # Tính các chỉ báo
        df['adx'], df['plus_di'], df['minus_di'] = calculate_adx(
            df['high'], df['low'], df['close'], period=self.adx_period
        )
        df['rsi'] = self.calculate_rsi(df['close'], period=self.rsi_period)
        df['ema20'] = calculate_ema(df['close'], period=20)
        df['is_red'] = df.apply(is_red_candle, axis=1)
        
        for idx, row in df.iterrows():
            timestamp = row.get('timestamp', idx)
            close_price = row['close']  # Entry/Exit tại close price
            
            # Logic bán
            if self.in_position:
                # Kiểm tra lợi nhuận
                profit_pct = self.get_current_profit_pct(close_price)
                
                # Chốt lãi khi đạt 5%
                if profit_pct >= (self.take_profit * 100):
                    self.sell(close_price, timestamp, f'TAKE_PROFIT_{self.take_profit*100:.0f}%')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Kiểm tra tín hiệu bán từ ADX
                if self.check_sell_signal(row):
                    self.sell(close_price, timestamp, 'ADX_SELL_SIGNAL')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
            
            # Logic mua
            # Kiểm tra tín hiệu mua từ ADX
            if self.check_buy_signal(row):
                if not self.in_position:
                    # Entry đầu tiên tại close price
                    self.buy(close_price, timestamp, is_dca=False, reason='ADX_BUY_SIGNAL')
                else:
                    # Kiểm tra điều kiện DCA
                    should_dca, direction = self.check_dca_condition(close_price)
                    if should_dca:
                        self.last_dca_direction = direction
                        reason = f'DCA_{direction.upper()}_5%'
                        self.buy(close_price, timestamp, is_dca=True, reason=reason)
            
            # Nếu đã có position, kiểm tra DCA (ngay cả khi không có tín hiệu mua mới)
            if self.in_position:
                should_dca, direction = self.check_dca_condition(close_price)
                if should_dca and self.last_dca_direction != direction:
                    self.last_dca_direction = direction
                    reason = f'DCA_{direction.upper()}_5%'
                    self.buy(close_price, timestamp, is_dca=True, reason=reason)
            
            self.equity_curve.append(self.get_current_value(close_price))
        
        # Bán hết nếu còn position
        if self.in_position:
            last_row = df.iloc[-1]
            last_price = last_row['close']
            last_timestamp = last_row.get('timestamp', df.index[-1])
            self.sell(last_price, last_timestamp, 'END_OF_DATA')
    
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

