import pandas as pd
import io
import numpy as np
from typing import List, Dict, Tuple
from app.schemas import RestockSettings

DEFAULT_COST = 0.78

# --- HELPER FUNCTIONS ---

def find_column(df: pd.DataFrame, possible_names: List[str]) -> str:
    """Finds a column in the dataframe matching a list of possible names."""
    # 1. Exact match
    for col in df.columns:
        if str(col).strip() in possible_names:
            return col
    
    # 2. Case-insensitive / Space-removed match
    normalized_possibilities = [p.replace(" ", "").lower() for p in possible_names]
    for col in df.columns:
        clean_col = str(col).replace(" ", "").lower()
        if clean_col in normalized_possibilities:
            return col
            
    # If we get here, column is missing. We return None (caller handles error)
    return None

def get_file_code(filename: str) -> str:
    """Extracts the code (e.g., '41') from a filename like '41-Ham.xlsx'"""
    return filename.split('-')[0]

# --- MAIN LOGIC ---

def process_restock_logic(
    ham_files: List[bytes], 
    ham_filenames: List[str],
    export_files: List[bytes], 
    export_filenames: List[str],
    restock_file: bytes,
    settings: RestockSettings
) -> bytes:
    
    # 1. LOAD DATAFRAMES
    ham_dfs = {}
    for content, name in zip(ham_files, ham_filenames):
        ham_dfs[name] = pd.read_excel(io.BytesIO(content))

    export_dfs = {}
    for content, name in zip(export_files, export_filenames):
        export_dfs[name] = pd.read_excel(io.BytesIO(content))

    restock_df = pd.read_excel(io.BytesIO(restock_file))

    # 2. STEP: EXPORT PROCESSING (Merging Qty from Export to Ham)
    # This replaces your 'export' function
    processed_ham_dfs = {} 
    
    for ham_name, ham_df in ham_dfs.items():
        ham_code = get_file_code(ham_name)
        
        # Find matching export file
        matching_export_name = next((name for name in export_filenames if get_file_code(name) == ham_code), None)
        
        if not matching_export_name:
            print(f"Warning: No matching export file for {ham_name}")
            processed_ham_dfs[ham_name] = ham_df # Keep original if no match
            continue

        export_df = export_dfs[matching_export_name]

        # Identify Columns
        h_upc_col = find_column(ham_df, settings.column_mappings['upc'])
        e_upc_col = find_column(export_df, settings.column_mappings['upc'])
        e_qty_col = find_column(export_df, settings.column_mappings['quantity'])

        if not (h_upc_col and e_upc_col and e_qty_col):
            raise ValueError(f"Missing required columns in {ham_name} or {matching_export_name}")

        # Filter: Keep Ham rows only if UPC exists in Export
        export_upcs = set(export_df[e_upc_col].astype(str).str.strip().tolist())
        
        # Ensure Ham UPCs are strings for comparison
        ham_df[h_upc_col] = ham_df[h_upc_col].astype(str).str.strip()
        ham_df = ham_df[ham_df[h_upc_col].isin(export_upcs)]

        # Map Quantities
        # Create a lookup dictionary from Export: UPC -> Quantity
        qty_map = dict(zip(export_df[e_upc_col].astype(str).str.strip(), export_df[e_qty_col]))
        
        ham_df['Qty on Hand'] = ham_df[h_upc_col].map(qty_map).fillna(0)
        
        processed_ham_dfs[ham_name] = ham_df

    # 3. STEP: PRICE WAR (Birbirinden Dusme)
    # Compare suppliers. If '41' is cheaper than '45', remove item from '45'.
    
    # We create a "Blocklist" dictionary: {filename: [list of UPCs to remove]}
    upcs_to_remove = {name: set() for name in processed_ham_dfs.keys()}
    file_list = list(processed_ham_dfs.keys())

    for i in range(len(file_list)):
        current_name = file_list[i]
        current_df = processed_ham_dfs[current_name]
        c_upc_col = find_column(current_df, settings.column_mappings['upc'])
        c_price_col = find_column(current_df, settings.column_mappings['price'])

        # Create lookup: UPC -> Price
        current_prices = dict(zip(current_df[c_upc_col], current_df[c_price_col]))

        for j in range(i + 1, len(file_list)):
            next_name = file_list[j]
            next_df = processed_ham_dfs[next_name]
            n_upc_col = find_column(next_df, settings.column_mappings['upc'])
            n_price_col = find_column(next_df, settings.column_mappings['price'])
            
            next_prices = dict(zip(next_df[n_upc_col], next_df[n_price_col]))

            # Compare overlapping UPCs
            common_upcs = set(current_prices.keys()) & set(next_prices.keys())
            
            for upc in common_upcs:
                try:
                    p1 = float(current_prices[upc])
                    p2 = float(next_prices[upc])
                    
                    if p1 < p2:
                        upcs_to_remove[next_name].add(upc) # Current is cheaper, remove Next
                    elif p1 > p2:
                        upcs_to_remove[current_name].add(upc) # Next is cheaper, remove Current
                    else:
                        # Equal price? Logic says remove Next (arbitrary preference)
                        upcs_to_remove[next_name].add(upc)
                except ValueError:
                    continue # Skip non-numeric prices

    # Apply removals
    final_dfs = {}
    for name, df in processed_ham_dfs.items():
        upc_col = find_column(df, settings.column_mappings['upc'])
        to_drop = upcs_to_remove[name]
        final_dfs[name] = df[~df[upc_col].isin(to_drop)]


    # 4. STEP: RESTOCK (Master Merge)
    
    m_upc_col = find_column(restock_df, settings.column_mappings['upc'])
    m_pk_col = find_column(restock_df, settings.column_mappings['pk'])
    
    if not m_upc_col:
        raise ValueError("Restock Master file missing UPC column")

    # Initialize new columns
    restock_df['Brand'] = "#YOK"
    restock_df['Price'] = "#YOK"
    restock_df['Maliyet'] = "#YOK"
    restock_df['Case'] = "#YOK"
    restock_df['Qty on Hand'] = "#YOK"
    restock_df['Supplier'] = "#YOK"

    # We iterate through the Master UPCs (This mimics your loop structure)
    # Note: For very large files (100k+ rows), we would use 'pd.merge', 
    # but to preserve your logic perfectly, we will use a loop-like application.
    
    # 1. Build a massive lookup dictionary from ALL supplier files
    # Structure: { UPC : { 'price': X, 'qty': Y, 'supplier': Z, 'case': A, 'brand': B } }
    master_lookup = {}

    for name, df in final_dfs.items():
        supplier_code = get_file_code(name)
        
        upc_c = find_column(df, settings.column_mappings['upc'])
        price_c = find_column(df, settings.column_mappings['price'])
        case_c = find_column(df, settings.column_mappings['case'])
        # Qty on Hand was standardized in Step 2
        
        # Convert to dicts
        for idx, row in df.iterrows():
            upc = str(row[upc_c]).strip()
            
            price = row[price_c]
            qty = row['Qty on Hand']
            case = row[case_c] if case_c else "#YOK"
            
            # Logic: If this UPC is already in lookup, only overwrite if logic demands
            # (But we already handled "Lowest Price" in Step 3, so we can just add)
            master_lookup[upc] = {
                'price': price,
                'qty': qty,
                'case': case,
                'supplier': supplier_code,
                'filename': name # Needed for maliyet calculation key
            }

    # 2. Apply lookup to Restock DF
    def update_row(row):
        upc = str(row[m_upc_col]).strip()
        
        if upc in master_lookup:
            data = master_lookup[upc]
            
            # Basic info
            row['Price'] = data['price']
            row['Qty on Hand'] = data['qty']
            row['Case'] = data['case']
            row['Supplier'] = data['supplier']
            
            # Maliyet Calculation
            pk_val = row[m_pk_col]
            try:
                # Clean PK (remove 'PK', convert to int)
                pk_clean = int(str(pk_val).upper().replace('PK', '').strip())
                price_float = float(data['price'])
                
                # Find supplier multiplier (e.g., '41 cost')
                # Try to find a key in MALIYET_SETTINGS that matches the supplier
                maliyet_add = DEFAULT_COST
                for key, val in settings.supplier_costs.items():
                    if data['supplier'] in key:
                        maliyet_add = val
                        break
                
                row['Maliyet'] = (pk_clean * price_float) + maliyet_add
                
            except:
                row['Maliyet'] = data['price'] # Fallback
                
        return row

    restock_df = restock_df.apply(update_row, axis=1)

    # 5. REMOVE FAILED ROWS (Where Price is still #YOK)
    restock_df = restock_df[restock_df['Price'] != "#YOK"]

    # 6. OUTPUT TO BYTES
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        restock_df.to_excel(writer, sheet_name='Restock Final', index=False)
        
        # Optional: Save the "Ham" sheets too if you want debugging
        # for name, df in final_dfs.items():
        #     df.to_excel(writer, sheet_name=name[:30], index=False)

    output.seek(0)
    return output.read()