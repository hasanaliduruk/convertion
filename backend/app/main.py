import json
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from typing import List, Dict
from app.schemas import RestockSettings, ShipmentSettings
from app.services.restock import process_restock_logic
from app.services.shipment import process_shipment_logic

app = FastAPI()

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_log(self, client_id: str, message: str, percent: int):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json({
                    "message": message,
                    "percent": percent
                })
            except:
                pass # Connection might be closed

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            await websocket.receive_text() # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# --- ROUTES ---

@app.post("/api/restock")
async def run_restock(
    ham_files: List[UploadFile] = File(...),
    export_files: List[UploadFile] = File(...),
    restock_file: UploadFile = File(...),
    settings_str: str = Form(...),
    client_id: str = Form(...)  # <--- NEW: Client ID to know who to notify
):
    try:
        settings_dict = json.loads(settings_str)
        settings = RestockSettings(**settings_dict)
        
        # 1. Read Files (We announce this)
        await manager.send_log(client_id, "🚀 Upload complete. Reading files into memory...", 5)
        
        ham_contents = [await f.read() for f in ham_files]
        ham_names = [f.filename for f in ham_files]
        
        export_contents = [await f.read() for f in export_files]
        export_names = [f.filename for f in export_files]
        
        restock_content = await restock_file.read()

        # 2. Define a callback wrapper to bridge Sync -> Async
        def progress_callback(msg, pct):
            # We run the async send in the main event loop
            asyncio.run_coroutine_threadsafe(
                manager.send_log(client_id, msg, pct), 
                asyncio.get_running_loop()
            )

        # 3. Run Logic (Modified to accept callback)
        result_excel = await asyncio.to_thread(
            process_restock_logic,
            ham_contents, ham_names,
            export_contents, export_names,
            restock_content,
            settings,
            progress_callback # Pass the reporter
        )

        await manager.send_log(client_id, "✅ Process Complete! Downloading...", 100)

        return Response(
            content=result_excel,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=processed_restock.xlsx"}
        )

    except Exception as e:
        await manager.send_log(client_id, f"❌ Error: {str(e)}", 0)
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shipment")
async def run_shipment(
    invoice_file: UploadFile = File(...),
    restock_files: List[UploadFile] = File(...),
    order_files: List[UploadFile] = File(...),
    dc_code: str = Form(...),
    settings_str: str = Form(...),
    client_id: str = Form(...) # <--- NEW
):
    try:
        settings_dict = json.loads(settings_str)
        settings = ShipmentSettings(**settings_dict)
        
        await manager.send_log(client_id, "🚀 Upload complete. Reading files...", 5)

        invoice_content = await invoice_file.read()
        restock_contents = [await f.read() for f in restock_files]
        order_contents = [await f.read() for f in order_files]

        def progress_callback(msg, pct):
            asyncio.run_coroutine_threadsafe(
                manager.send_log(client_id, msg, pct), 
                asyncio.get_running_loop()
            )

        result_excel = await asyncio.to_thread(
            process_shipment_logic,
            invoice_content, 
            order_contents, 
            restock_contents, 
            dc_code, 
            settings,
            progress_callback
        )
        
        await manager.send_log(client_id, "✅ Generation Complete!", 100)

        return Response(
            content=result_excel,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Shipment_Result.xlsx"}
        )
    except Exception as e:
        await manager.send_log(client_id, f"❌ Error: {str(e)}", 0)
        raise HTTPException(status_code=500, detail=str(e))