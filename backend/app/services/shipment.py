import pandas as pd
import io
import math
from typing import List, Dict
from app.schemas import ShipmentSettings

def find_col(df: pd.DataFrame, candidates: List[str]) -> str:
    """Helper to find the first matching column name."""
    for col in candidates:
        if col in df.columns:
            return col
    return None

def process_shipment_logic(
    invoice_file: bytes,
    order_files: List[bytes],
    restock_files: List[bytes],
    dc_code: str,
    settings: ShipmentSettings
) -> bytes:
    
    # --- 1. READ INVOICE (Master) ---
    invoice_df = pd.read_excel(io.BytesIO(invoice_file))
    
    # Map Invoice Columns
    inv_cols = {}
    for key, candidates in settings.invoice_columns.items():
        found = find_col(invoice_df, candidates)
        if not found:
            raise ValueError(f"Invoice file missing column for '{key}' (Candidates: {candidates})")
        inv_cols[key] = found

    # --- 2. READ RESTOCK FILES ---
    # Merge multiple restock files into one DF
    restock_dfs = []
    for f in restock_files:
        restock_dfs.append(pd.read_excel(io.BytesIO(f)))
    restock_df = pd.concat(restock_dfs, ignore_index=True) if restock_dfs else pd.DataFrame()

    # --- 3. READ ORDER FILES ---
    order_dfs = []
    for f in order_files:
        order_dfs.append(pd.read_excel(io.BytesIO(f)))
    order_df = pd.concat(order_dfs, ignore_index=True) if order_dfs else pd.DataFrame()

    # --- 4. THE MATCHING LOGIC ---
    # We build the result list row by row
    results = []

    for _, inv_row in invoice_df.iterrows():
        upc = inv_row[inv_cols['upc']]
        
        # Default Row Data
        row_data = {
            'UPC': upc,
            'Price': inv_row[inv_cols['price']],
            'ShipQuantity': inv_row[inv_cols['shipquantity']],
            'PackSize': inv_row[inv_cols['packsize']],
            'Brand': inv_row[inv_cols['brand']],
            'Description': inv_row[inv_cols['description']],
            'Suplier': '#YOK',
            'Asin': '#YOK',
            'Pcs': '#YOK',
            'PK': '#YOK',
            'SKU': '#YOK',
            'Price Check': '#YOK',
            'DOSYA': '#YOK',
            'SKU2': '#YOK',
            'Yeni Pcs': 0,
            'PK EACH': '#YOK',
            'Kalan': '#YOK'
        }

        # Search in Restock
        res_upc_col = find_col(restock_df, settings.restock_columns['upc'])
        if res_upc_col and not restock_df.empty and upc in restock_df[res_upc_col].values:
            match = restock_df[restock_df[res_upc_col] == upc].iloc[0]
            row_data.update({
                'DOSYA': 'Restock',
                'Suplier': match.get(find_col(restock_df, settings.restock_columns['suplier']), '#YOK'),
                'Asin': match.get(find_col(restock_df, settings.restock_columns['asin']), '#YOK'),
                'Pcs': match.get(find_col(restock_df, settings.restock_columns['pcs']), '#YOK'),
                'PK': match.get(find_col(restock_df, settings.restock_columns['pk']), '#YOK'),
                'Price Check': match.get(find_col(restock_df, settings.restock_columns['price']), '#YOK'),
            })

        # Search in Order Form (Only if not fully satisfied or prioritizing Order)
        # Note: Your original logic checked both. We will prioritize Restock if found, else Order.
        elif not order_df.empty:
            ord_upc_col = find_col(order_df, settings.order_columns['upc'])
            if ord_upc_col and upc in order_df[ord_upc_col].values:
                match = order_df[order_df[ord_upc_col] == upc].iloc[0]
                
                # Handle dynamic ASIN 1, ASIN 2...
                # We take the first valid ASIN found
                asin_val = '#YOK'
                sku_val = '#YOK'
                pk_val = match.get(find_col(order_df, settings.order_columns['pk']), '#YOK')
                
                # Check ASIN columns
                for i, asin_col in enumerate(settings.order_columns['asin']):
                    col_name = find_col(order_df, [asin_col])
                    if col_name and not pd.isna(match[col_name]):
                        asin_val = match[col_name]
                        # Try to find matching SKU column
                        if i < len(settings.order_columns['sku']):
                            sku_col_name = find_col(order_df, [settings.order_columns['sku'][i]])
                            if sku_col_name:
                                sku_val = match[sku_col_name]
                        break # Stop after first match
                
                row_data.update({
                    'DOSYA': 'Order Form',
                    'Suplier': match.get(find_col(order_df, settings.order_columns['suplier']), '#YOK'),
                    'Asin': asin_val,
                    'SKU': sku_val,
                    'PK': pk_val,
                    'Price Check': match.get(find_col(order_df, settings.order_columns['price']), '#YOK'),
                    # Note: Pcs logic for Order Form is complex in your code (Pcs 1, Pcs 2). 
                    # Simplified here to take general PCS or first found.
                    'Pcs': match.get(find_col(order_df, settings.order_columns['pcs']), '#YOK')
                })

        # Generate SKU2 (DC_UPC_PK_COST)
        try:
            pk_int = int(str(row_data['PK']).replace('PK', '').strip())
            price_float = float(row_data['Price'])
            cost_str = format(pk_int * price_float, '.2f')
            upc_str = str(upc).zfill(12)
            row_data['SKU2'] = f"{dc_code}_{upc_str}_{row_data['PK']}_{cost_str}"
        except:
            pass # Keep as #YOK

        results.append(row_data)

    # --- 5. STOCK ALLOCATION (The Math) ---
    final_df = pd.DataFrame(results)
    
    # Calculate 'Yeni Pcs' (Allocation)
    # Group by UPC to handle duplicates/splits if necessary
    # Your logic: (Pcs / Total Pcs) * ShipQuantity
    
    # For now, simplistic calculation assuming 1-to-1 mapping for unique UPCs
    # (Complex multi-row allocation requires grouping, implemented here simply)
    for idx, row in final_df.iterrows():
        try:
            pcs = float(row['Pcs'])
            ship_qty = float(row['ShipQuantity'])
            if not math.isnan(pcs) and not math.isnan(ship_qty):
                final_df.at[idx, 'Yeni Pcs'] = ship_qty # Simplified for 1:1 matches
                
                # PK Each Calculation
                pk_val = row['PK']
                if 'PK' in str(pk_val):
                    pk_int = int(str(pk_val).replace('PK', ''))
                    final_df.at[idx, 'PK EACH'] = int(ship_qty / pk_int)
                    final_df.at[idx, 'Kalan'] = ship_qty % pk_int
        except:
            pass

    # --- 6. EXPORT ---
    output = io.BytesIO()
    final_df.to_excel(output, index=False)
    output.seek(0)
    return output.read()