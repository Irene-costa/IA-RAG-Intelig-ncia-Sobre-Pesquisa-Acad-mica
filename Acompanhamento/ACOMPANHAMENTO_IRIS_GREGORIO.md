# Acompanhamento — Iris Gregorio

## 14/09/2026

## 16/09/2026

### Relato individual — Iris Gregorio

Neste dia, meu trabalho foi voltado ao entendimento da atividade proposta e à pesquisa dos documentos disponibilizados para o desenvolvimento do cenário. Analisei as informações do projeto para compreender os objetivos, requisitos e materiais que seriam utilizados nas etapas seguintes.

## 21/09/2026

### Relato individual — Iris Gregorio

Hoje trabalhei na implementação de uma melhoria no pipeline do cenário 3, com foco na persistência do histórico das interações do RAG.

Realizei a alteração no arquivo `src/pipeline.py` para que cada execução passe a registrar informações como `timestamp`, `run_id`, `query_id`, consulta realizada, resposta gerada, indicação de recusa, tempo de execução e fontes utilizadas. O histórico é armazenado em `data/history.jsonl`, mantendo os registros fora do versionamento do Git.

Também ajustei o estágio de feedback do pipeline para registrar que o histórico da interação foi persistido.

Utilizei o ChatGPT como apoio durante a análise da estrutura existente do pipeline, na definição da forma de persistência e na revisão dos comandos Git. A implementação final foi aplicada e validada no repositório.

Após a implementação, sincronizei o trabalho com o `main` utilizando `git pull --rebase`, validei a alteração e publiquei as mudanças no repositório remoto.

### Resumo do dia

O grupo avançou na implementação do cenário 3 e foi integrada uma funcionalidade de persistência do histórico das interações do RAG. A alteração foi sincronizada com o estado mais recente do repositório e publicada no `main`.

**Próximo passo:** continuar a implementação e validação das funcionalidades do cenário, conforme a divisão das atividades do grupo.
