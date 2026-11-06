import socket
import threading
import time

# configuracoes basicas de rede
PORT = 4444
HOST = "127.0.0.1"
ADDR = (HOST, PORT)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "SAIR"

# informacoes e estado atual do leilao
item_leilao = "Notebook Gamer Dell G15"
lance_atual = 1500.0  # valor inicial de partida
proponente_atual = "Nenhum"  # id de quem deu o maior lance
tempo_duracao = 180  # tempo total do leilao em segundos
tempo_inicio = time.time()
leilao_ativo = True

# socket udp do servidor
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(ADDR)
print(f"Servidor de leilão rodando em {ADDR}")

# guarda os licitantes conectados: endereco -> nome
clients = {}

# lock pra sincronizar os lances e garantir atomicidade
lock_leilao = threading.Lock()

def obter_tempo_restante():
    # calcula quantos segundos faltam pro leilao acabar
    if not leilao_ativo:
        return 0
    tempo_passado = time.time() - tempo_inicio
    tempo_restante = int(tempo_duracao - tempo_passado)
    return max(0, tempo_restante)

def send_rdt(mensagem, client_address):
    # envia mensagem com prefixo ack pro cliente
    pacote = f"ACK-{mensagem}"
    try:
        server.sendto(pacote.encode(FORMAT), client_address)
        return True
    except Exception as e:
        print(f"erro ao enviar pacote para {client_address}: {e}")
        return False

def receive_rdt(sock):
    # recebe pacotes no socket e devolve ack de confirmacao
    while True:
        try:
            pacote_bytes, endereco = sock.recvfrom(2048)
            pacote = pacote_bytes.decode(FORMAT)

            if pacote == "ACK":
                continue

            if pacote.startswith("ACK-"):
                # manda ack de volta confirmando que o pacote chegou
                sock.sendto("ACK".encode(FORMAT), endereco)
                mensagem = pacote.split('-', 1)[1]
                return mensagem, endereco
        except Exception as e:
            print(f"erro ao receber pacote: {e}")

def notificar_outros(mensagem, endereco_remetente=None):
    # avisa todos os outros clientes sobre o novo lance
    with lock_leilao:
        destinatarios = list(clients.keys())

    for endr in destinatarios:
        if endr != endereco_remetente:
            send_rdt(mensagem, endr)

def monitorar_tempo_leilao():
    # thread que acompanha o tempo restante do leilao
    global leilao_ativo
    while leilao_ativo:
        time.sleep(1)
        if obter_tempo_restante() <= 0:
            deve_avisar = False
            with lock_leilao:
                if leilao_ativo:
                    leilao_ativo = False
                    deve_avisar = True
                    if proponente_atual != "Nenhum":
                        msg_fim = f"TEMPO ESGOTADO! Leilão finalizado. Vencedor: {proponente_atual} com o lance de R$ {lance_atual:.2f} para o item '{item_leilao}'!"
                    else:
                        msg_fim = f"TEMPO ESGOTADO! Leilão finalizado sem nenhum lance para o item '{item_leilao}'."

            if deve_avisar:
                print(f"\n{msg_fim}")
                notificar_outros(msg_fim, endereco_remetente=None)
            break

# inicia a contagem do tempo em segundo plano
thread_tempo = threading.Thread(target=monitorar_tempo_leilao, daemon=True)
thread_tempo.start()

def tratar_mensagem(mensagem, endereco):
    # processa o comando recebido de cada cliente
    global lance_atual, proponente_atual

    # comando de conexao do licitante
    if mensagem.startswith("CONNECT"):
        partes = mensagem.split(maxsplit=1)
        id_proponente = partes[1] if len(partes) > 1 else f"Licitante_{endereco[1]}"

        with lock_leilao:
            if endereco not in clients:
                clients[endereco] = {"nome": id_proponente}
                print(f"novo licitante conectado: {id_proponente} em {endereco}")

                tempo_restante = obter_tempo_restante()
                msg_boas_vindas = (
                    f"Bem-vindo ao leilão, {id_proponente}!\n"
                    f"Item: {item_leilao} | Lance atual: R$ {lance_atual:.2f} ({proponente_atual}) | "
                    f"Tempo restante: {tempo_restante}s"
                )
            else:
                clients[endereco]["nome"] = id_proponente
                msg_boas_vindas = f"Bem-vindo de volta! Você já está conectado como {id_proponente}."

        send_rdt(msg_boas_vindas, endereco)
        return

    # comando de saida do licitante
    if mensagem in ("DISCONNECT", DISCONNECT_MESSAGE):
        with lock_leilao:
            if endereco in clients:
                nome_cliente = clients[endereco]["nome"]
                print(f"licitante desconectado: {nome_cliente} ({endereco})")
                del clients[endereco]
        return

    # checa se o cliente esta registrado
    with lock_leilao:
        cliente_info = clients.get(endereco)

    if not cliente_info:
        return

    nome_cliente = cliente_info["nome"]
    partes = mensagem.strip().split(maxsplit=1)
    comando = partes[0].upper()

    # comando de lance
    if comando in ("BID", "LANCE"):
        if len(partes) < 2:
            send_rdt("formato inválido! use: BID <valor>", endereco)
            return

        try:
            valor_oferta = float(partes[1].replace(",", "."))
        except ValueError:
            send_rdt("valor de lance inválido! digite um número (ex: BID 1600.00)", endereco)
            return

        deve_notificar = False
        msg_alerta = ""

        # valida e atualiza o lance de forma atomica
        with lock_leilao:
            tempo_restante = obter_tempo_restante()

            if not leilao_ativo or tempo_restante <= 0:
                resposta = "lance recusado! o leilão já está encerrado."
            elif valor_oferta > lance_atual:
                lance_atual = valor_oferta
                proponente_atual = nome_cliente
                print(f"novo lance aceito: R$ {lance_atual:.2f} por {proponente_atual}")

                resposta = f"seu lance de R$ {lance_atual:.2f} foi aceito e registrado com sucesso!"
                msg_alerta = (
                    f"NOVO LANCE MÁXIMO! {proponente_atual} ofertou R$ {lance_atual:.2f} "
                    f"para '{item_leilao}'. Tempo restante: {tempo_restante}s"
                )
                deve_notificar = True
            else:
                resposta = f"lance de R$ {valor_oferta:.2f} recusado! o lance atual é R$ {lance_atual:.2f} ({proponente_atual})."

        send_rdt(resposta, endereco)

        # se o lance foi o maior, avisa os outros participantes
        if deve_notificar:
            notificar_outros(msg_alerta, endereco_remetente=endereco)

    # comando pra consultar o status
    elif comando == "STATUS":
        with lock_leilao:
            tempo_restante = obter_tempo_restante()
            situacao = "ATIVO" if leilao_ativo else "ENCERRADO"
            msg_status = (
                f"\n--- ESTADO ATUAL DO LEILÃO ---\n"
                f"Item: {item_leilao}\n"
                f"Status: {situacao}\n"
                f"Lance Atual: R$ {lance_atual:.2f}\n"
                f"Licitante Líder: {proponente_atual}\n"
                f"Tempo Restante: {tempo_restante} segundos\n"
                f"------------------------------"
            )
        send_rdt(msg_status, endereco)

    else:
        send_rdt("comando não reconhecido. use BID <valor>, STATUS ou SAIR.", endereco)

# loop principal escutando a rede
while True:
    mensagem, endereco = receive_rdt(server)

    if mensagem:
        # roda cada requisicao em uma thread separada
        thread_cliente = threading.Thread(target=tratar_mensagem, args=(mensagem, endereco))
        thread_cliente.start()
