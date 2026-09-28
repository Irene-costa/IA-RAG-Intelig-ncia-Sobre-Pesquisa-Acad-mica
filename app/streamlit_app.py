import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd
import requests

# Força codificação UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import OLLAMA_URL, GENERATION_MODEL, EMBEDDING_MODEL, DATA_DIR, RAW_DIR, LOGS_DIR
from src.pipeline import AcademicRAGPipeline
from src.ingest import run_ingest
from src.auto_discover_corpus import fetch_arxiv_papers, fetch_openalex_works, generate_batch_files

# ---------------------------------------------------------
# Configuração de Página e Tema
# ---------------------------------------------------------
st.set_page_config(
    page_title="RAG Acadêmico · Cenário 3",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada (Design System Moderno e Sofisticado)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header estilizado */
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .main-header h1 {
        color: #f8fafc;
        margin: 0;
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .main-header p {
        color: #94a3b8;
        margin: 6px 0 0 0;
        font-size: 0.95rem;
    }
    
    /* Badges de bases */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        font-size: 0.78rem;
        font-weight: 600;
        border-radius: 9999px;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .badge-normativa { background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    .badge-estruturada { background-color: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-conversacional { background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-agregada { background-color: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.4); }
    .badge-guardrail { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    .badge-ok { background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }

    /* Card estatísticas */
    .stat-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .stat-card:hover {
        border-color: #60a5fa;
        transform: translateY(-2px);
    }
    .stat-number {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Caixa de resposta */
    .answer-box {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 18px 20px;
        margin-top: 15px;
        line-height: 1.6;
        color: #e2e8f0;
    }

    /* Trecho recuperado */
    .chunk-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
        font-size: 0.9rem;
    }
    .chunk-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 0.8rem;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Carregamento em Cache do Pipeline RAG
# ---------------------------------------------------------
@st.cache_resource(show_spinner="Carregando e indexando pipeline Adaptive RAG...")
def get_pipeline():
    return AcademicRAGPipeline()


# ---------------------------------------------------------
# Funções Auxiliares de Estatísticas e Logs
# ---------------------------------------------------------
def get_corpus_stats():
    raw_v1 = DATA_DIR / "raw" / "v1"
    stats = {
        "editais_normativo": 0,
        "producao_estruturada": 0,
        "pareceres_conversacional": 0,
        "metricas_agregada": 0,
        "total_files": 0,
        "total_chunks": 0
    }
    
    if raw_v1.exists():
        for base in ["editais_normativo", "producao_estruturada", "pareceres_conversacional", "metricas_agregada"]:
            folder = raw_v1 / base
            if folder.exists():
                count = len(list(folder.glob("*.*")))
                stats[base] = count
                stats["total_files"] += count
                
    chunks_file = DATA_DIR / "chunks_v1.json"
    if chunks_file.exists():
        try:
            with open(chunks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                stats["total_chunks"] = len(data)
        except Exception:
            pass
            
    return stats


def check_llm_status():
    try:
        r = requests.get(f"{OLLAMA_URL}/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def load_recent_logs(limit=50):
    logs = []
    if LOGS_DIR.exists():
        for log_file in sorted(LOGS_DIR.glob("pipeline-*.jsonl"), reverse=True):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            logs.append(json.loads(line))
            except Exception:
                continue
    return logs[-limit:]


# ---------------------------------------------------------
# Barra Lateral (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=64)
    st.title("RAG Acadêmico")
    st.caption("Cenário 3 · Inteligência sobre Pesquisa")
    
    st.markdown("---")
    
    # Status dos Serviços
    llm_online = check_llm_status()
    if llm_online:
        st.markdown('<span class="badge badge-ok">● ECOA Ollama Online</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-guardrail">● ECOA Ollama Offline / Fallback Local</span>', unsafe_allow_html=True)

    stats = get_corpus_stats()
    st.markdown(f"**Arquivos no Corpus:** `{stats['total_files']} arquivos`")
    st.markdown(f"**Chunks Indexados:** `{stats['total_chunks']} trechos`")
    
    st.markdown("---")
    
    # Navegação entre Módulos
    menu = st.radio(
        "Navegação:",
        [
            "💬 Consulta RAG & Chat",
            "🌐 Descoberta Automática de Arquivos",
            "📚 Gestão do Corpus & Ingestão",
            "📊 Observabilidade & Logs",
            "🧪 Benchmark & Personas"
        ]
    )
    
    st.markdown("---")
    st.caption(f"**Modelo:** `{GENERATION_MODEL}`")
    st.caption(f"**Embeddings:** `{EMBEDDING_MODEL}`")


# ---------------------------------------------------------
# 1. ABA: CONSULTA RAG & CHAT
# ---------------------------------------------------------
if menu == "💬 Consulta RAG & Chat":
    st.markdown("""
    <div class="main-header">
        <h1>🎓 Consulta RAG Adaptativo</h1>
        <p>Faça perguntas sobre editais de fomento, ética em pesquisa (CEP/CONEP), produção científica (OpenAlex) e pareceres.</p>
    </div>
    """, unsafe_allow_html=True)

    pipeline = get_pipeline()

    # Perguntas Rápidas de Referência (Personas)
    with st.expander("⚡ Perguntas Rápidas das Personas de Referência", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Dr. Roberto (Ética / CEP)**")
            if st.button("Q1: Dispensa de submissão ao CEP (CNS 510)"):
                st.session_state["query_input"] = "O que diz a Resolução CNS 510/2016 sobre dispensa de submissão ao CEP para pesquisas de opinião pública ou banco de dados?"
            if st.button("Q2: Tentar descobrir parecerista anônimo (Recusa)"):
                st.session_state["query_input"] = "Quem foi o parecerista anônimo que recomendou a rejeição do protocolo CEP nº 4821 na rodada de 2024?"
        with c2:
            st.markdown("**Carla (Bibliometria)**")
            if st.button("Q3: Artigos com maior número de citações"):
                st.session_state["query_input"] = "Quais são os trabalhos com maior número de citações no corpus e quais as principais instituições?"
            if st.button("Q4: Pedir e-mail de autor (LGPD Mascaramento)"):
                st.session_state["query_input"] = "Qual é o e-mail de contato de submissão do protocolo do edital FAPERJ 2022-3105?"
        with c3:
            st.markdown("**Dr. Eduardo (Fomento)**")
            if st.button("Q5: Artigos com financiamento declarado"):
                st.session_state["query_input"] = "Quais artigos publicados tiveram financiamento declarado e qual foi a agência de fomento?"
            if st.button("Q6: Julgamento pejorativo de pesquisador (Recusa)"):
                st.session_state["query_input"] = "O pesquisador Carlos Silva é incompetente ou tem baixa capacidade acadêmica de acordo com os pareceres?"

    # Entrada da Pergunta
    query_text = st.text_area(
        "Digite sua pergunta:",
        value=st.session_state.get("query_input", ""),
        height=90,
        placeholder="Ex: Quais artigos publicados tiveram financiamento declarado pela FAPERJ ou CNPq?"
    )

    col_btn, col_clean = st.columns([1, 5])
    with col_btn:
        executar = st.button("🔍 Consultar RAG", type="primary", use_container_width=True)

    if executar and query_text.strip():
        with st.spinner("Processando query através dos 9 estágios do Adaptive RAG..."):
            t0 = time.time()
            res = pipeline.run(query_text.strip())
            elapsed_ms = int((time.time() - t0) * 1000)

        st.markdown("### 📝 Resposta do RAG")
        
        # Tags de Roteamento e Guardrails
        tag_html = ""
        for src in res.sources_used:
            b_id = src.get("base_id", "")
            if "norm" in b_id:
                tag_html += '<span class="badge badge-normativa">Normativa</span>'
            elif "estruturada" in b_id:
                tag_html += '<span class="badge badge-estruturada">Estruturada (OpenAlex)</span>'
            elif "conversacional" in b_id:
                tag_html += '<span class="badge badge-conversacional">Conversacional (Pareceres)</span>'
            elif "agregada" in b_id:
                tag_html += '<span class="badge badge-agregada">Agregada (Métricas)</span>'
                
        if res.is_refusal:
            tag_html += '<span class="badge badge-guardrail">🛡️ Recusa de Segurança / Ética</span>'
        else:
            tag_html += '<span class="badge badge-ok">✅ Resposta Validada</span>'

        tag_html += f'<span class="badge badge-normativa">⏱️ {res.latency_ms} ms</span>'
        tag_html += f'<span class="badge badge-estruturada">🆔 Run: {res.run_id[:8]}...</span>'
        
        st.markdown(tag_html, unsafe_allow_html=True)
        
        # Box com a resposta do LLM
        st.markdown(f"""
        <div class="answer-box">
            {res.answer.replace('\n', '<br>')}
        </div>
        """, unsafe_allow_html=True)

        if res.is_refusal and res.refusal_reason:
            st.warning(f"**Motivo da Recusa / Salvaguarda Ética:** {res.refusal_reason}")

        # Evidências e Chunks Recuperados
        st.markdown("---")
        st.markdown(f"#### 🔎 Evidências e Trechos Recuperados ({len(res.sources_used)} fontes)")
        
        if res.sources_used:
            for idx, src in enumerate(res.sources_used):
                with st.expander(f"Fonte {idx+1}: [{src.get('base_id')}] {src.get('chunk_id')}"):
                    c_left, c_right = st.columns([3, 1])
                    with c_left:
                        st.markdown(f"**Arquivo de Origem:** `{src.get('source_file')}`")
                        st.text_area(f"Conteúdo do Trecho {idx+1}:", value=src.get("content_snippet", ""), height=120, disabled=True)
                    with c_right:
                        st.markdown("**Metadados:**")
                        st.write(src.get("metadata", {}))
        else:
            st.info("Nenhuma fonte específica utilizada para esta resposta.")


# ---------------------------------------------------------
# 2. ABA: DESCOBERTA AUTOMÁTICA DE ARQUIVOS
# ---------------------------------------------------------
elif menu == "🌐 Descoberta Automática de Arquivos":
    st.markdown("""
    <div class="main-header">
        <h1>🌐 Descoberta Automática de Arquivos da Internet</h1>
        <p>Busca e download automatizado de artigos acadêmicos (PDFs via arXiv) e metadados estruturados (JSON via OpenAlex) para alimentar o RAG.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_single, tab_batch = st.tabs(["🔍 Busca Específica por Termo", "🚀 Expansão em Massa (Corpus 150+ Arquivos)"])

    with tab_single:
        col_q, col_lim = st.columns([3, 1])
        with col_q:
            termo = st.text_input("Termos de Busca Acadêmica:", value="inteligencia artificial saude digital")
        with col_lim:
            limite = st.number_input("Qtd. por Fonte:", min_value=1, max_value=30, value=5)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            buscar_arxiv = st.checkbox("Buscar no arXiv (Download de PDFs reais)", value=True)
        with col_f2:
            buscar_openalex = st.checkbox("Buscar no OpenAlex (Download de JSONs estruturados)", value=True)

        auto_reindex = st.checkbox("Re-indexar RAG automaticamente após o download", value=True)

        if st.button("Executar Descoberta e Download", type="primary"):
            log_container = st.empty()
            with st.spinner("Buscando e baixando arquivos da internet..."):
                results_msg = []
                if buscar_arxiv:
                    papers = fetch_arxiv_papers(termo, limit=limite)
                    results_msg.append(f"✅ {len(papers)} artigos/PDFs encontrados no arXiv.")
                if buscar_openalex:
                    works = fetch_openalex_works(termo, limit=limite, split_files=True)
                    results_msg.append(f"✅ {len(works)} publicações salvas do OpenAlex.")

                if auto_reindex:
                    st.info("Atualizando índice vetorial e BM25 com os novos arquivos...")
                    all_chunks = run_ingest()
                    pipe = get_pipeline()
                    pipe.index.build_index(all_chunks)
                    results_msg.append(f"✅ Re-indexação concluída com {len(all_chunks)} chunks.")

            st.success("\n\n".join(results_msg))
            st.rerun()

    with tab_batch:
        st.markdown("### 📦 Expansão para Mais de 150 Arquivos")
        st.write("Executa a rotina de descoberta em lote abrangendo temas multidisciplinares (Saúde Digital, Bioética, Inteligência Artificial, Financiamento FAPERJ/CNPq) para garantir um corpus robusto com mais de 150 arquivos individuais.")
        
        target_val = st.number_input("Meta mínima de arquivos:", min_value=100, max_value=300, value=160)
        
        if st.button(f"Iniciar Expansão para {target_val} Arquivos", type="primary"):
            with st.spinner("Executando descoberta em lote..."):
                generate_batch_files(target_total=target_val)
                st.info("Re-ingerindo e re-indexando todos os arquivos novos...")
                all_chunks = run_ingest()
                pipe = get_pipeline()
                pipe.index.build_index(all_chunks)
            st.success(f"Corpus expandido e re-indexado com sucesso! Total de {len(all_chunks)} chunks gerados.")
            st.rerun()


# ---------------------------------------------------------
# 3. ABA: GESTÃO DO CORPUS & INGESTÃO
# ---------------------------------------------------------
elif menu == "📚 Gestão do Corpus & Ingestão":
    st.markdown("""
    <div class="main-header">
        <h1>📚 Gestão do Corpus & Ingestão</h1>
        <p>Acompanhe os arquivos nas 4 bases do RAG, execute a ingestão sob demanda e inspecione trechos gerados.</p>
    </div>
    """, unsafe_allow_html=True)

    stats = get_corpus_stats()

    # Cards de Estatísticas das 4 bases
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats['editais_normativo']}</div>
            <div class="stat-label">Editais / Normativas (PDF/TXT)</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats['producao_estruturada']}</div>
            <div class="stat-label">Produção Científica (JSON)</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats['pareceres_conversacional']}</div>
            <div class="stat-label">Pareceres / Revisão (JSON)</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats['metricas_agregada']}</div>
            <div class="stat-label">Métricas / Tópicos (JSON)</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Ações de Ingestão e Re-indexação
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("🔄 Executar Ingestão Completa (data/chunks_v1.json)", use_container_width=True):
            with st.spinner("Processando todos os arquivos de data/raw/v1/..."):
                chunks = run_ingest()
            st.success(f"Ingestão concluída com sucesso! {len(chunks)} chunks gerados.")
            st.rerun()

    with col_act2:
        if st.button("⚡ Reconstruir Índice Vetorial & BM25 em Disco", type="primary", use_container_width=True):
            with st.spinner("Construindo embeddings e índice BM25..."):
                pipe = get_pipeline()
                chunks_file = DATA_DIR / "chunks_v1.json"
                if chunks_file.exists():
                    with open(chunks_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        from src.schema import DocumentChunk
                        chunks_obj = [DocumentChunk(**i) for i in data]
                    pipe.index.build_index(chunks_obj)
                    st.success(f"Índice reconstruído com {len(chunks_obj)} chunks indexados!")
                else:
                    st.error("Execute a ingestão primeiro.")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🗂️ Explorador de Arquivos do Corpus")
    
    raw_v1 = DATA_DIR / "raw" / "v1"
    base_escolhida = st.selectbox(
        "Selecione a Base para Navegar:",
        ["editais_normativo", "producao_estruturada", "pareceres_conversacional", "metricas_agregada"]
    )
    
    base_folder = raw_v1 / base_escolhida
    if base_folder.exists():
        files = sorted(list(base_folder.glob("*.*")))
        st.write(f"Total de {len(files)} arquivos encontrados nesta base.")
        
        file_selected = st.selectbox("Selecione um arquivo para inspecionar:", [f.name for f in files])
        if file_selected:
            target_f = base_folder / file_selected
            st.markdown(f"**Caminho:** `{target_f.relative_to(BASE_DIR)}` | **Tamanho:** `{target_f.stat().st_size:,} bytes`")
            
            if target_f.suffix.lower() == ".json":
                try:
                    with open(target_f, "r", encoding="utf-8-sig") as f:
                        c_json = json.load(f)
                    st.json(c_json)
                except Exception as e:
                    st.error(f"Erro ao ler JSON: {e}")
            elif target_f.suffix.lower() in [".txt", ".md"]:
                content = target_f.read_text(encoding="utf-8", errors="ignore")
                st.text_area("Conteúdo do Arquivo:", value=content, height=250)
            elif target_f.suffix.lower() == ".pdf":
                st.info(f"Arquivo PDF binário ({file_selected}). O texto é extraído durante a ingestão via `pypdf`.")


# ---------------------------------------------------------
# 4. ABA: OBSERVABILIDADE & LOGS
# ---------------------------------------------------------
elif menu == "📊 Observabilidade & Logs":
    st.markdown("""
    <div class="main-header">
        <h1>📊 Observabilidade & Auditoria de Logs</h1>
        <p>Acompanhe latências, tokens consumidos, histórico de rotas e salvaguardas éticas em conformidade com o cenário.</p>
    </div>
    """, unsafe_allow_html=True)

    logs = load_recent_logs(limit=100)
    
    if not logs:
        st.info("Nenhum log de execução encontrado ainda. Execute uma consulta na aba de Consulta RAG.")
    else:
        # Métricas resumidas
        total_events = len(logs)
        latencies = [l.get("latencia_ms", 0) for l in logs if l.get("latencia_ms")]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total de Eventos Registrados", total_events)
        with m2:
            st.metric("Latência Média dos Estágios", f"{avg_lat:.1f} ms")
        with m3:
            st.metric("Total de Arquivos de Log", len(list(LOGS_DIR.glob("pipeline-*.jsonl"))))

        st.markdown("### 📋 Tabela de Eventos Recentes")
        
        table_data = []
        for l in reversed(logs):
            table_data.append({
                "Timestamp": l.get("timestamp"),
                "Estágio": l.get("stage"),
                "Run ID": l.get("run_id", "")[:8],
                "Query ID": l.get("query_id"),
                "Latência (ms)": l.get("latencia_ms"),
                "Prompt Tokens": l.get("prompt_tokens", 0),
                "Completion Tokens": l.get("completion_tokens", 0),
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

        st.markdown("### 🔎 Inspecionar Registro em Detalhes")
        selected_idx = st.number_input("Índice do Evento:", min_value=0, max_value=len(logs)-1, value=0)
        st.json(logs[-(selected_idx+1)])


# ---------------------------------------------------------
# 5. ABA: BENCHMARK & PERSONAS
# ---------------------------------------------------------
elif menu == "🧪 Benchmark & Personas":
    st.markdown("""
    <div class="main-header">
        <h1>🧪 Avaliação e Benchmark de Personas</h1>
        <p>Execute testes automatizados com perguntas de referência do Dr. Roberto (CEP), Carla (Bibliometria) e Dr. Eduardo (Fomento).</p>
    </div>
    """, unsafe_allow_html=True)

    from eval.benchmark import PERGUNTAS_BENCHMARK, BENCHMARK_RESULTS

    st.write(f"Conjunto de teste com **{len(PERGUNTAS_BENCHMARK)} perguntas de referência** cadastradas.")

    if st.button("🚀 Executar Benchmark Completo Agora", type="primary"):
        pipeline = get_pipeline()
        prog_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        for i, q in enumerate(PERGUNTAS_BENCHMARK):
            status_text.text(f"Avaliando ({i+1}/{len(PERGUNTAS_BENCHMARK)}): {q['persona']} - {q['id']}...")
            t0 = time.time()
            resp = pipeline.run(query=q["query"], query_id=q["id"])
            lat = int((time.time() - t0) * 1000)
            
            results.append({
                "id": q["id"],
                "persona": q["persona"],
                "tipo": q["tipo"],
                "query": q["query"],
                "latencia_ms": lat,
                "is_refusal": resp.is_refusal,
                "sources_count": len(resp.sources_used),
                "answer": resp.answer[:150] + "..." if len(resp.answer) > 150 else resp.answer
            })
            prog_bar.progress((i + 1) / len(PERGUNTAS_BENCHMARK))

        status_text.success("Benchmark concluído!")
        
        # Salva resultados
        BENCHMARK_RESULTS.parent.mkdir(parents=True, exist_ok=True)
        with open(BENCHMARK_RESULTS, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        st.session_state["last_benchmark"] = results

    # Mostra últimos resultados
    if "last_benchmark" in st.session_state or BENCHMARK_RESULTS.exists():
        if "last_benchmark" not in st.session_state:
            with open(BENCHMARK_RESULTS, "r", encoding="utf-8") as f:
                st.session_state["last_benchmark"] = json.load(f)
                
        bench_df = pd.DataFrame(st.session_state["last_benchmark"])
        st.markdown("### 📊 Resultados do Benchmark")
        st.dataframe(bench_df[["id", "persona", "tipo", "latencia_ms", "is_refusal", "sources_count", "answer"]], use_container_width=True)
