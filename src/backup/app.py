import streamlit as st

from lector_excel import leer_excel
from auditor import comprobar_columnas

# =====================================================
# CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="SIVAA",
    page_icon="🎓",
    layout="wide"
)

# =====================================================
# CABECERA
# =====================================================

st.title("🎓 SIVAA")

st.subheader(
    "Sistema Inteligente de Validación de Actas Académicas"
)

st.caption(
    "Prototipo de auditor inteligente para la validación automática de actas académicas."
)

st.divider()

# =====================================================
# BASE ACADÉMICA
# =====================================================

st.success("📚 Base Académica ESIC cargada correctamente")

st.caption("Curso académico: 2026-2027")

st.divider()

# =====================================================
# CARGA DEL ACTA
# =====================================================

st.header("📂 Acta del profesor")

excel_profesor = st.file_uploader(
    "Selecciona el Excel del profesor",
    type=["xlsx"]
)

st.divider()

# =====================================================
# BOTÓN
# =====================================================

if st.button(
    "🚀 VALIDAR ACTA",
    use_container_width=True
):

    # -----------------------------------------

    if excel_profesor is None:

        st.error("⚠️ Debes seleccionar un acta.")

    else:

        st.success("✅ Acta cargada correctamente.")

        # -----------------------------------------
        # Leer Excel
        # -----------------------------------------

        df = leer_excel(excel_profesor)

        # -----------------------------------------
        # Resumen
        # -----------------------------------------

        st.divider()

        st.subheader("📋 Resumen del acta")

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "👨‍🎓 Número de alumnos",
                len(df)
            )

            st.metric(
                "📊 Número de columnas",
                len(df.columns)
            )

        with col2:

            st.metric(
                "📄 Archivo",
                excel_profesor.name
            )

            st.metric(
                "🟢 Estado",
                "Correcto"
            )

        # -----------------------------------------
        # Auditoría
        # -----------------------------------------

        st.divider()

        st.subheader("🔎 Resultado de la auditoría")

        errores = comprobar_columnas(df)

        if len(errores) == 0:

            st.success(
                "✅ Todas las columnas obligatorias existen."
            )

        else:

            st.error(
                "❌ Se han encontrado errores."
            )

            for error in errores:

                st.write("•", error)