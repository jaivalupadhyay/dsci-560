import mysql.connector
import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta

# Database connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Password@123',
    'database': 'StockData'
}

# Function to fetch stock data from MySQL
def fetch_data_from_mysql():
    try:
        conn = mysql.connector.connect(**db_config)
        query = "SELECT * FROM stocks"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Function to preprocess stock data
def preprocess_data(df):
    # Handle missing values with forward fill and backward fill
    df.fillna(method='ffill', inplace=True)
    df.fillna(method='bfill', inplace=True)

    # Ensure date is in datetime format
    df['date'] = pd.to_datetime(df['date'])

    # Sort data by ticker and date
    df.sort_values(by=['ticker', 'date'], inplace=True)

    # Calculate daily returns
    df['prev_close'] = df.groupby('ticker')['close_price'].shift(1)
    df['daily_return'] = (df['close_price'] - df['prev_close']) / df['prev_close']
    df.drop(columns=['prev_close'], inplace=True)

    # Calculate 5-day moving average
    df['moving_avg_5'] = df.groupby('ticker')['close_price'].rolling(window=5).mean().reset_index(0, drop=True)

    # Calculate volatility (rolling standard deviation of daily returns over 5 days)
    df['volatility'] = df.groupby('ticker')['daily_return'].rolling(window=5).std().reset_index(0, drop=True)

    return df

# Function to save the processed data to a CSV file
def save_to_csv(df, file_name='processed_stock_data.csv'):
    try:
        df.to_csv(file_name, index=False)
        print(f"Processed data saved to {file_name}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

# Main execution
if __name__ == "__main__":
    # Fetch data from MySQL
    stock_df = fetch_data_from_mysql()

    if stock_df is not None:
        # Preprocess data
        processed_df = preprocess_data(stock_df)

        # Save processed data to CSV
        save_to_csv(processed_df)
