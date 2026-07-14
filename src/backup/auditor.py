import streamlit as st


def comprobar_columnas(df):

    st.subheader("🛠 Modo depuración")

    st.write("Columnas detectadas:")

    for columna in df.columns:

        st.write(f"➡️ {repr(columna)}")

    return []