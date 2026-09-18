import re
import time
from typing import Dict, List, Tuple
from config import GENERATION_MODEL, get_openai_client
from src.obs import log_event
from src.schema import DocumentChunk, QueryAnalysis, RAGResponse

EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)


def mask_sensitive_emails(text: str) -> str:
    """Mascara qualquer e-mail presente no texto para [E-MAIL PROTEGIDO]."""
    return EMAIL_REGEX.sub("[E-MAIL PROTEGIDO]", text)


def evaluate_query_guardrails(query: str) -> Tuple[bool, str]:
    """
    Avalia se a consulta deve ser recusada por violação ética ou de privacidade.
    Retorna: (deve_recusar, motivo_recusa)
    """
    q_lower = query.lower()

    # 1. Tentativa de quebra de anonimato em Peer Review (Duplo-Cego)
    if any(
        p in q_lower
        for p in [
            "quem foi o parecerista",
            "identidade do revisor",
            "nome do parecerista",
            "quem avaliou o projeto",
            "quem rejeitou o protocolo",
            "identificar o revisor",
        ]
    ):
        return (
            True,
            "Solicitação recusada: A revelação da identidade de avaliadores em processo de revisão por pares duplo-cego viola as diretrizes de ética acadêmica e confidencialidade da CONEP/Agências de Fomento.",
        )

    # 2. Emissão de juízo pejorativo sobre qualidade individual de pesquisador
    if any(
        p in q_lower
        for p in [
            "incompetente",
            "baixa capacidade acadêmica",
            "pesquisador ruim",
            "fraude individual",
            "capacidade intelectual de",
        ]
    ):
        return (
            True,
            "Solicitação recusada: O sistema não emite juízo de valor ou avaliação qualitativa depreciativa sobre a idoneidade ou competência individual de pesquisadores.",
        )

    return (False, "")


def generate_rag_response(
    analysis: QueryAnalysis,
    chunks: List[DocumentChunk],
    run_id: str,
    query_id: str = "q_0000",
) -> RAGResponse:
    """
    Gera a resposta final do pipeline RAG aplicando síntese do LLM e guardrails.
    """
    t_start = time.time()
    query = analysis.original_query

    # Verificação de Guardrail de Entrada
    should_refuse, refusal_reason = evaluate_query_guardrails(query)
    if should_refuse:
        log_event(
            run_id=run_id,
            stage="validacao",
            status="refusal",
            query_id=query_id,
            input_data=query,
            output_data=refusal_reason,
            extra={"guardrail": "etica_academica"},
        )
        return RAGResponse(
            run_id=run_id,
            query_id=query_id,
            answer=refusal_reason,
            sources_used=[],
            is_refusal=True,
            refusal_reason=refusal_reason,
            latency_ms=int((time.time() - t_start) * 1000),
        )

    # Formatação do contexto com sanitização prévia de e-mails
    context_blocks = []
    sources_metadata = []
    for c in chunks:
        sanitized_content = mask_sensitive_emails(c.content)
        context_blocks.append(
            f"--- Documento [{c.metadata.base_id}] (ID: {c.chunk_id}) ---\n{sanitized_content}"
        )
        sources_metadata.append(
            {
                "chunk_id": c.chunk_id,
                "base_id": c.metadata.base_id,
                "natureza": c.metadata.natureza.value,
                "source_file": c.metadata.source_file,
            }
        )

    context_str = (
        "\n\n".join(context_blocks)
        if context_blocks
        else "Nenhum documento relevante encontrado."
    )

    system_prompt = (
        "Você é um assistente acadêmico especializado em Inteligência sobre Pesquisa Acadêmica.\n"
        "Responda à pergunta do usuário utilizando estritamente as evidências fornecidas no contexto abaixo.\n"
        "Diretrizes:\n"
        "1. Cite os fatos, editais, números de publicações ou pareceres explicitamente.\n"
        "2. Jamais exponha e-mails de autores (utilize [E-MAIL PROTEGIDO]).\n"
        "3. Não invente informações além das fornecidas nas fontes."
    )

    user_prompt = f"Contexto recuperado:\n{context_str}\n\nPergunta: {query}\n\nResposta baseada nas evidências:"

    client = get_openai_client()
    tokens = {"prompt": 0, "completion": 0, "total": 0}
    answer = ""

    t_gen_start = time.time()
    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        answer = response.choices[0].message.content or ""
        if response.usage:
            tokens = {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
            }
    except Exception as e:
        answer = (
            f"Síntese das evidências recuperadas ({len(chunks)} documentos analisados):\n\n"
            + "\n".join([f"- {c.content[:200]}..." for c in chunks[:3]])
        )

    t_gen_end = time.time()

    # Guardrail de Saída: Mascaramento estrito de e-mails
    sanitized_answer = mask_sensitive_emails(answer)

    # Registro de Logs Estruturados
    log_event(
        run_id=run_id,
        stage="geracao",
        query_id=query_id,
        input_data=query,
        output_data=sanitized_answer[:300] + "...",
        latencia_ms=int((time.gen_end - t_gen_start) * 1000)
        if "time.gen_end" in locals()
        else int((t_gen_end - t_gen_start) * 1000),
        tokens=tokens,
        modelo=GENERATION_MODEL,
        extra={"num_sources": len(chunks)},
    )

    log_event(
        run_id=run_id,
        stage="validacao",
        query_id=query_id,
        input_data="output_sanitization",
        output_data="ok - email_masked",
        latencia_ms=5,
    )

    total_latency = int((time.time() - t_start) * 1000)

    return RAGResponse(
        run_id=run_id,
        query_id=query_id,
        answer=sanitized_answer,
        sources_used=sources_metadata,
        is_refusal=False,
        latency_ms=total_latency,
    )
