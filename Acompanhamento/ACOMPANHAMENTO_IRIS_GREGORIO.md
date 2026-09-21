# Encontro 1 14/09/2026

# Resumo do dia em conjunto: o que a equipe entregou, o que travou, qual o próximo passo.

# Encontro 2 16/09/2026

## 21/09/2026 — Validação do ambiente e estrutura do projeto

- Repositório local sincronizado com `origin/main`.
- Validada a estrutura principal do cenário 3.
- Confirmada a existência do manifesto `corpus_manifest.yaml`.
- Confirmado o módulo `src/fetch_corpus.py`.
- Confirmados os módulos de ingestão, indexação, recuperação, roteamento e pipeline.
- Validada a configuração local de identidade Git para os commits da integrante Iris Gregorio.

## 21/09/2026 — Persistência do histórico das interações do RAG

- Implementada a persistência do histórico das execuções em `src/pipeline.py`.
- Cada interação passa a registrar `timestamp`, `run_id`, `query_id`, consulta, resposta, indicação de recusa, latência e fontes utilizadas.
- O histórico é armazenado em `data/history.jsonl`.
- O pipeline registra no estágio de feedback que o histórico foi persistido.
- A alteração foi integrada aos commits mais recentes da equipe por `git pull --rebase` e publicada no `main`.
