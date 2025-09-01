import os, zipfile, io, uuid
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
from weasyprint import HTML
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
app = FastAPI(title=os.getenv("APP_NAME"))

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # 0. Leer la hoja completa para capturar la fila 5 (índice 4)
    raw = pd.read_excel(await file.read(), header=None)
    mes_anio = str(raw.iloc[0, 0]).strip() if not pd.isna(raw.iloc[0, 0]) else "facturas"
    # Limpiar caracteres no válidos en nombres de archivo
    mes_anio = "".join(c for c in mes_anio if c.isalnum() or c in (" ", "-", "_")).rstrip()

    # 1. Ahora sí leer con header=6
    await file.seek(0)  # volver al inicio del archivo
    df = pd.read_excel(await file.read(), header=1)
    df.columns = [str(col).strip() for col in df.columns]
    # 1. Leer Excel, saltar 6 filas (header=6) y limpiar nombres

    # print("Columnas detectadas:", df.columns.tolist())


    # 2. Renombrar
    rename_map = {
        "Fact Num": "fact_num",
        "N Factura": "n_factura",
        "Factura a:": "cliente",
        "Dirección": "direccion",
        "Pax": "pax",
        "Check in": "check_in",
        "Check out": "check_out",
        "Cant Noches": "noches",
        "Rate": "tarifa_noche",
        "Sub Total R": "subtotal",
        "Turis Tax 9,5%": "turis_tax",
        "Tax   3 USD (AFL)": "tax_af",
        "Total Cobrado": "total_cobrado",
    }
    df = df.rename(columns=rename_map)

    # 3. Descartar filas sin cliente o sin fecha
    df = df.dropna(subset=["cliente", "check_in", "check_out"])

    # 4. Preparar ZIP en memoria
    mem_zip = io.BytesIO()

    for idx, row in df.iterrows():
        def fmt(dt):
            return pd.to_datetime(dt).strftime("%d-%b") if pd.notna(dt) else ""
        data = {
            **row.to_dict(),
            "fact_num": str(int(row["fact_num"])) if pd.notna(row["fact_num"]) else "",
            "check_in_fmt": fmt(row["check_in"]),
            "check_out_fmt": fmt(row["check_out"]),
            "tarifa_fmt": f"${float(row['tarifa_noche']):,.2f}",
            "subtotal_fmt": f"${float(row['subtotal']):,.2f}",
            "turis_fmt": f"${float(row['turis_tax']):,.2f}",
            "tax_fmt": f"${float(row['tax_af']):,.2f}",
            "total_fmt": f"${float(row['total_cobrado']):,.2f}",
        }

        html = HTML_TEMPLATE.format(**data)
        pdf = HTML(string=html).write_pdf()
        filename = f"factura_{str(row['n_factura']).replace(' ','')}.pdf"
        with zipfile.ZipFile(mem_zip, "a", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, pdf)

    mem_zip.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{mes_anio}.zip"'}
    return Response(content=mem_zip.getvalue(), headers=headers, media_type="application/zip")

# Plantilla HTML/CSS (simplificada del PDF que viste)
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Factura</title>
<style>
 body {{ font-family: Arial; margin: 40px; color: #333; }}
 .header {{ text-align: center; margin-bottom: 30px; }}
 .logo {{ max-height: 80px; }}
 .details {{ margin-bottom: 30px; }}
 table {{ width: 100%; border-collapse: collapse; }}
 th, td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
 .right {{ text-align: right; }}
</style>
</head>
<body>
 <div class="header">
   <img src="logo_placeholder.png" class="logo" alt="Logo">
   <h1>INVOICE</h1>
   <p>YOUR COMPANY<br>
      Praesent Street, West Nulla, Leaflove 11510<br>
      +88 12 345 6789 10088<br>
      put_your_email_address@gmail.com<br>
      www.your_website_link.com</p>
 </div>
 <div class="details">
   <p><strong>Factura a:</strong> {cliente}</p>
    <p><strong>Fact Num:</strong> {fact_num}</p>
   <p><strong>N Factura:</strong> {n_factura}</p>
   <p><strong>Dirección:</strong> {direccion}</p>
 </div>
 <table>
  <tr><th>Pax</th><th>Check-In</th><th>Check-out</th><th>Cant Noches</th><th>Rate</th></tr>
  <tr>
    <td>{pax}</td>
    <td>{check_in_fmt}</td>
    <td>{check_out_fmt}</td>
    <td>{noches}</td>
    <td>{tarifa_fmt}</td>
  </tr>
 </table>
 <div class="right" style="margin-top:20px;">
   <p><strong>Sub Total R:</strong> {subtotal_fmt}</p>
   <p><strong>Turis Tax 9,5%:</strong> {turis_fmt}</p>
   <p><strong>Tax 3 USD (AFL):</strong> {tax_fmt}</p>
   <p><strong>Total Cobrado:</strong> {total_fmt}</p>
 </div>
</body>
</html>
"""