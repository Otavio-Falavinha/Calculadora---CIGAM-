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
    metric_media_top = col_top_1.empty()   # será preenchido com st.metric depois
    metric_total_top = col_top_2.empty()

# =========================
# Utilitários (formatação)
# =========================
def brl(x: float) -> str:
    """Formata número em Real (pt-BR)."""
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def show_df_currency(df: pd.DataFrame, money_cols: list[str]):
    """
    Mostra DataFrame com colunas monetárias formatadas com R$.
    Mantém colunas numéricas quando possível (column_config).
    """
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

# =========================
# Entradas (sidebar)
# =========================
# Agora este slider representa os MESES APÓS o 1º mês (fixo).
# Se escolher 6 => total = 1 (M1) + 6 (M2..M7) = 7 meses.
periodo_restante = st.sidebar.slider(
    "Meses após o 1º (M2..N)",
    min_value=6, max_value=12, value=6, step=1
)

# Custos fixos recorrentes por mês (R$)
nuvem = st.sidebar.number_input("Valor nuvem (R$/mês)", min_value=0.0, value=0.0, step=50.0, format="%.2f")
mensalidade_cigam = st.sidebar.number_input("Mensalidade CIGAM (R$/mês)", min_value=0.0, value=0.0, step=50.0, format="%.2f")
mensalidade_mercos = st.sidebar.number_input("Mensalidade Mercos (R$/mês)", min_value=0.0, value=0.0, step=50.0, format="%.2f")

st.sidebar.markdown("---")
st.sidebar.caption("Informe as **horas totais do projeto** (usadas nas fórmulas abaixo).")
horas_totais_projeto = st.sidebar.number_input("Horas totais do projeto", min_value=0.0, value=0.0, step=0.1, format="%.1f")
valor_hora = st.sidebar.number_input("Valor da hora (R$)", min_value=0.0, value=255.0, step=10.0, format="%.2f")

# Homologação é valor único (não depende de horas)
homologacao = st.sidebar.number_input("Homologação (R$)", min_value=0.0, value=0.0, step=50.0, format="%.2f")

# =========================
# Regras/Helpers de percentuais (100% automático)
# =========================
H_PRIMEIRO_MES = 70.0  # 70 horas fixas no 1º mês

def perfil_U_automatico(k: int) -> np.ndarray:
    """
    Gera k porcentagens (somam 100) com foco automático no início e no fim (perfil em U).
    Último mês recebe mais ênfase que o primeiro.
    k = quantidade de meses APÓS o 1º (ou seja, M2..MN).
    """
    if k <= 0:
        return np.array([])
    if k == 1:
        return np.array([100.0])

    # Parâmetros fixos (primeiro < último):
    forca = 3
    enfase_inicio = 1.4   # um pouco menor
    enfase_fim = 2.0      # um pouco maior

    x = np.linspace(0, 1, k)
    base = (1 - x) ** forca * enfase_inicio + x ** forca * enfase_fim
    p = 100 * base / base.sum()
    return p

def quantize_to_5(pcts_raw: np.ndarray, min_pct: float = 5.0) -> np.ndarray:
    """
    Converte % para múltiplos de 5 com mínimo por mês e normaliza para 100%.
    Sempre normaliza para 100 para manter robustez ao trocar o período.
    """
    arr = np.maximum(0.0, np.array(pcts_raw, dtype=float))
    k = arr.size
    if k == 0:
        return arr

    units_total = 20                         # 100% / 5%
    min_units = int(np.ceil(min_pct / 5.0))  # 5% -> 1 unidade

    # baseline: mínimo garantido para cada mês
    base_units = np.full(k, min_units, dtype=int)
    remaining_units = units_total - base_units.sum()
    if remaining_units <= 0:
        return base_units.astype(float) * 5.0

    # pesos para distribuir o restante
    if arr.sum() <= 0:
        ideal = np.full(k, remaining_units / k)
    else:
        ideal = arr / arr.sum() * remaining_units

    add_units = np.floor(ideal).astype(int)
    leftover = remaining_units - add_units.sum()

    # distribui sobras pelas maiores frações
    fracs = ideal - add_units
    order = np.argsort(-fracs)
    if leftover > 0:
        add_units[order[:leftover]] += 1

    units = base_units + add_units
    return units.astype(float) * 5.0

