"""
Parabolic SAR + DCA Strategy Backtest Engine
- Entry/Exit: Open price when SAR signal appears
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

def calculate_psar(high, low, close, af_start=0.02, af_increment=0.02, af_max=0.2):
    """
    Calculate Parabolic SAR (Stop and Reverse)
    
    Parameters:
    - af_start: Acceleration factor start (default 0.02)
    - af_increment: Acceleration factor increment (default 0.02)
    - af_max: Maximum acceleration factor (default 0.2)
    
    Returns:
    - psar: Parabolic SAR values
    - trend: 1 for uptrend, -1 for downtrend
    """
    psar = pd.Series(index=close.index, dtype=float)
    trend = pd.Series(index=close.index, dtype=int)
    
    # Initialize
    psar.iloc[0] = low.iloc[0]
    trend.iloc[0] = 1  # Start with uptrend
    af = af_start
    ep = high.iloc[0]  # Extreme point
    
    for i in range(1, len(close)):
        prev_psar = psar.iloc[i-1]
        prev_trend = trend.iloc[i-1]
        prev_af = af
        prev_ep = ep
        
        # Calculate new SAR
        if prev_trend == 1:  # Uptrend
            new_sar = prev_psar + prev_af * (prev_ep - prev_psar)
            new_sar = min(new_sar, low.iloc[i-1], low.iloc[i])
            
            # Check for reversal
            if new_sar >= low.iloc[i]:
                # Reverse to downtrend
                trend.iloc[i] = -1
                psar.iloc[i] = prev_ep
                af = af_start
                ep = low.iloc[i]
            else:
                # Continue uptrend
                trend.iloc[i] = 1
                psar.iloc[i] = new_sar
                
                # Update extreme point and acceleration factor
                if high.iloc[i] > prev_ep:
                    ep = high.iloc[i]
                    af = min(af + af_increment, af_max)
                else:
                    ep = prev_ep
                    af = prev_af
        else:  # Downtrend
            new_sar = prev_psar - prev_af * (prev_psar - prev_ep)
            new_sar = max(new_sar, high.iloc[i-1], high.iloc[i])
            
            # Check for reversal
            if new_sar <= high.iloc[i]:
                # Reverse to uptrend
                trend.iloc[i] = 1
                psar.iloc[i] = prev_ep
                af = af_start
                ep = high.iloc[i]
            else:
                # Continue downtrend
                trend.iloc[i] = -1
                psar.iloc[i] = new_sar
                
                # Update extreme point and acceleration factor
                if low.iloc[i] < prev_ep:
                    ep = low.iloc[i]
                    af = min(af + af_increment, af_max)
                else:
                    ep = prev_ep
                    af = prev_af
    
    return psar, trend

class PSARDCABacktestEngine:
    def __init__(self, initial_capital=10000, fixed_amount=500, 
                 take_profit=0.05, dca_threshold=0.05,
                 psar_af_start=0.02, psar_af_increment=0.02, psar_af_max=0.2):
        """
        Parabolic SAR + DCA Strategy Engine
        
        Parameters:
        - initial_capital: Vốn ban đầu
        - fixed_amount: Số tiền cố định mỗi lệnh ($500)
        - take_profit: Mục tiêu lợi nhuận (5%)
        - dca_threshold: Ngưỡng DCA (5% - giá lệch 5% so với entry đầu tiên)
        - psar_af_start: SAR acceleration factor start
        - psar_af_increment: SAR acceleration factor increment
        - psar_af_max: SAR acceleration factor max
        """
        self.initial_capital = initial_capital
        self.fixed_amount = fixed_amount
        self.take_profit = take_profit
        self.dca_threshold = dca_threshold
        self.psar_af_start = psar_af_start
        self.psar_af_increment = psar_af_increment
        self.psar_af_max = psar_af_max
        
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
        self.last_trend = 0  # Track last SAR trend to detect signal changes
    
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
        """Mua với số tiền cố định - Entry tại open price"""
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
        """Bán position - Exit tại open price"""
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
    
    def check_buy_signal(self, current_trend, prev_trend):
        """
        Kiểm tra tín hiệu mua từ Parabolic SAR
        Tín hiệu mua: SAR trend chuyển từ -1 (downtrend) sang 1 (uptrend)
        """
        if prev_trend == -1 and current_trend == 1:
            return True
        return False
    
    def check_sell_signal(self, current_trend, prev_trend):
        """
        Kiểm tra tín hiệu bán từ Parabolic SAR
        Tín hiệu bán: SAR trend chuyển từ 1 (uptrend) sang -1 (downtrend)
        """
        if prev_trend == 1 and current_trend == -1:
            return True
        return False
    
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
        """Chạy backtest với chiến lược Parabolic SAR + DCA"""
        self.reset()
        
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
        
        # Tính Parabolic SAR
        df['psar'], df['psar_trend'] = calculate_psar(
            df['high'], df['low'], df['close'],
            af_start=self.psar_af_start,
            af_increment=self.psar_af_increment,
            af_max=self.psar_af_max
        )
        
        for idx, row in df.iterrows():
            timestamp = row.get('timestamp', idx)
            open_price = row['open']  # Entry/Exit tại open price
            close_price = row['close']  # Dùng để tính profit hiện tại
            psar_trend = row['psar_trend']
            
            if pd.isna(psar_trend):
                self.equity_curve.append(self.get_current_value(close_price))
                continue
            
            # Logic bán
            if self.in_position:
                # Kiểm tra lợi nhuận
                profit_pct = self.get_current_profit_pct(close_price)
                
                # Chốt lãi khi đạt 5%
                if profit_pct >= (self.take_profit * 100):
                    self.sell(open_price, timestamp, f'TAKE_PROFIT_{self.take_profit*100:.0f}%')
                    self.equity_curve.append(self.get_current_value(close_price))
                    self.last_trend = psar_trend
                    continue
                
                # Kiểm tra tín hiệu bán từ SAR
                if self.check_sell_signal(psar_trend, self.last_trend):
                    self.sell(open_price, timestamp, 'PSAR_SELL_SIGNAL')
                    self.equity_curve.append(self.get_current_value(close_price))
                    self.last_trend = psar_trend
                    continue
            
            # Logic mua
            # Kiểm tra tín hiệu mua từ SAR
            if self.check_buy_signal(psar_trend, self.last_trend):
                if not self.in_position:
                    # Entry đầu tiên tại open price
                    self.buy(open_price, timestamp, is_dca=False, reason='PSAR_BUY_SIGNAL')
                else:
                    # Kiểm tra điều kiện DCA
                    should_dca, direction = self.check_dca_condition(open_price)
                    if should_dca:
                        self.last_dca_direction = direction
                        reason = f'DCA_{direction.upper()}_5%'
                        self.buy(open_price, timestamp, is_dca=True, reason=reason)
            
            # Nếu đã có position, kiểm tra DCA (ngay cả khi không có tín hiệu mua mới)
            if self.in_position:
                should_dca, direction = self.check_dca_condition(open_price)
                if should_dca and self.last_dca_direction != direction:
                    self.last_dca_direction = direction
                    reason = f'DCA_{direction.upper()}_5%'
                    self.buy(open_price, timestamp, is_dca=True, reason=reason)
            
            # Update last trend
            self.last_trend = psar_trend
            self.equity_curve.append(self.get_current_value(close_price))
        
        # Bán hết nếu còn position
        if self.in_position:
            last_row = df.iloc[-1]
            last_price = last_row['open']
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

