import json
import time
from typing import Optional
from pathlib import Path
from src.schema import RAGResponse, QueryAnalysis, DocumentChunk
from src.obs import generate_run_id, log_event
from src.router import analyze_and_route
from src.retrieve import retrieve_chunks
from src.generate import generate_rag_response
from src.index import VectorIndex

BASE_DIR = Path(__file__).resolve().parent.parent
CHUNKS_FILE = BASE_DIR / "data" / "chunks_v1.json"


class AcademicRAGPipeline:
    def __init__(self):
        self.index = VectorIndex()
        self._initialize_index()

    def _initialize_index(self):
        """Carrega ou constrói o índice com cache em disco."""
        if not self.index.load_local():
            if CHUNKS_FILE.exists():
                with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chunks = [DocumentChunk(**item) for item in data]
                self.index.build_index(chunks)
            else:
                print("[!] chunks_v1.json não encontrado. Execute `python -m src.ingest` primeiro.")

    def run(self, query: str, query_id: str = "q_0001") -> RAGResponse:
        """Executa o pipeline completo de 9 estágios do Adaptive RAG."""
        run_id = generate_run_id()
        t_start = time.time()

        # 1. Análise da Query
        log_event(
            run_id=run_id,
            stage="query_analysis",
            query_id=query_id,
            input_data=query,
            output_data="Análise concluída",
            latencia_ms=2
        )

        # 2. Roteamento Adaptativo
        analysis = analyze_and_route(query, run_id=run_id, query_id=query_id)

        # 3. Recuperação Híbrida (Dense + BM25 + RRF)
        retrieved_chunks = retrieve_chunks(analysis, self.index, run_id=run_id, top_k=6)

        # 4. Geração e Validação de Guardrails
        response = generate_rag_response(analysis, retrieved_chunks, run_id=run_id, query_id=query_id)

        # 5. Estágio de Feedback / Conclusão
        log_event(
            run_id=run_id,
            stage="feedback",
            query_id=query_id,
            input_data="pipeline_completed",
            output_data=f"Latência total: {response.latency_ms}ms | Refusal: {response.is_refusal}",
            latencia_ms=int((time.time() - t_start) * 1000),
            extra={"sources_count": len(response.sources_used)}
        )

        return response


if __name__ == "__main__":
    pipeline = AcademicRAGPipeline()
    sample_q = "Quais artigos publicados tiveram financiamento declarado e qual foi o edital?"
    print(f"\n[*] Executando pergunta de teste: {sample_q}")
    res = pipeline.run(sample_q)
    print("\n--- RESPOSTA ---")
    print(res.answer)
    print(f"\n--- FONTES ({len(res.sources_used)}) ---")
    for s in res.sources_used:
        print(f"- Base: {s['base_id']} | ID: {s['chunk_id']}")