# =========================
# Distribuição de meses e horas
# =========================
total_meses = periodo_restante + 1  # inclui o mês 1 fixo
meses_rotulo = [f"Mês {i}" for i in range(1, total_meses + 1)]

horas_m1 = min(H_PRIMEIRO_MES, horas_totais_projeto)            # 1º mês fixo
horas_restantes = max(0.0, horas_totais_projeto - horas_m1)     # saldo para M2..MN

st.subheader(f"Percentuais para os meses 2..{total_meses} (automático)")

# --- 100% automático: perfil em U nos meses 2..N, com ênfase no começo e no fim ---
k = periodo_restante  # quantidade de meses após o mês 1
pcts_raw = perfil_U_automatico(k)
pcts5 = quantize_to_5(pcts_raw, min_pct=5.0)  # múltiplos de 5 e soma=100
soma_pct = float(pcts5.sum())

# Pesos finais e horas por mês
w = pcts5 / 100.0 if soma_pct > 0 else (np.ones(k) / k if k > 0 else np.array([]))

horas_mes = np.zeros(total_meses, dtype=float)
horas_mes[0] = horas_m1  # 1º mês já é "enfatizado" pelas 70h fixas
if k > 0:
    # sobra distribuída com ênfase no início (M2) e fim (MN) do restante
    horas_mes[1:] = np.round(horas_restantes * w, 2)

# =========================
# Componentes únicos do projeto (não mensais)
# =========================
custo_instal = float(valor_hora * 20.0)  # Instalação infra = 20h
custo_map    = float(valor_hora * 50.0)  # Mapeamento inicial = 50h

# =========================
# Custos mensais
# =========================
consumo_projeto_mensal = np.round(horas_mes * valor_hora, 2)

# Gestão:
# - Mês 1: 20% * (Instalação + Mapeamento)
# - Meses 2..N: 20% * Consumo Horas Projeto Mensal do mês
gestao_mes = np.zeros(total_meses, dtype=float)
gestao_mes[0] = round(0.20 * (custo_instal + custo_map), 2)
if total_meses > 1:
    gestao_mes[1:] = np.round(0.20 * consumo_projeto_mensal[1:], 2)

# Fixos mensais (mesmo valor em todos os meses)
fixos_mensais = float(nuvem + mensalidade_cigam + mensalidade_mercos)

# Custo total por período
custo_total_mes = np.round(consumo_projeto_mensal + gestao_mes + fixos_mensais, 2)

# Total do projeto
total_projeto_reais = float(custo_instal + custo_map + homologacao + custo_total_mes.sum())

# =========================
# KPIs no topo
# =========================
metric_media_top.metric("Média por período", brl(float(custo_total_mes.mean())))
metric_total_top.metric("Total do projeto", brl(float(total_projeto_reais)))

# =========================
# Tabelas
# =========================
st.subheader("Tabela de Avanço x Horas mensais")
df_avanco = pd.DataFrame({
    "Período": meses_rotulo,
    "Avanço mensal (%)": [np.nan] + (list(np.round(pcts5, 2)) if k > 0 else []),
    "Horas do mês": horas_mes
})
try:
    st.dataframe(df_avanco, use_container_width=True, hide_index=True)
except TypeError:
    st.dataframe(df_avanco.reset_index(drop=True), use_container_width=True)

st.subheader("Custos por período")
df_custos = pd.DataFrame({
    "Período": meses_rotulo,
    "Horas do mês": horas_mes,
    "Consumo Horas Projeto Mensal (R$)": consumo_projeto_mensal,
    "Gestão do Projeto (R$)": gestao_mes,
    "Fixos mensais (R$)": np.round(fixos_mensais, 2),
    "Total do Período (R$)": custo_total_mes
})
show_df_currency(
    df_custos,
    ["Consumo Horas Projeto Mensal (R$)", "Gestão do Projeto (R$)", "Fixos mensais (R$)", "Total do Período (R$)"]
)

st.subheader("Componentes únicos do projeto (não mensais)")
df_unicos = pd.DataFrame({
    "Componente": ["Instalação infra", "Mapeamento inicial", "Homologação"],
    "Custo (R$)": [custo_instal, custo_map, homologacao]
})
show_df_currency(df_unicos, ["Custo (R$)"])

# =========================
# Estilo: topbar "grudada" ao rolar
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