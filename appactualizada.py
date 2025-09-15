import io
import re
from datetime import datetime
import urllib.parse

import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

# --- Configuración de la app ---
st.set_page_config(page_title="Generador de Etiquetas PDF con QR", page_icon="🧾", layout="wide")
st.title("🧾 Generador de etiquetas PDF con QR")
st.write("Crea un PDF con etiquetas consecutivas. Usa `{SERIAL}` donde quieras que aparezca el serial consecutivo.")

# --- Sidebar / Parámetros ---
with st.sidebar:
    st.header("⚙️ Parámetros")
    serial_inicio = st.text_input("Serial inicial (ej. MG-0001)", value="MG-0001")
    n = st.number_input("Cantidad de seriales diferentes", min_value=1, value=5, step=1)
    serial_repeticiones = st.number_input("Repetir cada serial cuántas veces", min_value=1, value=1, step=1)

    page_label = st.selectbox("Tamaño de página", ["Letter (8.5×11 in)", "A4"])
    page_size = letter if page_label.startswith("Letter") else A4

    etiqueta_width_mm = st.number_input("Ancho etiqueta (mm)", min_value=10.0, value=70.0, step=1.0)
    etiqueta_height_mm = st.number_input("Alto etiqueta (mm)", min_value=10.0, value=50.0, step=1.0)

    margen_x_mm = st.number_input("Margen horizontal entre etiquetas (mm)", min_value=0.0, value=10.0, step=1.0)
    margen_y_mm = st.number_input("Margen vertical entre etiquetas (mm)", min_value=0.0, value=10.0, step=1.0)

    padding_interno_mm = st.number_input("Padding interno (mm)", min_value=0.0, value=5.0, step=1.0)

    font_size = st.number_input("Tamaño de fuente (pt)", min_value=4, value=6, step=1)
    line_spacing = st.number_input("Espaciado entre líneas (pt)", min_value=6, value=8, step=1)

    usar_qr = st.checkbox("Incluir código QR", value=True)
    qr_size_mm = st.number_input("Tamaño del QR (mm)", min_value=0.0, value=30.0, step=1.0, disabled=not usar_qr)

# Texto por defecto de la etiqueta
default_text = (
    "IMPORTADOR: LIVIDNEM S.A.S.\n"
    "NIT: 901.789.453-8\n"
    "COD.SIC: {COD_SIC}\n"
    "REFERENCIA: {REFERENCIA}\n"
    "MARCA: SAN JOSE\n"
    "SERIAL: {SERIAL}\n"
    "PAIS ORIGEN CHINA"
)

st.subheader("📝 Líneas de texto de la etiqueta")
st.caption("Usa `{SERIAL}`, `{REFERENCIA}`, `{COD_SIC}` en cualquier línea para insertar info dinámica.")
textos_usuario = st.text_area("Contenido", default_text, height=220)
lineas = [ln for ln in textos_usuario.splitlines() if ln.strip() != ""]

# --- Función para generar PDF ---
def generar_etiquetas_pdf(
    serial_inicio, n, serial_repeticiones, page_size,
    etiqueta_w_mm, etiqueta_h_mm, margen_x_mm, margen_y_mm,
    lineas, font_size, line_spacing, padding_interno_mm,
    incluir_qr, qr_size_mm
):
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
    if match:
        letras = match.group(1) if match.group(1) else ''
        numero = int(match.group(2)) if match.group(2) else None
        num_digits = len(match.group(2)) if match.group(2) else 0
    else:
        letras = serial_inicio
        numero = None
        num_digits = 0

    x = margen_x
    y = height - etiqueta_h - margen_y

    # Ejemplo: generar info de referencia y cod_sic automáticamente (puedes ajustar)
    for i in range(n):
        serial_actual = f"{letras}{str(numero + i).zfill(num_digits)}" if numero is not None else serial_inicio
        referencia = f"MG-{320+i}"  # Ejemplo automático
        cod_sic = f"90178945{3+i}"   # Ejemplo automático

        for _ in range(serial_repeticiones):
            # Borde
            c.rect(x, y, etiqueta_w, etiqueta_h)
            # Texto
            c.setFont("Helvetica", int(font_size))
            offset = 10
            for t in (ln.replace("{SERIAL}", serial_actual).replace("{REFERENCIA}", referencia).replace("{COD_SIC}", cod_sic) for ln in lineas):
                c.drawString(x + padding_interno, y + etiqueta_h - offset, t)
                offset += int(line_spacing)
            # QR
            if incluir_qr and qr_size > 0:
                url = f"https://bright-starlight-4b0351.netlify.app/?serial={urllib.parse.quote(serial_actual)}&referencia={urllib.parse.quote(referencia)}&cod_sic={urllib.parse.quote(cod_sic)}"
                qr_code = qr.QrCodeWidget(url)
                bounds = qr_code.getBounds()
                qr_w = bounds[2] - bounds[0]
                qr_h = bounds[3] - bounds[1]
                d = Drawing(qr_size, qr_size, transform=[qr_size/qr_w,0,0,qr_size/qr_h,0,0])
                d.add(qr_code)
                renderPDF.draw(d, c, x + etiqueta_w - qr_size - padding_interno, y + padding_interno)

            # Posición siguiente
            x += etiqueta_w + margen_x
            if x + etiqueta_w > width - 1:
                x = margen_x
                y -= etiqueta_h + margen_y
                if y < margen_y:
                    c.showPage()
                    x = margen_x
                    y = height - etiqueta_h - margen_y

    c.save()
    buffer.seek(0)
    return buffer

width_px, height_px = page_size
cols = max(1, int((width_px - margen_x_mm * mm) // (etiqueta_width_mm * mm + margen_x_mm * mm)))
rows = max(1, int((height_px - margen_y_mm * mm) // (etiqueta_height_mm * mm + margen_y_mm * mm)))
por_pagina = cols * rows
st.info(f"Est. por página: **{por_pagina}** etiquetas (≈ {cols} columnas × {rows} filas)")

# --- Botón para generar ---
col_a, col_b = st.columns([1, 2])
with col_a:
    generar = st.button("Generar PDF")

if generar:
    pdf_bytes = generar_etiquetas_pdf(
        serial_inicio=serial_inicio,
        n=n,
        serial_repeticiones=serial_repeticiones,
        page_size=page_size,
        etiqueta_w_mm=etiqueta_width_mm,
        etiqueta_h_mm=etiqueta_height_mm,
        margen_x_mm=margen_x_mm,
        margen_y_mm=margen_y_mm,
        lineas=lineas,
        font_size=font_size,
        line_spacing=line_spacing,
        padding_interno_mm=padding_interno_mm,
        incluir_qr=usar_qr,
        qr_size_mm=qr_size_mm,
    )
    st.success("PDF generado correctamente.")
    st.download_button(
        label="⬇️ Descargar PDF",
        data=pdf_bytes,
        file_name=f"etiquetas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
    )

st.caption("Imprime al 100% de escala para respetar las medidas.")

