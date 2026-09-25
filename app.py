import json
import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

st.set_page_config(page_title="Petrol Transportes", layout="wide", page_icon="🚛")

LOCAL_DATA_PATH = os.path.join(os.path.dirname(__file__), "local_programacoes.json")
LOCAL_MASTER_DATA_PATH = os.path.join(os.path.dirname(__file__), "local_cadastros.json")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        .stMetric {
            background: linear-gradient(135deg, #111827, #1f2937);
            border-radius: 12px;
            padding: 12px;
            border: 1px solid #374151;
            box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        }
        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a, #111827);
        }
        div[data-testid="stFormSubmitButton"] button {
            background: linear-gradient(90deg, #f59e0b, #f97316);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
        }
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
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


def normalize_programacoes(raw_list):
    if not isinstance(raw_list, list):
        return []

    dados = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        registro = {**item}
        registro.setdefault("data_programacao", str(datetime.date.today()))
        registro.setdefault("data_entrega", str(datetime.date.today()))
        registro.setdefault("numero_pedido", "")
        registro.setdefault("cliente", "")
        registro.setdefault("origem", "")
        registro.setdefault("destino", "")
        registro.setdefault("rota", "")
        registro.setdefault("motorista", "")
        registro.setdefault("placa", "")
        registro.setdefault("tipo_produto", "Outros")
        registro.setdefault("tipo_carga", "Carga geral")
        registro.setdefault("quantidade", 0)
        registro.setdefault("valor_frete", 0)
        registro.setdefault("valor_diaria", 0)
        registro.setdefault("status", "Programado")
        registro.setdefault("usuario_lancamento", usuario_atual)
        registro.setdefault("observacoes", "")
        registro["valor_frete"] = float(registro.get("valor_frete", 0) or 0)
        registro["valor_diaria"] = float(registro.get("valor_diaria", 0) or 0)
        registro["quantidade"] = float(registro.get("quantidade", 0) or 0)
        if not registro.get("rota") and registro.get("origem") and registro.get("destino"):
            registro["rota"] = f"{registro.get('origem')} x {registro.get('destino')}"
        dados.append(registro)
    return dados


def get_programacoes():
    if supabase is None:
        dados = get_local_programacoes()
        return normalize_programacoes(dados)
    try:
        res = supabase.table("programacoes").select("*").execute()
        return normalize_programacoes(res.data or [])
    except Exception:
        st.warning("Não foi possível acessar o Supabase; usando dados locais da sessão.")
        return normalize_programacoes(get_local_programacoes())


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


def get_master_data(chave, padrao=None):
    if os.path.exists(LOCAL_MASTER_DATA_PATH):
        try:
            with open(LOCAL_MASTER_DATA_PATH, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            if isinstance(dados, dict) and chave in dados:
                return dados[chave]
        except Exception:
            pass
    if padrao is None:
        return []
    return padrao


def save_master_data(chave, valor):
    try:
        dados = {}
        if os.path.exists(LOCAL_MASTER_DATA_PATH):
            with open(LOCAL_MASTER_DATA_PATH, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo) or {}
        dados[chave] = valor
        with open(LOCAL_MASTER_DATA_PATH, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


if supabase is None:
    st.warning("Modo local ativado: configure as chaves do Supabase para salvar em nuvem. Os dados ficam apenas nesta sessão.")

st.sidebar.title("🚛 Petrol Transportes")
usuario_atual = st.sidebar.text_input("Seu Nome / Usuário", value="Operador")

menu = st.sidebar.radio("Navegação", [
    "🏠 Visão Geral",
    "📝 Lançar Pedidos", 
    "📊 Programação & Relatórios", 
    "💰 Faturamento & Projeções",
    "📋 Cadastros",
    "🚛 Frota & Motoristas"
])

# --- TELA 0: VISÃO GERAL ---
if menu == "🏠 Visão Geral":
    st.title("🚛 Petrol Transportes")
    st.caption("Operações, programação e faturamento em um só painel")

    programacoes = get_programacoes()
    if programacoes:
        df = pd.DataFrame(programacoes)
        if "valor_frete" in df.columns:
            df["valor_frete"] = pd.to_numeric(df["valor_frete"], errors="coerce").fillna(0)
        else:
            df["valor_frete"] = 0
        if "status" in df.columns:
            df["status"] = df["status"].fillna("Programado")
        else:
            df["status"] = "Programado"

        hoje = pd.Timestamp(datetime.date.today())
        qtd_total = len(df)
        qtd_programado = int((df["status"] == "Programado").sum())
        qtd_transito = int((df["status"] == "Em Trânsito").sum())
        faturamento_total = float(df["valor_frete"].sum())
        media_valor = float(df["valor_frete"].mean()) if not df.empty else 0.0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pedidos", qtd_total)
        c2.metric("Programados", qtd_programado)
        c3.metric("Em trânsito", qtd_transito)
        c4.metric("Faturamento", f"R$ {faturamento_total:,.2f}")

        st.markdown("---")
        st.subheader("📌 Visão rápida")
        resumos = pd.DataFrame({
            "Indicador": ["Pedidos ativos", "Valor médio", "Motoristas", "Rotas"],
            "Valor": [
                qtd_total,
                f"R$ {media_valor:,.2f}",
                df["motorista"].nunique() if "motorista" in df.columns else 0,
                df["rota"].nunique() if "rota" in df.columns else 0,
            ]
        })
        st.dataframe(resumos, use_container_width=True, hide_index=True)

        st.subheader("📊 Faturamento por status")
        st.bar_chart(df.groupby("status")["valor_frete"].sum())
    else:
        st.info("Ainda não há pedidos cadastrados. Comece pelo menu de lançamento.")

# --- TELA 1: CADASTROS BASE ---
elif menu == "📋 Cadastros":
    st.title("📋 Cadastro de Rotas, Preços e Frota")

    rotas = get_master_data("rotas", [])
    precos = get_master_data("precos", [])
    motoristas = get_master_data("motoristas", [])
    veiculos = get_master_data("veiculos", [])

    tab_rotas, tab_precos, tab_motoristas, tab_veiculos = st.tabs(["Rotas", "Tabela de Preços", "Motoristas", "Placas / Carretas"])

    with tab_rotas:
        st.subheader("Cadastrar rota")
        with st.form("form_rota", clear_on_submit=True):
            origem = st.text_input("Origem")
            destino = st.text_input("Destino")
            km = st.number_input("Distância (km)", min_value=0, step=10)
            tempo_estimado = st.number_input("Tempo estimado (h)", min_value=0, step=1)
            valor_base = st.number_input("Valor base (R$)", min_value=0.0, step=50.0)
            submitted = st.form_submit_button("💾 Salvar rota")
            if submitted and origem and destino:
                rota = {
                    "origem": origem,
                    "destino": destino,
                    "km": int(km),
                    "tempo_estimado": int(tempo_estimado),
                    "valor_base": float(valor_base),
                    "rota": f"{origem} x {destino}"
                }
                rotas.append(rota)
                save_master_data("rotas", rotas)
                st.success("Rota salva com sucesso!")

        if rotas:
            st.dataframe(pd.DataFrame(rotas), use_container_width=True)

    with tab_precos:
        st.subheader("Cadastrar tabela de preços")
        with st.form("form_precos", clear_on_submit=True):
            produto = st.selectbox("Produto", ["Combustível", "Etanol", "Diesel", "Gasolina", "Outros"])
            tipo = st.selectbox("Tipo", ["Frete por KM", "Frete por viagem", "Diária", "Adicional"])
            valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            unidade = st.text_input("Unidade / Observação", value="KM")
            submitted = st.form_submit_button("💾 Salvar preço")
            if submitted:
                precos.append({
                    "produto": produto,
                    "tipo": tipo,
                    "valor": float(valor),
                    "unidade": unidade
                })
                save_master_data("precos", precos)
                st.success("Tabela de preços salva!")
        if precos:
            st.dataframe(pd.DataFrame(precos), use_container_width=True)

    with tab_motoristas:
        st.subheader("Cadastrar motorista")
        with st.form("form_motorista", clear_on_submit=True):
            nome = st.text_input("Nome do motorista")
            cnh = st.text_input("CNH / Registro")
            telefone = st.text_input("Telefone")
            status = st.selectbox("Status", ["Ativo", "Folga", "Férias", "Inativo"])
            submitted = st.form_submit_button("💾 Salvar motorista")
            if submitted and nome:
                motoristas.append({
                    "nome": nome,
                    "cnh": cnh,
                    "telefone": telefone,
                    "status": status,
                })
                save_master_data("motoristas", motoristas)
                st.success("Motorista salvo com sucesso!")
        if motoristas:
            st.dataframe(pd.DataFrame(motoristas), use_container_width=True)

    with tab_veiculos:
        st.subheader("Cadastrar placa / carreta")
        with st.form("form_veiculo", clear_on_submit=True):
            placa = st.text_input("Placa")
            tipo = st.selectbox("Tipo", ["Caminhão", "Carreta", "Bitruck", "Truck", "Outro"])
            marca = st.text_input("Marca")
            modelo = st.text_input("Modelo")
            status = st.selectbox("Status", ["Disponível", "Em operação", "Manutenção", "Inativo"])
            submitted = st.form_submit_button("💾 Salvar veículo")
            if submitted and placa:
                veiculos.append({
                    "placa": placa,
                    "tipo": tipo,
                    "marca": marca,
                    "modelo": modelo,
                    "status": status,
                })
                save_master_data("veiculos", veiculos)
                st.success("Veículo cadastrado com sucesso!")
        if veiculos:
            st.dataframe(pd.DataFrame(veiculos), use_container_width=True)

# --- TELA 1: LANÇAR PEDIDOS ---
elif menu == "📝 Lançar Pedidos":
    st.title("📝 Lançamento de Pedidos")
    st.caption(f"Registrando como: **{usuario_atual}**")
    
    rotas_cadastradas = get_master_data("rotas", [])
    motoristas_cadastrados = get_master_data("motoristas", [])
    veiculos_cadastrados = get_master_data("veiculos", [])
    precos_cadastrados = get_master_data("precos", [])

    with st.form("form_pedido", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_prog = st.date_input("Data da Programação", datetime.date.today())
            data_entrega = st.date_input("Data de Entrega / Destino", datetime.date.today())
            no_pedido = st.text_input("Nº do Pedido / Carga")
            cliente = st.text_input("Cliente")
        with col2:
            origem = st.text_input("Origem")
            destino = st.text_input("Destino")
            rotas_opcoes = [r.get("rota") or f"{r.get('origem')} x {r.get('destino')}" for r in rotas_cadastradas]
            rota_padrao = f"{origem} x {destino}".strip(" x ")
            rota = st.selectbox("Rota cadastrada", ["Personalizada"] + rotas_opcoes, index=(0 if rota_padrao == "" else 0))
            if rota == "Personalizada":
                rota = st.text_input("Rota (Origem x Destino)", value=rota_padrao)
            motorista = st.selectbox("Nome do Motorista", [m.get("nome") for m in motoristas_cadastrados] or [""], index=0)
        with col3:
            placa = st.selectbox("Placa / Conjunto", [v.get("placa") for v in veiculos_cadastrados] or [""], index=0)
            tipo_produto = st.selectbox("Tipo de Produto", ["Combustível", "Etanol", "Diesel", "Gasolina", "Outros"])
            tipo_carga = st.selectbox("Tipo de Carga", ["Carga geral", "Combustível", "Etanol", "Diesel", "Gasolina", "Produtos"])
            quantidade = st.number_input("Quantidade / Volume", min_value=0.0, step=100.0)
            valor_padrao = 0.0
            if precos_cadastrados:
                valor_padrao = float(precos_cadastrados[0].get("valor", 0.0))
            valor_frete = st.number_input("Valor do Frete / Faturamento (R$)", min_value=0.0, step=100.0, value=valor_padrao)
            valor_diaria = st.number_input("Valor da Diária (R$)", min_value=0.0, step=50.0)
            
        status = st.selectbox("Status", ["Programado", "Em Trânsito", "Concluído", "Cancelado"])
        obs = st.text_area("Observações")
        
        btn_salvar = st.form_submit_button("💾 Salvar Pedido")
        
        if btn_salvar:
            if not no_pedido or not motorista or not placa:
                st.warning("Preencha ao menos Pedido, Motorista e Placa!")
            else:
                rota_final = rota or f"{origem} x {destino}".strip(" x ")
                novo_dado = {
                    "usuario_lancamento": usuario_atual,
                    "data_programacao": str(data_prog),
                    "data_entrega": str(data_entrega),
                    "numero_pedido": no_pedido,
                    "cliente": cliente,
                    "origem": origem,
                    "destino": destino,
                    "rota": rota_final,
                    "motorista": motorista,
                    "placa": placa,
                    "tipo_produto": tipo_produto,
                    "tipo_carga": tipo_carga,
                    "quantidade": quantidade,
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

        filtro_data = st.date_input(
            "Filtrar por data da programação",
            value=(pd.to_datetime(df["data_programacao"]).min().date(), pd.to_datetime(df["data_programacao"]).max().date()),
            min_value=pd.to_datetime(df["data_programacao"]).min().date() if not df.empty else datetime.date.today(),
            max_value=pd.to_datetime(df["data_programacao"]).max().date() if not df.empty else datetime.date.today(),
        )
            
        df_filtrado = df.copy()
        if isinstance(filtro_data, tuple) and len(filtro_data) == 2:
            data_ini, data_fim = filtro_data
            df_filtrado = df_filtrado[
                df_filtrado["data_programacao"].apply(lambda x: str(x)[:10] if isinstance(x, str) else str(pd.Timestamp(x).date()))
                .between(str(data_ini), str(data_fim))
            ]
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
            "data_programacao", "data_entrega", "numero_pedido", "cliente",
            "origem", "destino", "rota", "motorista", "placa",
            "tipo_produto", "tipo_carga", "quantidade", "valor_frete",
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
                    edit_cliente = st.text_input("Cliente", value=str(registro.get("cliente", "")))
                with col_b:
                    edit_placa = st.text_input("Placa", value=str(registro.get("placa", "")))
                    edit_status = st.selectbox("Status", ["Programado", "Em Trânsito", "Concluído", "Cancelado"], index=["Programado", "Em Trânsito", "Concluído", "Cancelado"].index(str(registro.get("status", "Programado"))))
                    edit_origem = st.text_input("Origem", value=str(registro.get("origem", "")))
                with col_c:
                    edit_valor = st.number_input("Valor do Frete", min_value=0.0, value=float(registro.get("valor_frete", 0.0)))
                    edit_destino = st.text_input("Destino", value=str(registro.get("destino", "")))
                    edit_quantidade = st.number_input("Quantidade", min_value=0.0, value=float(registro.get("quantidade", 0.0)))

                if st.form_submit_button("💾 Salvar alterações"):
                    update_programacao(df.index.get_loc(df_filtrado.index[selected_index]), {
                        "numero_pedido": edit_numero,
                        "motorista": edit_motorista,
                        "placa": edit_placa,
                        "status": edit_status,
                        "valor_frete": edit_valor,
                        "cliente": edit_cliente,
                        "origem": edit_origem,
                        "destino": edit_destino,
                        "quantidade": edit_quantidade,
                        "rota": f"{edit_origem} x {edit_destino}".strip(" x ")
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
    motoristas_cadastrados = get_master_data("motoristas", [])
    veiculos_cadastrados = get_master_data("veiculos", [])

    if programacoes or motoristas_cadastrados or veiculos_cadastrados:
        df = pd.DataFrame(programacoes)
        df_frota = df[[col for col in ["motorista", "placa"] if col in df.columns]].drop_duplicates().dropna(how="all")
        if motoristas_cadastrados:
            df_motoristas = pd.DataFrame(motoristas_cadastrados)
            df_frota = pd.concat([df_frota, df_motoristas[["nome"]].rename(columns={"nome": "motorista"})], ignore_index=True) if "motorista" in df_frota.columns else pd.concat([pd.DataFrame(columns=["motorista", "placa"]), df_motoristas[["nome"]].rename(columns={"nome": "motorista"})], ignore_index=True)
        if veiculos_cadastrados:
            df_veiculos = pd.DataFrame(veiculos_cadastrados)
            df_frota = pd.concat([df_frota, df_veiculos[["placa"]].assign(motorista="")], ignore_index=True)

        busca = st.text_input("🔍 Buscar Motorista ou Placa")
        if busca:
            df_frota = df_frota[
                df_frota.get("motorista", pd.Series("", index=df_frota.index)).astype(str).str.contains(busca, case=False, na=False)
                | df_frota.get("placa", pd.Series("", index=df_frota.index)).astype(str).str.contains(busca, case=False, na=False)
            ]
        st.table(df_frota.drop_duplicates().reset_index(drop=True))
    else:
        st.info("Nenhum motorista ou veículo localizado.")