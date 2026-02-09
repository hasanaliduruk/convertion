from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import Response
from typing import List
from app.services.restock import process_restock_logic
import json
from app.schemas import RestockSettings, ShipmentSettings
from app.services.shipment import process_shipment_logic

app = FastAPI()

@app.post("/api/restock")
async def run_restock(
    ham_files: List[UploadFile] = File(...),
    export_files: List[UploadFile] = File(...),
    restock_file: UploadFile = File(...),
    settings_str: str = Form(...)
):
    # 1. Parse the JSON string into our Pydantic model
    try:
        settings_dict = json.loads(settings_str)
        settings = RestockSettings(**settings_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid settings format: {e}")
    try:
        # 1. Read all files into memory
        ham_contents = [await f.read() for f in ham_files]
        ham_names = [f.filename for f in ham_files]
        
        export_contents = [await f.read() for f in export_files]
        export_names = [f.filename for f in export_files]
        
        restock_content = await restock_file.read()

        # 2. Run the logic
        result_excel = process_restock_logic(
            ham_contents, ham_names,
            export_contents, export_names,
            restock_content,
            settings
        )

        # 3. Return the file
        return Response(
            content=result_excel,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=processed_restock.xlsx"}
        )

    except Exception as e:
        # In production, log the error properly
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/shipment")
async def run_shipment(
    invoice_file: UploadFile = File(...),
    restock_files: List[UploadFile] = File(...),
    order_files: List[UploadFile] = File(...),
    dc_code: str = Form(...),
    settings_str: str = Form(...)
):
    try:
        settings_dict = json.loads(settings_str)
        settings = ShipmentSettings(**settings_dict)
        
        invoice_content = await invoice_file.read()
        restock_contents = [await f.read() for f in restock_files]
        order_contents = [await f.read() for f in order_files]

        result_excel = process_shipment_logic(
            invoice_content, 
            order_contents, 
            restock_contents, 
            dc_code, 
            settings
        )

        return Response(
            content=result_excel,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Shipment_Result.xlsx"}
        )
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))