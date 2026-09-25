import json
import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

st.set_page_config(page_title="Petrol Transportes", layout="wide", page_icon="🚛")

LOCAL_DATA_PATH = os.path.join(os.path.dirname(__file__), "local_programacoes.json")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        .stMetric {
            background: #111827;
            border-radius: 12px;
            padding: 12px;
            border: 1px solid #2d3748;
        }
        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a, #111827);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Conexão com Supabase
@st.cache_resource
def init_supabase() -> Client | None:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        return None
    return create_client(url, key)

supabase = init_supabase()


def persist_local_programacoes(dados):
    with open(LOCAL_DATA_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
    st.session_state["local_programacoes"] = dados


def get_local_programacoes():
    if "local_programacoes" in st.session_state:
        return st.session_state["local_programacoes"]

    if os.path.exists(LOCAL_DATA_PATH):
        try:
            with open(LOCAL_DATA_PATH, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            st.session_state["local_programacoes"] = dados if isinstance(dados, list) else []
            return st.session_state["local_programacoes"]
        except Exception:
            st.session_state["local_programacoes"] = []
            return []

    st.session_state["local_programacoes"] = []
    return []


def get_programacoes():
    if supabase is None:
        return get_local_programacoes()
    try:
        res = supabase.table("programacoes").select("*").execute()
        return res.data or []
    except Exception:
        st.warning("Não foi possível acessar o Supabase; usando dados locais da sessão.")
        return get_local_programacoes()


def save_programacao(novo_dado):
    if supabase is not None:
        supabase.table("programacoes").insert(novo_dado).execute()
        return
    dados = get_local_programacoes()
    dados.append(novo_dado)
    persist_local_programacoes(dados)


def update_programacao(index, novo_dado):
    if supabase is not None:
        supabase.table("programacoes").update(novo_dado).eq("numero_pedido", novo_dado["numero_pedido"]).execute()
        return
    dados = get_local_programacoes()
    if 0 <= index < len(dados):
        dados[index] = {**dados[index], **novo_dado}
        persist_local_programacoes(dados)


def delete_programacao(index):
    if supabase is not None:
        dados = get_programacoes()
        if index < len(dados):
            pedido = dados[index]
            supabase.table("programacoes").delete().eq("numero_pedido", pedido.get("numero_pedido")).execute()
        return
    dados = get_local_programacoes()
    if 0 <= index < len(dados):
        dados.pop(index)
        persist_local_programacoes(dados)


def reset_local_programacoes():
    persist_local_programacoes([])


if supabase is None:
    st.warning("Modo local ativado: configure as chaves do Supabase para salvar em nuvem. Os dados ficam apenas nesta sessão.")

st.sidebar.title("🚛 Petrol Transportes")
usuario_atual = st.sidebar.text_input("Seu Nome / Usuário", value="Operador")

menu = st.sidebar.radio("Navegação", [
    "📝 Lançar Pedidos", 
    "📊 Programação & Relatórios", 
    "💰 Faturamento & Projeções", 
    "🚛 Frota & Motoristas"
])

# --- TELA 1: LANÇAR PEDIDOS ---
if menu == "📝 Lançar Pedidos":
    st.title("📝 Lançamento de Pedidos")
    st.caption(f"Registrando como: **{usuario_atual}**")
    
    with st.form("form_pedido", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_prog = st.date_input("Data da Programação", datetime.date.today())
            no_pedido = st.text_input("Nº do Pedido / Carga")
            cliente = st.text_input("Cliente")
        with col2:
            rota = st.text_input("Rota (Origem x Destino)")
            motorista = st.text_input("Nome do Motorista")
            placa = st.text_input("Placa / Conjunto")
        with col3:
            tipo_produto = st.selectbox("Tipo de Produto", ["Combustível", "Etanol", "Diesel", "Gasolina", "Outros"])
            valor_frete = st.number_input("Valor do Frete / Faturamento (R$)", min_value=0.0, step=100.0)
            valor_diaria = st.number_input("Valor da Diária (R$)", min_value=0.0, step=50.0)
            
        status = st.selectbox("Status", ["Programado", "Em Trânsito", "Concluído", "Cancelado"])
        obs = st.text_area("Observações")
        
        btn_salvar = st.form_submit_button("💾 Salvar Pedido")
        
        if btn_salvar:
            if not no_pedido or not motorista or not placa:
                st.warning("Preencha ao menos Pedido, Motorista e Placa!")
            else:
                novo_dado = {
                    "usuario_lancamento": usuario_atual,
                    "data_programacao": str(data_prog),
                    "numero_pedido": no_pedido,
                    "cliente": cliente,
                    "rota": rota,
                    "motorista": motorista,
                    "placa": placa,
                    "tipo_produto": tipo_produto,
                    "valor_frete": valor_frete,
                    "valor_diaria": valor_diaria,
                    "status": status,
                    "observacoes": obs
                }
                save_programacao(novo_dado)
                st.success("✅ Pedido registrado com sucesso!")

# --- TELA 2: PROGRAMAÇÃO & RELATÓRIOS ---
elif menu == "📊 Programação & Relatórios":
    st.title("📊 Programação e Filtros de Cargas")
    
    programacoes = get_programacoes()
    if programacoes:
        df = pd.DataFrame(programacoes)
        if "valor_frete" not in df.columns:
            df["valor_frete"] = 0
        df["valor_frete"] = pd.to_numeric(df["valor_frete"], errors="coerce").fillna(0)
        if "status" not in df.columns:
            df["status"] = "Programado"
        df["status"] = df["status"].fillna("Programado")
        
        st.subheader("🔍 Filtros de Busca")
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
        
        with f_col1:
            motoristas = ["Todos"] + sorted(filter(None, df.get("motorista", pd.Series(dtype=str)).dropna().unique().tolist()))
            f_motorista = st.selectbox("Motorista", motoristas)
        with f_col2:
            placas = ["Todas"] + sorted(filter(None, df.get("placa", pd.Series(dtype=str)).dropna().unique().tolist()))
            f_placa = st.selectbox("Placa", placas)
        with f_col3:
            rotas = ["Todas"] + sorted(filter(None, df.get("rota", pd.Series(dtype=str)).dropna().unique().tolist()))
            f_rota = st.selectbox("Rota", rotas)
        with f_col4:
            produtos = ["Todos"] + sorted(filter(None, df.get("tipo_produto", pd.Series(dtype=str)).dropna().unique().tolist()))
            f_produto = st.selectbox("Tipo de Produto", produtos)
        with f_col5:
            statuses = ["Todos"] + sorted(filter(None, df.get("status", pd.Series(dtype=str)).dropna().unique().tolist()))
            f_status = st.selectbox("Status", statuses)
            
        df_filtrado = df.copy()
        if f_motorista != "Todos":
            df_filtrado = df_filtrado[df_filtrado["motorista"].astype(str).str.contains(f_motorista, case=False, na=False)]
        if f_placa != "Todas":
            df_filtrado = df_filtrado[df_filtrado["placa"].astype(str).str.contains(f_placa, case=False, na=False)]
        if f_rota != "Todas":
            df_filtrado = df_filtrado[df_filtrado["rota"].astype(str).str.contains(f_rota, case=False, na=False)]
        if f_produto != "Todos":
            df_filtrado = df_filtrado[df_filtrado["tipo_produto"].astype(str).str.contains(f_produto, case=False, na=False)]
        if f_status != "Todos":
            df_filtrado = df_filtrado[df_filtrado["status"].astype(str).str.contains(f_status, case=False, na=False)]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total", len(df_filtrado))
        k2.metric("Programados", int((df_filtrado["status"] == "Programado").sum()))
        k3.metric("Em Trânsito", int((df_filtrado["status"] == "Em Trânsito").sum()))
        k4.metric("Faturado", f"R$ {df_filtrado['valor_frete'].sum():,.2f}")
            
        st.markdown("---")
        st.subheader("📋 Resumo das Programações")
        
        colunas_visiveis = [
            "data_programacao", "numero_pedido", "cliente", "rota", 
            "motorista", "placa", "tipo_produto", "valor_frete", 
            "status", "usuario_lancamento"
        ]
        st.dataframe(df_filtrado[colunas_visiveis], use_container_width=True)

        if not df_filtrado.empty:
            options = [
                f"{row['numero_pedido']} - {row.get('motorista', 'Sem motorista')}"
                for _, row in df_filtrado.iterrows()
            ]
            idx_selecionado = st.selectbox("Editar ou remover registro", options, index=0)
            selected_index = options.index(idx_selecionado)
            registro = df_filtrado.iloc[selected_index].to_dict()

            with st.form("editar_programacao"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    edit_numero = st.text_input("Nº do Pedido / Carga", value=str(registro.get("numero_pedido", "")))
                    edit_motorista = st.text_input("Motorista", value=str(registro.get("motorista", "")))
                with col_b:
                    edit_placa = st.text_input("Placa", value=str(registro.get("placa", "")))
                    edit_status = st.selectbox("Status", ["Programado", "Em Trânsito", "Concluído", "Cancelado"], index=["Programado", "Em Trânsito", "Concluído", "Cancelado"].index(str(registro.get("status", "Programado"))))
                with col_c:
                    edit_valor = st.number_input("Valor do Frete", min_value=0.0, value=float(registro.get("valor_frete", 0.0)))
                    edit_cliente = st.text_input("Cliente", value=str(registro.get("cliente", "")))

                if st.form_submit_button("💾 Salvar alterações"):
                    update_programacao(df.index.get_loc(df_filtrado.index[selected_index]), {
                        "numero_pedido": edit_numero,
                        "motorista": edit_motorista,
                        "placa": edit_placa,
                        "status": edit_status,
                        "valor_frete": edit_valor,
                        "cliente": edit_cliente,
                    })
                    st.success("Registro atualizado com sucesso!")

                if st.form_submit_button("🗑️ Excluir registro"):
                    delete_programacao(df.index.get_loc(df_filtrado.index[selected_index]))
                    st.success("Registro removido com sucesso!")
        
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Relatório (Excel / CSV)",
            data=csv,
            file_name=f"relatorio_programacao_{datetime.date.today()}.csv",
            mime="text/csv"
        )

        if supabase is None:
            if st.button("🧹 Limpar dados locais"):
                reset_local_programacoes()
                st.success("Dados locais limpos com sucesso.")
    else:
        if supabase is None and st.button("🧹 Limpar dados locais"):
            reset_local_programacoes()
            st.success("Dados locais limpos com sucesso.")
        st.info("Nenhum pedido cadastrado ainda.")

# --- TELA 3: FATURAMENTO & PROJEÇÕES ---
elif menu == "💰 Faturamento & Projeções":
    st.title("💰 Projeção de Faturamento")
    
    programacoes = get_programacoes()
    if programacoes:
        df = pd.DataFrame(programacoes)
        df['data_programacao'] = pd.to_datetime(df['data_programacao'])
        
        hoje = pd.Timestamp(datetime.date.today())
        inicio_semana = hoje - pd.Timedelta(days=hoje.dayofweek)
        inicio_mes = hoje.replace(day=1)
        
        fat_dia = df[df['data_programacao'] == hoje]['valor_frete'].sum()
        fat_semana = df[df['data_programacao'] >= inicio_semana]['valor_frete'].sum()
        fat_mes = df[df['data_programacao'] >= inicio_mes]['valor_frete'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento de Hoje", f"R$ {fat_dia:,.2f}")
        m2.metric("Projeção / Semana", f"R$ {fat_semana:,.2f}")
        m3.metric("Projeção / Mês", f"R$ {fat_mes:,.2f}")
        
        st.markdown("---")
        st.subheader("📈 Faturamento por Período")
        fat_diario = df.groupby('data_programacao')['valor_frete'].sum().reset_index()
        st.line_chart(fat_diario.set_index('data_programacao'))
    else:
        st.info("Sem dados financeiros para exibir.")

# --- TELA 4: FROTA & MOTORISTAS ---
elif menu == "🚛 Frota & Motoristas":
    st.title("🚛 Consulta de Motoristas e Conjuntos")
    
    programacoes = get_programacoes()
    if programacoes:
        df = pd.DataFrame(programacoes)
        df_frota = df[[col for col in ["motorista", "placa"] if col in df.columns]].drop_duplicates().dropna(how="all")
        busca = st.text_input("🔍 Buscar Motorista ou Placa")
        
        if busca:
            df_frota = df_frota[
                df_frota.get("motorista", pd.Series("", index=df_frota.index)).astype(str).str.contains(busca, case=False, na=False)
                | df_frota.get("placa", pd.Series("", index=df_frota.index)).astype(str).str.contains(busca, case=False, na=False)
            ]
        st.table(df_frota)
    else:
        st.info("Nenhum motorista ou veículo localizado.")