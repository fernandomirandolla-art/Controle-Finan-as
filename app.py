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
            if usuario == "admin" and senha == "1234":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")
        return False
    return True

if check_password():
    st.title("📊 Meu Dashboard Financeiro")

    # --- LER DADOS DA PLANILHA (Histórico) ---
    @st.cache_data(ttl=60)
    def carregar_dados():
        url = "https://docs.google.com/spreadsheets/d/1EEVo7R_OlvVnHLBE2kfzGc2LuES-DEdY-v5V9gkHDJw/export?format=csv&gid=0"
        df = pd.read_csv(url)
        
        if 'Cartão Usado' in df.columns:
            df = df.rename(columns={'Cartão Usado': 'Cartão'})
            
        df['Valor'] = df['Valor'].astype(str).str.replace("R$", "", regex=False)
        df['Valor'] = df['Valor'].str.replace(" ", "", regex=False)
        df['Valor'] = df['Valor'].str.replace(".", "", regex=False)
        df['Valor'] = df['Valor'].str.replace(",", ".", regex=False)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
        
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        
        # REGRA CORRIGIDA: Pix/Débito no mês exato, Cartão com regra do dia 15
        def calcular_mes_fechamento(row):
            data_compra = row['Data']
            pagamento = str(row['Pagamento']).strip()
            
            if pd.isnull(data_compra):
                return "Indefinido"
                
            # Se for Pix/Debito, o gasto entra no mês exato em que ocorreu
            if pagamento == "Pix/Debito":
                mes = data_compra.month
                ano = data_compra.year
            # Se for Cartão de Crédito, compras a partir do dia 15 caem na fatura do mês seguinte
            else:
                if data_compra.day >= 15:
                    mes = data_compra.month + 1 if data_compra.month < 12 else 1
                    ano = data_compra.year if data_compra.month < 12 else data_compra.year + 1
                else:
                    mes = data_compra.month
                    ano = data_compra.year
            return f"{mes:02d}/{ano}"

        df['Mês Fechamento'] = df.apply(calcular_mes_fechamento, axis=1)
        df['Data'] = df['Data'].dt.date
        df = df.dropna(subset=['Valor'])
        return df

    try:
        if 'dados_carregados' not in st.session_state:
            st.session_state.gastos = carregar_dados()
            st.session_state.dados_carregados = True
    except Exception as e:
        st.error("Erro ao puxar a planilha. Verifique se você liberou o link para 'Qualquer Pessoa'!")
        st.session_state.gastos = pd.DataFrame(columns=["Data", "Origem", "Gasto", "Pagamento", "Valor", "Cartão", "Mês Fechamento"])

    # --- TELA DE CADASTRO (Aviso) ---
    with st.expander("➕ Cadastrar Novo Gasto (Temporário - Não salva no Google Sheets)", expanded=False):
        st.warning("⚠️ Os gastos salvos aqui aparecem no gráfico apenas para simulação.")
        col1, col2, col3 = st.columns(3)
        with col1:
            data_input = st.date_input("Data da Compra", date.today())
            origem_input = st.selectbox("Origem / Segmento", ["Casa", "Delivery", "Mercado", "Lazer", "Transporte", "Saúde", "Pet's", "Assinatura", "Educação", "Compras", "Gastos Extra"])
        with col2:
            gasto_input = st.text_input("Gasto (Ex: Padaria, Conta de Luz)")
            pagamento_input = st.selectbox("Forma de Pagamento", ["Pix/Debito", "Cartão Credito"])
        with col3:
            valor_input = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
            cartao_input = st.selectbox("Cartão Usado", ["Nubank", "BTG", "Nenhum (Pix)"])
        
        if st.button("Salvar na Visualização", type="primary"):
            if pagamento_input == "Pix/Debito":
                novo_mes = f"{data_input.month:02d}/{data_input.year}"
            else:
                novo_mes = f"{data_input.month + 1 if data_input.day >= 15 else data_input.month:02d}/{data_input.year}"
            
            novo_gasto = pd.DataFrame([{"Data": data_input, "Origem": origem_input, "Gasto": gasto_input, "Pagamento": pagamento_input, "Valor": valor_input, "Cartão": cartao_input, "Mês Fechamento": novo_mes}])
            st.session_state.gastos = pd.concat([st.session_state.gastos, novo_gasto], ignore_index=True)
            st.success("✅ Gasto incluído no Dashboard atual!")

    st.divider()

    # --- DASHBOARD E GRÁFICOS ---
    if not st.session_state.gastos.empty:
        st.subheader("📈 Resumo e Gráficos do Seu Histórico")
        
        # Filtros Lado a Lado
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            meses_ordenados = sorted(st.session_state.gastos["Mês Fechamento"].unique(), reverse=True)
            mes_selecionado = st.selectbox("📅 Selecione o Mês (Fatura/Competência)", meses_ordenados)
        with col_f2:
            tipos_pagamento = ["Todos"] + list(st.session_state.gastos["Pagamento"].dropna().unique())
            pagamento_selecionado = st.selectbox("💳 Filtrar por Pagamento", tipos_pagamento)
        
        # Aplicando os filtros
        df_filtrado = st.session_state.gastos[st.session_state.gastos["Mês Fechamento"] == mes_selecionado]
        if pagamento_selecionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Pagamento"] == pagamento_selecionado]
        
        # Total Gasto no Mês
        st.metric(f"Total Gasto ({pagamento_selecionado})", f"R$ {df_filtrado['Valor'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        colA, colB = st.columns(2)
        with colA:
            if not df_filtrado.empty:
                fig_origem = px.pie(df_filtrado, values="Valor", names="Origem", title="Gastos por Origem (Segmento)", hole=0.4)
                st.plotly_chart(fig_origem, use_container_width=True)
        with colB:
            if not df_filtrado.empty:
                df_cartao = df_filtrado.groupby("Cartão")["Valor"].sum().reset_index()
                fig_cartao = px.bar(df_cartao, x="Cartão", y="Valor", text="Valor", title="Gastos por Cartão", color="Cartão")
                fig_cartao.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
                st.plotly_chart(fig_cartao, use_container_width=True)
                
        # Tabela Detalhada
        st.write("📋 **Detalhes dos Lançamentos Filtrados**")
        df_visual = df_filtrado[["Data", "Origem", "Gasto", "Pagamento", "Cartão", "Valor"]].copy()
        df_visual["Valor"] = df_visual["Valor"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.dataframe(df_visual, use_container_width=True, hide_index=True)
