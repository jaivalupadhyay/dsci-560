import mysql.connector
import yfinance as yf
from datetime import datetime,date,timedelta

# Database connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Password@123',
    'database': 'StockData'
}


# Function to create the database and tables
def create_database_and_tables():
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS StockData")
        conn.database = db_config['database']
        cursor.execute("DROP TABLE IF EXISTS stocks")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                name VARCHAR(100),
                date DATE,
                sector VARCHAR(100),
                market_cap BIGINT,
                open_price DECIMAL(10, 4),
                high_price DECIMAL(10, 4),
                low_price DECIMAL(15, 4),
                close_price DECIMAL(15, 4),
                volume BIGINT
            )
        """)
        print("Database and table created successfully.")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()


# Function to fetch stock data from Yahoo Finance
def fetch_stock_data_date_range(tickers, start_date, end_date):
    stock_data = []
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=(datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"))
        info = stock.info

        for date, row in history.iterrows():
            stock_data_instance = {
                'ticker': ticker,
                'name': info.get('longName', 'N/A'),
                'date': date.date(),
                'sector': info.get('sector', 'N/A'),
                'market_cap': info.get('marketCap', 0),
                'open_price': row['Open'],
                'high_price': row['High'],
                'low_price': row['Low'],
                'close_price': row['Close'],
                'volume': row['Volume']
            }
            #print(stock_data_instance)
            stock_data.append(stock_data_instance)

        # print(len(stock_data),stock_data)
        # print('\n')

    return stock_data


# Function to write data to MySQL
def write_stock_data_to_mysql(stock_data):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        for stock in stock_data:
            cursor.execute("""
                INSERT INTO stocks (ticker,name,date,sector,market_cap,open_price,high_price,low_price,close_price,volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                stock['ticker'],
                stock['name'],
                stock['date'],
                stock['sector'],
                stock['market_cap'],
                stock['open_price'],
                stock['high_price'],
                stock['low_price'],
                stock['close_price'],
                stock['volume']
            ))
            conn.commit()
            print(f"Data for {stock['ticker']} inserted successfully.")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()


    
        

# Main execution
if __name__ == "__main__":
    #create database and table
    create_database_and_tables()


    # Define a list of stock tickers to fetch data for
    stock_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']


    # Fetch data from Yahoo Finance
    start_date = '2025-01-01'  # YYYY-MM-DD
    end_date = date.today().strftime("%Y-%m-%d")  # end is exlcusive
    
    stock_data = fetch_stock_data_date_range(stock_tickers, start_date, end_date)
    
    # Insert into table
    write_stock_data_to_mysql(stock_data)
    
  
    
