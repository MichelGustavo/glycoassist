"""Versão simples de terminal do assistente."""

from assistente import responder
from database import listar_pacientes, obter_dados_paciente


def main():
    pacientes = listar_pacientes()
    if not pacientes:
        print("Nenhum paciente cadastrado no banco.")
        return

    print("Pacientes:")
    for p in pacientes:
        print(f"{p['id']}: {p['nome']} (idade: {p.get('idade')})")

    paciente_id = int(input("\nID do paciente: "))
    dados = obter_dados_paciente(paciente_id)
    if not dados:
        print("Paciente não encontrado.")
        return

    historico = []
    print("\nAssistente iniciado. Digite 'sair' para encerrar.\n")

    while True:
        mensagem = input("Você: ").strip()
        if mensagem.lower() == "sair":
            break
        if not mensagem:
            continue

        # Recarrega o banco antes de cada pergunta.
        dados = obter_dados_paciente(paciente_id)
        texto = responder(mensagem, dados, historico)
        print(f"Assistente: {texto}\n")
        historico.extend(
            [
                {"role": "user", "content": mensagem},
                {"role": "assistant", "content": texto},
            ]
        )
        historico = historico[-12:]


if __name__ == "__main__":
    main()
