import pandas as pd
import sqlite3
import requests
from io import StringIO

# Standard NSE Tickers
TICKERS = ['SCOM', 'EQTY', 'KCB', 'EABL', 'COOP']

def fetch_and_store_data():
    print("Starting data ingestion from African Financials...")
    
    # Connect to your SQLite memory bank
    conn = sqlite3.connect('nse_data.db')
    cursor = conn.cursor()
    
    # We use headers to mimic a real web browser so the site doesn't block us
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for ticker in TICKERS:
        print(f"Fetching data for {ticker}...")
        # The specific URL for each stock's historical data page
        url = f"https://afx.kwayisi.org/nse/{ticker.lower()}.html"
        
        try:
            response = requests.get(url, headers=headers)
            
            # Wrap the HTML text in StringIO so Pandas doesn't think it's a file path
            html_data = StringIO(response.text)
            tables = pd.read_html(html_data)
            
            # Find the specific table that contains the 'Date' and 'Close' columns
            hist_df = None
            for table in tables:
                if 'Date' in table.columns and 'Close' in table.columns:
                    hist_df = table
                    break
                    
            if hist_df is None or hist_df.empty:
                print(f"  -> Warning: No historical data table found for {ticker}.")
                continue
                
            # Iterate through the table rows and inject them into the database
            for index, row in hist_df.iterrows():
                try:
                    date_str = str(row['Date'])
                    close_price = float(row['Close'])
                    
                    # Clean up the volume data (remove commas and convert to integer)
                    vol_str = str(row['Volume']).replace(',', '')
                    volume = int(vol_str) if vol_str.isdigit() else 0
                    
                    # Check if this exact date and ticker combo already exists
                    cursor.execute('''
                        SELECT 1 FROM daily_prices WHERE date = ? AND ticker = ?
                    ''', (date_str, ticker))
                    
                    # If it doesn't exist, insert it safely
                    if not cursor.fetchone():
                        cursor.execute('''
                            INSERT INTO daily_prices (date, ticker, close_price, volume)
                            VALUES (?, ?, ?, ?)
                        ''', (date_str, ticker, close_price, volume))
                except Exception as row_err:
                    # Skips any empty or malformed rows on the website
                    continue 
                    
        except Exception as e:
            print(f"  -> Error connecting to page for {ticker}: {e}")
            
    # Save the changes and close the connection
    conn.commit()
    conn.close()
    print("Data ingestion complete. Database successfully updated!")

if __name__ == "__main__":
    fetch_and_store_data()