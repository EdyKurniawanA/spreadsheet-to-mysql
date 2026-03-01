import gspread
import pandas as pd
import mysql.connector
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONNECTION SETUP ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
client = gspread.authorize(creds)
spreadsheet = client.open("DATABASE_EYSA Language Center Data")

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "edykurniawan1054",
    "database": "eysa_database",
}

# Fetch Raw DataFrames
df_leads = pd.DataFrame(spreadsheet.get_worksheet(1).get_all_records())
df_closing = pd.DataFrame(spreadsheet.get_worksheet(2).get_all_records())
df_hot_history = pd.DataFrame(spreadsheet.get_worksheet(3).get_all_records())

# Clean headers
for df in [df_leads, df_closing, df_hot_history]:
    df.columns = df.columns.str.strip()

# --- 2. PREPARE LEADS + HOT LEADS MERGE ---
fu_cols = ["Name", "Phone_Number", "First_fu", "Second_fu", "Third_fu", "Fourth_fu"]
df_leads_merged = pd.merge(
    df_leads,
    df_hot_history[fu_cols].drop(columns=["Phone_Number"]),
    on="Name",
    how="left",
)

# Convert FUs to 1/0 for MySQL
for col in ["First_fu", "Second_fu", "Third_fu", "Fourth_fu"]:
    df_leads_merged[col] = (
        df_leads_merged[col]
        .map({"TRUE": 1, "FALSE": 0, True: 1, False: 0})
        .fillna(0)
        .astype(int)
    )


# --- 3. MAIN SYNC FUNCTION ---
def push_to_mysql(df, table_name, columns_list):
    try:
        # Date & Numeric Formatting
        for col in ["Placement_Test_Date", "Next_Follow_up_Date", "Date"]:
            if col in df.columns:
                df[col] = (
                    pd.to_datetime(df[col], errors="coerce")
                    .dt.strftime("%Y-%m-%d")
                    .replace({"NaT": None})
                )

        for col in ["Fee", "DP", "Installment", "Paid_off"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r"[^\d.]", "", regex=True)
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df_clean = df.replace({np.nan: None, pd.NA: None, "nan": None, "": None})

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute(f"TRUNCATE TABLE `{table_name}`")

        placeholders = ", ".join(["%s"] * len(columns_list))
        columns_sql = ", ".join([f"`{col}`" for col in columns_list])
        update_sql = ", ".join([f"`{col}` = VALUES(`{col}`)" for col in columns_list])

        query = f"INSERT INTO `{table_name}` ({columns_sql}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_sql}"

        for _, row in df_clean[columns_list].iterrows():
            cursor.execute(query, tuple(row))

        conn.commit()
        print(f"Table '{table_name}' updated successfully.")
    except Exception as e:
        print(f"Error updating {table_name}: {e}")
    finally:
        if "conn" in locals() and conn.is_connected():
            conn.close()


# --- 4. MASTER DATA LOGIC (COMBINING LEADS & CLOSING) ---
print("Generating Master Data (main_data)...")

# Prepare Leads for Master
leads_sub = pd.DataFrame()
leads_sub["Name"] = df_leads["Name"]
leads_sub["Phone_Number"] = df_leads["Phone_Number"]
leads_sub["Source"] = df_leads["Source"]
leads_sub["Subdistrict"] = df_leads["Subdistrict"]
leads_sub["Age"] = None
leads_sub["Occupation"] = None

# Prepare Closing for Master
closing_sub = pd.DataFrame()
closing_sub["Name"] = df_closing["Name"]
closing_sub["Phone_Number"] = df_closing["Phone_Number"]
closing_sub["Source"] = df_closing["Channel_Info"]
closing_sub["Subdistrict"] = df_closing["Subdistrict"]
closing_sub["Age"] = df_closing["Age"]
closing_sub["Occupation"] = df_closing["Occupation"]
closing_sub["Batch"] = df_closing["Batch"]

# Combine & Deduplicate
df_master = pd.concat([leads_sub, closing_sub], ignore_index=True)
df_master["Batch"] = df_master["Batch"].fillna("Leads Tracking")
df_master["Phone_Number"] = (
    df_master["Phone_Number"].astype(str).str.replace(r"\D", "", regex=True)
)
# Deduplikasi berdasarkan kombinasi Nomor HP DAN Batch
df_master = df_master.drop_duplicates(subset=["Phone_Number", "Batch"], keep="last")
df_master = df_master[df_master["Name"].astype(bool)]  # Remove empty names

# --- 5. EXECUTION ---
print("Starting synchronization...")

# Define column sets
leads_cols = [
    "Date",
    "Source",
    "Subdistrict",
    "Status",
    "Name",
    "Phone_Number",
    "Social_Media",
    "Placement_Test_Status",
    "Placement_Test_Date",
    "Next_Follow_up_Date",
    "Notes",
    "First_fu",
    "Second_fu",
    "Third_fu",
    "Fourth_fu",
]

closing_cols = [
    "Date",
    "Name",
    "Age",
    "Phone_Number",
    "Gender",
    "Channel_Info",
    "Subdistrict",
    "Occupation",
    "Institution",
    "Batch",
    "Programs",
    "Level",
    "Fee",
    "Payment_Status",
    "Payment_Type",
    "DP",
    "Installment",
    "Paid_off",
]

master_cols = ["Name", "Age", "Phone_Number", "Subdistrict", "Occupation", "Source"]

# Sync all 3 tables
push_to_mysql(df_leads_merged, "leads_tracking", leads_cols)
push_to_mysql(df_closing, "closing_students", closing_cols)
push_to_mysql(df_master, "main_data", master_cols)

print("Synchronization complete. Master Data is now settled! Hehe.")
