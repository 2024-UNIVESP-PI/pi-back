# Fundamentação teórica: estabilidade em picos de acesso

## Objetivo

Estabilidade em picos significa manter o serviço correto e responsivo quando a
taxa de requisições aumenta durante o evento. A análise abaixo é teórica: não
define uma capacidade numérica sem um teste de carga controlado.

## Modelo de capacidade

O throughput útil é limitado pelo recurso mais disputado (CPU, banco, rede ou
limite da hospedagem). Pela teoria de filas, a utilização `ρ = λ/μ` deve ficar
abaixo de 1; quando `ρ` se aproxima de 1, a fila e a latência crescem de forma
acentuada. A Lei de Little (`L = λW`) relaciona requisições no sistema (`L`),
taxa de chegada (`λ`) e tempo médio no sistema (`W`). Portanto, reduzir
consultas e o tempo de transação reduz a quantidade de requisições acumuladas.

## Aplicação ao ArraiáTech

- O frontend é estático e pode atender a interface sem manter sessões no
  servidor.
- A API Django REST concentra autenticação, reservas e operações de estoque.
- Vendas, recargas e confirmações usam transações atômicas e bloqueio de linhas,
  preservando saldo e estoque quando há concorrência.
- Consultas do dashboard são agregadas e previsões são calculadas a partir do
  histórico; esse endpoint deve ser observado em horários de pico.
- PostgreSQL é o cenário recomendado para produção. SQLite limita escritores
  concorrentes e pode aumentar a espera em operações simultâneas.

## Degradação e observabilidade

Sob saturação, o comportamento esperado é rejeitar requisições excedentes com
erro controlado, preservar transações já iniciadas e permitir nova tentativa,
em vez de deixar saldo ou estoque parcialmente gravados. Para validar números
futuramente, medir latência de p50/p95/p99, taxa de erro, throughput e uso de
CPU/banco em cargas progressivas, incluindo o pior horário do evento.

Esta fundamentação apoia a arquitetura atual, mas não substitui teste de carga
nem comprova a capacidade máxima do ambiente PythonAnywhere.
