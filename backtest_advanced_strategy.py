"""
Advanced Backtest Engine with Multiple Improvements
Based on analysis: Only 3/24 reports were profitable
Key improvements:
1. Stricter trend filter (3-5 candle confirmation)
2. Support level confirmation
3. Market condition assessment
4. Multi-timeframe confirmation
5. Trailing stop loss
6. Higher volume threshold
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

def calculate_sma(prices, period=20):
    """Tính toán SMA"""
    return prices.rolling(window=period).mean()

def is_red_candle(row):
    """Kiểm tra nến đỏ"""
    return row['close'] < row['open']

def calculate_atr(high, low, close, period=14):
    """Tính Average True Range (ATR) cho volatility"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

class AdvancedStrategyBacktestEngine:
    def __init__(self, initial_capital=10000, fixed_amount=500, 
                 take_profit=0.05, stop_loss=0.025, 
                 rsi_buy=25, rsi_sell=75, max_dca=2,
                 rsi_period=14, timeframe='4H', higher_timeframe_df=None):
        """
        Advanced engine với nhiều cải tiến
        
        Parameters:
        - higher_timeframe_df: DataFrame của timeframe cao hơn để multi-timeframe confirmation
        """
        self.initial_capital = initial_capital
        self.fixed_amount = fixed_amount
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell
        self.max_dca = max_dca
        self.rsi_period = rsi_period
        self.timeframe = timeframe
        self.higher_timeframe_df = higher_timeframe_df
        
        # Điều chỉnh tham số theo timeframe
        self._adjust_params_by_timeframe()
        
        self.reset()
    
    def _adjust_params_by_timeframe(self):
        """Điều chỉnh tham số theo khung thời gian"""
        if self.timeframe in ['1H', '2H']:
            # Tránh 1H - quá nhiều noise
            if self.timeframe == '1H':
                self.rsi_buy = 20  # Stricter
                self.take_profit = 0.025  # 2.5% - smaller TP
                self.stop_loss = 0.015   # 1.5% - tighter SL
            else:  # 2H
                self.rsi_buy = 22
                self.take_profit = 0.04  # 4%
                self.stop_loss = 0.02   # 2%
        elif self.timeframe in ['4H', '6H']:
            # Focus on 4H and 6H - more stable
            self.rsi_buy = 24
            self.take_profit = 0.05  # 5%
            self.stop_loss = 0.025  # 2.5%
    
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
        self.last_dca_price = 0
        self.trend_confirmation_count = 0  # Track trend confirmation
        self.break_even_stop = False  # Trailing stop at break-even
    
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
        
        if is_dca:
            self.dca_count += 1
            self.last_dca_price = price
        else:
            self.dca_count = 0
            self.entry_timestamp = timestamp
            self.highest_price = price
            self.last_dca_price = price
            self.trend_confirmation_count = 0
            self.break_even_stop = False
        
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
        self.last_dca_price = 0
        self.trend_confirmation_count = 0
        self.break_even_stop = False
        
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
    
    def check_higher_timeframe_trend(self, current_timestamp):
        """Kiểm tra xu hướng trên timeframe cao hơn (multi-timeframe confirmation)"""
        if self.higher_timeframe_df is None or len(self.higher_timeframe_df) == 0:
            return True  # No higher timeframe data, allow trade
        
        # Find closest higher timeframe candle
        current_time = pd.to_datetime(current_timestamp)
        higher_df = self.higher_timeframe_df.copy()
        if 'timestamp' in higher_df.columns:
            higher_df['timestamp'] = pd.to_datetime(higher_df['timestamp'])
            higher_df = higher_df.sort_values('timestamp')
            
            # Find the most recent higher timeframe candle before current time
            past_candles = higher_df[higher_df['timestamp'] <= current_time]
            if len(past_candles) == 0:
                return True
            
            latest_candle = past_candles.iloc[-1]
            
            # Check if higher timeframe shows uptrend
            if 'ema50' in latest_candle and 'ema200' in latest_candle:
                if pd.notna(latest_candle['ema50']) and pd.notna(latest_candle['ema200']):
                    return latest_candle['close'] > latest_candle['ema200'] and latest_candle['ema50'] > latest_candle['ema200']
        
        return True
    
    def check_support_level(self, df, current_idx, lookback=20):
        """Kiểm tra giá có gần support level không"""
        if current_idx < lookback:
            return True  # Not enough data
        
        recent_lows = df.iloc[current_idx - lookback:current_idx]['low'].min()
        current_price = df.iloc[current_idx]['close']
        
        # Price is within 2% of recent low (support)
        support_distance = abs(current_price - recent_lows) / recent_lows
        return support_distance <= 0.02
    
    def assess_market_condition(self, df, current_idx, lookback=50):
        """Đánh giá điều kiện thị trường: trending up, trending down, or ranging"""
        if current_idx < lookback:
            return 'unknown'
        
        recent_data = df.iloc[current_idx - lookback:current_idx]
        prices = recent_data['close'].values
        
        # Calculate trend strength
        price_change = (prices[-1] - prices[0]) / prices[0]
        ema50 = recent_data['ema50'].iloc[-1] if 'ema50' in recent_data.columns else prices[-1]
        ema200 = recent_data['ema200'].iloc[-1] if 'ema200' in recent_data.columns else prices[-1]
        
        # Strong uptrend
        if price_change > 0.05 and ema50 > ema200 and prices[-1] > ema50:
            return 'uptrend'
        # Strong downtrend
        elif price_change < -0.05 and ema50 < ema200 and prices[-1] < ema50:
            return 'downtrend'
        # Ranging/consolidation
        else:
            return 'ranging'
    
    def run(self, df):
        """Chạy backtest với chiến lược nâng cao"""
        self.reset()
        
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
        
        # Tính các chỉ báo
        df['rsi14'] = calculate_rsi(df['close'], period=self.rsi_period)
        df['ema50'] = calculate_ema(df['close'], period=50)
        df['ema200'] = calculate_ema(df['close'], period=200)
        df['sma20'] = calculate_sma(df['close'], period=20)
        df['is_red'] = df.apply(is_red_candle, axis=1)
        df['atr'] = calculate_atr(df['high'], df['low'], df['close'], period=14)
        df['atr_ma'] = df['atr'].rolling(window=20).mean()
        
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
            ema50 = row['ema50']
            ema200 = row['ema200']
            sma20 = row['sma20']
            volume = row['volume']
            volume_ma = row['volume_ma']
            atr = row['atr']
            atr_ma = row['atr_ma']
            
            if pd.isna(rsi) or pd.isna(ema50) or pd.isna(ema200):
                self.equity_curve.append(self.get_current_value(close_price))
                continue
            
            # Logic bán với trailing stop
            if self.in_position:
                if close_price > self.highest_price:
                    self.highest_price = close_price
                
                profit_pct = self.get_current_profit_pct(close_price)
                avg_entry = self.get_average_entry_price()
                
                # Trailing stop loss: Move to break-even at 3% profit
                if profit_pct >= 3.0 and not self.break_even_stop:
                    self.break_even_stop = True
                
                # Trailing stop: 2% from highest when profit >= 5%
                if profit_pct >= (self.take_profit * 100):
                    trailing_stop_price = self.highest_price * 0.98
                    if close_price < trailing_stop_price:
                        self.sell(close_price, timestamp, rsi, f'TRAILING_STOP_{self.take_profit*100:.0f}%')
                        self.equity_curve.append(self.get_current_value(close_price))
                        continue
                
                # Break-even stop
                if self.break_even_stop and close_price < avg_entry:
                    self.sell(close_price, timestamp, rsi, 'BREAK_EVEN_STOP')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Cắt lỗ
                if profit_pct <= -(self.stop_loss * 100):
                    self.sell(close_price, timestamp, rsi, f'STOP_LOSS_{self.stop_loss*100:.1f}%')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Chốt lãi
                if profit_pct >= (self.take_profit * 100):
                    self.sell(close_price, timestamp, rsi, f'TAKE_PROFIT_{self.take_profit*100:.0f}%')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Bán khi RSI quá cao
                if rsi >= self.rsi_sell:
                    self.sell(close_price, timestamp, rsi, 'RSI_SELL')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
            
            # Logic mua với nhiều điều kiện
            can_buy = False
            
            # Điều kiện cơ bản: RSI thấp
            if rsi <= self.rsi_buy:
                # Strategy 1: Stricter trend filter - require 3-5 candles above EMA200
                is_uptrend = close_price > ema200 and ema50 > ema200
                
                if is_uptrend:
                    # Count consecutive candles above EMA200
                    if close_price > ema200:
                        self.trend_confirmation_count += 1
                    else:
                        self.trend_confirmation_count = 0
                    
                    # Require at least 3 candles above EMA200
                    if self.trend_confirmation_count >= 3:
                        can_buy = True
                else:
                    self.trend_confirmation_count = 0
                
                # Strategy 2: Support level confirmation
                if can_buy:
                    if not self.check_support_level(df, idx):
                        can_buy = False
                
                # Strategy 3: Market condition filter - avoid strong downtrends
                if can_buy:
                    market_condition = self.assess_market_condition(df, idx)
                    if market_condition == 'downtrend':
                        can_buy = False
                
                # Strategy 4: Multi-timeframe confirmation
                if can_buy:
                    if not self.check_higher_timeframe_trend(timestamp):
                        can_buy = False
                
                # Strategy 5: Higher volume threshold (1.2x instead of 0.8x)
                if can_buy:
                    if volume < volume_ma * 1.2:
                        can_buy = False
            
            if can_buy:
                if not self.in_position:
                    # Mua lần đầu
                    self.buy(close_price, timestamp, rsi, is_dca=False)
                else:
                    # DCA với điều kiện nghiêm ngặt hơn
                    avg_entry = self.get_average_entry_price()
                    price_drop_from_entry = ((avg_entry - close_price) / avg_entry) * 100
                    price_drop_from_last_dca = ((self.last_dca_price - close_price) / self.last_dca_price) * 100 if self.last_dca_price > 0 else 0
                    
                    # DCA chỉ khi:
                    # 1. Chưa đạt max DCA
                    # 2. Giá giảm ít nhất 4% từ entry (stricter)
                    # 3. Giá giảm ít nhất 3% từ lần DCA trước (stricter)
                    # 4. Vẫn trong uptrend
                    if (self.dca_count < self.max_dca and 
                        is_red and 
                        price_drop_from_entry >= 4.0 and
                        price_drop_from_last_dca >= 3.0 and
                        close_price > ema200):
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

