import os
import sys

import streamlit as st

# Asegurar que los módulos del proyecto (app.py, acta.py, etc.) se
# encuentran aunque streamlit se lance desde otra carpeta.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from app import auditar_acta
from config import EXCEL_MAESTRO

ASSETS_DIR = os.path.join(ROOT_DIR, "assets")

RUTA_MAESTRO_DEFECTO = (
    EXCEL_MAESTRO
    if os.path.isabs(EXCEL_MAESTRO)
    else os.path.join(ROOT_DIR, EXCEL_MAESTRO)
)

# =====================================================
# CONFIGURACIÓN DE LA PÁGINA
# =====================================================
st.set_page_config(
    page_title="SIVAA",
    page_icon="🎓",
    layout="wide",
)

# Cargar estilos propios (style.css)
ruta_css = os.path.join(BASE_DIR, "style.css")
if os.path.exists(ruta_css):
    with open(ruta_css, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# =====================================================
# CABECERA CON LOGOS
# =====================================================
col_logo1, col_titulo, col_logo2 = st.columns([1, 4, 1])

with col_logo1:
    ruta_logo_esic = os.path.join(ASSETS_DIR, "logo_esic.png")
    if os.path.exists(ruta_logo_esic):
        st.image(ruta_logo_esic, width=110)

with col_titulo:
    st.markdown(
        """
        <div class="header">
            <h1>🎓 SIVAA</h1>
            <h3>Sistema Inteligente de Validación de Actas Académicas</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_logo2:
    ruta_logo_sivaa = os.path.join(ASSETS_DIR, "logo_sivaa.png")
    if os.path.exists(ruta_logo_sivaa):
        st.image(ruta_logo_sivaa, width=110)

st.divider()

# =====================================================
# CARGA DEL ACTA
# =====================================================
st.header("📂 Acta a auditar")
archivo_acta = st.file_uploader(
    "Selecciona el Excel del acta del profesor",
    type=["xlsx"],
)

with st.expander("⚙️ Excel maestro (opcional — si no subes uno, se usa el del proyecto)"):
    archivo_maestro = st.file_uploader(
        "Excel maestro (.xlsx)",
        type=["xlsx"],
        key="maestro_uploader",
    )
    st.caption(f"Por defecto se usa: `{EXCEL_MAESTRO}`")

st.divider()

# =====================================================
# BOTÓN DE VALIDACIÓN
# =====================================================
if st.button("🚀 VALIDAR ACTA", use_container_width=True):

    if archivo_acta is None:
        st.error("⚠️ Debes seleccionar un acta antes de validar.")
    else:
        maestro_a_usar = (
            archivo_maestro if archivo_maestro is not None else RUTA_MAESTRO_DEFECTO
        )

        try:
            with st.spinner("Auditando acta, un momento..."):
                informe, asignatura, curso, total_alumnos = auditar_acta(
                    archivo_acta, maestro_a_usar
                )

            st.success(f"✅ Auditoría completada: {asignatura}")

            # ---------------- Resumen ----------------
            st.divider()
            st.subheader("📋 Resumen del acta")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📚 Asignatura", asignatura)
            with col2:
                st.metric("🏫 Curso", curso)
            with col3:
                st.metric("👨‍🎓 Nº de alumnos", total_alumnos)

            # ---------------- Informe ----------------
            st.divider()
            st.subheader("🔎 Informe de auditoría")
            st.code(informe, language=None)

            st.download_button(
                "⬇️ Descargar informe (.txt)",
                data=informe,
                file_name=f"informe_{asignatura}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        except (FileNotFoundError, ValueError) as error:
            st.error(f"❌ {error}")
        except Exception as error:
            st.error(f"❌ Ha ocurrido un error inesperado: {error}")
