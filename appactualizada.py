import io
import re
from datetime import datetime

import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

st.set_page_config(page_title="Generador de Etiquetas PDF con QR", page_icon="🧾", layout="wide")
st.title("🧾 Generador de etiquetas PDF con QR")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Parámetros")
    serial_inicio = st.text_input("Serial inicial (ej. MG-0001)", value="MG-0001")
    n = st.number_input("Cantidad de seriales", min_value=1, value=5, step=1)  # por defecto pocos para probar
    serial_repeticiones = st.number_input("Repetir cada serial", min_value=1, value=1, step=1)

    page_label = st.selectbox("Tamaño de página", ["Letter (8.5×11 in)", "A4"])
    page_size = letter if page_label.startswith("Letter") else A4

    etiqueta_width_mm = st.number_input("Ancho etiqueta (mm)", min_value=10.0, value=70.0, step=1.0)
    etiqueta_height_mm = st.number_input("Alto etiqueta (mm)", min_value=10.0, value=50.0, step=1.0)
    margen_x_mm = st.number_input("Margen horizontal (mm)", min_value=0.0, value=10.0, step=1.0)
    margen_y_mm = st.number_input("Margen vertical (mm)", min_value=0.0, value=10.0, step=1.0)
    padding_interno_mm = st.number_input("Padding interno (mm)", min_value=0.0, value=5.0, step=1.0)
    font_size = st.number_input("Tamaño fuente (pt)", min_value=4, value=6, step=1)
    line_spacing = st.number_input("Espaciado líneas (pt)", min_value=6, value=8, step=1)
    usar_qr = st.checkbox("Incluir QR", value=True)
    qr_size_mm = st.number_input("Tamaño QR (mm)", min_value=0.0, value=30.0, step=1.0, disabled=not usar_qr)

# Texto base de la etiqueta
default_text = (
    "IMPORTADOR: LIVIDNEM S.A.S.\n"
    "NIT: 901.789.453-8\n"
    "COD.SIC:{COD_SIC}\n"
    "REFERENCIA:{REFERENCIA}\n"
    "MARCA: SAN JOSE\n"
    "SERIAL: {SERIAL}\n"
    "PAIS ORIGEN CHINA"
)
st.subheader("📝 Contenido de la etiqueta")
textos_usuario = st.text_area("Contenido (usa {SERIAL}, {REFERENCIA}, {COD_SIC})", default_text, height=220)
lineas = [ln for ln in textos_usuario.splitlines() if ln.strip() != ""]

# --- Función PDF ---
def generar_etiquetas_pdf(serial_inicio, n, serial_repeticiones, page_size,
                          etiqueta_w_mm, etiqueta_h_mm, margen_x_mm, margen_y_mm,
                          lineas, font_size, line_spacing, padding_interno_mm,
                          incluir_qr, qr_size_mm):
    etiqueta_w = etiqueta_w_mm * mm
    etiqueta_h = etiqueta_h_mm * mm
    margen_x = margen_x_mm * mm
    margen_y = margen_y_mm * mm
    padding_interno = padding_interno_mm * mm
    qr_size = qr_size_mm * mm

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    match = re.match(r'(.+?)(\d+)?$', serial_inicio)
    letras = match.group(1) if match else serial_inicio
    numero = int(match.group(2)) if match and match.group(2) else None
    num_digits = len(match.group(2)) if match and match.group(2) else 0

    x_start = margen_x
    y_start = height - etiqueta_h - margen_y
    x = x_start
    y = y_start

    for i in range(n):
        serial_actual = f"{letras}{str(numero + i).zfill(num_digits)}" if numero is not None else serial_inicio
        referencia = f"MG-{320+i}"
        cod_sic = f"901789{453+i}"

        for _ in range(serial_repeticiones):
            c.rect(x, y, etiqueta_w, etiqueta_h)
            c.setFont("Helvetica", int(font_size))
            offset = 10
            for t in lineas:
                t_reemplazado = t.replace("{SERIAL}", serial_actual)\
                                 .replace("{REFERENCIA}", referencia)\
                                 .replace("{COD_SIC}", cod_sic)
                c.drawString(x + padding_interno, y + etiqueta_h - offset, t_reemplazado)
                offset += int(line_spacing)

            if incluir_qr and qr_size > 0:
                link = f"https://miweb.com/etiqueta?serial={serial_actual}&referencia={referencia}&cod_sic={cod_sic}"
                qr_code = qr.QrCodeWidget(link)
                bounds = qr_code.getBounds()
                qr_w = bounds[2] - bounds[0]
                qr_h = bounds[3] - bounds[1]
                d = Drawing(qr_size, qr_size, transform=[qr_size/qr_w,0,0,qr_size/qr_h,0,0])
                d.add(qr_code)
                renderPDF.draw(d, c, x + etiqueta_w - qr_size - padding_interno, y + padding_interno)

            x += etiqueta_w + margen_x
            if x + etiqueta_w > width - 1:
                x = x_start
                y -= etiqueta_h + margen_y
                if y < margen_y:
                    c.showPage()
                    x = x_start
                    y = y_start

    c.save()
    buffer.seek(0)
    return buffer

# --- Estimación ---
width_px, height_px = page_size
cols = max(1, int((width_px - margen_x_mm * mm) // (etiqueta_width_mm * mm + margen_x_mm * mm)))
rows = max(1, int((height_px - margen_y_mm * mm) // (etiqueta_height_mm * mm + margen_y_mm * mm)))
por_pagina = cols * rows
st.info(f"≈ {por_pagina} etiquetas por página ({cols}x{rows})")

# --- Botón generar PDF ---
if st.button("Generar PDF"):
    pdf_bytes = generar_etiquetas_pdf(
        serial_inicio, n, serial_repeticiones, page_size,
        etiqueta_width_mm, etiqueta_height_mm, margen_x_mm, margen_y_mm,
        lineas, font_size, line_spacing, padding_interno_mm,
        usar_qr, qr_size_mm
    )
    st.success("PDF generado correctamente.")
    st.download_button(
        label="⬇️ Descargar PDF",
        data=pdf_bytes,
        file_name=f"etiquetas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf"
    )
