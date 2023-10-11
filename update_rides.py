import csv
import os
import requests
from bs4 import BeautifulSoup
import shutil


# Function to read column names from existing CSV file
def read_existing_columns(filepath):
    try:
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            return next(reader)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None

# Function to fetch HTML from a URL
def fetch_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"An error occurred while fetching HTML: {e}")
        return None

# Function to parse HTML and generate CSV data
def parse_html_to_csv(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find(id="powerClassTable")

        rows = table.find_all('tr')
        headers = [header.text for header in rows[0].find_all('th')]
        
        data = []
        for row in rows[1:]:
            data.append([cell.text for cell in row.find_all('td')])
        
        return headers, data
    except Exception as e:
        print(f"An error occurred while parsing HTML: {e}")
        return None, None

# Function to compare columns and print warnings
def compare_columns(existing_columns, new_columns):
    for column in existing_columns:
        if column not in new_columns:
            print(f"Warning: Column {column} does not exist in the new HTML.")

# Main function
def main():
    # Step 1
    print("Reading existing columns...")
    existing_columns = read_existing_columns('./powerzone.csv')
    
    # Step 2
    print("Fetching HTML...")
    html = fetch_html("https://app.homefitnessbuddy.com/peloton/powerzone/")
    if html is None:
        print("Exiting due to error in fetching HTML.")
        return

    # Step 3 and Step 4
    print("Parsing HTML...")
    new_columns, data = parse_html_to_csv(html)
    if new_columns is None or data is None:
        print("Exiting due to error in parsing HTML.")
        return

    # Step 5
    if existing_columns:
        print("Comparing columns...")
        compare_columns(existing_columns, new_columns)

    # Step 6
# Copy existing CSV to backup
    shutil.copy('./powerzone.csv', './powerzone.bk.csv')
    print("Writing to CSV...")
    try:
        with open('./powerzone.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(new_columns)
            writer.writerows(data)
    except Exception as e:
        print(f"An error occurred while writing to CSV: {e}")

if __name__ == "__main__":
    main()
