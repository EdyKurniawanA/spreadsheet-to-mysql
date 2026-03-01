import pandas as pd
from difflib import get_close_matches

# 1. Load Data
leads = pd.read_csv('leads_tracking - leads_tracking.csv')
closing = pd.read_csv('closing_students - closing_students.csv')

# 2. Pembersihan Dasar (Lower case & Strip Spasi)
leads['clean_name'] = leads['Name'].str.lower().str.strip()
closing['clean_name'] = closing['Full Name'].str.lower().str.strip()

# Simpan ID asli leads (index) untuk referensi
leads['lead_id_ref'] = leads.index + 1 

# 3. Fungsi Fuzzy Matching
lead_names = leads['clean_name'].dropna().unique().tolist()

def find_best_match(name):
    # Mencari 1 kecocokan terbaik dengan tingkat kemiripan minimal 60%
    match = get_close_matches(name, lead_names, n=1, cutoff=0.6)
    return match[0] if match else None

# 4. Proses Pencocokan
closing['matched_name'] = closing['clean_name'].apply(find_best_match)

# 5. Gabungkan untuk mengambil Info Source dan ID dari Leads
final_mapping = pd.merge(
    closing, 
    leads[['clean_name', 'lead_id_ref', 'Source', 'Phone Number']], 
    left_on='matched_name', 
    right_on='clean_name', 
    how='left'
)

# 6. Export Hasil untuk kamu periksa
final_mapping[['Full Name', 'matched_name', 'lead_id_ref', 'Source']].to_csv('mapping_leads_closing.csv', index=False)

print("Mapping Selesai! File 'mapping_leads_closing.csv' siap diunduh.")