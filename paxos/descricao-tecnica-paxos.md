# Descrição Técnica da Implementação Persistente do Paxos

## 1. Arquitetura do Sistema

### 1.1 Componentes

1. **PersistentPaxosNode**: A classe principal que implementa o algoritmo Paxos. Ela combina os papéis de Proponente, Aceitador e Aprendiz.

2. **SocketMessenger**: Gerencia a comunicação em rede entre os nós usando sockets UDP.

3. **DurableObjectHandler**: Gerencia a persistência de dados para cada nó.

### 1.2 Papéis

- **Proponente**: Propõe valores para serem acordados.
- **Aceitador**: Aceita ou rejeita propostas.
- **Aprendiz**: Aprende o valor acordado.

Nesta implementação, cada nó desempenha os três papéis.

### 1.3 Interações

Os nós interagem entre si através da troca de mensagens. O componente SocketMessenger lida com o envio e recebimento de mensagens entre os nós. Os principais tipos de mensagens são:

- Prepare (Preparar)
- Promise (Prometer)
- Accept (Aceitar)
- Accepted (Aceito)

## 2. Explicação do Algoritmo

### 2.1 Fase de Preparação

1. Um proponente (líder) seleciona um número de proposta e envia uma mensagem Prepare para a maioria dos aceitadores.
2. Se um aceitador recebe uma mensagem Prepare, ele compara o número da proposta com o maior número que já viu. Se o novo número for maior, ele promete não aceitar propostas com números menores e envia uma mensagem Promise de volta ao proponente.

### 2.2 Fase de Aceitação

1. Se o proponente receber promessas da maioria dos aceitadores, ele envia uma mensagem Accept com o número da proposta e o valor para os aceitadores.
2. Se um aceitador receber uma mensagem Accept para um número de proposta igual ou maior que o maior número que ele prometeu, ele aceita a proposta e envia uma mensagem Accepted para todos os aprendizes.

### 2.3 Fase de Aprendizagem

1. Quando um aprendiz recebe mensagens Accepted para a mesma proposta da maioria dos aceitadores, ele considera que o valor foi escolhido e pode agir sobre ele.

### 2.4 Alcance do Consenso

O consenso é alcançado quando a maioria dos nós aceitou o mesmo valor. Nesta implementação, quando um nó recebe uma mensagem Accepted, ele considera que o consenso foi alcançado e imprime o valor acordado.

## 3. Justificativa das Escolhas de Projeto

### 3.1 Estruturas de Dados

- **ProposalID**: Uma tupla nomeada combinando um número e um UID. Isso garante a identificação única das propostas e permite fácil comparação.
- **Conjuntos (sets) para promises_received**: Eficientes para verificar membros e prevenir duplicatas.

### 3.2 Algoritmos

- **UDP para comunicação**: Escolhido pela simplicidade e velocidade, embora em um ambiente de produção, TCP possa ser preferido para maior confiabilidade.
- **JSON para serialização de mensagens**: Fácil de usar e legível por humanos, facilitando a depuração.

### 3.3 Persistência

- **DurableObjectHandler**: Usado para armazenamento à prova de falhas do estado de cada nó. Isso permite que o sistema se recupere de falhas e continue a operação.

## 4. Instruções de Compilação e Execução

### 4.1 Pré-requisitos

- Python 3.6 ou superior
- Módulo `durable.py` no mesmo diretório que `paxos_node.py`

### 4.2 Execução

1. Abra três janelas de terminal, uma para cada nó.
2. Em cada terminal, navegue até o diretório contendo `paxos_node.py`.
3. Execute os seguintes comandos, um em cada terminal:

   ```
   python paxos_node.py A
   python paxos_node.py B
   python paxos_node.py C
   ```

4. Os nós começarão a se comunicar, e você verá a saída em cada terminal à medida que o consenso é alcançado para cada valor proposto.

### 4.3 Observações

- Certifique-se de que as portas 5000, 5001 e 5002 estão disponíveis em sua máquina.
- O diretório `paxos_data` será criado automaticamente para armazenar dados persistentes.

## 5. Limitações e Possíveis Melhorias

- Esta implementação assume uma rede estável e não lida com falhas de nós ou partições de rede.
- Em um ambiente de produção, seriam necessários mecanismos adicionais de tratamento de erros, registro de logs e recuperação.
- A implementação atual usa um líder fixo (Nó A). Um mecanismo de eleição de líder poderia ser implementado para maior robustez.
