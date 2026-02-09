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

    # --- 2. READ & MERGE FILES ---
    restock_dfs = [pd.read_excel(io.BytesIO(f)) for f in restock_files]
    restock_df = pd.concat(restock_dfs, ignore_index=True) if restock_dfs else pd.DataFrame()

    order_dfs = [pd.read_excel(io.BytesIO(f)) for f in order_files]
    order_df = pd.concat(order_dfs, ignore_index=True) if order_dfs else pd.DataFrame()

    # [CRITICAL RESTORATION] Calculate 'Total PCS' for Ratio Math
    # We need to know the total PCS for each UPC across ALL order files to calculate the ratio
    total_pcs_map = {}
    if not order_df.empty:
        ord_upc = find_col(order_df, settings.order_columns['upc'])
        ord_pcs = find_col(order_df, settings.order_columns['pcs'])
        if ord_upc and ord_pcs:
            # Group by UPC and sum the PCS
            total_pcs_map = order_df.groupby(ord_upc)[ord_pcs].sum().to_dict()

    # --- 3. THE MATCHING LOGIC ---
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
            'Pcs': 0,     # Changed default to 0 for math
            'PK': '#YOK',
            'SKU': '#YOK',
            'Price Check': '#YOK',
            'DOSYA': '#YOK',
            'SKU2': '#YOK',
            'Yeni Pcs': '#YOK',
            'PK EACH': '#YOK',
            'Kalan': '#YOK'
        }

        found_match = False

        # A. Search in Restock
        res_upc_col = find_col(restock_df, settings.restock_columns['upc'])
        if res_upc_col and not restock_df.empty and upc in restock_df[res_upc_col].values:
            match = restock_df[restock_df[res_upc_col] == upc].iloc[0]
            row_data.update({
                'DOSYA': 'Restock',
                'Suplier': match.get(find_col(restock_df, settings.restock_columns['suplier']), '#YOK'),
                'Asin': match.get(find_col(restock_df, settings.restock_columns['asin']), '#YOK'),
                'Pcs': match.get(find_col(restock_df, settings.restock_columns['pcs']), 0),
                'PK': match.get(find_col(restock_df, settings.restock_columns['pk']), '#YOK'),
                'Price Check': match.get(find_col(restock_df, settings.restock_columns['price']), '#YOK'),
            })
            found_match = True

        # B. Search in Order Form (If not found in Restock)
        elif not order_df.empty:
            ord_upc_col = find_col(order_df, settings.order_columns['upc'])
            if ord_upc_col and upc in order_df[ord_upc_col].values:
                match = order_df[order_df[ord_upc_col] == upc].iloc[0]
                
                # ASIN Priority Loop
                asin_val = '#YOK'
                sku_val = '#YOK'
                
                for i, asin_col in enumerate(settings.order_columns['asin']):
                    col_name = find_col(order_df, [asin_col])
                    if col_name and not pd.isna(match[col_name]):
                        asin_val = match[col_name]
                        # Try to find matching SKU
                        if i < len(settings.order_columns['sku']):
                            sku_col_name = find_col(order_df, [settings.order_columns['sku'][i]])
                            if sku_col_name:
                                sku_val = match[sku_col_name]
                        break 
                
                row_data.update({
                    'DOSYA': 'Order Form',
                    'Suplier': match.get(find_col(order_df, settings.order_columns['suplier']), '#YOK'),
                    'Asin': asin_val,
                    'SKU': sku_val,
                    'PK': match.get(find_col(order_df, settings.order_columns['pk']), '#YOK'),
                    'Price Check': match.get(find_col(order_df, settings.order_columns['price']), '#YOK'),
                    'Pcs': match.get(find_col(order_df, settings.order_columns['pcs']), 0)
                })
                found_match = True

        # --- 4. CALCULATIONS (Restored Logic) ---
        
        # SKU2 Generation (DC_UPC_PK_COST)
        if str(row_data['PK']) != '#YOK' and str(row_data['Price']) != '#YOK':
            try:
                pk_clean = int(str(row_data['PK']).upper().replace('PK', '').strip())
                price_clean = float(row_data['Price'])
                cost_calc = pk_clean * price_clean
                
                # Format: 12-digit UPC, 2-decimal Cost
                upc_str = str(upc).strip().zfill(12)
                cost_str = "{:.2f}".format(cost_calc)
                
                row_data['SKU2'] = f"{dc_code}_{upc_str}_{row_data['PK']}_{cost_str}"
            except:
                pass

        # Yeni Pcs (The Ratio Calculation)
        try:
            pcs_val = float(row_data['Pcs'])
            ship_qty = float(row_data['ShipQuantity'])
            
            # If we found it in Order Files, use the Ratio: (Row Pcs / Total Pcs for this UPC)
            if row_data['DOSYA'] == 'Order Form' and upc in total_pcs_map:
                total_pcs = float(total_pcs_map[upc])
                if total_pcs > 0:
                    # The Magic Formula from your old app
                    yeni_pcs = (pcs_val / total_pcs) * ship_qty
                    row_data['Yeni Pcs'] = math.floor(yeni_pcs) # Usually floored or rounded
                else:
                    row_data['Yeni Pcs'] = ship_qty
            else:
                # If Restock or no match, just take full quantity
                row_data['Yeni Pcs'] = ship_qty

            # PK EACH & Remainder
            if str(row_data['PK']) != '#YOK':
                 pk_int = int(str(row_data['PK']).upper().replace('PK', '').strip())
                 if pk_int > 0:
                     final_qty = row_data['Yeni Pcs']
                     row_data['PK EACH'] = int(final_qty / pk_int)
                     row_data['Kalan'] = final_qty % pk_int

        except Exception as e:
            pass 

        results.append(row_data)

    # --- 5. EXPORT ---
    final_df = pd.DataFrame(results)
    output = io.BytesIO()
    final_df.to_excel(output, index=False)
    output.seek(0)
    return output.read()