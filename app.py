import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Controle de Finanças", layout="wide")

# --- SISTEMA DE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 Login - Finanças")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            # Troque "admin" e "1234" pelo login que você quiser
            if usuario == "admin" and senha == "1234":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")
        return False
    return True

# --- SE O LOGIN FOR SUCESSO, MOSTRA O SISTEMA ---
if check_password():
    st.title("📊 Meu Dashboard Financeiro")
    
    # Criando o banco de dados temporário (pode ser conectado ao seu Excel depois)
    if 'gastos' not in st.session_state:
        st.session_state.gastos = pd.DataFrame(columns=["Data", "Origem", "Gasto", "Pagamento", "Valor", "Cartão", "Mês Fechamento"])

    # --- REGRA DO DIA 15 AO DIA 15 ---
    def calcular_mes_fechamento(data_compra):
        if data_compra.day >= 15:
            mes = data_compra.month + 1 if data_compra.month < 12 else 1
            ano = data_compra.year if data_compra.month < 12 else data_compra.year + 1
        else:
            mes = data_compra.month
            ano = data_compra.year
        return f"{mes:02d}/{ano}"

    # --- TELA DE CADASTRO ---
    with st.expander("➕ Cadastrar Novo Gasto (Clique para abrir)", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_input = st.date_input("Data da Compra", date.today())
            origem_input = st.selectbox("Origem / Segmento", 
                                        ["Casa", "Delivery", "Mercado", "Lazer", "Transporte", "Saúde", "Pet's", "Assinatura", "Educação", "Compras", "Gastos Extra"])
        with col2:
            gasto_input = st.text_input("Gasto (Ex: Padaria, Conta de Luz)")
            pagamento_input = st.selectbox("Forma de Pagamento", ["Pix/Debito", "Cartão Credito"])
        with col3:
            valor_input = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
            cartao_input = st.selectbox("Cartão Usado", ["Nenhum (Pix)", "Nubank", "BTG"])
        
        if st.button("Salvar Gasto", type="primary"):
            novo_gasto = {
                "Data": data_input,
                "Origem": origem_input,
                "Gasto": gasto_input,
                "Pagamento": pagamento_input,
                "Valor": valor_input,
                "Cartão": cartao_input,
                "Mês Fechamento": calcular_mes_fechamento(data_input)
            }
            # Adiciona o gasto na tabela
            st.session_state.gastos = pd.concat([st.session_state.gastos, pd.DataFrame([novo_gasto])], ignore_index=True)
            st.success("✅ Gasto cadastrado com sucesso!")

    st.divider()

    # --- DASHBOARD E GRÁFICOS ---
    if not st.session_state.gastos.empty:
        st.subheader("📈 Resumo e Gráficos")
        
        # Filtro de Mês
        meses_disponiveis = st.session_state.gastos["Mês Fechamento"].unique()
        mes_selecionado = st.selectbox("📅 Selecione o Mês da Fatura para Visualizar", meses_disponiveis)
        
        df_filtrado = st.session_state.gastos[st.session_state.gastos["Mês Fechamento"] == mes_selecionado]
        
        # Total Gasto no Mês
        st.metric("Total Gasto na Fatura", f"R$ {df_filtrado['Valor'].sum():.2f}")
        
        # Gráficos
        colA, colB = st.columns(2)
        with colA:
            # Quem gastou mais (Origem)
            if not df_filtrado.empty:
                fig_origem = px.pie(df_filtrado, values="Valor", names="Origem", title="Gastos por Origem (Segmento)", hole=0.4)
                st.plotly_chart(fig_origem, use_container_width=True)
        with colB:
            # Gráfico de Barras por Cartão
            if not df_filtrado.empty:
                df_cartao = df_filtrado.groupby("Cartão")["Valor"].sum().reset_index()
                fig_cartao = px.bar(df_cartao, x="Cartão", y="Valor", text="Valor", title="Gastos por Cartão", color="Cartão")
                st.plotly_chart(fig_cartao, use_container_width=True)
                
        # Mostrar a tabela com os lançamentos daquele mês
        st.write("📋 **Detalhes dos Lançamentos**")
        st.dataframe(df_filtrado[["Data", "Origem", "Gasto", "Pagamento", "Cartão", "Valor"]], use_container_width=True)
        
    else:
        st.info("Nenhum gasto cadastrado ainda. Faça um lançamento acima para ver o Dashboard!")