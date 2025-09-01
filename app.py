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
periodo = st.sidebar.slider("Período (meses)", min_value=6, max_value=12, value=6, step=1)

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
# Regras/Helpers de percentuais
# =========================
H_PRIMEIRO_MES = 70.0  # 70 horas fixas no 1º mês

def auto_pcts_inicio_fim(k: int, forca: int = 3, enfase_inicio: float = 1.6, enfase_fim: float = 1.8) -> np.ndarray:
    """Gera k porcentagens (somam ~100) com foco no início e no fim (perfil em U)."""
    if k <= 0:
        return np.array([])
    if k == 1:
        return np.array([100.0])
    x = np.linspace(0, 1, k)
    base = (1 - x) ** forca * enfase_inicio + x ** forca * enfase_fim
    p = 100 * base / base.sum()
    return p

def quantize_to_5(pcts_raw: np.ndarray, normalize_to_100: bool = True, min_pct: float = 5.0) -> np.ndarray:
    """
    Converte % para múltiplos de 5.
    Se normalize_to_100=True, aloca 20 unidades de 5% com mínimo min_pct por mês.
    """
    arr = np.maximum(0.0, np.array(pcts_raw, dtype=float))
    k = arr.size
    if k == 0:
        return arr

    units_total = 20                      # 100% / 5%
    min_units = int(np.ceil(min_pct / 5.0))  # 5% -> 1 unidade
    if not normalize_to_100:
        return np.round(arr / 5.0) * 5.0  # apenas arredonda para múltiplo de 5

    # segurança: se k*min_units > units_total, reduz min_units (não deve acontecer com k<=11)
    if k * min_units > units_total:
        min_units = max(1, units_total // k)

    # baseline: mínimo garantido para cada mês
    base_units = np.full(k, min_units, dtype=int)
    remaining_units = units_total - base_units.sum()
    if remaining_units <= 0:
        return base_units.astype(float) * 5.0

    # pesos para distribuir o restante
    w = arr.copy()
    if w.sum() <= 0:
        ideal = np.full(k, remaining_units / k)
    else:
        ideal = w / w.sum() * remaining_units

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
# Distribuição de horas
# =========================
horas_m1 = min(H_PRIMEIRO_MES, horas_totais_projeto)           # 1º mês fixo
horas_restantes = max(0.0, horas_totais_projeto - horas_m1)    # saldo para M2..MN

meses_rotulo = [f"Mês {i}" for i in range(1, periodo + 1)]
rest_count = periodo - 1
pct_equal = round(100 / rest_count, 2) if rest_count > 0 else 0.0

st.subheader("Percentuais para os meses 2..N")

# Modo de definição dos percentuais (sem tabela)
modo_pct = st.radio(
    "Como definir os percentuais?",
    ["Manual", "Automático (início e fim)"],
    horizontal=True
)

if modo_pct == "Automático (início e fim)":
    c1, c2, c3 = st.columns(3)
    with c1:
        forca = st.slider("Força (1–8)", 1, 8, 3, 1)
    with c2:
        enfase_inicio = st.slider("Ênfase no começo", 1.0, 3.0, 1.6, 0.1)
    with c3:
        enfase_fim = st.slider("Ênfase no último mês", 1.0, 3.0, 1.8, 0.1)
    pcts_default = auto_pcts_inicio_fim(rest_count, forca, enfase_inicio, enfase_fim)
else:
    pcts_default = np.array([pct_equal] * rest_count, dtype=float)

auto_normalizar = st.checkbox("Normalizar para 100%", value=True)

# Captura dos percentuais (sem data_editor)
if modo_pct == "Automático (início e fim)":
    pcts_raw = pcts_default
else:
    pcts_inputs = []
    for i, rot in enumerate(meses_rotulo[1:], start=1):
        v = st.number_input(
            f"{rot} (%)", min_value=5.0, max_value=100.0, step=5.0,
            value=float(np.clip(pcts_default[i-1], 5, 100)), format="%.0f", key=f"pct_{i}"
        )
        pcts_inputs.append(v)
    pcts_raw = np.array(pcts_inputs, dtype=float)

# Converte para múltiplos de 5, mínimo 5% e (opcional) soma=100
pcts5 = quantize_to_5(pcts_raw, normalize_to_100=auto_normalizar, min_pct=5.0)
soma_pct = float(pcts5.sum())


# Se NÃO normalizar, exige soma=100 e valida mínimo/múltiplos
if rest_count > 0 and not auto_normalizar:
    erros = []
    if abs(soma_pct - 100.0) > 1e-6:
        erros.append("a soma precisa ser exatamente 100%")
    if (pcts5 < 5 - 1e-9).any():
        erros.append("cada mês precisa ter pelo menos 5%")
    if np.any((pcts5 % 5) != 0):
        erros.append("use apenas múltiplos de 5%")
    if erros:
        st.error("Corrija os percentuais: " + "; ".join(erros) + " (ou marque a opção de normalizar).")
        st.stop()

# Pesos finais e horas por mês
if soma_pct <= 0:
    w = np.ones(rest_count) / rest_count if rest_count > 0 else np.array([])
else:
    w = pcts5 / 100.0

horas_mes = np.zeros(periodo, dtype=float)
horas_mes[0] = horas_m1
if rest_count > 0:
    horas_mes[1:] = np.round(horas_restantes * w, 2)

# =========================
# Componentes únicos do projeto (não mensais)
# =========================
custo_instal = float(valor_hora * 20.0)  # Instalação infra = horas_totais * 20
custo_map    = float(valor_hora * 50.0)  # Mapeamento inicial = horas_totais * 50

# =========================
# Custos mensais
# =========================
# Consumo Horas Projeto Mensal (mês a mês): valor_hora * horas daquele mês
consumo_projeto_mensal = np.round(horas_mes * valor_hora, 2)

# Gestão do Projeto:
#  - Mês 1: 20% * (Instalação + Mapeamento)
#  - Meses 2..N: 20% * Consumo Horas Projeto Mensal do mês
gestao_mes = np.zeros(periodo, dtype=float)
gestao_mes[0] = round(0.20 * (custo_instal + custo_map), 2)
if periodo > 1:
    gestao_mes[1:] = np.round(0.20 * consumo_projeto_mensal[1:], 2)

# Fixos mensais (mesmo valor em todos os meses)
fixos_mensais = float(nuvem + mensalidade_cigam + mensalidade_mercos)

# Custo total por período = Consumo (mês) + Gestão (mês) + Fixos
custo_total_mes = np.round(consumo_projeto_mensal + gestao_mes + fixos_mensais, 2)

# Total do projeto = Itens únicos + soma dos custos mensais
total_projeto_reais = float(custo_instal + custo_map + homologacao + custo_total_mes.sum())

# =========================
# KPIs no topo (preenche placeholders)
# =========================
metric_media_top.metric("Média por período", brl(float(custo_total_mes.mean())))
metric_total_top.metric("Total do projeto", brl(float(total_projeto_reais)))

# =========================
# Tabelas (criadas ANTES de exibir)
# =========================
st.subheader("Tabela de Avanço x Horas mensais")
df_avanco = pd.DataFrame({
    "Período": meses_rotulo,
    "Avanço mensal (%)": [np.nan] + (list(np.round(pcts5, 2)) if rest_count > 0 else []),
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
# 👉 AQUI usamos show_df_currency depois de df_custos existir
show_df_currency(
    df_custos,
    ["Consumo Horas Projeto Mensal (R$)", "Gestão do Projeto (R$)", "Fixos mensais (R$)", "Total do Período (R$)"]
)

st.subheader("Componentes únicos do projeto (não mensais)")
df_unicos = pd.DataFrame({
    "Componente": ["Instalação infra", "Mapeamento inicial", "Homologação"],
    "Custo (R$)": [custo_instal, custo_map, homologacao]
})
# 👉 E aqui idem para df_unicos
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
