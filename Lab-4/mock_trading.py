#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import math

############################################
# TECHNICAL INDICATOR & SIGNAL FUNCTIONS
############################################

def calculate_sma(df, window):
    """
    Calculate the Simple Moving Average (SMA) for the 'close_price' column.
    """
    return df['close_price'].rolling(window=window, min_periods=1).mean()

def generate_signals(df):
    """
    Generate buy and sell signals using a simple moving average crossover.
    
    Strategy:
      - Buy signal (set to 1): When the 5-day SMA crosses above the 20-day SMA and you are not holding shares.
      - Sell signal (set to -1): When the 5-day SMA crosses below the 20-day SMA and you are holding shares.
      
    This function iterates sequentially so that only one signal is generated until the position is switched.
    """
    df['buy_signal'] = 0
    df['sell_signal'] = 0
    position = 0  # 0 means no position; 1 means long
    
    for i in range(1, len(df)):
        if df.iloc[i]['sma_short'] > df.iloc[i]['sma_long'] and position == 0:
            df.at[df.index[i], 'buy_signal'] = 1
            position = 1
        elif df.iloc[i]['sma_short'] < df.iloc[i]['sma_long'] and position == 1:
            df.at[df.index[i], 'sell_signal'] = -1
            position = 0
    return df

############################################
# MOCK TRADING ENVIRONMENT FUNCTIONS
############################################

def simulate_trading(df, initial_cash):
    """
    Simulate a trading environment:
      - Start with an initial amount of cash.
      - When a buy signal occurs, buy as many shares as possible.
      - When a sell signal occurs, sell all shares held.
      - Update the portfolio value over time (cash + shares * current price).
      - Maintain a record of the number of shares held.
      - Record each transaction.
      
    Returns the updated DataFrame (with columns 'portfolio_value' and 'shares_held')
    and a transaction log (a list of dictionaries).
    """
    cash = initial_cash
    shares = 0
    portfolio_values = []
    shares_held_list = []
    transactions = []  # Each transaction is a dict: {date, action, shares, price}
    
    for idx, row in df.iterrows():
        price = row['close_price']
        current_date = idx  # since index is set to date
        # Buy signal: if buy_signal == 1 and cash is available
        if row['buy_signal'] == 1 and cash > 0:
            shares_to_buy = int(cash // price)
            if shares_to_buy > 0:
                cash -= shares_to_buy * price
                shares += shares_to_buy
                transactions.append({
                    'date': current_date,
                    'action': 'BUY',
                    'shares': shares_to_buy,
                    'price': price
                })
        # Sell signal: if sell_signal == -1 and shares are held
        elif row['sell_signal'] == -1 and shares > 0:
            cash += shares * price
            transactions.append({
                'date': current_date,
                'action': 'SELL',
                'shares': shares,
                'price': price
            })
            shares = 0
        
        portfolio_value = cash + shares * price
        portfolio_values.append(portfolio_value)
        shares_held_list.append(shares)
    
    df['portfolio_value'] = portfolio_values
    df['shares_held'] = shares_held_list
    return df, transactions

def compute_performance_metrics(df, initial_cash):
    """
    Compute performance metrics:
      - Final portfolio value.
      - Total return.
      - Annualized return.
      - Sharpe ratio (using daily returns).
    """
    # Assume the DataFrame index is datetime and sorted in ascending order.
    start_date = df.index[0]
    end_date = df.index[-1]
    days = (end_date - start_date).days
    years = days / 365.0 if days > 0 else 0
    final_value = df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_cash) / initial_cash
    annualized_return = ((final_value / initial_cash) ** (1 / years)) - 1 if years > 0 else 0

    df['daily_return'] = df['portfolio_value'].pct_change().fillna(0)
    avg_daily_return = df['daily_return'].mean()
    std_daily_return = df['daily_return'].std()
    sharpe_ratio = (avg_daily_return * 365 / (std_daily_return * np.sqrt(365))
                    if std_daily_return != 0 else np.nan)
    return final_value, total_return, annualized_return, sharpe_ratio

