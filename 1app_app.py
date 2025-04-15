import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ========== CONFIGURAÇÕES INICIAIS ==========
st.set_page_config(
    page_title="Unifolhas",
    page_icon="🌿",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: scale(1.05);
    }
    .stAlert { border-left: 4px solid #4CAF50; }
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        transition: all 0.3s;
    }
    .product-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-5px);
    }
    .login-section {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .carrinho-item {
        border-bottom: 1px solid #eee;
        padding: 8px 0;
    }
    .carrinho-total {
        font-weight: bold;
        font-size: 1.1em;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ========== BANCO DE DADOS SQLite ==========
def init_db():
    conn = sqlite3.connect('unifolhas.db')
    c = conn.cursor()

    # Tabela de vendas
    c.execute('''CREATE TABLE IF NOT EXISTS vendas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  Produto TEXT,
                  Quantidade INTEGER,
                  Preço REAL,
                  Subtotal REAL,
                  Usuario TEXT,
                  Data TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Tabela de usuários
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT UNIQUE,
                  email TEXT,
                  favoritos TEXT)''')

    # Tabela de produtos
    c.execute('''CREATE TABLE IF NOT EXISTS produtos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  Nome TEXT,
                  Preço REAL,
                  Estoque INTEGER,
                  Categoria TEXT,
                  Descricao TEXT,
                  Imagem TEXT)''')

    # Inserir produtos de exemplo se a tabela estiver vazia
    c.execute("SELECT COUNT(*) FROM produtos")
    if c.fetchone()[0] == 0:
        produtos_exemplo = [
            ("Shampoo Sólido", 42.50, 15, "Higiene", "Shampoo livre de sulfatos em barra", "https://via.placeholder.com/300?text=Shampoo"),
            ("Condicionador Natural", 45.75, 20, "Higiene", "Condicionador com óleo de argan", "https://via.placeholder.com/300?text=Condicionador"),
            ("Polpa Hidratante", 56.90, 37, "Tratamento", "Hidratante corporal com manteiga de karité", "https://via.placeholder.com/300?text=Polpa+Hidratante"),
            ("Sabonete Líquido", 47.90, 17, "Higiene", "Sabonete vegano com extrato de camomila", "https://via.placeholder.com/300?text=Sabonete"),
            ("Polpa Esfoliante", 57.10, 28, "Tratamento", "Esfoliante natural com cristais de açúcar", "https://via.placeholder.com/300?text=Polpa+Esfoliante")
        ]
        c.executemany('''INSERT INTO produtos (Nome, Preço, Estoque, Categoria, Descricao, Imagem)
                         VALUES (?, ?, ?, ?, ?, ?)''', produtos_exemplo)

    conn.commit()
    conn.close()

init_db()

# ========== ESTADO DA SESSÃO ==========
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'favoritos' not in st.session_state:
    st.session_state.favoritos = []

# ========== FUNÇÕES AUXILIARES ==========
def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(".", "~").replace(",", ".").replace("~", ",")

def carregar_produtos():
    conn = sqlite3.connect('unifolhas.db')
    produtos = pd.read_sql('''SELECT * FROM produtos''', conn)
    conn.close()
    return produtos

def salvar_favoritos():
    if st.session_state.usuario:
        conn = sqlite3.connect('unifolhas.db')
        fav_str = ','.join(st.session_state.favoritos)
        conn.execute('''INSERT OR REPLACE INTO usuarios (nome, favoritos)
                        VALUES (?, ?)''',
                     (st.session_state.usuario, fav_str))
        conn.commit()
        conn.close()

def carregar_favoritos():
    if st.session_state.usuario:
        conn = sqlite3.connect('unifolhas.db')
        c = conn.cursor()
        c.execute('''SELECT favoritos FROM usuarios WHERE nome = ?''',
                  (st.session_state.usuario,))
        resultado = c.fetchone()
        conn.close()
        if resultado and resultado[0]:
            st.session_state.favoritos = resultado[0].split(',')

def adicionar_ao_carrinho(produto_nome, produto_preco, quantidade=1):
    carrinho = st.session_state.carrinho
    item_existente = next((item for item in carrinho if item["Produto"] == produto_nome), None)

    if item_existente:
        item_existente["Quantidade"] += quantidade
        item_existente["Subtotal"] = item_existente["Quantidade"] * item_existente["Preço"]
    else:
        carrinho.append({
            "Produto": produto_nome,
            "Preço": produto_preco,
            "Quantidade": quantidade,
            "Subtotal": produto_preco * quantidade
        })

    st.success(f"{quantidade}x {produto_nome} adicionado ao carrinho!")
    st.rerun()

def remover_do_carrinho(produto_nome):
    st.session_state.carrinho = [item for item in st.session_state.carrinho if item["Produto"] != produto_nome]
    st.rerun()

def calcular_total_carrinho():
    return sum(item["Subtotal"] for item in st.session_state.carrinho)

def finalizar_compra():
    if not st.session_state.usuario:
        st.error("Por favor, faça login para finalizar a compra")
        return

    conn = sqlite3.connect('unifolhas.db')
    try:
        for item in st.session_state.carrinho:
            conn.execute('''INSERT INTO vendas (Produto, Quantidade, Preço, Subtotal, Usuario)
                           VALUES (?, ?, ?, ?, ?)''',
                        (item["Produto"], item["Quantidade"], item["Preço"],
                         item["Subtotal"], st.session_state.usuario))
        conn.commit()
        st.session_state.carrinho = []
        st.success("Compra finalizada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao finalizar compra: {e}")
    finally:
        conn.close()
    st.rerun()

# ========== BARRA LATERAL ==========
with st.sidebar:
    st.markdown('<div class="login-section">', unsafe_allow_html=True)
    st.markdown("## Entrar")

    if st.session_state.usuario:
        st.success(f"Logado como: {st.session_state.usuario}")
        if st.button("Sair"):
            salvar_favoritos()
            st.session_state.usuario = None
            st.session_state.carrinho = []
            st.rerun()
    else:
        usuario = st.text_input("Nome de usuário")
        email = st.text_input("E-mail")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Entrar"):
                if usuario.strip() and len(usuario) >= 3:
                    st.session_state.usuario = usuario
                    carregar_favoritos()
                    st.rerun()
                else:
                    st.error("Nome inválido (mín. 3 caracteres)")
        with col2:
            if st.button("Cadastrar"):
                if usuario.strip() and len(usuario) >= 3 and "@" in email:
                    conn = sqlite3.connect('unifolhas.db')
                    conn.execute('''INSERT OR IGNORE INTO usuarios (nome, email)
                                    VALUES (?, ?)''', (usuario, email))
                    conn.commit()
                    conn.close()
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Dados inválidos para cadastro")

    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.header("🌿 Navegação")
    pagina = st.radio("Menu", ["🏠 Home", "📦 Catálogo", "👤 Perfil", "📊 Dashboard"])

    st.divider()
    st.header(f"🛒 Carrinho ({len(st.session_state.carrinho)})")

    if st.session_state.carrinho:
        for item in st.session_state.carrinho:
            col1, col2 = st.columns([4,1])
            with col1:
                st.markdown(f"**{item['Produto']}**")
                st.markdown(f"{item['Quantidade']} x {formatar_moeda(item['Preço'])} = {formatar_moeda(item['Subtotal'])}")
            with col2:
                if st.button("❌", key=f"rem_{item['Produto']}"):
                    remover_do_carrinho(item['Produto'])

        st.markdown("---")
        st.markdown(f"**Total:** {formatar_moeda(calcular_total_carrinho())}", unsafe_allow_html=True)

        if st.button("Finalizar Compra", type="primary", use_container_width=True):
            finalizar_compra()
    else:
        st.info("Carrinho vazio")

# ========== PÁGINA: HOME ==========
if pagina == "🏠 Home":
    # Banner principal
    st.image("https://via.placeholder.com/1200x400?text=Bem-vindo+à+Unifolhas",
             use_column_width=True)

    # Mensagem de boas-vindas
    st.markdown("""
    <div style="text-align: center; margin: 40px 0;">
        <h1 style="color: #2e8b57;">🌿 Unifolhas Cosméticos Naturais</h1>
        <h3 style="color: #555;">Produtos naturais feitos com amor e cuidado com o meio ambiente</h3>
    </div>
    """, unsafe_allow_html=True)

    # Destaques
    st.subheader("⭐ Produtos em Destaque", divider="green")

    produtos = carregar_produtos()
    produtos_selecionados = produtos[produtos['Nome'].isin(["Shampoo Sólido", "Condicionador Natural", "Polpa Hidratante"])]

    for _, produto in produtos_selecionados.iterrows():
        with st.container():
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            st.markdown(f"### {produto['Nome']}")
            st.markdown(f"{produto['Descricao']}")
            st.markdown(f"**Preço:** {formatar_moeda(produto['Preço'])}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"🛒 Adicionar", key=f"add_{produto['Nome']}"):
                    adicionar_ao_carrinho(produto['Nome'], produto['Preço'])

            with col2:
                if st.button(f"❤️ Favoritar", key=f"fav_{produto['Nome']}"):
                    if produto['Nome'] not in st.session_state.favoritos:
                        st.session_state.favoritos.append(produto['Nome'])
                        st.toast(f"{produto['Nome']} favoritado!")
                    else:
                        st.warning("Este produto já está nos favoritos")

            st.markdown('</div>', unsafe_allow_html=True)

    # Seção de valores
    st.divider()
    st.subheader("🌱 Nossos Valores", divider="green")

    valores = st.columns(3)
    with valores[0]:
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h3>♻️ Sustentabilidade</h3>
            <p>Embalagens recicláveis e ingredientes biodegradáveis</p>
        </div>
        """, unsafe_allow_html=True)

    with valores[1]:
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h3>🚫 Livre de crueldade</h3>
            <p>Nunca testamos em animais</p>
        </div>
        """, unsafe_allow_html=True)

    with valores[2]:
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h3>🌍 Impacto Local</h3>
            <p>Apoio às comunidades de agricultores</p>
        </div>
        """, unsafe_allow_html=True)

    # Newsletter
    st.divider()
    with st.form("newsletter"):
        st.subheader("📩 Assine nossa newsletter")
        email = st.text_input("Seu e-mail", placeholder="email@exemplo.com", key="email_newsletter")
        if st.form_submit_button("Assinar"):
            st.success("Obrigado por assinar nossa newsletter!")

# ========== PÁGINA: CATÁLOGO ==========
elif pagina == "📦 Catálogo":
    st.title("📦 Catálogo Completo")
    produtos = carregar_produtos()

    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            categoria = st.selectbox("Categoria:", ["Todas"] + list(produtos["Categoria"].unique()))
        with col_f2:
            preco_min, preco_max = st.slider("Faixa de preço:",
                                           float(produtos["Preço"].min()),
                                           float(produtos["Preço"].max()),
                                           (float(produtos["Preço"].min()), float(produtos["Preço"].max())))
        with col_f3:
            ordenacao = st.selectbox("Ordenar por:", ["Padrão", "Preço Crescente", "Preço Decrescente", "Mais Estoque"])

    # Aplicar filtros
    produtos_filtrados = produtos.copy()
    if categoria != "Todas":
        produtos_filtrados = produtos_filtrados[produtos_filtrados["Categoria"] == categoria]
    produtos_filtrados = produtos_filtrados[
        (produtos_filtrados["Preço"] >= preco_min) &
        (produtos_filtrados["Preço"] <= preco_max)
    ]

    # Ordenação
    if ordenacao == "Preço Crescente":
        produtos_filtrados = produtos_filtrados.sort_values("Preço")
    elif ordenacao == "Preço Decrescente":
        produtos_filtrados = produtos_filtrados.sort_values("Preço", ascending=False)
    elif ordenacao == "Mais Estoque":
        produtos_filtrados = produtos_filtrados.sort_values("Estoque", ascending=False)

    # Exibir produtos
    st.subheader(f"🎯 {len(produtos_filtrados)} produtos encontrados")

    for _, produto in produtos_filtrados.iterrows():
        with st.container():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(produto["Imagem"], width=200)

            with col2:
                st.markdown(f"### {produto['Nome']}")
                st.markdown(f"**Categoria:** {produto['Categoria']}")
                st.markdown(f"**Preço:** {formatar_moeda(produto['Preço'])}")
                st.markdown(f"**Estoque:** {produto['Estoque']} unidades")
                st.markdown(f"**Descrição:** {produto['Descricao']}")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    quantidade = st.number_input(f"Qtd {produto['Nome']}",
                                               min_value=1,
                                               max_value=min(10, produto['Estoque']),
                                               value=1,
                                               key=f"qtd_{produto['Nome']}")

                with col_btn2:
                    if st.button(f"🛒 Adicionar", key=f"add_{produto['Nome']}"):
                        adicionar_ao_carrinho(produto['Nome'], produto['Preço'], quantidade)

                if st.button(f"❤️ Favoritar {produto['Nome']}", key=f"fav_{produto['Nome']}"):
                    if produto['Nome'] not in st.session_state.favoritos:
                        st.session_state.favoritos.append(produto['Nome'])
                        st.toast(f"{produto['Nome']} favoritado!")
                    else:
                        st.warning("Este produto já está nos favoritos")

            st.divider()

# ========== PÁGINA: PERFIL ==========
elif pagina == "👤 Perfil":
    if st.session_state.usuario:
        st.title(f"👤 Perfil de {st.session_state.usuario}")

        # Seção de Favoritos
        st.subheader("❤️ Seus Favoritos", divider="green")
        if st.session_state.favoritos:
            produtos = carregar_produtos()
            favoritos_df = produtos[produtos['Nome'].isin(st.session_state.favoritos)]

            if not favoritos_df.empty:
                for _, produto in favoritos_df.iterrows():
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.image(produto["Imagem"], width=100)
                    with col2:
                        st.markdown(f"**{produto['Nome']}**")
                        st.markdown(f"Preço: {formatar_moeda(produto['Preço'])}")

                        if st.button(f"Adicionar ao carrinho", key=f"favcart_{produto['Nome']}"):
                            adicionar_ao_carrinho(produto['Nome'], produto['Preço'])

                        if st.button(f"Remover dos favoritos", key=f"removefav_{produto['Nome']}"):
                            st.session_state.favoritos.remove(produto['Nome'])
                            st.rerun()
                    st.divider()
            else:
                st.info("Nenhum produto favoritado ainda.")
        else:
            st.info("Nenhum produto favoritado ainda.")

        # Histórico de Compras
        st.subheader("📦 Histórico de Compras", divider="green")
        conn = sqlite3.connect('unifolhas.db')
        historico = pd.read_sql('''SELECT Produto, Quantidade, Subtotal, Data
                                  FROM vendas
                                  WHERE Usuario = ?
                                  ORDER BY Data DESC''',
                               conn, params=(st.session_state.usuario,))
        conn.close()

        if not historico.empty:
            # Resumo de compras
            total_gasto = historico["Subtotal"].sum()
            total_itens = historico["Quantidade"].sum()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Gasto", formatar_moeda(total_gasto))
            with col2:
                st.metric("Itens Comprados", total_itens)

            # Gráfico de compras por mês
            historico['Data'] = pd.to_datetime(historico['Data'])
            historico['Mês'] = historico['Data'].dt.to_period('M')
            compras_por_mes = historico.groupby('Mês').agg({'Subtotal': 'sum', 'Quantidade': 'sum'}).reset_index()
            compras_por_mes['Mês'] = compras_por_mes['Mês'].astype(str)

            st.line_chart(compras_por_mes.set_index('Mês')['Subtotal'])

            # Tabela detalhada
            st.dataframe(
                historico,
                column_config={
                    "Data": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                    "Subtotal": st.column_config.NumberColumn(format="R$ %.2f")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Nenhuma compra registrada ainda.")
    else:
        st.warning("🔒 Faça login para acessar seu perfil")

# ========== PÁGINA: DASHBOARD ==========
elif pagina == "📊 Dashboard":
    st.title("📊 Dashboard de Vendas")

    if st.session_state.usuario == "admin":
        conn = sqlite3.connect('unifolhas.db')
        vendas = pd.read_sql('''SELECT * FROM vendas''', conn)
        produtos = pd.read_sql('''SELECT * FROM produtos''', conn)
        conn.close()

        if not vendas.empty:
            # Métricas gerais
            st.subheader("📈 Métricas Gerais", divider="green")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total de Vendas", len(vendas))
            with col2:
                st.metric("Receita Total", formatar_moeda(vendas["Subtotal"].sum()))
            with col3:
                st.metric("Produtos Vendidos", vendas["Quantidade"].sum())
            with col4:
                clientes_unicos = vendas["Usuario"].nunique()
                st.metric("Clientes Únicos", clientes_unicos)

            st.divider()

            # Análise temporal
            st.subheader("🕒 Análise Temporal", divider="green")
            vendas['Data'] = pd.to_datetime(vendas['Data'])
            vendas['Dia'] = vendas['Data'].dt.date

            vendas_por_dia = vendas.groupby('Dia').agg({'Subtotal': 'sum', 'Quantidade': 'sum'}).reset_index()

            tab1, tab2 = st.tabs(["Receita Diária", "Volume de Vendas"])
            with tab1:
                st.area_chart(vendas_por_dia.set_index('Dia')['Subtotal'])
            with tab2:
                st.bar_chart(vendas_por_dia.set_index('Dia')['Quantidade'])

            # Produtos mais vendidos
            st.subheader("🏆 Produtos Mais Vendidos", divider="green")
            top_produtos = vendas.groupby("Produto").agg({
                "Quantidade": "sum",
                "Subtotal": "sum"
            }).nlargest(5, "Quantidade").reset_index()

            col_graf1, col_graf2 = st.columns(2)
            with col_graf1:
                st.bar_chart(top_produtos.set_index("Produto")["Quantidade"])
            with col_graf2:
                st.bar_chart(top_produtos.set_index("Produto")["Subtotal"])

            # Clientes mais ativos
            st.subheader("👥 Clientes Mais Ativos", divider="green")
            top_clientes = vendas.groupby("Usuario").agg({
                "Subtotal": "sum",
                "Quantidade": "sum",
                "id": "count"
            }).rename(columns={"id": "Compras"}).nlargest(5, "Subtotal")

            st.dataframe(
                top_clientes,
                column_config={
                    "Subtotal": st.column_config.NumberColumn(format="R$ %.2f")
                },
                hide_index=True,
                use_container_width=True
            )

            # Dados completos
            st.subheader("📝 Dados Completos", divider="green")
            st.dataframe(
                vendas.merge(produtos, left_on="Produto", right_on="Nome"),
                column_config={
                    "Data": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                    "Preço_x": st.column_config.NumberColumn("Preço Vendido", format="R$ %.2f"),
                    "Preço_y": st.column_config.NumberColumn("Preço Atual", format="R$ %.2f"),
                    "Subtotal": st.column_config.NumberColumn(format="R$ %.2f")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Nenhum dado de vendas disponível ainda.")
    else:
        st.error("🚨 Acesso restrito - apenas administradores podem visualizar esta página")

# ========== RODAPÉ ==========
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em; padding: 20px;">
    Unifolhas Cosméticos Naturais • © 2024 • Fase 5
</div>
""", unsafe_allow_html=True)
