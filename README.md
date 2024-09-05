Extensão da implementção de Tom Cocagne &lt;tom.cocagne@gmail.com&gt;  
v2.0, January 2013
url='https://github.com/cocagne/paxos'



# Implementação do Algoritmo Paxos com Comunicação por Sockets
## 1. Arquitetura do Sistema
### 1.1 Componentes
A arquitetura do sistema é composta pelos seguintes componentes principais:
1. **SocketMessenger**: Responsável pela comunicação entre os nós usando sockets UDP. Essa classe implementa a interface `Messenger` e fornece métodos para enviar e receber mensagens.
2. **SocketHeartbeatMessenger**: Estende o `SocketMessenger` e implementa a interface `HeartbeatMessenger`. Adiciona funcionalidades de envio de heartbeats e agendamento de tarefas.
3. **run_node**: Função que configura e executa um nó Paxos, incluindo a criação do `SocketHeartbeatMessenger` e do `PaxosNode`.
5. **generate_shared_values**: Script separado que gera valores aleatórios e os grava em um arquivo compartilhado (`shared_values.txt`).
Os nós Paxos interagem entre si por meio do envio de mensagens usando o `SocketMessenger`. O nó líder (Node A) envia heartbeats regularmente e lida com as propostas recebidas dos outros nós. Os nós seguidores (Node B e Node C) leem os valores do arquivo compartilhado e os enviam como propostas.

### 1.2 Papéis

- **Proposer**: Propõe valores para serem acordados.
- **Accepter**: Aceita ou rejeita propostas.
- **Leaner**: Aprende o valor acordado.

Nesta implementação, cada nó desempenha os três papéis.

### 1.3 Interações

Os nós interagem entre si através da troca de mensagens. O componente SocketMessenger lida com o envio e recebimento de mensagens entre os nós. Os principais tipos de mensagens são:
- Prepare 
- Promise 
- Accept 
- Accepted 

## 2. Explicação do Algoritmo

1. **Inicialização**: Quando um nó é executado, verifica se é o líder (Node A) ou um seguidor (Node B ou Node C). O líder começa imediatamente o processo de liderança, enquanto os seguidores aguardam a criação do arquivo compartilhado.
2. **Leitura de Valores Compartilhados**: Os nós seguidores monitoram a existência do arquivo `shared_values.txt` e, quando o arquivo é criado, leem os valores nele contidos.
3. **Proposição de Valores**: Após ler os valores do arquivo compartilhado, os nós seguidores começam a propor esses valores um por um, com um pequeno atraso entre cada proposta.
4. **Preparação e Aceite**: Quando um nó (líder ou seguidor) envia uma proposta, o processo Paxos é iniciado. O nó líder envia mensagens de "prepare" para todos os nós, enquanto os nós seguidores recebem essas mensagens e respondem com "promise" se a proposta tiver um número maior que a última proposta aceita.
5. **Alcance de Consenso**: Quando o nó líder recebe promessas de um quórum de nós, ele envia uma mensagem de "accept" para todos os nós. Os nós aceitam a proposta e enviam uma mensagem de "accepted" para informar o resultado.
6. **Liderança e Heartbeats**: O nó líder (Node A) envia heartbeats regularmente para indicar que ainda está ativo. Se os outros nós não receberem heartbeats por um determinado período, eles iniciarão o processo de aquisição de liderança.

## 3. Justificativa das Escolhas de Projeto

### 3.1 Estruturas de Dados

- **ProposalID**: Uma tupla nomeada combinando um número e um UID. Isso garante a identificação única das propostas e permite fácil comparação.
- **Conjuntos (sets) para promises_received**: Eficientes para verificar membros e prevenir duplicatas.
- **SocketMessenger e SocketHeartbeatMessenger**: Essas classes foram criadas para fornecer uma camada de comunicação por sockets, permitindo que os nós Paxos se comuniquem entre si. Isso facilita a execução dos nós em máquinas separadas e a replicação do sistema.

### 3.2 Algoritmos

- **UDP para comunicação**: Escolhido pela simplicidade e velocidade, embora em um ambiente de produção, TCP possa ser preferido para maior confiabilidade.
- **Arquivo Compartilhado**: O uso de um arquivo compartilhado (`shared_values.txt`) para armazenar os valores a serem propostos permite que os nós seguidores acessem as mesmas informações, sem a necessidade de uma etapa adicional de comunicação para distribuir esses valores.
- **Estruturas de Dados**: O uso de dicionários e conjuntos (dictionaries e sets) para armazenar informações sobre propostas, promessas e aceitações é eficiente e permite uma fácil manipulação desses dados.

## 4. Instruções de Execução
1. Certifique-se de ter o Python 3 instalado em sua máquina.
2. Edite o arquivo commands.txt para simular o cenário. Ele conterá a lista de comandos para cada nó, no formato Nó: Comando. Cada linha deve especificar o nome do nó (por exemplo, A, B, C, etc.) seguido de um comando a ser executado. 
3. Para rodar o programa, use `python main.py --<numero de nós>`, se não especificado, o número de nós será 3.
4. Pressione Ctrl+C no terminal para encerrar a execução.

