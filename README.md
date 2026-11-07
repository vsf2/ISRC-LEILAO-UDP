Para rodar o código você primeiro precisa executar o server.py e depois executar quantos clients quiser utilizando o client.py em terminais diferentes.

Os códigos funcionam da seguinte maneira: O server.py fica permanentemente escutando na porta UDP 4444 para aguardar as mensagens dos clients. Quando um client envia uma mensagem ou se conecta com o comando "conectar <nome>", o server cria uma thread para tratar aquela requisição específica. Dessa maneira, o server principal não precisa parar de escutar por novos pacotes e novos clients na rede.

Para manter a "conexão persistente" exigida no UDP (já que o UDP não tem conexão nativa de transporte como o TCP), o server armazena o endereço (IP e porta) de cada client conectado em um dicionário. Assim, o server consegue manter o controle de quem está na sala e mandar mensagens ativas para eles a qualquer momento.

Quando conectado, o server espera requisições do client. Nós definimos os seguintes comandos:
- "conectar <nome>": para se registrar como participante no leilão.
- "BID <valor>": para dar um lance. O server valida se o valor é maior que o lance atual e usa um lock para garantir que lances concorrentes sejam registrados de forma atômica.
- "STATUS": para conferir a situação do leilão, quantidade de participantes conectados, o item leiloado, o valor mais alto com o líder atual e o tempo restante.
- "SAIR": para encerrar e fechar a conexão do client.

Além disso, o client por meio da thread receive_messages consegue receber mensagens do server sem tê-las requisitado, o que se provou essencial para que o server atualize e notifique imediatamente todos os outros clients conectados sempre que um novo valor máximo de lance for definido (broadcast). Também utilizamos um esquema simples de confirmação mútua (ACK) para dar confiabilidade aos envios.

Diferente da versão anterior, dessa vez nós conseguimos implementar o timer que finaliza o leilão com sucesso! Uma thread fica rodando em segundo plano acompanhando o tempo restante em tempo real e, quando o tempo esgota, o leilão é encerrado automaticamente e o server avisa todo mundo quem foi o vencedor e qual foi o lance final.

Aprendemos bastante a utilizar sockets UDP, entender as diferenças práticas dele pro TCP, como fazer a sincronização de dados com threads e locks para evitar condições de corrida, e como contornar a falta de conexão nativa do UDP gerenciando os clientes na aplicação.
