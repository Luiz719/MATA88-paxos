# Implementação do Algoritmo Paxos com Comunicação por _Sockets_

Extensão da [implementação](https://github.com/cocagne/paxos) de Tom Cocagne &lt;tom.cocagne@gmail.com&gt;, v2.0, janeiro de 2013.

## 1. Arquitetura do Sistema

### 1.1 Componentes
A arquitetura do sistema é composta principalmente pelos seguintes componentes:
1. **`SocketMessenger`**: Responsável pela comunicação entre os nós utilizando _sockets_ UDP. Esta classe implementa a interface `Messenger` e fornece métodos para enviar e receber mensagens.
2. **`SocketHeartbeatMessenger`**: Estende `SocketMessenger` e implementa a interface `HeartbeatMessenger`. Adiciona funcionalidades de envio de _heartbeats_ e agendamento/cancelamento de tarefas.
3. **`run_node`**: Função que configura e executa um nó Paxos, incluindo a criação do `SocketHeartbeatMessenger` e do `PaxosNode`. Localizada em `main.py`.
4. **`generate_shared_values`**: Script separado que gera valores aleatórios e os grava em um arquivo compartilhado (`shared_values.txt`).

Os nós Paxos interagem entre si por meio do envio de mensagens usando o `SocketMessenger`. O nó líder (Node `A`) envia _heartbeats_ regularmente e lida com as propostas recebidas dos outros nós. Os nós seguidores (Node `B` e Node `C`) leem os valores do arquivo compartilhado e os enviam como propostas.

### 1.2 Papéis
- **Proposer**: Propõe valores para serem acordados.
- **Accepter**: Aceita ou rejeita propostas.
- **Learner**: Aprende o valor acordado.

Nesta implementação, cada nó desempenha os três papéis.

### 1.3 Interações
Os nós interagem entre si através da troca de mensagens. O componente `SocketMessenger` lida com o envio e recebimento de mensagens entre os nós. Os principais tipos de mensagens são:
- Prepare
- Promise
- Accept
- Accepted

Mensagens são, no geral, estruturadas da seguinte maneira:
```python
message = {
    'type': 'prepare', # ou 'promise'/'accept'/'accepted'/'prepare_nack'/'accept_nack'/'heartbeat'
    'proposal_id': proposal_id._asdict() # ou leader_proposal_id._asdict(), caso hearbeat
    # a depender do tipo da mensagem, podem haver outros campos:
    # 'value'/'accepted_value'/'previous_id'
}
```

## 2. Explicação do Algoritmo

1. **Inicialização**: Quando um nó qualquer é executado, este verifica se é o líder (Node `A`) ou um seguidor (Node `B` ou Node `C`). O líder começa imediatamente o processo de liderança, enquanto os seguidores aguardam a criação do arquivo compartilhado (`shared_values.txt`).
2. **Leitura de Valores Compartilhados**: Os nós seguidores monitoram a existência do arquivo `shared_values.txt` e, quando o arquivo é criado, leem os valores nele contidos.
3. **Proposição de Valores**: Após ler os valores do arquivo compartilhado, os nós seguidores começam a propor esses valores, um por um, com um pequeno atraso entre cada proposta.
4. **Preparação e Aceite**: Quando um nó (seja este líder ou seguidor) envia uma proposta, o processo Paxos é iniciado. O nó líder envia mensagens de `'prepare'` para todos os nós; os nós seguidores recebem essas mensagens e respondem com um `'promise'` se a proposta tiver um número maior que a última proposta aceita.
5. **Alcance de Consenso**: Quando o nó líder recebe promessas o suficiente para cumprir com o quórum pré-determinado de nós, ele envia uma mensagem de `'accept'` para todos os nós. Os nós aceitam a proposta e enviam uma mensagem de `'accepted'` para informar o resultado.
6. **Liderança e _Heartbeats_**: O nó líder (Node `A`) envia _heartbeats_ regularmente para indicar que ainda está ativo. Se os outros nós não receberem _heartbeats_ por um período predefinido, assumirão que o líder falhou e então iniciarão o processo de aquisição de liderança.

## 3. Justificativa das Escolhas de Projeto

### 3.1 Estruturas de Dados
- **`ProposalID`**: Uma tupla nomeada `('ProposalID', ['number', 'uid'])` combinando um número e um `UID`. Isso garante a identificação única das propostas e permite fácil comparação.
- **Conjuntos (`sets`) para `promises_received`**: Eficientes para verificar membros e prevenir duplicatas.
- **`SocketMessenger` e `SocketHeartbeatMessenger`**: Essas classes foram criadas para fornecer uma camada de comunicação por _sockets_, permitindo que os nós Paxos se comuniquem entre si. Isso facilita a execução dos nós em máquinas separadas e a replicação do sistema.

### 3.2 Algoritmos
- **UDP para comunicação**: Escolhido por sua simplicidade em não precisar estabelecer conexões contínuas e velocidade de entrega de pacotes. Utilizar TCP para a implementação do algoritmo Paxos seria, em muitos aspectos, redundante.
- **Arquivo Compartilhado**: O uso de um arquivo compartilhado (`shared_values.txt`) para armazenar os valores a serem propostos permite que os nós seguidores acessem as mesmas informações simultaneamente e sem atrasos, pois não há necessidade de uma etapa adicional de comunicação para distribuir esses valores.
- **Estruturas de Dados**: Dicionários e conjuntos (`dictionaries` e `sets`) são utilizados para armazenar informações sobre propostas, promessas e aceitações. Estas são estuturas relativamente eficientes que permitem uma fácil manipulação de tais dados.

## 4. Instruções de Execução

1. Certifique-se de ter o Python 3 instalado em sua máquina.
2. Edite o arquivo `commands.txt` para simular o cenário. Ele conterá a lista de comandos para cada nó, no formato `[Nó]: [Comando]`. Cada linha deve especificar o nome do nó (por exemplo, `A`, `B`, `C`, etc.) seguido de um comando a ser executado. 
3. Para rodar o programa, rode `$ python main.py --node_count <numero de nós>`. Caso não seja especificado, o número de nós será 3.
4. Pressione `Ctrl+C` no terminal para encerrar a execução.

