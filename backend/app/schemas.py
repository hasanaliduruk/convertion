from pydantic import BaseModel
from typing import List, Dict

class RestockSettings(BaseModel):
    # Column Aliases
    column_mappings: Dict[str, List[str]] = {
        'upc': ['UPC', 'upc', 'Upc', 'UPC #'],
        'brand': ['BRAND', 'Brand', 'brand'],
        'price': ['NET_AMOUNT', 'Price', 'price'],
        'case': ['CASEPACK', 'Size', 'Case', 'case', 'size'],
        'quantity': ['Qty on Hand', 'Quantity Available', 'Quantity'],
        'pk': ['PK', 'pk', 'PK ']
    }
    
    # Cost Multipliers (Supplier -> Cost)
    supplier_costs: Dict[str, float] = {
        "41 cost": 0.78, "41 standart": 0.78,
        "45 cost": 0.78, "45 standart": 0.78,
        "19 cost": 0.78, "19 standart": 0.78,
        "27 cost": 1.10, "27 standart": 1.10,
        "18 cost": 1.10, "18 standart": 1.10,
        "01 cost": 1.10, "01 standart": 1.10,
        "NF": 0.78
    }