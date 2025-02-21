import mysql.connector
import os
import re
from PyPDF2 import PdfReader
import pdfplumber
import csv
import numpy as np

def read_pdf(pdf_path,filename):
    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        print(f"Number of pages: {num_pages}")

        for i, page in enumerate(pdf.pages, start=0):
            page_text = page.extract_text()
            if not page_text:
                page_text = "Text could not be extracted by pdfplumber"

            text = f"--- Page {i} ---\n{page_text}\n\n"
            read_text_extracted_from_PDF_page(i, text,filename)

    return "PDF processing completed."

def read_text_extracted_from_PDF_page(page_no,text,filename):
    def get_api():
        api_id_pattern = (
            r"(?:\b\d{2}-\d{3}-\d{5}\b)|(?:\b\d{2} - \d{3} - \d{5}\b)|(?:^API(?:\s)?#:(?:\s)?\d{10}$)|(?:API(?:\s+)?\d{10})"
        )

        api_id = set(re.findall(api_id_pattern, text))
        api_id = [re.sub(r"[^\d-]", "", id) for id in api_id]

        api_id_final_pattern = r"(\d{2})(\d{3})(\d{5})"
        for i in range(len(api_id)):
            # Find all matches of the pattern in the string
            if len(api_id[i]) != 12:
                match = re.search(api_id_final_pattern, api_id[i])
                if match:
                    # Format the match into 'XX-XXX-XXXXX' format
                    api_id[i] = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        return api_id

    extracted_data = {}  # Dictionary to store results
    processed_keys = set()  # Set to track extracted keys
    # print(f"API : {get_api()}") if get_api() else None
    patterns = {
        "operator": r"Well Operator : (.*?)\n",
        "well_name": r"Well Name\s*:\s*(.*)\n",
        "enseco_job": r"\bJob (\d+)\b",
        "job_type": r"Type of Incident : (.*?)\n",
        "county": r"County : (.*?)\n",
        "latitude": r'(\d+°\d+\'\d+\.\d+\"[NS])',
        "longitude": r'(\d+°\d+\'\d+\.\d+\"[EW])',
        "datum": r"Vertical Datum to DDZ\s+([\d.]+ ft)",
        "date_simulated": r"Date Stimulated\s*\n\s*(\d{1,2}/\d{1,2}/\d{4})",
        "formation": r"Stimulated Formation\s*\n\s*([^\n]+)",
        "top_bottom_stimulation_stages": r"Top \(Ft\)\s*Bottom \(Ft\)\s*Stimulation Stages\n\s*(\d+)\s+(\d+)\s+(\d+)",
        "psi": r"Maximum Treatment Pressure \(PSI\)\s*\n\s*(\d+)",
        "lbs": r"Lbs Proppant\s*\n\s*(\d+)",
        "type_treatment": r"Type Treatment\s*\n\s*([^\n]+)",
        "volume": r"Volume Units\s*\n(\d+)\s*(\w+)",
        "max_treatment_rate": r"Maximum Treatment Rate \(BBLS/Min\)\s*\n\s*(\d+(?:\.\d+)?)"
    }

    for field, regex in patterns.items():
        found_match = re.search(regex, text)
        if found_match:
            extracted_data[field] = found_match.group(1)
            processed_keys.add(field)  # Track processed fields
        else:
            extracted_data[field]= np.nan

    output_csv = "extracted_data.csv"
    with open(output_csv, mode="a", newline="", encoding="utf-8") as file:
        field_names = ["pdf_name", "page_no"] + list(extracted_data.keys()) + ["API"]
        writer = csv.DictWriter(file, fieldnames=field_names)

        # Write the header only if the file is empty
        if file.tell() == 0:
            writer.writeheader()

        writer.writerow({
            "pdf_name": filename,
            "page_no": page_no,
            **extracted_data,
            "API": get_api()
        })

    # print(f"Extracted data saved to {output_csv}")

    return extracted_data

def Extract_data_from_pdfs():
    output_csv = "extracted_data.csv"

    # Check if the file exists and delete it
    if os.path.exists(output_csv):
        os.remove(output_csv)
        print(f"{output_csv} has been deleted.")
    else:
        print(f"{output_csv} does not exist.")

    directory = "DSCI560_Lab5"  # Change this to your target directory
    count = 0
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        if os.path.isfile(file_path):  # Ensure it's a file
            count += 1
            print(f"\n\n file name {file_path} \n")
            read_pdf(file_path, filename)

    print("Count of pdf files", count)
    return None


