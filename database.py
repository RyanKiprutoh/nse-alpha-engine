import sqlite3

def init_db():
    # This creates the file nse_data.db automatically if it does not exist
    conn = sqlite3.connect('nse_data.db')
    cursor = conn.cursor()

    # Create the daily_prices table 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            close_price REAL NOT NULL,
            volume INTEGER NOT NULL
        )
    ''')

    # Create the dividend_calender table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dividend_calender (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            book_closure_date TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print ("Database initialized and tables created successfully.")

if __name__ == "__main__":
    init_db()
