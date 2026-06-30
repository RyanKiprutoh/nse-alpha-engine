import sqlite3
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'nse_data.db')

def analyze_market_data():
    print("Booting up the Analytical Engine...")
    
    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    
    # Load all the data you just scraped into a Pandas DataFrame
    query = "SELECT * FROM daily_prices"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("No historical market data found to analyze.")
        return
        
    # Convert dates and sort so our timeline math works correctly
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['ticker', 'date'])
    
    alerts = []
    database_inserts = []
    
    # Group the data by ticker so we run the math on each stock individually
    for ticker, group in df.groupby('ticker'):
        # Skip if we somehow don't have enough data
        if len(group) < 10:
            continue
            
        # 1. The Statistical Support Module (30-Day Mean Reversion)
        group['SMA_30'] = group['close_price'].rolling(window=30, min_periods=1).mean()
        group['STD_30'] = group['close_price'].rolling(window=30, min_periods=1).std()
        group['Z_Score'] = (group['close_price'] - group['SMA_30']) / group['STD_30']
        
        # 2. The Volume Breakout Module (10-Day Volume Average)
        group['VMA_10'] = group['volume'].rolling(window=10, min_periods=1).mean()
        
        # 3. The Institutional Guardrail (Trend Slope)
        # Calculates if the 30-day average is pointing up or down over the last 3 days
        group['Trend_Slope'] = group['SMA_30'].diff(periods=3).fillna(0)
        
        # Grab the very last row (today's closing data) to check for signals
        latest_data = group.iloc[-1]
        
        date_str = latest_data['date'].strftime('%Y-%m-%d')
        price = latest_data['close_price']
        z_score = latest_data['Z_Score']
        volume = latest_data['volume']
        vma = latest_data['VMA_10']
        trend_slope = latest_data['Trend_Slope']
        
        # THE LOGIC GATES
        is_high_volume = volume > (vma * 1.5)  
        is_uptrend = trend_slope >= 0
        is_downtrend = trend_slope < 0
        
        # 🟢 BUY ALERTS (Healthy Dips ONLY)
        # Price dropped to -1.5, but not into panic territory (>-2.5), and the broader trend is UP
        if -2.5 <= z_score <= -1.5 and is_high_volume and is_uptrend:
            msg = "Healthy Support Bounce in an Uptrend!"
            alerts.append(f"[BUY ALERT] | {ticker} | Price: {price} | Z-Score: {z_score:.2f} | {msg}")
            database_inserts.append((date_str, ticker, 'BUY', price, z_score, msg))
            
        # 🔴 SELL ALERTS (Overbought Rips)
        # Price jumped to +1.5, and the broader trend is DOWN (Dead Cat Bounce)
        elif 1.5 <= z_score <= 2.5 and is_high_volume and is_downtrend:
            msg = "Resistance Hit in a Downtrend!"
            alerts.append(f"[SELL ALERT] | {ticker} | Price: {price} | Z-Score: {z_score:.2f} | {msg}")
            database_inserts.append((date_str, ticker, 'SELL', price, z_score, msg))
            
        # ⚠️ DANGER ALERTS (Falling Knives / Institutional Dumping)
        # Price crashed violently below -2.5. Do not try to catch it.
        elif z_score < -2.5 and is_high_volume:
            msg = "CRASH WARNING: Severe Institutional Dumping. Avoid!"
            alerts.append(f"[AVOID ALERT] | {ticker} | Price: {price} | Z-Score: {z_score:.2f} | {msg}")
            database_inserts.append((date_str, ticker, 'AVOID', price, z_score, msg))
            
    # Output the final results to console terminal
    print("\n--- TODAY'S MARKET SIGNALS ---")
    if not alerts:
        print("No actionable signals today. The market is within normal ranges.")
    else:
        for alert in alerts:
            print(alert)
            print("--------------------------------------------------")
            
        # Write findings permanently to the database so Flask can see them
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO trade_signals (date, ticker, signal_type, price, z_score, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', database_inserts)
        conn.commit()
        conn.close()
        print(f"Successfully logged {len(database_inserts)} signal(s) to the database log file.")

if __name__ == "__main__":
    analyze_market_data()