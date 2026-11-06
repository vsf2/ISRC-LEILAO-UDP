import socket
import threading
import sys

# endereco do servidor
SERVER_ADDRESS = ('127.0.0.1', 4444)

# socket udp do cliente
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.bind(('127.0.0.1', 0))

# controle de conexao e id do licitante
conectado = False
nome_usuario = ""

# evento pra avisar que o ack chegou
ack_event = threading.Event()

def send_rdt(mensagem, sock, server):
    # envia uma mensagem garantindo a entrega
    seq_num = 0
    pacote = f"ACK-{mensagem}"

    while seq_num < 4:
        ack_event.clear()
        sock.sendto(pacote.encode(), server)

        # espera a thread de escuta avisar que o ack chegou
        if ack_event.wait(timeout=1.5):
            return True

        seq_num += 1

    print("\n[aviso] não foi possível obter confirmação do servidor após 4 tentativas.")
    return False

def receive_messages():
    # thread que roda no fundo escutando o servidor
    global conectado

    while True:
        try:
            pacote_bytes, endereco = client_socket.recvfrom(2048)
            pacote = pacote_bytes.decode()

            if pacote == "ACK":
                # confirmacao recebida, libera o envio
                ack_event.set()
            elif pacote.startswith("ACK-"):
                # responde ack de volta pro servidor
                client_socket.sendto("ACK".encode(), endereco)

                mensagem = pacote.split("-", 1)[1]
                if "Bem-vindo" in mensagem or "conectado" in mensagem.lower():
                    conectado = True

                print(f"\n[Servidor]: {mensagem}")

                if conectado:
                    print("Digite um comando: ", end="", flush=True)

        except Exception:
            break

# inicia a escuta em segundo plano
thread_recebimento = threading.Thread(target=receive_messages, daemon=True)
thread_recebimento.start()

def exibir_menu():
    # mostra as opcoes do menu
    print("-" * 55)
    print("SISTEMA DE LEILÃO EM TEMPO REAL (SOCKETS UDP)")
    print(" 1. Conectar:  conectar <seu_id>  (ex: conectar Maria)")
    print(" 2. Dar lance: BID <valor>        (ex: BID 1600.00)")
    print(" 3. Estado:    STATUS             (consulta o leilão)")
    print(" 4. Ajuda:     menu")
    print(" 5. Sair:      sair")
    print("-" * 55)

if __name__ == "__main__":
    exibir_menu()

    while True:
        try:
            comando = input("\nDigite um comando: ").strip()

            if not comando:
                continue

            # comandos de saida
            if comando.lower() in ("sair", "bye"):
                if conectado:
                    send_rdt("DISCONNECT", client_socket, SERVER_ADDRESS)
                print("encerrando cliente...")
                client_socket.close()
                sys.exit(0)

            # menu de ajuda
            elif comando.lower() in ("menu", "help", "ajuda"):
                exibir_menu()
                continue

            # precisa conectar antes de mandar lances
            if not conectado:
                if comando.lower().startswith("conectar"):
                    partes = comando.split(maxsplit=1)
                    if len(partes) >= 2:
                        nome_usuario = partes[1]
                        send_rdt(f"CONNECT {nome_usuario}", client_socket, SERVER_ADDRESS)
                    else:
                        print("uso correto: conectar <seu_id>")
                else:
                    print("você precisa se conectar ao leilão primeiro! digite: conectar <seu_id>")

            # comandos enviados pro servidor
            else:
                send_rdt(comando, client_socket, SERVER_ADDRESS)

        except KeyboardInterrupt:
            if conectado:
                send_rdt("DISCONNECT", client_socket, SERVER_ADDRESS)
            client_socket.close()
            sys.exit(0)
