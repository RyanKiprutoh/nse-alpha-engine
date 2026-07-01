import os
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import subprocess
import sys

app = Flask(__name__)
app.secret_key = 'nse_alpha_secure_key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'nse_data.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    
    # Fetch active monitored tickers
    tickers = conn.execute("SELECT ticker FROM monitored_tickers").fetchall()
    
    # Fetch the recent historical price entries to show database health
    recent_data = conn.execute("SELECT * FROM daily_prices ORDER BY date DESC, ticker ASC LIMIT 15").fetchall()
    
    # Fetch log records of generated signals
    signals = conn.execute("SELECT * FROM trade_signals ORDER BY timestamp DESC LIMIT 10").fetchall()
    
    # Fetch the active portfolio positions
    portfolio = conn.execute("SELECT * FROM portfolio WHERE status='OPEN' ORDER BY date_entered DESC").fetchall()
    
    conn.close()
    return render_template('index.html', tickers=tickers, recent_data=recent_data, signals=signals, portfolio=portfolio)

@app.route('/add_ticker', methods=['POST'])
def add_ticker():
    ticker = request.form.get('ticker', '').strip().upper()
    if ticker:
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO monitored_tickers (ticker) VALUES (?)", (ticker,))
            conn.commit()
            flash(f"Successfully added {ticker} to watchlists!", "success")
        except sqlite3.IntegrityError:
            flash(f"{ticker} is already being monitored.", "warning")
        finally:
            conn.close()
    return redirect(url_for('index'))

@app.route('/execute_trade/<signal_id>', methods=['POST'])
def execute_trade(signal_id):
    conn = get_db_connection()
    signal = conn.execute("SELECT * FROM trade_signals WHERE id = ?", (signal_id,)).fetchone()
    
    # Grab the manual notes the user typed in the dashboard
    user_notes = request.form.get('user_notes', '').strip()
    
    if signal:
        # Save both the engine's thesis (from the message) and the user's manual notes
        conn.execute('''
            INSERT INTO portfolio (ticker, entry_price, date_entered, thesis, user_notes) 
            VALUES (?, ?, ?, ?, ?)
        ''', (signal['ticker'], signal['price'], signal['date'], signal['message'], user_notes))
        conn.commit()
        flash(f"Trade Journaled for {signal['ticker']}. Ready for SokoPlay execution.", "success")
    
    conn.close()
    return redirect(url_for('index'))

@app.route('/run_scraper')
def run_scraper():
    try:
        # Executes scraper.py safely using the current Python environment environment
        result = subprocess.run([sys.executable, 'scraper.py'], capture_output=True, text=True, check=True)
        flash("Scraper executed successfully!", "success")
        return render_template('logs.html', title="Scraper Console Output", stdout=result.stdout, stderr=result.stderr)
    except subprocess.CalledProcessError as e:
        flash("Scraper encountered an execution error.", "danger")
        return render_template('logs.html', title="Scraper Execution Failure", stdout=e.stdout, stderr=e.stderr)

@app.route('/run_engine')
def run_engine():
    try:
        result = subprocess.run([sys.executable, 'engine.py'], capture_output=True, text=True, check=True)
        flash("Analytical Engine execution completed!", "success")
        return render_template('logs.html', title="Engine Analysis Output", stdout=result.stdout, stderr=result.stderr)
    except subprocess.CalledProcessError as e:
        flash("Engine encountered an execution error.", "danger")
        return render_template('logs.html', title="Engine Execution Failure", stdout=e.stdout, stderr=e.stderr)

if __name__ == '__main__':
    # Initialize connection using the absolute path file locator
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure the analytical logging platform exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            ticker TEXT,
            signal_type TEXT,
            price REAL,
            z_score REAL,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Ensure the NEW portfolio table exists with thesis and user_notes columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            entry_price REAL,
            shares INTEGER,
            date_entered TEXT,
            thesis TEXT,
            user_notes TEXT,
            status TEXT DEFAULT 'OPEN'
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Launch local web service engine
    app.run(debug=True, port=5000)
