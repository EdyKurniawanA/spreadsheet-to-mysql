import requests
from bs4 import BeautifulSoup
import mysql.connector
import time

# --- 1. CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'edykurniawan1054', 
    'database': 'eysa_database'
}

def check_price():
    url = 'https://www.english-academy.id/explorer'
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"} # Your existing headers
    
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.content, "html.parser")
    
    # Use class_ instead of id
    title_el = soup.find(class_="price-setara")
    price_el = soup.find(class_="price-tiering")
    
    if title_el and price_el:
        title = title_el.get_text().strip()
        raw_price = price_el.get_text().strip()
        
        # Only keep digits to remove Rp, dots, and "/bulan"
        clean_price = "".join(filter(str.isdigit, raw_price))
        
        print(f"Scraped {title}: {clean_price}")
        # Call your database save function here
    else:
        print("Error: Could not find elements. Check if the class names changed.")

def save_to_db(program, price, raw_string):
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = """
            INSERT INTO competitor_prices 
            (competitor_name, program_name, price, original_string) 
            VALUES (%s, %s, %s, %s)
        """
        data = ("English Academy", program, price, raw_string)
        
        cursor.execute(query, data)
        conn.commit()
        
        print(f"Success: Saved {program} price ({price}) to database.")
        
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- 5. EXECUTION ---
if __name__ == "__main__":
    print("Process started...")
    # For testing, we run it once. 
    # For automation, use Windows Task Scheduler instead of a while loop.
    check_price()
    print("Process finished.")