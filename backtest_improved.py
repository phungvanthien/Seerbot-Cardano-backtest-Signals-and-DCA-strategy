"""
Script backtest chiến lược RSI14 + DCA CẢI TIẾN cho Cardano DEX
Các cải tiến:
- Tăng take profit lên 8-10%
- Thêm stop loss 3-5%
- Điều chỉnh RSI ngưỡng (mua <= 25, bán >= 75)
- Giới hạn số lần DCA (tối đa 3 lần)
- Thêm filter xu hướng (EMA)
- Trailing stop loss
- Điều kiện volume
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
import matplotlib.pyplot as plt
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
    """Tính toán RSI (Relative Strength Index)"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(prices, period=20):
    """Tính toán EMA (Exponential Moving Average)"""
    return prices.ewm(span=period, adjust=False).mean()

def is_red_candle(row):
    """Kiểm tra xem nến có phải là nến đỏ không (close < open)"""
    return row['close'] < row['open']

class ImprovedBacktestEngine:
    def __init__(self, initial_capital=10000, position_size=0.05, 
                 take_profit=0.08, stop_loss=0.04, 
                 rsi_buy=25, rsi_sell=75, max_dca=3,
                 use_trend_filter=True, use_volume_filter=True):
        """
        Khởi tạo engine backtest cải tiến
        
        Parameters:
        - initial_capital: Vốn ban đầu
        - position_size: Tỷ lệ vốn mỗi lần mua (5% = 0.05)
        - take_profit: Mục tiêu lợi nhuận (8% = 0.08)
        - stop_loss: Stop loss (4% = 0.04)
        - rsi_buy: Ngưỡng RSI để mua (25)
        - rsi_sell: Ngưỡng RSI để bán (75)
        - max_dca: Số lần DCA tối đa (3)
        - use_trend_filter: Sử dụng filter xu hướng (EMA)
        - use_volume_filter: Sử dụng filter volume
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell
        self.max_dca = max_dca
        self.use_trend_filter = use_trend_filter
        self.use_volume_filter = use_volume_filter
        
        # Trạng thái giao dịch
        self.reset()
    
    def reset(self):
        """Reset trạng thái về ban đầu"""
        self.cash = self.initial_capital
        self.position = 0
        self.entry_prices = []
        self.entry_amounts = []
        self.entry_capital = []
        self.in_position = False
        self.dca_count = 0
        self.highest_price = 0  # Cho trailing stop
        self.entry_timestamp = None
        
        # Lịch sử giao dịch
        self.trades = []
        self.equity_curve = []
    
    def get_average_entry_price(self):
        """Tính giá mua trung bình (weighted average)"""
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
        """Thực hiện lệnh mua"""
        capital_to_use = self.cash * self.position_size
        
        if capital_to_use < 0.01:
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
            'cash': self.cash,
            'dca_count': self.dca_count
        })
        
        return True
    
    def sell(self, price, timestamp, rsi, reason):
        """Thực hiện lệnh bán"""
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
        
        # Reset position
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
        """Tính giá trị hiện tại của portfolio"""
        return self.cash + (self.position * current_price)
    
    def get_current_profit_pct(self, current_price):
        """Tính lợi nhuận hiện tại (phần trăm)"""
        if not self.in_position:
            return 0
        total_invested = self.get_total_invested()
        if total_invested == 0:
            return 0
        current_value = self.position * current_price
        profit = current_value - total_invested
        return (profit / total_invested) * 100
    
    def run(self, df):
        """Chạy backtest trên DataFrame"""
        self.reset()
        
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
        
        # Tính các chỉ báo
        df['rsi14'] = calculate_rsi(df['close'], period=14)
        df['ema20'] = calculate_ema(df['close'], period=20)
        df['is_red'] = df.apply(is_red_candle, axis=1)
        
        # Tính volume trung bình (cho filter)
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
        else:
            df['volume_ma'] = 1
            df['volume'] = 1
        
        # Vòng lặp qua từng nến
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
            
            # Logic bán trước (ưu tiên)
            if self.in_position:
                # Cập nhật highest price cho trailing stop
                if close_price > self.highest_price:
                    self.highest_price = close_price
                
                # Trailing stop loss (3% từ đỉnh)
                trailing_stop_price = self.highest_price * (1 - 0.03)
                if close_price < trailing_stop_price and close_price < self.get_average_entry_price():
                    self.sell(close_price, timestamp, rsi, 'TRAILING_STOP')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Stop loss (4% từ giá mua trung bình)
                avg_entry = self.get_average_entry_price()
                stop_loss_price = avg_entry * (1 - self.stop_loss)
                if close_price <= stop_loss_price:
                    self.sell(close_price, timestamp, rsi, 'STOP_LOSS')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Bán nếu RSI >= ngưỡng bán
                if rsi >= self.rsi_sell:
                    self.sell(close_price, timestamp, rsi, 'RSI_SELL')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
                
                # Bán nếu lợi nhuận >= take profit
                profit_pct = self.get_current_profit_pct(close_price)
                if profit_pct >= (self.take_profit * 100):
                    self.sell(close_price, timestamp, rsi, 'TAKE_PROFIT')
                    self.equity_curve.append(self.get_current_value(close_price))
                    continue
            
            # Logic mua
            # Kiểm tra điều kiện mua
            can_buy = False
            
            # Điều kiện RSI
            if rsi <= self.rsi_buy:
                can_buy = True
                
                # Filter xu hướng: chỉ mua khi giá trên EMA20 (uptrend) hoặc gần EMA20
                if self.use_trend_filter:
                    if close_price < ema20 * 0.95:  # Giá thấp hơn EMA20 quá 5%
                        can_buy = False
                
                # Filter volume: chỉ mua khi volume cao hơn trung bình
                if self.use_volume_filter and can_buy:
                    if volume < volume_ma * 0.8:  # Volume thấp hơn trung bình 20%
                        can_buy = False
            
            if can_buy:
                if not self.in_position:
                    # Mua lần đầu
                    self.buy(close_price, timestamp, rsi, is_dca=False)
                else:
                    # DCA: mua thêm khi nến đỏ và chưa vượt quá max_dca
                    if is_red and self.dca_count < self.max_dca:
                        # Chỉ DCA khi giá thấp hơn giá mua trung bình
                        avg_entry = self.get_average_entry_price()
                        if close_price < avg_entry:
                            self.buy(close_price, timestamp, rsi, is_dca=True)
            
            # Ghi lại equity curve
            self.equity_curve.append(self.get_current_value(close_price))
        
        # Nếu còn position ở cuối, bán hết
        if self.in_position:
            last_row = df.iloc[-1]
            last_price = last_row['close']
            last_rsi = last_row['rsi14']
            last_timestamp = last_row.get('timestamp', df.index[-1])
            self.sell(last_price, last_timestamp, last_rsi, 'END_OF_DATA')
    
    def get_results(self):
        """Tính toán và trả về kết quả backtest"""
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
        
        # Phân tích lý do bán
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

def filter_data_by_date(df, year=2025, month=11, days=25):
    """Filter dữ liệu để lấy N ngày gần nhất của tháng/năm chỉ định"""
    if 'timestamp' not in df.columns:
        return df
    
    df_filtered = df[
        (df['timestamp'].dt.year == year) & 
        (df['timestamp'].dt.month == month)
    ].copy()
    
    if len(df_filtered) == 0:
        df_filtered = df.tail(days).copy()
    else:
        df_filtered = df_filtered.tail(days).copy()
    
    return df_filtered.reset_index(drop=True)

def backtest_pair_improved(pair, initial_capital=10000, position_size=0.05, 
                          take_profit=0.08, stop_loss=0.04,
                          rsi_buy=25, rsi_sell=75, max_dca=3,
                          use_trend_filter=True, use_volume_filter=True,
                          filter_year=None, filter_month=None, filter_days=None):
    """Backtest cho một cặp token với chiến lược cải tiến"""
    filename = f"data/{pair}_ohlcv.csv"
    
    if not os.path.exists(filename):
        print(f"✗ Không tìm thấy file {filename}")
        return None
    
    print(f"\n{'='*60}")
    print(f"Backtest CẢI TIẾN cho {pair}")
    print(f"{'='*60}")
    
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
        
        print(f"✓ Đã tải {len(df)} nến dữ liệu ban đầu")
        print(f"  Từ: {df['timestamp'].iloc[0]} đến {df['timestamp'].iloc[-1]}")
        
        if filter_year and filter_month and filter_days:
            df = filter_data_by_date(df, filter_year, filter_month, filter_days)
            print(f"✓ Sau khi filter: {len(df)} nến dữ liệu")
            if len(df) > 0:
                print(f"  Từ: {df['timestamp'].iloc[0]} đến {df['timestamp'].iloc[-1]}")
        
    except Exception as e:
        print(f"✗ Lỗi khi đọc file {filename}: {e}")
        return None
    
    engine = ImprovedBacktestEngine(
        initial_capital=initial_capital,
        position_size=position_size,
        take_profit=take_profit,
        stop_loss=stop_loss,
        rsi_buy=rsi_buy,
        rsi_sell=rsi_sell,
        max_dca=max_dca,
        use_trend_filter=use_trend_filter,
        use_volume_filter=use_volume_filter
    )
    
    engine.run(df)
    results = engine.get_results()
    
    if results is None:
        print("✗ Không có kết quả backtest")
        return None
    
    print(f"\n📊 KẾT QUẢ BACKTEST:")
    print(f"  Vốn ban đầu: ${results['initial_capital']:,.2f}")
    print(f"  Vốn cuối cùng: ${results['final_capital']:,.2f}")
    print(f"  Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:+.2f}%)")
    print(f"\n📈 THỐNG KÊ GIAO DỊCH:")
    print(f"  Tổng số lệnh mua: {results['total_buys']}")
    print(f"  Tổng số lệnh bán: {results['total_trades']}")
    print(f"  Lệnh thắng: {results['winning_trades']}")
    print(f"  Lệnh thua: {results['losing_trades']}")
    print(f"  Tỷ lệ thắng: {results['win_rate']:.2f}%")
    print(f"  Lợi nhuận trung bình: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:+.2f}%)")
    print(f"  Vốn tối đa: ${results['max_equity']:,.2f}")
    print(f"  Vốn tối thiểu: ${results['min_equity']:,.2f}")
    
    if results.get('sell_reasons'):
        print(f"\n📋 LÝ DO BÁN:")
        for reason, count in results['sell_reasons'].items():
            print(f"  {reason}: {count} lần")
    
    return results

def main():
    """Hàm chính để chạy backtest cải tiến"""
    print("=" * 60)
    print("BACKTEST CHIẾN LƯỢC RSI14 + DCA CẢI TIẾN")
    print("=" * 60)
    print("\nCác cải tiến:")
    print("  ✓ Tăng take profit lên 8%")
    print("  ✓ Thêm stop loss 4%")
    print("  ✓ Trailing stop loss 3%")
    print("  ✓ Điều chỉnh RSI (mua <= 25, bán >= 75)")
    print("  ✓ Giới hạn DCA tối đa 3 lần")
    print("  ✓ Filter xu hướng (EMA20)")
    print("  ✓ Filter volume")
    print("=" * 60)
    
    # Tham số backtest cải tiến
    INITIAL_CAPITAL = 10000
    POSITION_SIZE = 0.05  # 5%
    TAKE_PROFIT = 0.08  # 8% (tăng từ 5%)
    STOP_LOSS = 0.04  # 4%
    RSI_BUY = 25  # Giảm từ 30 xuống 25 (mua ở oversold sâu hơn)
    RSI_SELL = 75  # Tăng từ 70 lên 75 (bán ở overbought cao hơn)
    MAX_DCA = 3  # Giới hạn DCA
    
    FILTER_YEAR = 2025
    FILTER_MONTH = 11
    FILTER_DAYS = 25
    
    print(f"\n📅 Filter dữ liệu: {FILTER_DAYS} ngày gần nhất của tháng {FILTER_MONTH}/{FILTER_YEAR}")
    print("=" * 60)
    
    all_results = {}
    
    for pair in PAIRS:
        results = backtest_pair_improved(
            pair=pair,
            initial_capital=INITIAL_CAPITAL,
            position_size=POSITION_SIZE,
            take_profit=TAKE_PROFIT,
            stop_loss=STOP_LOSS,
            rsi_buy=RSI_BUY,
            rsi_sell=RSI_SELL,
            max_dca=MAX_DCA,
            use_trend_filter=True,
            use_volume_filter=True,
            filter_year=FILTER_YEAR,
            filter_month=FILTER_MONTH,
            filter_days=FILTER_DAYS
        )
        all_results[pair] = results
    
    # Tổng hợp kết quả
    print(f"\n{'='*60}")
    print("TỔNG HỢP KẾT QUẢ")
    print(f"{'='*60}")
    
    total_initial = INITIAL_CAPITAL * len([r for r in all_results.values() if r is not None])
    total_final = sum(r['final_capital'] for r in all_results.values() if r is not None)
    total_profit = total_final - total_initial
    total_profit_pct = (total_profit / total_initial * 100) if total_initial > 0 else 0
    
    print(f"\nTổng vốn ban đầu: ${total_initial:,.2f}")
    print(f"Tổng vốn cuối cùng: ${total_final:,.2f}")
    print(f"Tổng lợi nhuận: ${total_profit:,.2f} ({total_profit_pct:+.2f}%)")
    
    # Lưu kết quả
    try:
        summary_data = []
        for pair, results in all_results.items():
            if results is None:
                continue
            summary_data.append({
                'Pair': pair,
                'Initial Capital': results['initial_capital'],
                'Final Capital': results['final_capital'],
                'Profit': results['total_profit'],
                'Profit %': results['total_profit_pct'],
                'Total Trades': results['total_trades'],
                'Total Buys': results['total_buys'],
                'Winning Trades': results['winning_trades'],
                'Losing Trades': results['losing_trades'],
                'Win Rate %': results['win_rate'],
                'Avg Profit': results['avg_profit'],
                'Avg Profit %': results['avg_profit_pct'],
                'Max Equity': results['max_equity'],
                'Min Equity': results['min_equity']
            })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv('backtest_improved_summary.csv', index=False)
            print(f"\n✓ Đã lưu tổng hợp kết quả vào backtest_improved_summary.csv")
    except Exception as e:
        print(f"\n⚠ Không thể lưu kết quả: {e}")

if __name__ == "__main__":
    main()