def simulate_trading_for_ticker(df_ticker, initial_cash):
    """
    For a single ticker's DataFrame:
      - Parse the dates and sort the data.
      - Compute technical indicators (5-day and 20-day SMAs).
      - Generate buy/sell signals.
      - Run the mock trading simulation.
      - Compute performance metrics.
      
    Returns:
      - Updated DataFrame with portfolio and position info.
      - Transaction log (list of dicts).
      - Final portfolio value, total return, annualized return, Sharpe ratio.
    """
    # Convert 'date' column to datetime and sort the data.
    df_ticker['date'] = pd.to_datetime(df_ticker['date'])
    df_ticker = df_ticker.sort_values(by='date')
    df_ticker.set_index('date', inplace=True)
    
    # Compute moving averages.
    df_ticker['sma_short'] = calculate_sma(df_ticker, window=5)
    df_ticker['sma_long'] = calculate_sma(df_ticker, window=20)
    
    # Generate buy/sell signals.
    df_ticker = generate_signals(df_ticker)
    
    # Run the trading simulation.
    df_ticker, transactions = simulate_trading(df_ticker, initial_cash)
    
    # Compute performance metrics.
    final_value, total_return, annualized_return, sharpe_ratio = compute_performance_metrics(df_ticker, initial_cash)
    
    return df_ticker, transactions, final_value, total_return, annualized_return, sharpe_ratio

############################################
# MAIN EXECUTION
############################################

if __name__ == "__main__":
    # Load the processed CSV file.
    # Expected columns: ticker, name, date, sector, market_cap, open_price, high_price, low_price, close_price, volume, daily_return, moving_avg_5, volatility
    csv_file = "processed_stock_data.csv"
    data = pd.read_csv(csv_file)
    
    # Check required columns.
    required_columns = ['ticker', 'date', 'close_price']
    for col in required_columns:
        if col not in data.columns:
            print(f"Error: Missing required column '{col}' in CSV.")
            exit(1)
    
    # Define total initial investment and allocate equally across tickers.
    total_initial_fund = 100000  # For example, $100,000 total
    tickers = data['ticker'].unique()
    allocation = total_initial_fund / len(tickers)  # equal allocation per ticker
    
    overall_portfolio_value = 0
    performance_summary = {}
    all_transactions = []  # To collect all transaction logs across tickers
    
    for ticker in tickers:
        print(f"\n--- Simulating for ticker: {ticker} ---")
        df_ticker = data[data['ticker'] == ticker].copy()
        
        # Run simulation for this ticker.
        sim_df, transactions, final_value, total_return, annualized_return, sharpe_ratio = simulate_trading_for_ticker(df_ticker, allocation)
        
        # Add the ticker info to each transaction.
        for t in transactions:
            t['ticker'] = ticker
        
        # Append to overall transactions.
        all_transactions.extend(transactions)
        
        # Display performance summary.
        print(f"Ticker: {ticker}")
        print(f"Final Portfolio Value: ${final_value:.2f}")
        print(f"Total Return: {total_return*100:.2f}%")
        print(f"Annualized Return: {annualized_return*100:.2f}%")
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        
        performance_summary[ticker] = {
            'final_value': final_value,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'transactions': transactions
        }
        
        # Plot portfolio value over time for this ticker.
        plt.figure(figsize=(10, 5))
        plt.plot(sim_df.index, sim_df['portfolio_value'], label='Portfolio Value', color='blue')
        plt.title(f"{ticker} Portfolio Value Over Time")
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value ($)")
        plt.legend()
        plt.grid(True)
        plt.show()
        
        overall_portfolio_value += final_value
    
    # Print overall summary.
    print("\n--- OVERALL PORTFOLIO SUMMARY ---")
    print(f"Total Portfolio Value: ${overall_portfolio_value:.2f}")
    print("Performance by Ticker:")
    for ticker, metrics in performance_summary.items():
        print(f"{ticker}: Final Value = ${metrics['final_value']:.2f}, Annualized Return = {metrics['annualized_return']*100:.2f}%, Sharpe Ratio = {metrics['sharpe_ratio']:.2f}")
    
    # Generate a CSV file for the transaction log.
    if all_transactions:
        transactions_df = pd.DataFrame(all_transactions)
        # Rearrange columns if desired.
        transactions_df = transactions_df[['ticker', 'date', 'action', 'shares', 'price']]
        transactions_df.to_csv("transaction_log.csv", index=False)
        print("\nTransaction log saved to 'transaction_log.csv'.")
    else:
        print("No transactions were recorded.")
