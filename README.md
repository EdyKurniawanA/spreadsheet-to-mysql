# EYSA Language Center Data Pipeline

A comprehensive data synchronization system that integrates Google Sheets data with MySQL database for managing student leads, closing records, and competitor pricing intelligence.

## Project Overview

This project automates the flow of lead management and student enrollment data from Google Sheets to a MySQL database. It includes fuzzy matching capabilities to track lead-to-student conversions and web scraping for competitor price monitoring.

**Current Status:** Production-ready (as of March 2026)

---

## File Structure & Descriptions

### Core Scripts (Primary Data Pipeline)

#### **`pull_data.py`** (PRIMARY SCRIPT)

- **Purpose:** Main orchestrator for all data synchronization
- **Function:**
  - Fetches leads, closing students, and hot history from Google Sheets
  - Merges lead data with follow-up history (First_fu, Second_fu, Third_fu, Fourth_fu)
  - Deduplicates records by phone number
  - Syncs three MySQL tables: `leads_tracking`, `closing_students`, `main_data`
- **Execution:** Run this script weekly or as per your schedule
- **Output:** Updates three MySQL tables directly
- **Dependencies:** `key.json`, MySQL database, gspread, pandas

```bash
python pull_data.py
```

---

### Data Mapping Scripts

#### **`mapping_data.py`**

- **Purpose:** Maps closing students back to their original leads using fuzzy matching
- **Function:**
  - Reads `leads_tracking.csv` and `closing_students.csv`
  - Performs fuzzy name matching (60% similarity threshold)
  - Extracts source and lead ID for each student
- **Execution:** Run after closing students are enrolled
- **Output:** `mapping_leads_closing.csv` (links closing students to their source leads)
- **Use Case:** Track which lead source converted to paying students

```bash
python mapping_data.py
```

---

### Monitoring & Intelligence Scripts

#### **`competitor_scraping.py`**

- **Purpose:** Monitor competitor pricing for market intelligence
- **Function:**
  - Scrapes English Academy website pricing
  - Stores prices in MySQL `competitor_prices` table
  - Helps track competitive positioning
- **Current Status:** Functional but requires Windows Task Scheduler for automation
- **Dependencies:** requests, BeautifulSoup4, mysql.connector

```bash
python competitor_scraping.py
```

---

### Deprecated/Legacy Scripts

These files are no longer actively used. They've been superseded by `pull_data.py`:

- **`gspread_api.py`** - Old Google Sheets integration (merged into pull_data.py)
- **`sync_database.py`** - CSV-based sync (replaced by pull_data.py)
- **`eysa_api_pull_data.py`** - Incomplete draft with syntax errors

---

## Data Flow Diagram

```
┌─────────────────────────────────────────┐
│ Google Sheets                           │
│ "DATABASE_EYSA Language Center Data"   │
├─────────────────────────────────────────┤
│ Sheet 1: Leads                          │
│ Sheet 2: Closing Students               │
│ Sheet 3: Hot History (Follow-ups)       │
└──────────────────┬──────────────────────┘
                   │
                   │ Requires: key.json
                   ↓
         ┌─────────────────────┐
         │   pull_data.py      │
         │   (Orchestrator)    │
         └──────────┬──────────┘
                    │
        ┌───────────┼───────────┐
        ↓           ↓           ↓
    ┌────────┐ ┌────────┐ ┌────────┐
    │ Leads  │ │Closing │ │Master  │
    │Tracking│ │Students│ │  Data  │
    └────────┘ └────────┘ └────────┘
        ↓           ↓           ↓
    MySQL Database (eysa_database)

    Additional Pipeline:
    ┌──────────────────┐      ┌──────────────────┐
    │ leads_tracking   │      │ closing_students │
    │    (CSV)         │──→   │    (CSV)         │
    └──────────────────┘      └──────────────────┘
            │
            └─→ mapping_data.py
                     │
                     ↓
            ┌──────────────────────────┐
            │ mapping_leads_closing.csv │
            │  (Lead → Student Mapping) │
            └──────────────────────────┘
```

---

## Database Structure

### MySQL Database: `eysa_database`

#### **Table: `leads_tracking`**

Stores lead pipeline data with follow-up history

- Columns: Date, Source, Subdistrict, Status, Name, Phone_Number, Social_Media, Notes
- Follow-up tracking: First_fu, Second_fu, Third_fu, Fourth_fu (TINYINT 0/1)
- Placement Test fields: Placement_Test_Status, Placement_Test_Date, Next_Follow_up_Date

#### **Table: `closing_students`**

Enrolled student records

- Columns: Date, Name, Age, Phone_Number, Gender, Channel_Info, Subdistrict, Occupation
- Program info: Institution, Batch, Programs, Level
- Payment tracking: Fee, Payment_Status, Payment_Type, DP, Installment, Paid_off

#### **Table: `main_data`**

Master deduplicated dataset (combination of leads + closing)

- Columns: Name, Age, Phone_Number, Subdistrict, Occupation, Source
- Purpose: Single source of truth for all contacts (leads + students)

#### **Table: `competitor_prices`** (Optional)

Competitor pricing intelligence

- Columns: competitor_name, program_name, price, original_string

---

## Setup & Configuration

### Prerequisites

```
Python 3.8+
MySQL Server (localhost)
Google Sheets API Access
```

### Required Python Packages

```bash
pip install gspread oauth2client pandas mysql-connector-python
pip install requests beautifulsoup4  # For competitor scraping
```

### Configuration Files

#### **`key.json`**

