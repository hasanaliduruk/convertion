import pandas as pd
import io
import concurrent.futures
from typing import List, Dict, Tuple
from app.schemas import RestockSettings

# --- HELPER: Read File Function (Must be outside for ProcessPool) ---
def read_excel_bytes(file_data: bytes, filename: str) -> Tuple[str, pd.DataFrame]:
    """
    Reads an Excel file from bytes using the fast 'calamine' engine.
    Returns (filename, DataFrame).
    """
    try:
        # 'calamine' is 5x-10x faster than openpyxl
        df = pd.read_excel(io.BytesIO(file_data), engine="calamine")
        return filename, df
    except Exception:
        # Fallback if calamine fails or isn't installed
        df = pd.read_excel(io.BytesIO(file_data), engine="openpyxl")
        return filename, df

# --- HELPER: Column Finder ---
def find_column(df: pd.DataFrame, possible_names: List[str]) -> str:
    # Check exact match
    columns = list(df.columns)
    for col in columns:
        if str(col).strip() in possible_names:
            return col
            
    # Check normalized
    normalized_possibilities = [p.replace(" ", "").lower() for p in possible_names]
    for col in columns:
        clean_col = str(col).replace(" ", "").lower()
        if clean_col in normalized_possibilities:
            return col
    return None

def get_file_code(filename: str) -> str:
    return filename.split('-')[0]

