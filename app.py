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
    @st.cache_data(ttl=60) # Atualiza automaticamente a cada 1 minuto
    def carregar_dados():
        # Link especial que baixa a aba "Base Mês"
        url = "https://docs.google.com/spreadsheets/d/1EEVo7R_OlvVnHLBE2kfzGc2LuES-DEdY-v5V9gkHDJw/export?format=csv&gid=0"
        df = pd.read_csv(url)
        
        # Ajusta o nome da coluna de cartão
        if 'Cartão Usado' in df.columns:
            df = df.rename(columns={'Cartão Usado': 'Cartão'})
            
        # Limpa o "R$" e arruma a formatação de dinheiro brasileiro para o gráfico entender
        df['Valor'] = df['Valor'].astype(str).str.replace("R$", "", regex=False)
        df['Valor'] = df['Valor'].str.replace(" ", "", regex=False)
        df['Valor'] = df['Valor'].str.replace(".", "", regex=False)
        df['Valor'] = df['Valor'].str.replace(",", ".", regex=False)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
        
        # Converte a coluna Data
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        
        # Aplica a REGRA DO DIA 15 (Fechamento)
        def calcular_mes_fechamento(data_compra):
            if pd.isnull(data_compra):
                return "Indefinido"
            if data_compra.day >= 15:
                mes = data_compra.month + 1 if data_compra.month < 12 else 1
                ano = data_compra.year if data_compra.month < 12 else data_compra.year + 1
            else:
                mes = data_compra.month
                ano = data_compra.year
            return f"{mes:02d}/{ano}"

        df['Mês Fechamento'] = df['Data'].apply(calcular_mes_fechamento)
        df['Data'] = df['Data'].dt.date
        
        # Remove eventuais linhas em branco
        df = df.dropna(subset=['Valor'])
        return df

    # Tenta carregar o histórico
    try:
        if 'dados_carregados' not in st.session_state:
            st.session_state.gastos = carregar_dados()
            st.session_state.dados_carregados = True
    except Exception as e:
        st.error("Erro ao puxar a planilha. Verifique se você liberou o link para 'Qualquer Pessoa'!")
        st.session_state.gastos = pd.DataFrame(columns=["Data", "Origem", "Gasto", "Pagamento", "Valor", "Cartão", "Mês Fechamento"])

    # --- TELA DE CADASTRO (Aviso) ---
    with st.expander("➕ Cadastrar Novo Gasto (Temporário - Não salva no Google Sheets)", expanded=False):
        st.warning("⚠️ Os gastos salvos aqui aparecem no gráfico apenas para simulação. Eles não são enviados para sua planilha do Excel ainda.")
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
            novo_mes = f"{data_input.month + 1 if data_input.day >= 15 else data_input.month:02d}/{data_input.year}"
            novo_gasto = pd.DataFrame([{"Data": data_input, "Origem": origem_input, "Gasto": gasto_input, "Pagamento": pagamento_input, "Valor": valor_input, "Cartão": cartao_input, "Mês Fechamento": novo_mes}])
            st.session_state.gastos = pd.concat([st.session_state.gastos, novo_gasto], ignore_index=True)
            st.success("✅ Gasto incluído no Dashboard atual!")

    st.divider()

    # --- DASHBOARD E GRÁFICOS ---
    if not st.session_state.gastos.empty:
        st.subheader("📈 Resumo e Gráficos do Seu Histórico")
        
        # Filtro de Mês
        meses_ordenados = sorted(st.session_state.gastos["Mês Fechamento"].unique(), reverse=True)
        mes_selecionado = st.selectbox("📅 Selecione o Mês da Fatura para Visualizar", meses_ordenados)
        
        df_filtrado = st.session_state.gastos[st.session_state.gastos["Mês Fechamento"] == mes_selecionado]
        
        # Total Gasto no Mês
        st.metric("Total Gasto na Fatura Selecionada", f"R$ {df_filtrado['Valor'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
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
        st.write("📋 **Detalhes dos Lançamentos da Fatura**")
        # Formatar valor na tabela para o visual
        df_visual = df_filtrado[["Data", "Origem", "Gasto", "Pagamento", "Cartão", "Valor"]].copy()
        df_visual["Valor"] = df_visual["Valor"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.dataframe(df_visual, use_container_width=True, hide_index=True)
