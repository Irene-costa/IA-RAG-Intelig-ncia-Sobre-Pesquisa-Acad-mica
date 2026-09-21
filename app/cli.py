import sys
from src.pipeline import AcademicRAGPipeline

def main():
    print("=" * 70)
    print("  Inteligência sobre Pesquisa Acadêmica · Adaptive RAG")
    print("  Residência TIC em Trilhas · PUC-Rio / ECOA (Cenário 3)")
    print("=" * 70)
    print("Digite sua pergunta ou 'sair' para encerrar.\n")

    pipeline = AcademicRAGPipeline()

    while True:
        try:
            query = input("\n[Pergunta] > ").strip()
            if not query:
                continue
            if query.lower() in ["sair", "exit", "quit"]:
                print("[*] Encerrando sessão. Até logo!")
                break

            print("[*] Processando pergunta através do pipeline Adaptive RAG...")
            response = pipeline.run(query)

            print("\n" + "-" * 70)
            print("  RESPOSTA GERADA")
            print("-" * 70)
            print(response.answer)

            if response.is_refusal:
                print(f"\n[!] AVISO DE ÉTICA/GUARDRAILS: {response.refusal_reason}")

            if response.sources_used:
                print("\n" + "-" * 70)
                print(f"  FONTES CONSULTADAS ({len(response.sources_used)})")
                print("-" * 70)
                for s in response.sources_used:
                    print(f"  • Base: {s['base_id']} | Natureza: {s['natureza']} | Chunk: {s['chunk_id']}")

            print(f"\n[Latência Total: {response.latency_ms} ms]")

        except KeyboardInterrupt:
            print("\n[*] Sessão interrompida.")
            break
        except Exception as e:
            print(f"[Erro] Falha ao processar a pergunta: {e}")

if __name__ == "__main__":
    main()