# --- MAIN LOGIC ---
def process_restock_logic(
    ham_files: List[bytes], 
    ham_filenames: List[str],
    export_files: List[bytes], 
    export_filenames: List[str],
    restock_file: bytes,
    settings: RestockSettings,
    callback=None
) -> bytes:
    def log(msg, pct):
        if callback: callback(msg, pct)
    
    # 1. PARALLEL LOADING (The Speed Fix)
    # We use ProcessPoolExecutor to max out your CPU cores reading files
    log("Started parallel file reading...", 10)
    ham_dfs = {}
    export_dfs = {}

    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Submit all reading jobs at once
        ham_futures = [
            executor.submit(read_excel_bytes, content, name) 
            for content, name in zip(ham_files, ham_filenames)
        ]
        export_futures = [
            executor.submit(read_excel_bytes, content, name) 
            for content, name in zip(export_files, export_filenames)
        ]
        
        # Track progress
        total_files = len(ham_files) + len(export_files)
        completed = 0
        
        # We iterate futures as they complete to update the bar
        for future in concurrent.futures.as_completed(ham_futures):
            name = ham_futures[future]
            try:
                _, df = future.result()
                ham_dfs[name] = df
                completed += 1
                pct = 10 + int((completed / total_files) * 30) # 10% to 40%
                log(f"Loaded {name}", pct)
            except Exception as e:
                log(f"Failed to load {name}: {e}", pct)

        for future in concurrent.futures.as_completed(export_futures):
            name = export_futures[future]
            try:
                _, df = future.result()
                export_dfs[name] = df
                completed += 1
                pct = 10 + int((completed / total_files) * 30)
                log(f"Loaded {name}", pct)
            except Exception as e:
                log(f"Failed to load {name}: {e}", pct)

    # 2. LOGIC: EXPORT PROCESSING
    log("Matching Ham files with Export data...", 45)
    processed_ham_dfs = {} 
    
    # Note: Logic processing is usually fast in memory; reading files was the bottleneck.
    # We keep this part sequential to avoid complex inter-process communication overhead.
    
    for ham_name, ham_df in ham_dfs.items():
        ham_code = get_file_code(ham_name)
        
        # Fuzzy match filename logic
        matching_export_name = next((name for name in export_filenames if get_file_code(name) == ham_code), None)
        
        if not matching_export_name:
            processed_ham_dfs[ham_name] = ham_df
            continue

        export_df = export_dfs[matching_export_name]

        h_upc_col = find_column(ham_df, settings.column_mappings['upc'])
        e_upc_col = find_column(export_df, settings.column_mappings['upc'])
        e_qty_col = find_column(export_df, settings.column_mappings['quantity'])

        if h_upc_col and e_upc_col and e_qty_col:
            # OPTIMIZATION: Vectorized filtering instead of loops
            export_df[e_upc_col] = export_df[e_upc_col].astype(str).str.strip()
            ham_df[h_upc_col] = ham_df[h_upc_col].astype(str).str.strip()
            
            # Filter Ham
            valid_upcs = set(export_df[e_upc_col])
            ham_df = ham_df[ham_df[h_upc_col].isin(valid_upcs)].copy()

            # Map Quantities
            qty_map = dict(zip(export_df[e_upc_col], export_df[e_qty_col]))
            ham_df['Qty on Hand'] = ham_df[h_upc_col].map(qty_map).fillna(0)
        
        processed_ham_dfs[ham_name] = ham_df

    # 3. LOGIC: PRICE WAR (Birbirinden Dusme)
    log("Running Price War (Birbirinden Düşme)...", 70)
    # Using the ORDER defined by the user (the list order of ham_filenames)
    # The file list passed from frontend is ALREADY ordered by the user
    
    # We create a "Blocklist" dictionary: {filename: {set of UPCs}}
    upcs_to_remove = {name: set() for name in processed_ham_dfs.keys()}
    
    # Sort keys based on the input order (Priority)
    ordered_keys = [k for k in ham_filenames if k in processed_ham_dfs]

    for i in range(len(ordered_keys)):
        current_name = ordered_keys[i]
        current_df = processed_ham_dfs[current_name]
        c_upc_col = find_column(current_df, settings.column_mappings['upc'])
        c_price_col = find_column(current_df, settings.column_mappings['price'])
        
        if not c_upc_col or not c_price_col: continue

        current_prices = dict(zip(current_df[c_upc_col], current_df[c_price_col]))

        for j in range(i + 1, len(ordered_keys)):
            next_name = ordered_keys[j]
            next_df = processed_ham_dfs[next_name]
            n_upc_col = find_column(next_df, settings.column_mappings['upc'])
            n_price_col = find_column(next_df, settings.column_mappings['price'])
            
            if not n_upc_col or not n_price_col: continue
            
            next_prices = dict(zip(next_df[n_upc_col], next_df[n_price_col]))

            # Compare Intersecting UPCs
            common = set(current_prices.keys()) & set(next_prices.keys())
            
            for upc in common:
                try:
                    p1 = float(current_prices[upc])
                    p2 = float(next_prices[upc])
                    
                    if p1 < p2:
                        upcs_to_remove[next_name].add(upc) # Keep Current
                    elif p1 > p2:
                        upcs_to_remove[current_name].add(upc) # Keep Next
                    else:
                        # Equal price? Remove Next (because Current is higher priority in list)
                        upcs_to_remove[next_name].add(upc)
                except:
                    pass

    # Apply Removals
    final_dfs = {}
    for name in ordered_keys:
        df = processed_ham_dfs[name]
        col = find_column(df, settings.column_mappings['upc'])
        to_drop = upcs_to_remove[name]
        final_dfs[name] = df[~df[col].isin(to_drop)]

    # 4. LOGIC: MASTER MERGE
    log("Merging final data into Master Excel...", 85)
    m_upc_col = find_column(restock_df, settings.column_mappings['upc'])
    m_pk_col = find_column(restock_df, settings.column_mappings['pk'])
    
    # Build Master Lookup
    master_lookup = {}
    for name, df in final_dfs.items():
        supplier_code = get_file_code(name)
        upc_c = find_column(df, settings.column_mappings['upc'])
        price_c = find_column(df, settings.column_mappings['price'])
        case_c = find_column(df, settings.column_mappings['case'])
        
        # Vectorized dictionary creation is faster than iterrows
        # Create a temp DF with normalized columns
        temp_df = pd.DataFrame({
            'upc': df[upc_c].astype(str).str.strip(),
            'price': df[price_c],
            'case': df[case_c] if case_c else "#YOK",
            'qty': df['Qty on Hand']
        })
        
        # Iterate efficiently
        for row in temp_df.itertuples():
            # If priority order matters, we only add if NOT exists, 
            # BUT Step 3 already handled priority logic (Price War), 
            # so we just aggregate or take first available.
            if row.upc not in master_lookup:
                master_lookup[row.upc] = {
                    'price': row.price,
                    'qty': row.qty,
                    'case': row.case,
                    'supplier': supplier_code
                }

    # Apply to Master
    # Use map/apply optimized
    def get_row_data(upc):
        upc = str(upc).strip()
        return master_lookup.get(upc, None)

    # We extract data into new lists to assign as columns (Faster than apply(axis=1))
    prices, qtys, cases, suppliers, maliyets = [], [], [], [], []
    
    restock_upcs = restock_df[m_upc_col].astype(str).str.strip()
    restock_pks = restock_df[m_pk_col].fillna('0').astype(str)

    for upc, pk_val in zip(restock_upcs, restock_pks):
        data = master_lookup.get(upc)
        if data:
            prices.append(data['price'])
            qtys.append(data['qty'])
            cases.append(data['case'])
            suppliers.append(data['supplier'])
            
            # Maliyet
            try:
                pk_clean = int(pk_val.upper().replace('PK', '').strip())
                m_add = settings.supplier_costs.get(f"{data['supplier']} cost", 
                        settings.supplier_costs.get(f"{data['supplier']} standart", 0.78))
                maliyets.append((pk_clean * float(data['price'])) + m_add)
            except:
                maliyets.append(data['price'])
        else:
            prices.append("#YOK")
            qtys.append("#YOK")
            cases.append("#YOK")
            suppliers.append("#YOK")
            maliyets.append("#YOK")

    restock_df['Price'] = prices
    restock_df['Qty on Hand'] = qtys
    restock_df['Case'] = cases
    restock_df['Supplier'] = suppliers
    restock_df['Maliyet'] = maliyets

    # Filter invalid
    restock_df = restock_df[restock_df['Price'] != "#YOK"]

    # Export
    log("Saving file...", 95)
    output = io.BytesIO()
    restock_df.to_excel(output, index=False, engine='xlsxwriter')
    output.seek(0)
    return output.read()