#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import math
import warnings
warnings.filterwarnings("ignore")

############################################
# TECHNICAL INDICATOR & TRADING FUNCTIONS
############################################

def calculate_sma(df, window):
    """
    Calculate the Simple Moving Average (SMA) for the 'close_price' column.
    """
    return df['close_price'].rolling(window=window, min_periods=1).mean()

def calculate_rsi(df, window):
    """
    Calculate the Relative Strength Index (RSI) for the 'close_price' column.
    """
    delta = df['close_price'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.rolling(window=window, min_periods=1).mean()
    ma_down = down.rolling(window=window, min_periods=1).mean()
    rsi = 100 - (100 / (1 + ma_up / ma_down))
    return rsi

def generate_signals(df):
    """
    Generate buy and sell signals.
    
    Rules:
      - Buy Signal (1): When sma_short > sma_long and RSI < 40, and no current "long" position.
      - Sell Signal (-1): When sma_short < sma_long or RSI > 60, and a long position is held.
    """
    df['buy_signal'] = 0
    df['sell_signal'] = 0
    position = None  # Track whether we hold a 'long' position

    for idx, row in df.iterrows():
        if row['sma_short'] > row['sma_long'] and row['rsi'] < 40:
            if position != 'long':
                df.at[idx, 'buy_signal'] = 1
                position = 'long'
        elif row['sma_short'] < row['sma_long'] or row['rsi'] > 60:
            if position == 'long':
                df.at[idx, 'sell_signal'] = -1
                position = None
    return df

def mock_trading(df, initial_fund):
    """
    Mock Trading Environment:
      - Start with initial_fund as cash.
      - On a buy signal, buy as many shares as possible.
      - On a sell signal, sell all held shares.
      - Record transactions and update the portfolio value over time.
    """
    cash = initial_fund
    shares_held = 0
    portfolio_values = []
    transaction_log = []  # Records tuples: (Date, Action, Shares, Price)

    for idx, row in df.iterrows():
        price = row['close_price']
        # Execute buy if buy_signal is set and not already in a long position.
        if row['buy_signal'] == 1:
            shares_to_buy = int(cash // price)
            if shares_to_buy > 0:
                cash -= shares_to_buy * price
                shares_held += shares_to_buy
                transaction_log.append((row.name, 'BUY', shares_to_buy, price))
        # Execute sell if sell_signal is set and shares are held.
        elif row['sell_signal'] == -1 and shares_held > 0:
            cash += shares_held * price
            transaction_log.append((row.name, 'SELL', shares_held, price))
            shares_held = 0

        portfolio_values.append(cash + shares_held * price)

    df['portfolio_value'] = portfolio_values
    transaction_df = pd.DataFrame(transaction_log, columns=['Date', 'Action', 'Shares', 'Price'])
    return df, transaction_df

def calculate_annualized_returns(df, initial_fund):
    """
    Calculate the annualized return from the portfolio value time series.
    """
    start_date = df.index[0]
    end_date = df.index[-1]
    years = (end_date - start_date).days / 365.0
    final_value = df['portfolio_value'].iloc[-1]
    annualized_return = ((final_value / initial_fund) ** (1 / years)) - 1 if years > 0 else 0
    return annualized_return

def calculate_sharpe_ratio(df, risk_free_rate=0.0001):
    """
    Calculate the Sharpe ratio using the daily returns of the portfolio.
    """
    daily_returns = df['portfolio_value'].pct_change().fillna(0)
    avg_daily_return = daily_returns.mean()
    std_daily_return = daily_returns.std()
    annualized_avg_return = avg_daily_return * 365
    annualized_std = std_daily_return * np.sqrt(365)
    sharpe_ratio = ((annualized_avg_return - risk_free_rate) / annualized_std
                    if annualized_std != 0 else float('nan'))
    return sharpe_ratio

############################################
# PREDICTION FUNCTION USING ARIMA
############################################

def forecast_arima(df, forecast_steps=5):
    """
    Fit an ARIMA model on the 'close_price' series and forecast future prices.
    Returns the forecasted mean and confidence intervals.
    """
    from statsmodels.tsa.arima.model import ARIMA

    series = df['close_price']
    try:
        # ARIMA order (4,1,1) is chosen as an example – adjust as needed
        model = ARIMA(series, order=(4, 1, 1))
        fitted_model = model.fit()
        forecast = fitted_model.get_forecast(steps=forecast_steps)
        forecast_mean = forecast.predicted_mean
        conf_int = forecast.conf_int(alpha=0.05)
    except Exception as e:
        print("ARIMA forecasting error:", e)
        forecast_mean, conf_int = None, None
    return forecast_mean, conf_int

############################################
# SIMULATION FOR EACH TICKER
############################################

def simulate_trading_for_ticker(df, initial_fund):
    """
    For a single ticker DataFrame:
      - Ensure data is sorted and the 'date' column is parsed.
      - Calculate technical indicators (SMA, RSI).
      - Generate buy/sell signals.
      - Run the mock trading simulation.
      - Compute performance metrics.
    """
    # Convert 'date' column to datetime and sort
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by='date', inplace=True)
    df.set_index('date', inplace=True)

    # Define technical indicator parameters
    sma_short_window = 50
    sma_long_window = 200
    rsi_window = 20

    # Calculate technical indicators using 'close_price'
    df['sma_short'] = calculate_sma(df, sma_short_window)
    df['sma_long'] = calculate_sma(df, sma_long_window)
    df['rsi'] = calculate_rsi(df, rsi_window)

    # Generate buy/sell signals
    df = generate_signals(df)

    # Run the mock trading simulation
    df, transaction_log = mock_trading(df, initial_fund)

    # Compute performance metrics
    annual_return = calculate_annualized_returns(df, initial_fund)
    sharpe_ratio = calculate_sharpe_ratio(df)
    
    return df, transaction_log, annual_return, sharpe_ratio

############################################
# MAIN EXECUTION
############################################

if __name__ == "__main__":
    # Load the processed CSV file (generated by your MySQL extraction/preprocessing code)
    csv_file = 'processed_stock_data.csv'
    all_data = pd.read_csv(csv_file)
    
    # Ensure the date column is in datetime format
    all_data['date'] = pd.to_datetime(all_data['date'])
    
    # Define initial investment fund per ticker
    initial_investment = 10000

    # Dictionaries to store results per ticker
    portfolios = {}
    annual_returns = {}
    sharpe_ratios = {}
    overall_transactions = {}

    # Group the data by ticker (each group is one stock)
    tickers = all_data['ticker'].unique()
    
    for ticker in tickers:
        print(f"\nProcessing ticker: {ticker}")
        df_ticker = all_data[all_data['ticker'] == ticker].copy()
        
        # Run the trading simulation for this ticker
        sim_df, transactions, ann_return, sharpe = simulate_trading_for_ticker(df_ticker, initial_investment)
        
        # Plot historical close_price with buy/sell signals
        plt.figure(figsize=(12,6))
        plt.plot(sim_df.index, sim_df['close_price'], label='Close Price', alpha=0.7)
        buy_signals = sim_df[sim_df['buy_signal'] == 1]
        sell_signals = sim_df[sim_df['sell_signal'] == -1]
        plt.scatter(buy_signals.index, buy_signals['close_price'], marker='^', color='green', label='Buy Signal', s=100)
        plt.scatter(sell_signals.index, sell_signals['close_price'], marker='v', color='red', label='Sell Signal', s=100)
        plt.title(f"{ticker} - Buy and Sell Signals")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.legend()
        plt.grid(True)
        plt.show()

        # Print transaction log and performance metrics for this ticker
        print(f"Transaction Log for {ticker}:\n{transactions}")
        final_value = sim_df['portfolio_value'].iloc[-1]
        print(f"Final Portfolio Value for {ticker}: ${final_value:.2f}")
        print(f"Annualized Return for {ticker}: {ann_return:.2%}")
        print(f"Sharpe Ratio for {ticker}: {sharpe:.2f}")
        
        portfolios[ticker] = final_value
        annual_returns[ticker] = ann_return
        sharpe_ratios[ticker] = sharpe
        overall_transactions[ticker] = transactions

        # --- Prediction using ARIMA ---
        forecast_steps = 5  # number of days to forecast
        forecast_mean, conf_int = forecast_arima(sim_df, forecast_steps=forecast_steps)
        if forecast_mean is not None:
            plt.figure(figsize=(12,6))
            plt.plot(sim_df.index, sim_df['close_price'], label='Historical Close Price')
            plt.plot(forecast_mean.index, forecast_mean, label='Forecast', color='orange', marker='o')
            plt.fill_between(forecast_mean.index,
                             conf_int.iloc[:, 0],
                             conf_int.iloc[:, 1],
                             color='grey', alpha=0.3, label='95% Confidence Interval')
            plt.title(f"{ticker} ARIMA Forecast (Next {forecast_steps} Days)")
            plt.xlabel("Date")
            plt.ylabel("Price")
            plt.legend()
            plt.grid(True)
            plt.show()
        else:
            print(f"Forecasting failed for ticker {ticker}.")

    # Overall summary
    print("\n--- OVERALL SUMMARY ---")
    print("Final Portfolio Values:")
    print(portfolios)
    print("\nAnnualized Returns:")
    print(annual_returns)
    print("\nSharpe Ratios:")
    print(sharpe_ratios)