def csv_to_sql():

    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': 'Password@123',
        # 'database': 'OilWellAnalysis'
    }

    # Connect to MySQL server (without specifying a database)
    connection = mysql.connector.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"]
    )
    cursor = connection.cursor()

    # Create Database
    cursor.execute("CREATE DATABASE IF NOT EXISTS Lab6_database")
    print("Database 'Lab6_database' created or already exists.")

    # Connect to the newly created database
    connection.database = "Lab6_database"

    # Create Table 'oilwell_data'
    create_table_query = """
    CREATE TABLE IF NOT EXISTS oilwell_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pdf_path VARCHAR(255),
        page_no INT,
        operator VARCHAR(255),
        well_name VARCHAR(255),
        enseco_job VARCHAR(50),
        job_type VARCHAR(100),
        county VARCHAR(100),
        latitude VARCHAR(50),
        longitude VARCHAR(50),
        datum VARCHAR(50),
        date_simulated DATE,
        formation VARCHAR(255),
        top_ft INT,
        bottom_ft INT,
        stimulation_stages INT,
        psi INT,
        lbs_proppant INT,
        type_treatment VARCHAR(255),
        volume FLOAT,
        volume_units VARCHAR(50),
        max_treatment_rate FLOAT,
        api VARCHAR(500)
    );
    """

    cursor.execute(create_table_query)
    print("Table 'oilwell_data' created or already exists.")

    csv_file = "extracted_data.csv"

    # Insert CSV Data into MySQL
    if os.path.exists(csv_file):
        with open(csv_file, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            headers = next(reader)  # Read column names

            # Ensure CSV headers match the MySQL table
            expected_columns = [
                "pdf_path", "page_no", "operator", "well_name", "enseco_job",
                "job_type", "county", "latitude", "longitude", "datum",
                "date_simulated", "formation", "top_ft", "bottom_ft",
                "stimulation_stages", "psi", "lbs_proppant", "type_treatment",
                "volume", "volume_units", "max_treatment_rate", "api"
            ]

            if headers != expected_columns:
                print(" CSV column names do not match table structure. Please check the headers.")
            else:
                # Prepare SQL Insert Statement
                placeholders = ", ".join(["%s"] * len(headers))
                sql_query = f"INSERT INTO oilwell_data ({', '.join(headers)}) VALUES ({placeholders})"

                for row in reader:
                    cursor.execute(sql_query, row)

                connection.commit()
                print(f" Data from '{csv_file}' successfully inserted into 'oilwell_data'.")
    else:
        print(f" CSV file '{csv_file}' not found. Please ensure it exists.")

    # Close Database Connection
    cursor.close()
    connection.close()
    print("MySQL Connection Closed.")

    return None


Extract_data_from_pdfs()









# db_config = {
#     'host': 'localhost',
#     'user': 'root',
#     'password': 'Password@123',
#     'database': 'OilWellAnalysis'
# }
#
#
# # Function to create the database and tables
# def create_database_and_tables():
#     try:
#         conn = mysql.connector.connect(
#             host=db_config['host'],
#             user=db_config['user'],
#             password=db_config['password']
#         )
#         cursor = conn.cursor()
#         cursor.execute("CREATE DATABASE IF NOT EXISTS OilWellAnalysis")
#         conn.database = db_config['database']
#         cursor.execute("DROP TABLE IF EXISTS oilwelldata")
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS stocks (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 ticker VARCHAR(10),
#                 name VARCHAR(100),
#                 date VARCHAR(100),
#                 sector VARCHAR(100),
#                 market_cap BIGINT,
#                 open_price DECIMAL(10, 4),
#                 high_price DECIMAL(10, 4),
#                 low_price DECIMAL(15, 4),
#                 close_price DECIMAL(15, 4),
#                 volume BIGINT
#             )
#         """)
#         print("Database and table created successfully.")
#     except mysql.connector.Error as err:
#         print(f"Error: {err}")
#     finally:
#         cursor.close()
#         conn.close()