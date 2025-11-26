"""
Script so sánh chiến lược cũ và mới
"""

import pandas as pd
import subprocess
import sys

def run_backtest(script_name):
    """Chạy backtest và lấy kết quả"""
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout, result.stderr
    except Exception as e:
        return None, str(e)

def extract_results(output):
    """Trích xuất kết quả từ output"""
    results = {}
    lines = output.split('\n')
    
    for line in lines:
        if 'Tổng vốn ban đầu:' in line:
            try:
                value = float(line.split('$')[1].replace(',', ''))
                results['initial'] = value
            except:
                pass
        elif 'Tổng vốn cuối cùng:' in line:
            try:
                value = float(line.split('$')[1].replace(',', ''))
                results['final'] = value
            except:
                pass
        elif 'Tổng lợi nhuận:' in line:
            try:
                parts = line.split('$')[1].split('(')
                profit = float(parts[0].replace(',', ''))
                pct = float(parts[1].replace('%)', '').replace('+', '').replace(',', ''))
                results['profit'] = profit
                results['profit_pct'] = pct
            except:
                pass
    
    return results

def main():
    print("=" * 60)
    print("SO SÁNH CHIẾN LƯỢC CŨ VÀ MỚI")
    print("=" * 60)
    
    print("\n1. Chạy chiến lược cũ...")
    old_output, old_error = run_backtest('backtest.py')
    
    print("\n2. Chạy chiến lược cải tiến...")
    new_output, new_error = run_backtest('backtest_improved.py')
    
    print("\n" + "=" * 60)
    print("KẾT QUẢ SO SÁNH")
    print("=" * 60)
    
    old_results = extract_results(old_output) if old_output else {}
    new_results = extract_results(new_output) if new_output else {}
    
    if old_results and new_results:
        print(f"\n{'Chỉ số':<30} {'Chiến lược Cũ':<20} {'Chiến lược Mới':<20} {'Thay đổi':<15}")
        print("-" * 85)
        
        if 'profit_pct' in old_results and 'profit_pct' in new_results:
            change = new_results['profit_pct'] - old_results['profit_pct']
            change_str = f"{change:+.2f}%" if change != 0 else "0.00%"
            print(f"{'Lợi nhuận (%)':<30} {old_results['profit_pct']:>18.2f}% {new_results['profit_pct']:>18.2f}% {change_str:>15}")
        
        if 'final' in old_results and 'initial' in old_results:
            old_roi = ((old_results['final'] - old_results['initial']) / old_results['initial']) * 100
            print(f"{'ROI Chiến lược Cũ':<30} {old_roi:>18.2f}%")
        
        if 'final' in new_results and 'initial' in new_results:
            new_roi = ((new_results['final'] - new_results['initial']) / new_results['initial']) * 100
            print(f"{'ROI Chiến lược Mới':<30} {new_roi:>18.2f}%")
    
    print("\n" + "=" * 60)
    print("KHUYẾN NGHỊ")
    print("=" * 60)
    print("""
Dựa trên kết quả backtest, các cải tiến chính:

1. **Stop Loss**: Bảo vệ vốn khi thị trường đi ngược
2. **Trailing Stop**: Bảo vệ lợi nhuận khi giá đã tăng
3. **Take Profit cao hơn**: Cho phép position tăng giá nhiều hơn
4. **RSI ngưỡng tối ưu**: Giảm false signals
5. **Filter xu hướng**: Tránh mua trong downtrend
6. **Giới hạn DCA**: Quản lý rủi ro tốt hơn

Lưu ý: Kết quả có thể khác nhau tùy vào:
- Chất lượng dữ liệu
- Khung thời gian backtest
- Điều kiện thị trường
- Từng cặp token cụ thể

Nên test trên nhiều khoảng thời gian và điều chỉnh tham số cho phù hợp.
    """)

if __name__ == "__main__":
    main()


