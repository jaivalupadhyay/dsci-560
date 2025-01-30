import mysql.connector
import yfinance as yf
from datetime import datetime,date

# Database connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Password@123',
    'database': 'StockData'
}
def create_portfolio_table():
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        conn.database = db_config['database']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("DROP TABLE IF EXISTS portfolio")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                date Date,
                stock_count BIGINT)
        """)
    
    
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()
        
def get_available_stock_data():
    try:
        start_date,end_date=1,1
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("select DISTINCT ticker from stocks") 
        stock_names = [ row[0] for row in cursor.fetchall() ]
        
        cursor.execute("select Min(date) from stocks")
        start_date = cursor.fetchone()
        
        cursor.execute("select Max(date) from stocks")
        end_date = cursor.fetchone()

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()
    
    return stock_names,start_date[0],end_date[0]
    
    
def add_stock(available_stock_names,start_date,end_date,requested_stock,stock_count):
    requested_buy_date = '2025-01-28'#.strftime("%Y-%m-%d")

    
    if requested_stock not in available_stock_names:
        print("request stock not available")
        return 
    
    if requested_buy_date != end_date.strftime("%Y-%m-%d"):
        print("Market is Closed")
        return 
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
                INSERT INTO portfolio (ticker,date,stock_count)
                VALUES (%s, %s, %s )
            """, (
                requested_stock,
                requested_buy_date,
                stock_count
            ))
        conn.commit()

        print(f" {stock_count} {requested_stock} stocks successfully bought.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()
    
    return None
    
def remove_stock(available_stock_names,start_date,end_date,requested_stock,stock_count):
    requested_buy_date = '2025-01-28'#.strftime("%Y-%m-%d")

    
    if requested_stock not in available_stock_names:
        print("request stock not available")
        return 
    
    if requested_buy_date != end_date.strftime("%Y-%m-%d"):
        print("Market is Closed")
        return 
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            select sum(stock_count)
            from portfolio
            where ticker = %s
        """
        ,(requested_stock,))
        
        total_stock = cursor.fetchone()
        if total_stock is None:
            print('You have no stocks to sell of this company')
            return 
        else:
            total_stock = total_stock[0]
            if total_stock < stock_count:
                print("Invalid, Stocks to sell less than total stocks present")
                return   
            #print('total stock = ',total_stock)
        
        
        cursor.execute("""
                INSERT INTO portfolio (ticker,date,stock_count)
                VALUES (%s, %s, %s )
            """, (
                requested_stock,
                requested_buy_date,
                -stock_count
            ))
        conn.commit()

        print(f" {stock_count} {requested_stock} stocks successfully sold.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()
    
    return None
    

def display():
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        query = """ 
        select ticker,sum(stock_count)
        from portfolio
        group by ticker
        
                """
        cursor.execute(query)
        
        data = cursor.fetchall()
        print("Present Portfolio")
        for stock in data:
            print("Stock Name:",stock[0],"Stock Count:",stock[1])
    
        # Buying History
        print("Buying History")
        query = """ 
            select ticker,date,stock_count
            from portfolio
            where stock_count > 0
                """
        cursor.execute(query)
        
        data = cursor.fetchall()
        
        for stock in data:
            print("Date :",stock[1],"Stock Name:",stock[0],"Bought",stock[2])
        
        # Selling History
        print("Buying History")
        query = """ 
            select ticker,date,stock_count
            from portfolio
            where stock_count < 0
                """
        cursor.execute(query)
        
        data = cursor.fetchall()
        
        for stock in data:
            print("Date :",stock[1],"Stock Name:",stock[0],"Sold",-stock[2])
        
        
        
 
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()
    
    return None


# Main execution
#if __name__ == "__main__":
# Main code
create_portfolio_table()
available_stock_names, start_date, end_date = get_available_stock_data()
while True:



    # Input operations
    print("\nChoose an operation:")
    print("1. Add stock")
    print("2. Remove stock")
    print("3. Display portfolio")
    print("4. Exit")
    choice = input("Enter your choice (1/2/3/4): ")

    if choice == '1':  # Add stock
        print("Available stocks:", available_stock_names)
        requested_stock = input("Enter the stock symbol to add: ").upper()
        stock_count = int(input("Enter the number of units to add: "))
        add_stock(available_stock_names, start_date, end_date, requested_stock, stock_count)

    elif choice == '2':  # Remove stock
        requested_stock = input("Enter the stock symbol to remove: ").upper()
        stock_count = int(input("Enter the number of units to remove: "))
        remove_stock(available_stock_names, start_date, end_date, requested_stock, stock_count)

    elif choice == '3':  # Display portfolio
        display()

    elif choice == '4':  # Exit
        print("Exiting program. Goodbye!")
        break

    else:
        print("Invalid choice! Please try again.")

    # create portfolio table
    #create_portfolio_table()
    
    # get data of available stocks
    #available_stock_names,start_date,end_date = get_available_stock_data()
    #print("Available stocks:",available_stock_names)
    # operations
    
    #ADD
    #requested_stock = 'MSFT'
    #stock_count =3
    #add_stock(available_stock_names,start_date,end_date,requested_stock,stock_count)
    
    #Remove
    #requested_stock = 'MSFT'
    stock_count = 1
    #remove_stock(available_stock_names,start_date,end_date,requested_stock,stock_count)
    
    # displaying
    #display()
    
    
    
    
    
    



