"""
Script backtest chiến lược RSI14 + DCA cho Cardano DEX
- Mua khi RSI14 <= 30 tại giá đóng cửa, sử dụng 5% vốn
- DCA tại các nến đỏ (close < open) sau lệnh mua đầu tiên, khi RSI14 < 30
- Bán khi RSI14 >= 70 hoặc lợi nhuận tổng >= 5%
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
    """
    Tính toán RSI (Relative Strength Index)
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def is_red_candle(row):
    """
    Kiểm tra xem nến có phải là nến đỏ không (close < open)
    """
    return row['close'] < row['open']

class BacktestEngine:
    def __init__(self, initial_capital=10000, position_size=0.05, take_profit=0.05):
        """
        Khởi tạo engine backtest
        
        Parameters:
        - initial_capital: Vốn ban đầu
        - position_size: Tỷ lệ vốn mỗi lần mua (5% = 0.05)
        - take_profit: Mục tiêu lợi nhuận (5% = 0.05)
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.take_profit = take_profit
        
        # Trạng thái giao dịch
        self.reset()
    
    def reset(self):
        """Reset trạng thái về ban đầu"""
        self.cash = self.initial_capital
        self.position = 0  # Số lượng token đang nắm giữ
        self.entry_prices = []  # Danh sách giá mua (để tính giá trung bình)
        self.entry_amounts = []  # Danh sách số lượng mua mỗi lần
        self.entry_capital = []  # Danh sách vốn sử dụng mỗi lần mua
        self.in_position = False
        self.first_buy_index = None
        
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
        """
        Thực hiện lệnh mua
        
        Parameters:
        - price: Giá mua (giá đóng cửa)
        - timestamp: Thời điểm mua
        - rsi: Giá trị RSI tại thời điểm mua
        - is_dca: Có phải là lệnh DCA không
        """
        # Tính số vốn sử dụng (5% tổng vốn hiện tại)
        capital_to_use = self.cash * self.position_size
        
        if capital_to_use < 0.01:  # Không đủ vốn
            return False
        
        # Tính số lượng token mua được
        amount = capital_to_use / price
        
        if amount <= 0:
            return False
        
        # Cập nhật trạng thái
        self.cash -= capital_to_use
        self.position += amount
        self.entry_prices.append(price)
        self.entry_amounts.append(amount)
        self.entry_capital.append(capital_to_use)
        self.in_position = True
        
        if not is_dca:
            self.first_buy_index = len(self.trades)
        
        # Ghi lại lệnh mua
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
        """
        Thực hiện lệnh bán
        
        Parameters:
        - price: Giá bán (giá đóng cửa)
        - timestamp: Thời điểm bán
        - rsi: Giá trị RSI tại thời điểm bán
        - reason: Lý do bán ('RSI' hoặc 'TAKE_PROFIT')
        """
        if self.position <= 0:
            return False
        
        # Tính tổng vốn thu về
        proceeds = self.position * price
        
        # Tính lợi nhuận
        total_invested = self.get_total_invested()
        profit = proceeds - total_invested
        profit_pct = (profit / total_invested * 100) if total_invested > 0 else 0
        
        # Cập nhật trạng thái
        self.cash += proceeds
        
        # Ghi lại lệnh bán
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
        self.first_buy_index = None
        
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
        """
        Chạy backtest trên DataFrame
        
        Parameters:
        - df: DataFrame chứa OHLCV data với cột: timestamp, open, high, low, close, volume
        """
        self.reset()
        
        # Đảm bảo có cột timestamp
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
        
        # Tính RSI14
        df['rsi14'] = calculate_rsi(df['close'], period=14)
        df['is_red'] = df.apply(is_red_candle, axis=1)
        
        # Vòng lặp qua từng nến
        for idx, row in df.iterrows():
            timestamp = row.get('timestamp', idx)
            close_price = row['close']
            rsi = row['rsi14']
            is_red = row['is_red']
            
            # Bỏ qua nếu RSI chưa tính được (NaN)
            if pd.isna(rsi):
                self.equity_curve.append(self.get_current_value(close_price))
                continue
            
            # Logic bán trước (ưu tiên)
            if self.in_position:
                # Bán nếu RSI >= 70
                if rsi >= 70:
                    self.sell(close_price, timestamp, rsi, 'RSI')
                # Bán nếu lợi nhuận >= 5%
                elif self.get_current_profit_pct(close_price) >= (self.take_profit * 100):
                    self.sell(close_price, timestamp, rsi, 'TAKE_PROFIT')
            
            # Logic mua
            if not self.in_position:
                # Mua lần đầu khi RSI <= 30
                if rsi <= 30:
                    self.buy(close_price, timestamp, rsi, is_dca=False)
            else:
                # DCA: mua thêm khi nến đỏ và RSI < 30 (sau lệnh mua đầu tiên)
                if is_red and rsi < 30:
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
        
        # Tách các lệnh mua và bán
        buys = [t for t in self.trades if t['type'] in ['BUY', 'DCA']]
        sells = [t for t in self.trades if t['type'] == 'SELL']
        
        # Tính tổng lợi nhuận
        total_profit = sum(s['profit'] for s in sells)
        total_profit_pct = ((self.cash - self.initial_capital) / self.initial_capital) * 100
        
        # Tính các chỉ số
        winning_trades = [s for s in sells if s['profit'] > 0]
        losing_trades = [s for s in sells if s['profit'] < 0]
        
        win_rate = (len(winning_trades) / len(sells) * 100) if len(sells) > 0 else 0
        
        avg_profit = np.mean([s['profit'] for s in sells]) if len(sells) > 0 else 0
        avg_profit_pct = np.mean([s['profit_pct'] for s in sells]) if len(sells) > 0 else 0
        
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
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        return results

def filter_data_by_date(df, year=2025, month=11, days=25):
    """
    Filter dữ liệu để lấy N ngày gần nhất của tháng/năm chỉ định
    
    Parameters:
    - df: DataFrame với cột timestamp
    - year: Năm cần filter
    - month: Tháng cần filter
    - days: Số ngày gần nhất cần lấy
    """
    if 'timestamp' not in df.columns:
        return df
    
    # Tìm các nến trong tháng/năm chỉ định
    df_filtered = df[
        (df['timestamp'].dt.year == year) & 
        (df['timestamp'].dt.month == month)
    ].copy()
    
    if len(df_filtered) == 0:
        # Nếu không có dữ liệu trong tháng/năm đó, lấy N ngày gần nhất từ toàn bộ dữ liệu
        print(f"⚠ Không tìm thấy dữ liệu cho {month}/{year}, lấy {days} ngày gần nhất")
        df_filtered = df.tail(days).copy()
    else:
        # Lấy N ngày gần nhất trong tháng
        df_filtered = df_filtered.tail(days).copy()
    
    return df_filtered.reset_index(drop=True)

def backtest_pair(pair, initial_capital=10000, position_size=0.05, take_profit=0.05, 
                  filter_year=None, filter_month=None, filter_days=None):
    """
    Backtest cho một cặp token
    
    Parameters:
    - pair: Tên cặp token (ví dụ: 'ADAUSDM')
    - initial_capital: Vốn ban đầu
    - position_size: Tỷ lệ vốn mỗi lần mua (5% = 0.05)
    - take_profit: Mục tiêu lợi nhuận (5% = 0.05)
    - filter_year: Năm để filter (None = không filter)
    - filter_month: Tháng để filter (None = không filter)
    - filter_days: Số ngày gần nhất cần lấy (None = lấy tất cả)
    """
    filename = f"data/{pair}_ohlcv.csv"
    
    if not os.path.exists(filename):
        print(f"✗ Không tìm thấy file {filename}")
        print(f"  Vui lòng chạy download_data.py trước để tải dữ liệu")
        return None
    
    print(f"\n{'='*60}")
    print(f"Backtest cho {pair}")
    print(f"{'='*60}")
    
    # Đọc dữ liệu
    try:
        df = pd.read_csv(filename)
        
        # Chuẩn hóa tên cột
        column_mapping = {
            'Timestamp': 'timestamp',
            'Date': 'timestamp',
            'time': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Đảm bảo timestamp là datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"✓ Đã tải {len(df)} nến dữ liệu ban đầu")
        print(f"  Từ: {df['timestamp'].iloc[0]} đến {df['timestamp'].iloc[-1]}")
        
        # Filter dữ liệu nếu có yêu cầu
        if filter_year and filter_month and filter_days:
            df = filter_data_by_date(df, filter_year, filter_month, filter_days)
            print(f"✓ Sau khi filter: {len(df)} nến dữ liệu")
            if len(df) > 0:
                print(f"  Từ: {df['timestamp'].iloc[0]} đến {df['timestamp'].iloc[-1]}")
        
    except Exception as e:
        print(f"✗ Lỗi khi đọc file {filename}: {e}")
        return None
    
    # Chạy backtest
    engine = BacktestEngine(
        initial_capital=initial_capital,
        position_size=position_size,
        take_profit=take_profit
    )
    
    engine.run(df)
    results = engine.get_results()
    
    if results is None:
        print("✗ Không có kết quả backtest")
        return None
    
    # In kết quả
    print(f"\n📊 KẾT QUẢ BACKTEST:")
    print(f"  Vốn ban đầu: ${results['initial_capital']:,.2f}")
    print(f"  Vốn cuối cùng: ${results['final_capital']:,.2f}")
    print(f"  Lợi nhuận: ${results['total_profit']:,.2f} ({results['total_profit_pct']:.2f}%)")
    print(f"\n📈 THỐNG KÊ GIAO DỊCH:")
    print(f"  Tổng số lệnh mua: {results['total_buys']}")
    print(f"  Tổng số lệnh bán: {results['total_trades']}")
    print(f"  Lệnh thắng: {results['winning_trades']}")
    print(f"  Lệnh thua: {results['losing_trades']}")
    print(f"  Tỷ lệ thắng: {results['win_rate']:.2f}%")
    print(f"  Lợi nhuận trung bình: ${results['avg_profit']:,.2f} ({results['avg_profit_pct']:.2f}%)")
    print(f"  Vốn tối đa: ${results['max_equity']:,.2f}")
    print(f"  Vốn tối thiểu: ${results['min_equity']:,.2f}")
    
    return results

def plot_results(results_dict):
    """
    Vẽ biểu đồ kết quả cho tất cả các cặp
    """
    if not results_dict:
        print("Không có dữ liệu để vẽ biểu đồ")
        return
    
    n_pairs = len(results_dict)
    fig, axes = plt.subplots(n_pairs, 1, figsize=(14, 4 * n_pairs))
    
    if n_pairs == 1:
        axes = [axes]
    
    for idx, (pair, results) in enumerate(results_dict.items()):
        if results is None:
            continue
        
        ax = axes[idx]
        equity = results['equity_curve']
        
        ax.plot(equity, label=f'{pair} Equity Curve', linewidth=2)
        ax.axhline(y=results['initial_capital'], color='r', linestyle='--', 
                   label='Initial Capital', alpha=0.7)
        ax.set_title(f'{pair} - Final: ${results["final_capital"]:,.2f} '
                    f'({results["total_profit_pct"]:+.2f}%)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Time (Candles)')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('backtest_results.png', dpi=300, bbox_inches='tight')
    print(f"\n✓ Đã lưu biểu đồ vào backtest_results.png")
    plt.show()

def generate_detailed_report(results_dict, output_file='backtest_detailed_report.csv'):
    """
    Tạo báo cáo chi tiết với tất cả các lệnh giao dịch
    """
    all_trades = []
    
    for pair, results in results_dict.items():
        if results is None:
            continue
        
        for trade in results['trades']:
            trade_record = trade.copy()
            trade_record['pair'] = pair
            all_trades.append(trade_record)
    
    if all_trades:
        df_trades = pd.DataFrame(all_trades)
        # Sắp xếp theo timestamp
        if 'timestamp' in df_trades.columns:
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'])
            df_trades = df_trades.sort_values(['pair', 'timestamp']).reset_index(drop=True)
        
        df_trades.to_csv(output_file, index=False)
        print(f"✓ Đã lưu báo cáo chi tiết vào {output_file}")
        return df_trades
    
    return None

def main():
    """
    Hàm chính để chạy backtest cho tất cả các cặp
    """
    print("=" * 60)
    print("BACKTEST CHIẾN LƯỢC RSI14 + DCA")
    print("=" * 60)
    print("\nTham số chiến lược:")
    print("  - Mua khi RSI14 <= 30, sử dụng 5% vốn")
    print("  - DCA tại nến đỏ khi RSI14 < 30")
    print("  - Bán khi RSI14 >= 70 hoặc lợi nhuận >= 5%")
    print("=" * 60)
    
    # Tham số backtest
    INITIAL_CAPITAL = 10000
    POSITION_SIZE = 0.05  # 5%
    TAKE_PROFIT = 0.05  # 5%
    
    # Filter: 25 ngày gần nhất của tháng 11/2025
    FILTER_YEAR = 2025
    FILTER_MONTH = 11
    FILTER_DAYS = 25
    
    print(f"\n📅 Filter dữ liệu: {FILTER_DAYS} ngày gần nhất của tháng {FILTER_MONTH}/{FILTER_YEAR}")
    print("=" * 60)
    
    # Chạy backtest cho từng cặp
    all_results = {}
    
    for pair in PAIRS:
        results = backtest_pair(
            pair=pair,
            initial_capital=INITIAL_CAPITAL,
            position_size=POSITION_SIZE,
            take_profit=TAKE_PROFIT,
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
    print(f"Tổng lợi nhuận: ${total_profit:,.2f} ({total_profit_pct:.2f}%)")
    
    # Vẽ biểu đồ
    try:
        plot_results(all_results)
    except Exception as e:
        print(f"\n⚠ Không thể vẽ biểu đồ: {e}")
    
    # Lưu kết quả chi tiết vào CSV
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
            summary_df.to_csv('backtest_summary.csv', index=False)
            print(f"\n✓ Đã lưu tổng hợp kết quả vào backtest_summary.csv")
            
            # Tạo báo cáo chi tiết với tất cả các lệnh
            generate_detailed_report(all_results, 'backtest_detailed_report.csv')
    except Exception as e:
        print(f"\n⚠ Không thể lưu kết quả: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

