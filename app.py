# =========================
# Imports
# =========================
import streamlit as st
import pandas as pd
import numpy as np

# =========================
# Configuração da página + Topbar
# =========================
st.set_page_config(page_title="🧮 Calculadora | CIGAM", layout="wide")
st.sidebar.title("Calculadora | CIGAM")

# Barra fixa no topo para as métricas
topbar = st.container()
with topbar:
    col_top_1, col_top_2 = st.columns(2)
    metric_total_top = col_top_1.empty()

# =========================
# Utilitários (formatação)
# =========================
def brl(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_horas(valor: float) -> str:
    horas = int(round(valor))
    return f"{horas}h"

def show_df_currency(
    df: pd.DataFrame,
    money_cols: list[str],
    highlight_col: str | None = None,
    text_color: str = "#22c55e",
    bg_color: str | None = None,
    hours_cols: list[str] = []
):
    df2 = df.copy()
    fmt = {c: lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for c in money_cols}
    styler = df2.style.format(fmt)

    for c in hours_cols:
        df2[c] = df2[c].apply(format_horas)

    if highlight_col and highlight_col in df2.columns:
        props = {}
        if text_color: props["color"] = text_color
        if bg_color:   props["background-color"] = bg_color
        if props:
            styler = styler.set_properties(subset=[highlight_col], **props)

    st.table(styler)

# =========================
# Entradas (sidebar)
# =========================
periodo_total = st.sidebar.slider(
    "Meses totais do projeto (incluindo o 1º)",
    min_value=6, max_value=12, value=6, step=1
)

# Fixos mensais (variáveis)
nuvem = st.sidebar.number_input("Nuvem (R$/mês)", min_value=0.0, value=0.0, step=50.0, format="%.2f")
mensalidade_cigam = st.sidebar.number_input("Mensalidade CIGAM (R$/mês)", min_value=0.0, value=0.0, step=50.0, format="%.2f")

# Mercos com mudança de valor
mensalidade_mercos_inicial = st.sidebar.number_input(
    "Mensalidade Mercos inicial (R$/mês)", min_value=0.0, value=693.0, step=10.0, format="%.2f"
)
mes_inicio_novo_valor = st.sidebar.number_input(
    "Mês da mudança de valor (ex: 5 = a partir do Mês 5)", min_value=1, max_value=periodo_total, value=5, step=1
)
mensalidade_mercos_novo = st.sidebar.number_input(
    "Novo valor Mercos (R$/mês)", min_value=0.0, value=2079.0, step=10.0, format="%.2f"
)

st.sidebar.markdown("---")
st.sidebar.caption("Informe as **horas totais do projeto**.")
horas_totais_projeto = st.sidebar.number_input("Horas totais do projeto", min_value=0.0, value=0.0, step=0.1, format="%.1f")
valor_hora = st.sidebar.number_input("Valor da hora (R$)", min_value=0.0, value=270.0, step=10.0, format="%.2f")

# Componentes únicos informados pelo usuário
st.sidebar.markdown("---")
custo_instal = st.sidebar.number_input("Instalação infra (R$)", min_value=0.0, value=valor_hora * 20, step=20.0, format="%.2f")
custo_map = st.sidebar.number_input("Mapeamento inicial (R$)", min_value=0.0, value=valor_hora * 50, step=50.0, format="%.2f")
homologacao = st.sidebar.number_input("Homologação (R$)", min_value=0.0, value=0.0, step=50.0, format="%.2f")

# =========================
# Regras/Helpers
# =========================
H_PRIMEIRO_MES = 70.0

def perfil_U_automatico(k: int) -> np.ndarray:
    if k <= 0:
        return np.array([])
    if k == 1:
        return np.array([100.0])
    forca = 2
    enfase_inicio = 1.6
    enfase_fim = 2.5
    x = np.linspace(0, 1, k)
    base = (1 - x) ** forca * enfase_inicio + x ** forca * enfase_fim
    p = 100 * base / base.sum()
    return p

def quantize_to_5(pcts_raw: np.ndarray, min_pct: float = 5.0) -> np.ndarray:
    arr = np.maximum(0.0, np.array(pcts_raw, dtype=float))
    k = arr.size
    if k == 0:
        return arr
    units_total = 20
    min_units = int(np.ceil(min_pct / 5.0))
    base_units = np.full(k, min_units, dtype=int)
    remaining_units = units_total - base_units.sum()
    if remaining_units <= 0:
        return base_units.astype(float) * 5.0
    if arr.sum() <= 0:
        ideal = np.full(k, remaining_units / k)
    else:
        ideal = arr / arr.sum() * remaining_units
    add_units = np.floor(ideal).astype(int)
    leftover = remaining_units - add_units.sum()
    fracs = ideal - add_units
    order = np.argsort(-fracs)
    if leftover > 0:
        add_units[order[:leftover]] += 1
    units = base_units + add_units
    return units.astype(float) * 5.0

# =========================
# Cálculos principais
# =========================
total_meses = periodo_total
meses_rotulo = [f"Mês {i}" for i in range(1, total_meses + 1)]

horas_m1 = min(H_PRIMEIRO_MES, horas_totais_projeto)
horas_restantes = max(0.0, horas_totais_projeto - horas_m1)

k = total_meses - 1
pcts_raw = perfil_U_automatico(k)
pcts5 = quantize_to_5(pcts_raw, min_pct=5.0)
soma_pct = float(pcts5.sum())

w = pcts5 / 100.0 if soma_pct > 0 else (np.ones(k) / k if k > 0 else np.array([]))

horas_mes = np.zeros(total_meses, dtype=float)
horas_mes[0] = horas_m1
if k > 0:
    horas_mes[1:] = np.round(horas_restantes * w, 2)

# Consumo do projeto mensal
consumo_projeto_mensal = np.round(horas_mes * valor_hora, 2)
gestao_mes = np.round(0.20 * consumo_projeto_mensal, 2)

# Fixos mensais considerando mudança no Mercos
fixos_mensais_array = np.zeros(total_meses)
for i in range(total_meses):
    if i+1 < mes_inicio_novo_valor:  # antes da mudança
        fixos_mensais_array[i] = nuvem + mensalidade_cigam + mensalidade_mercos_inicial
    else:  # após ou no mês da mudança
        fixos_mensais_array[i] = nuvem + mensalidade_cigam + mensalidade_mercos_novo

# Custos mensais (somados) -> apenas recorrentes
custo_total_mes = np.round(consumo_projeto_mensal + gestao_mes + fixos_mensais_array, 2)

# Total do projeto = recorrentes + componentes únicos (apenas uma vez)
total_projeto_reais = float(custo_total_mes.sum() + custo_instal + custo_map + homologacao)

# =========================
# KPI no topo
# =========================
if (horas_totais_projeto > 0 or custo_instal > 0 or custo_map > 0 or homologacao > 0 or np.any(fixos_mensais_array > 0)):
    metric_total_top.metric("Total do projeto", brl(total_projeto_reais))
else:
    metric_total_top.metric("Total do projeto", "—")

# =========================
# Tabelas
# =========================
df_custos = pd.DataFrame({
    "Período": meses_rotulo,
    "Horas do mês": horas_mes,
    "Consumo Horas Projeto Mensal (R$)": consumo_projeto_mensal,
    "Gestão do Projeto (R$)": gestao_mes,
    "Fixos mensais (R$)": np.round(fixos_mensais_array, 2),
    "Total do Período (R$)": custo_total_mes
})

st.subheader("Custos por período")
show_df_currency(
    df_custos,
    ["Consumo Horas Projeto Mensal (R$)", "Gestão do Projeto (R$)", "Fixos mensais (R$)", "Total do Período (R$)"],
    hours_cols=["Horas do mês"],
    highlight_col="Total do Período (R$)"
)

st.subheader("Tabela de Avanço x Horas mensais")
df_avanco = pd.DataFrame({
    "Período": meses_rotulo,
    "Avanço mensal (%)": [np.nan] + (list(np.round(pcts5, 2)) if k > 0 else []),
    "Horas do mês": horas_mes
})
st.dataframe(df_avanco, use_container_width=True, hide_index=True)

st.subheader("Componentes únicos do projeto (não mensais)")
df_unicos = pd.DataFrame({
    "Componente": ["Instalação infra", "Mapeamento inicial", "Homologação"],
    "Custo (R$)": [custo_instal, custo_map, homologacao]
})
show_df_currency(df_unicos, ["Custo (R$)"])

# =========================
# Estilo: topbar grudada
# =========================
st.markdown(
    """
    <style>
    section.main > div:first-child {
        position: sticky; top: 0; z-index: 999;
        background: var(--background-color);
        padding-top: .5rem; padding-bottom: .5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)