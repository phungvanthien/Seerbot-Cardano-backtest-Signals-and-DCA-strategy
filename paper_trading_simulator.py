"""
Paper Trading Simulator - Mô phỏng giao dịch thực tế
Theo dõi và ghi lại tất cả các lệnh như giao dịch thực
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from backtest_improved import ImprovedBacktestEngine, PAIRS

class PaperTradingSimulator:
    def __init__(self, initial_capital=10000, params=None):
        """
        Khởi tạo Paper Trading Simulator
        
        Parameters:
        - initial_capital: Vốn ban đầu
        - params: Tham số chiến lược
        """
        self.initial_capital = initial_capital
        self.params = params or {
            'position_size': 0.07,
            'take_profit': 0.10,
            'stop_loss': 0.04,
            'rsi_buy': 25,
            'rsi_sell': 75,
            'max_dca': 3,
            'use_trend_filter': False,
            'use_volume_filter': False
        }
        
        self.trades_log = []
        self.daily_equity = []
        self.current_date = None
        
    def simulate_day(self, date, price_data):
        """
        Mô phỏng giao dịch trong một ngày
        
        Parameters:
        - date: Ngày giao dịch
        - price_data: Dict chứa open, high, low, close, volume, rsi
        """
        self.current_date = date
        
        # Lưu equity hàng ngày
        # (Trong thực tế, sẽ tính từ engine)
        self.daily_equity.append({
            'date': date,
            'equity': self.initial_capital  # Sẽ cập nhật từ engine
        })
    
    def run_simulation(self, pair, start_date=None, end_date=None):
        """
        Chạy mô phỏng paper trading cho một cặp
        
        Parameters:
        - pair: Tên cặp token
        - start_date: Ngày bắt đầu (None = từ đầu dữ liệu)
        - end_date: Ngày kết thúc (None = đến cuối dữ liệu)
        """
        filename = f"data/{pair}_ohlcv.csv"
        
        if not os.path.exists(filename):
            print(f"✗ Không tìm thấy file {filename}")
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
            
            # Filter theo ngày
            if start_date:
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['timestamp'] <= pd.to_datetime(end_date)]
            
            if len(df) < 14:
                return None
            
            # Chạy backtest engine
            engine_params = {
                'initial_capital': self.initial_capital,
                **self.params
            }
            
            engine = ImprovedBacktestEngine(**engine_params)
            engine.run(df)
            results = engine.get_results()
            
            if results:
                # Ghi lại tất cả các lệnh
                for trade in results['trades']:
                    self.trades_log.append({
                        'pair': pair,
                        'date': trade['timestamp'],
                        'type': trade['type'],
                        'price': trade['price'],
                        'amount': trade.get('amount', 0),
                        'capital': trade.get('capital', 0),
                        'rsi': trade.get('rsi', 0),
                        'profit': trade.get('profit', 0),
                        'profit_pct': trade.get('profit_pct', 0),
                        'reason': trade.get('reason', '')
                    })
                
                # Ghi lại equity curve
                for i, equity in enumerate(results['equity_curve']):
                    if i < len(df):
                        self.daily_equity.append({
                            'pair': pair,
                            'date': df.iloc[i]['timestamp'],
                            'equity': equity
                        })
            
            return results
            
        except Exception as e:
            print(f"Lỗi khi chạy simulation cho {pair}: {e}")
            return None
    
    def get_summary(self):
        """Tính toán và trả về tổng hợp kết quả"""
        if not self.trades_log:
            return None
        
        df_trades = pd.DataFrame(self.trades_log)
        
        buys = df_trades[df_trades['type'].isin(['BUY', 'DCA'])]
        sells = df_trades[df_trades['type'] == 'SELL']
        
        summary = {
            'total_trades': len(sells),
            'total_buys': len(buys),
            'winning_trades': len(sells[sells['profit'] > 0]),
            'losing_trades': len(sells[sells['profit'] <= 0]),
            'total_profit': sells['profit'].sum() if len(sells) > 0 else 0,
            'avg_profit': sells['profit'].mean() if len(sells) > 0 else 0,
            'win_rate': (len(sells[sells['profit'] > 0]) / len(sells) * 100) if len(sells) > 0 else 0
        }
        
        return summary
    
    def save_log(self, filename='paper_trading_log.json'):
        """Lưu log giao dịch"""
        log_data = {
            'initial_capital': self.initial_capital,
            'params': self.params,
            'trades': self.trades_log,
            'summary': self.get_summary()
        }
        
        with open(filename, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"✓ Đã lưu log vào {filename}")
    
    def export_trades_csv(self, filename='paper_trading_trades.csv'):
        """Xuất các lệnh giao dịch ra CSV"""
        if self.trades_log:
            df = pd.DataFrame(self.trades_log)
            df.to_csv(filename, index=False)
            print(f"✓ Đã xuất lệnh giao dịch vào {filename}")

def main():
    """Chạy Paper Trading Simulator"""
    print("=" * 80)
    print("PAPER TRADING SIMULATOR")
    print("=" * 80)
    print("\nMô phỏng giao dịch thực tế để test chiến lược")
    print("=" * 80)
    
    # Tham số
    initial_capital = 10000
    params = {
        'position_size': 0.07,
        'take_profit': 0.10,
        'stop_loss': 0.04,
        'rsi_buy': 25,
        'rsi_sell': 75,
        'max_dca': 3,
        'use_trend_filter': False,
        'use_volume_filter': False
    }
    
    # Thời gian test (30 ngày gần nhất)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\n📅 Thời gian test: {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}")
    print(f"💰 Vốn ban đầu: ${initial_capital:,.2f}")
    print(f"📊 Tham số: Position Size {params['position_size']*100}%, "
          f"Take Profit {params['take_profit']*100}%, "
          f"Stop Loss {params['stop_loss']*100}%")
    print("=" * 80)
    
    simulator = PaperTradingSimulator(initial_capital, params)
    
    # Chạy simulation cho từng cặp
    all_results = {}
    
    for pair in PAIRS:
        print(f"\n{'='*80}")
        print(f"Paper Trading: {pair}")
        print(f"{'='*80}")
        
        results = simulator.run_simulation(
            pair,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        all_results[pair] = results
        
        if results:
            print(f"✓ Kết quả:")
            print(f"  Lợi nhuận: {results['total_profit_pct']:.2f}%")
            print(f"  Số lệnh: {results['total_trades']}")
            print(f"  Win Rate: {results['win_rate']:.1f}%")
    
    # Tổng hợp
    print(f"\n{'='*80}")
    print("TỔNG HỢP KẾT QUẢ PAPER TRADING")
    print(f"{'='*80}")
    
    summary = simulator.get_summary()
    if summary:
        print(f"\n📊 Thống kê:")
        print(f"  Tổng số lệnh: {summary['total_trades']}")
        print(f"  Lệnh thắng: {summary['winning_trades']}")
        print(f"  Lệnh thua: {summary['losing_trades']}")
        print(f"  Win Rate: {summary['win_rate']:.1f}%")
        print(f"  Tổng lợi nhuận: ${summary['total_profit']:,.2f}")
        print(f"  Lợi nhuận trung bình/lệnh: ${summary['avg_profit']:,.2f}")
    
    # Lưu log
    simulator.save_log()
    simulator.export_trades_csv()
    
    print(f"\n{'='*80}")
    print("KHUYẾN NGHỊ")
    print(f"{'='*80}")
    print("""
1. Theo dõi kết quả paper trading trong ít nhất 1-2 tháng
2. So sánh với backtest để đảm bảo tính nhất quán
3. Điều chỉnh tham số nếu cần
4. Chỉ bắt đầu giao dịch thực khi paper trading cho kết quả ổn định
    """)

if __name__ == "__main__":
    main()


