"""
src/retrieve.py
===============
Pipeline de recuperação híbrida:
  1. ChromaDB  → busca semântica vetorial (substitui FAISS)
  2. BM25      → busca léxica esparsa (via VectorIndex existente)
  3. SQL       → consultas relacionais estruturadas (filtros precisos)
  4. RRF       → fusão dos rankings vetorial + léxico
  5. Reranker  → cross-encoder para reordenação final

O SQL é consultado ANTES do LLM para enriquecer o contexto com dados
precisos (ex: top artigos por citações, beneficiários de editais, pareceres).
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

from src.index import VectorIndex
from src.obs import log_event
from src.schema import DocumentChunk, QueryAnalysis
from src.db_chroma import search as chroma_search, search_cross_source
from src import db_sql

from config import RERANKER_MODEL
from sentence_transformers import CrossEncoder


# ---------------------------------------------------------------------------
# Reranker
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(RERANKER_MODEL)


def rerank_results(
    query: str,
    results: List[Tuple[DocumentChunk, float]],
    top_n: int = 8,
) -> List[Tuple[DocumentChunk, float]]:
    if not results:
        return []
    model = get_reranker()
    pairs = [(query, chunk.content) for chunk, _ in results]
    scores = model.predict(pairs)
    reranked = [
        (chunk, float(score))
        for (chunk, _), score in zip(results, scores)
    ]
    reranked.sort(key=lambda item: item[1], reverse=True)
    return reranked[:top_n]


# ---------------------------------------------------------------------------
# RRF: Fusão de rankings
# ---------------------------------------------------------------------------

def compute_rrf(
    chroma_results: List[Tuple[DocumentChunk, float]],
    bm25_results: List[Tuple[DocumentChunk, float]],
    k: int = 60,
    top_n: int = 8,
) -> List[Tuple[DocumentChunk, float]]:
    """Combina rankings ChromaDB e BM25 com Reciprocal Rank Fusion."""
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, DocumentChunk] = {}

    for rank, (chunk, _) in enumerate(chroma_results):
        cid = chunk.chunk_id
        chunk_map[cid] = chunk
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + (rank + 1)))

    for rank, (chunk, _) in enumerate(bm25_results):
        cid = chunk.chunk_id
        chunk_map[cid] = chunk
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + (rank + 1)))

    sorted_chunks = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [(chunk_map[cid], score) for cid, score in sorted_chunks[:top_n]]


# ---------------------------------------------------------------------------
# Consulta SQL inteligente baseada na análise da query
# ---------------------------------------------------------------------------

def _sql_context_for_query(analysis: QueryAnalysis) -> Optional[str]:
    """
    Executa consultas SQL específicas com base na intenção detectada pelo roteador.
    Retorna um bloco de texto de contexto para enriquecer o prompt do LLM.
    """
    q = analysis.original_query.lower()
    intent = analysis.intent
    filters = analysis.extracted_filters
    ano = int(filters.get("ano", 0)) or None
    context_parts = []

    # Q05-style: top artigos mais citados
    if any(w in q for w in ["mais citado", "mais citados", "maior número de citações",
                             "citações", "top", "ranking"]):
        rows = db_sql.query_top_artigos_citacoes(ano=ano, limit=5)
        if rows:
            context_parts.append(db_sql.format_sql_context(rows, "Top 5 Artigos por Citações (SQL)"))

    # Q03-style: artigos ética IA com CEP
    if any(w in q for w in ["ética", "etica", "comitê de ética", "aprovação cep",
                             "aprovacao cep", "mencao cep", "inteligência artificial"]) and \
       any(w in q for w in ["cep", "conep", "aprovação", "resumo", "menção"]):
        rows = db_sql.query_artigos_etica_cep(ano=ano)
        if rows:
            context_parts.append(db_sql.format_sql_context(rows[:5], "Artigos Ética em IA com Aprovação CEP (SQL)"))

    # Q07/Q08-style: editais e beneficiários FAPERJ
    if any(w in q for w in ["faperj", "edital", "fomento", "beneficiário",
                             "financiamento", "auxílio", "chamada pública"]):
        # Editais
        rows_editais = db_sql.query_editais(orgao="FAPERJ", ano=ano)
        if rows_editais:
            context_parts.append(db_sql.format_sql_context(rows_editais, "Editais FAPERJ (SQL)"))

        # Beneficiários com publicações
        rows_ben = db_sql.query_beneficiarios_fomento("05/2022")
        if rows_ben:
            context_parts.append(db_sql.format_sql_context(rows_ben[:4], "Beneficiários FAPERJ 2022 + Publicações (SQL)"))

    # Artigos financiados por FAPERJ/CNPq
    if any(w in q for w in ["publicaram", "publicado", "artigo", "financiamento declarado"]) and \
       any(w in q for w in ["faperj", "cnpq", "capes", "fapesp"]):
        for financiador in ["FAPERJ", "CNPq", "CAPES"]:
            if financiador.lower() in q:
                rows = db_sql.query_artigos_financiamento(financiador=financiador, ano=ano)
                if rows:
                    context_parts.append(db_sql.format_sql_context(rows[:5], f"Artigos financiados por {financiador} (SQL)"))

    # Q01-style: resolução CNS / normativas CEP
    if any(w in q for w in ["resolução", "resolucao", "510", "cns", "conep", "dispensa",
                             "questionário", "tcle", "submissão"]):
        rows = db_sql.query_editais(orgao="CNS")
        if rows:
            context_parts.append(db_sql.format_sql_context(rows, "Normativos CNS/CONEP (SQL)"))

    # Q02/Q09-style: pareceres
    if any(w in q for w in ["parecer", "parecerista", "decisão", "rejeitado",
                             "aprovado", "peer review"]):
        decisao = None
        if "rejeit" in q:
            decisao = "Rejeitado"
        elif "aprovad" in q:
            decisao = "Aprovado"
        protocolo = None
        import re
        m = re.search(r'\b(\d{4,5})\b', analysis.original_query)
        if m:
            protocolo = m.group(1)
        rows = db_sql.query_pareceres(decisao=decisao, protocolo=protocolo)
        if rows:
            context_parts.append(db_sql.format_sql_context(rows[:3], "Pareceres de Revisão (SQL)"))

    return "\n\n".join(context_parts) if context_parts else None


# ---------------------------------------------------------------------------
# Função principal de recuperação
# ---------------------------------------------------------------------------

def retrieve_chunks(
    analysis: QueryAnalysis,
    index: VectorIndex,
    run_id: str = None,
    top_k: int = 8,
) -> List[DocumentChunk]:
    """
    Pipeline de recuperação híbrida em 4 etapas:
    1. ChromaDB (semântico vetorial)
    2. BM25 léxico (via VectorIndex)
    3. Fusão RRF
    4. Cross-Encoder Reranker

    Retorna chunks + injeta contexto SQL como chunk sintético extra.
    """
    query = analysis.original_query
    target_bases = analysis.target_bases
    t0 = time.time()

    # ── 1. ChromaDB: busca semântica ─────────────────────────────────────────
    if analysis.requires_cross_source and target_bases:
        chroma_results = search_cross_source(
            query, bases=target_bases, top_k_per_base=max(2, top_k // len(target_bases))
        )
    else:
        chroma_results = chroma_search(
            query, bases=target_bases if target_bases else None, top_k=top_k * 2
        )
    t_chroma = int((time.time() - t0) * 1000)

    if run_id:
        log_event(
            run_id=run_id, stage="retrieval_chroma",
            query_id=analysis.query_id, input_data=query,
            output_data=f"{len(chroma_results)} chunks ChromaDB",
            latencia_ms=t_chroma,
            extra={"target_bases": target_bases, "cross_source": analysis.requires_cross_source}
        )

    # ── 2. BM25 léxico ────────────────────────────────────────────────────────
    t1 = time.time()
    bm25_results = index.search_bm25(
        query=query, top_k=top_k * 2,
        base_filter=target_bases if target_bases else None,
        structured_filters=analysis.extracted_filters
    )
    t_bm25 = int((time.time() - t1) * 1000)

    if run_id:
        log_event(
            run_id=run_id, stage="retrieval_bm25",
            query_id=analysis.query_id, input_data=query,
            output_data=f"{len(bm25_results)} chunks BM25",
            latencia_ms=t_bm25,
            extra={"target_bases": target_bases}
        )

    # ── 3. Fusão RRF ─────────────────────────────────────────────────────────
    t2 = time.time()
    fused = compute_rrf(chroma_results, bm25_results, k=60, top_n=top_k * 2)
    reranked = rerank_results(query, fused, top_n=top_k)
    t_rrf = int((time.time() - t2) * 1000)

    if run_id:
        log_event(
            run_id=run_id, stage="fusao_rrf_rerank",
            query_id=analysis.query_id,
            input_data=f"Chroma({len(chroma_results)}) + BM25({len(bm25_results)})",
            output_data=f"{len(reranked)} chunks após rerank",
            latencia_ms=t_rrf,
            extra={"top_ids": [c.chunk_id for c, _ in reranked[:3]]}
        )

    # ── 4. Cross-source: garante cobertura de todas as bases ─────────────────
    if analysis.requires_cross_source and target_bases:
        selected = []
        selected_ids = set()
        all_pool = chroma_results + bm25_results

        for base in target_bases:
            base_pool = [(c, s) for c, s in all_pool if c.metadata.base_id == base]
            if not base_pool:
                continue
            base_reranked = rerank_results(query, base_pool, top_n=1)
            if base_reranked:
                item = base_reranked[0]
                if item[0].chunk_id not in selected_ids:
                    selected.append(item)
                    selected_ids.add(item[0].chunk_id)

        for item in reranked:
            if item[0].chunk_id not in selected_ids:
                selected.append(item)
                selected_ids.add(item[0].chunk_id)
            if len(selected) >= top_k:
                break

        reranked = selected[:top_k]

    final_chunks = [c for c, _ in reranked]

    # ── 5. SQL: injeta contexto estruturado como chunk sintético ─────────────
    t3 = time.time()
    sql_ctx = _sql_context_for_query(analysis)
    if sql_ctx:
        from src.schema import ChunkMetadata, BaseNatureza, SensitivityLevel
        sql_chunk = DocumentChunk(
            chunk_id="sql_context_synthetic",
            content=sql_ctx,
            metadata=ChunkMetadata(
                chunk_id="sql_context_synthetic",
                doc_type="sql_query_result",
                source_file="data/academic_rag.db",
                base_id="sql_structured",
                natureza=BaseNatureza.ESTRUTURADA,
                sensitivity=SensitivityLevel.PUBLICO,
                extras={"tipo": "sql_resultado", "is_synthetic": True}
            )
        )
        # Insere o contexto SQL no INÍCIO (maior prioridade)
        final_chunks.insert(0, sql_chunk)

        t_sql = int((time.time() - t3) * 1000)
        if run_id:
            log_event(
                run_id=run_id, stage="retrieval_sql",
                query_id=analysis.query_id, input_data=query,
                output_data=f"Contexto SQL injetado ({len(sql_ctx)} chars)",
                latencia_ms=t_sql,
                extra={"sql_chars": len(sql_ctx)}
            )

    return final_chunks
