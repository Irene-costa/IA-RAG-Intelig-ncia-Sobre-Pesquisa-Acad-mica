import time
from typing import Dict, List, Tuple
from src.index import VectorIndex
from src.obs import log_event
from src.schema import DocumentChunk, QueryAnalysis


def compute_rrf(
    dense_results: List[Tuple[DocumentChunk, float]],
    bm25_results: List[Tuple[DocumentChunk, float]],
    k: int = 60,
    top_n: int = 8,
) -> List[Tuple[DocumentChunk, float]]:
    """
    Combina rankings denso e BM25 com Reciprocal Rank Fusion (RRF).
    Score(d) = sum( 1 / (k + rank(d)) )
    """
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, DocumentChunk] = {}

    # Ranqueamento Denso
    for rank, (chunk, _) in enumerate(dense_results):
        cid = chunk.chunk_id
        chunk_map[cid] = chunk
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + (rank + 1)))

    # Ranqueamento BM25
    for rank, (chunk, _) in enumerate(bm25_results):
        cid = chunk.chunk_id
        chunk_map[cid] = chunk
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + (rank + 1)))

    sorted_chunks = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [(chunk_map[cid], score) for cid, score in sorted_chunks[:top_n]]


def retrieve_chunks(
    analysis: QueryAnalysis,
    index: VectorIndex,
    run_id: str = None,
    top_k: int = 8,
) -> List[DocumentChunk]:
    """
    Executa o pipeline de recuperação híbrida respeitando as bases selecionadas pelo roteador.
    """
    query = analysis.original_query
    target_bases = analysis.target_bases
    t0 = time.time()

    # 1. Retrieval Denso
    dense_results = index.search_dense(
        query=query, top_k=top_k * 2, base_filter=target_bases
    )
    t_dense = int((time.time() - t0) * 1000)
    if run_id:
        log_event(
            run_id=run_id,
            stage="retrieval_denso",
            query_id=analysis.query_id,
            input_data=query,
            output_data=f"{len(dense_results)} chunks recuperados",
            latencia_ms=t_dense,
            extra={"target_bases": target_bases},
        )

    # 2. Retrieval BM25
    t1 = time.time()
    bm25_results = index.search_bm25(
        query=query, top_k=top_k * 2, base_filter=target_bases
    )
    t_bm25 = int((time.time() - t1) * 1000)
    if run_id:
        log_event(
            run_id=run_id,
            stage="retrieval_bm25",
            query_id=analysis.query_id,
            input_data=query,
            output_data=f"{len(bm25_results)} chunks recuperados",
            latencia_ms=t_bm25,
            extra={"target_bases": target_bases},
        )

    # 3. Fusão RRF
    t2 = time.time()
    fused_results = compute_rrf(dense_results, bm25_results, k=60, top_n=top_k)
    t_rrf = int((time.time() - t2) * 1000)
    if run_id:
        log_event(
            run_id=run_id,
            stage="fusao_rrf",
            query_id=analysis.query_id,
            input_data=f"Denso ({len(dense_results)}) + BM25 ({len(bm25_results)})",
            output_data=f"{len(fused_results)} chunks selecionados",
            latencia_ms=t_rrf,
            extra={
                "top_ids": [c.chunk_id for c, _ in fused_results[:5]],
                "top_bases": [
                    c.metadata.base_id for c, _ in fused_results[:5]
                ],
            },
        )

    return [c for c, _ in fused_results]
