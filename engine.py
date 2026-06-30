import sqlite3
import pandas as pd

def analyze_market_data():
    print("Booting up the Analytical Engine...")
    
    # Connect to the database
    conn = sqlite3.connect('nse_data.db')
    
    # Load all the data you just scraped into a Pandas DataFrame
    query = "SELECT * FROM daily_prices"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert dates and sort so our timeline math works correctly
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['ticker', 'date'])
    
    alerts = []
    
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
        
        # Grab the very last row (today's closing data) to check for signals
        latest_data = group.iloc[-1]
        
        price = latest_data['close_price']
        z_score = latest_data['Z_Score']
        volume = latest_data['volume']
        vma = latest_data['VMA_10']
        
        # THE LOGIC GATE: Is volume 50% higher than the 10-day average?
        is_high_volume = volume > (vma * 1.5)  
        
        # Generate Alerts based on Z-Score and Volume confirmation
        if z_score <= -1.5 and is_high_volume:
            alerts.append(f"🟢 BUY ALERT | {ticker} | Price: {price} | Z-Score: {z_score:.2f} | High Volume Support Bounce!")
        elif z_score >= 1.5 and is_high_volume:
            alerts.append(f"🔴 SELL ALERT | {ticker} | Price: {price} | Z-Score: {z_score:.2f} | High Volume Resistance Hit!")
            
    # Output the final results
    print("\n--- TODAY'S MARKET SIGNALS ---")
    if not alerts:
        print("No actionable signals today. The market is within normal ranges.")
    else:
        for alert in alerts:
            print(alert)
            print("--------------------------------------------------")

if __name__ == "__main__":
    analyze_market_data()