import streamlit as st

st.sidebar.title("🧮Calculadora - CIGAM")

periodo = st.sidebar.slider("Período:", min_value=6, max_value=12)
valor_hora = st.sidebar.number_input("Valor hora:")
nuvem = st.sidebar.number_input("Valor nuvem?")
mensalidade_cigam = st.sidebar.number_input("Mensalidade CIGAM:")
homologacao = st.sidebar.number_input("Homologação")
resultado = valor_hora + nuvem + mensalidade_cigam + homologacao

resultado = mensalidade_cigam * periodo

st.set_page_config(
    page_title="Calculadora | CIGAM", 
    page_icon="🧮",
    layout="wide"
)
st.header("Cálculo:")
st.metric(label="Total:", value=resultado, delta="+ 5%")

