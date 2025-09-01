import streamlit as st
import pandas as pd
import numpy as np

def brl(x: float) -> str:
    "Formatar o valor para moeda BR"
    return f"R$ {x:,.2f}".replace(",", ".").replace(".", ",").replace("X", ".")

def show_df_currency(df, money_cols):
    try:
        cfg = {c: st.column_config.NumberColumn(c, format="R$ %.2f") for c in money_cols}
        st.dataframe(df, use_container_width=True, hide_index=True, column_config=cfg)
    except Exception:
        df2 = df.copy()
        for c in money_cols:
            df2[c] = df2[c].map(brl)
        try:
            st.dataframe(df2, use_container_width=True, hide_index=True)
        except TypeError:
            st.dataframe(df2.reset_index(drop=True), use_container_width=True)