- **Purpose:** Google Sheets API authentication
- **Obtain:**
  1. Create a Google Cloud project
  2. Enable Google Sheets API
  3. Create a Service Account
  4. Download credentials as JSON
  5. Place in project root directory

#### **Database Credentials**

Located in each script:

```python
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "edykurniawan1054",
    "database": "eysa_database"
}
```

**Security Note:** Consider using environment variables for production

#### **Google Spreadsheet**

- Named: `"DATABASE_EYSA Language Center Data"`
- Worksheet indices:
  - Index 1: Leads
  - Index 2: Closing Students
  - Index 3: Hot History (Follow-ups)

---

## Data Processing Logic

### Leads Processing (`pull_data.py`)

1. **Fetch** leads from Google Sheets (Sheet 1)
2. **Merge** with hot history (Sheet 3) by Name
3. **Convert** follow-up flags (TRUE/FALSE → 1/0)
4. **Format** dates and phone numbers
5. **Sync** to `leads_tracking` table

### Closing Students Processing

1. **Fetch** closing records from Google Sheets (Sheet 2)
2. **Format** numeric fields (Fee, DP, Installment, Paid_off)
3. **Format** date fields
4. **Sync** to `closing_students` table

### Master Data Generation

1. **Extract** key columns from leads (Name, Phone_Number, Source, etc.)
2. **Extract** key columns from closing (Age, Occupation, etc.)
3. **Combine** both datasets
4. **Deduplicate** by normalized phone number (remove non-digits)
5. **Filter** empty names
6. **Sync** to `main_data` table

### Lead-to-Student Mapping (`mapping_data.py`)

1. **Load** leads and closing CSV files
2. **Normalize** names (lowercase, strip whitespace)
3. **Fuzzy Match** each closing student to a lead (60% similarity minimum)
4. **Extract** source and lead ID
5. **Export** mapping to CSV for verification

---

## Usage Guide

### Standard Workflow

#### 1. Run Main Data Sync

```bash
python pull_data.py
```

**Output:** Updates MySQL tables, prints status messages

#### 2. Generate Lead-to-Student Mapping (Weekly)

```bash
python mapping_data.py
```

**Output:** `mapping_leads_closing.csv` for analysis

#### 3. Track Competitor Pricing (Manual or Scheduled)

```bash
python competitor_scraping.py
```

**Output:** Updates `competitor_prices` table

### Scheduling with Windows Task Scheduler

For **`pull_data.py`** (Daily 10 AM):

1. Task Scheduler → Create Basic Task
2. Name: "EYSA Data Sync"
3. Trigger: Daily, 10:00 AM
4. Action: Run program
   - Program: `C:\Users\TUFGAMINGF15\AppData\Local\Programs\Python\Python310\python.exe`
   - Arguments: `"c:\Users\TUFGAMINGF15\Documents\EYSA Data Project\pull_data.py"`
   - Start in: `c:\Users\TUFGAMINGF15\Documents\EYSA Data Project`

---

## CSV Data Files

### Input Files

- **`leads_tracking - leads_tracking.csv`** - Backup of leads from Google Sheets
- **`closing_students - closing_students.csv`** - Backup of closing students

### Output Files

- **`main_data - main_data.csv`** - Deduplicated master dataset
- **`mapping_leads_closing.csv`** - Lead ID mapping to closing students

**Note:** These CSVs are generated/used by the scripts. Keep them for backups but primary data lives in MySQL.

---

## Troubleshooting

### Issue: "Unable to locate key.json"

**Solution:** Ensure `key.json` is in the project root directory

### Issue: "MySQL connection refused"

**Solution:**

- Verify MySQL is running
- Check credentials in db_config
- Ensure `eysa_database` exists

### Issue: "Spreadsheet not found"

**Solution:**

- Confirm spreadsheet name is exactly `"DATABASE_EYSA Language Center Data"`
- Verify service account has access to the spreadsheet
- Check worksheet indices (1=Leads, 2=Closing, 3=Hot History)

### Issue: "KeyError" on column names

**Solution:**

- Column names in code must match Google Sheets exactly
- Check for hidden spaces in headers (scripts handle this with `.str.strip()`)

### Issue: Phone number deduplication not working

**Solution:**

- Ensure phone numbers are consistent format
- Script removes all non-digits: `555-1234` and `5551234` both become `5551234`
- Empty/missing phone numbers fall back to Social_Media for dedup

---

## Data Sync Frequency Recommendations

| Script                   | Frequency | Time           |
| ------------------------ | --------- | -------------- |
| `pull_data.py`           | Daily     | 10:00 AM       |
| `mapping_data.py`        | Weekly    | Friday 5:00 PM |
| `competitor_scraping.py` | Weekly    | Monday 8:00 AM |

---

## Maintenance Checklist

- [ ] Verify Google Sheets connections monthly
- [ ] Check database disk space quarterly
- [ ] Review deduplication logic for accuracy
- [ ] Monitor task scheduler logs for failures
- [ ] Backup `eysa_database` weekly
- [ ] Update credentials before they expire
- [ ] Review competitor pricing trends monthly

---

## Space Optimization

The following files can be safely deleted to free up space:

- `gspread_api.py` - Legacy (100 KB)
- `sync_database.py` - Legacy (2 KB)
- `eysa_api_pull_data.py` - Incomplete (8 KB)
- CSV backup files (if database is backup-safe)

**Estimated savings:** ~110 KB

---

## Quick Reference

```python
# Main sync
python pull_data.py

# Lead-student mapping
python mapping_data.py

# Competitor monitoring
python competitor_scraping.py
```

---

## Project Contact

Developed for EYSA Language Center Data Management
Last Updated: March 1, 2026
