# Plano de Implementação - ArraiáTech

## Histórico de Implementações

### Fase 1: Sistema Base

- ✅ Estrutura Django REST Framework
- ✅ Modelos básicos (Caixa, Ficha, Produto, Venda)
- ✅ API RESTful completa
- ✅ Frontend React com roteamento básico
- ✅ Páginas de vendas e fichas

### Fase 2: Sistema de Reservas Antecipadas

- ✅ Modelos de reserva (ReservaAntecipada, ReservaProduto)
- ✅ Geração de QR codes para reservas
- ✅ Página pública de reservas
- ✅ Página administrativa de gestão de reservas
- ✅ Download de PDF com QR codes
- ✅ Validação de reservas por CPF

### Fase 3: Dashboard Administrativo

- ✅ Endpoint de dashboard com métricas agregadas
- ✅ Gráficos de vendas por horário e categoria
- ✅ Top produtos mais vendidos
- ✅ Exportação de dados em CSV
- ✅ Visualização de receita e estatísticas
- ✅ **Predições simples de Machine Learning**:
  - Predição de demanda por horário (média móvel)
  - Tendência de vendas (comparação de períodos)
  - Previsão de estoque necessário
  - Produtos em risco de estoque
  - Horários de pico
  - Predição de receita futura
- ✅ **Melhorias visuais profissionais**:
  - Layout moderno com cards com gradientes
  - Gráficos melhorados (Area Chart, Composed Chart, Bar Chart)
  - Gráfico de rosca (donut) para categorias
  - Indicadores visuais de crescimento
  - Mensagens informativas para dados vazios
- ✅ **Exportação completa de dados**:
  - Exportação de todas as vendas com dados completos (caixa, ficha, produto, categoria)
  - Exportação de predições de demanda
  - Exportação de previsão de estoque
- ✅ **Tratamento de dados vazios**:
  - Sistema funciona corretamente sem dados pré-registrados
  - Arrays vazios retornados quando não há dados
  - Gráficos exibem mensagens informativas ou dados padrão
  - Sem erros de divisão por zero

### Fase 4: Melhorias de UI/UX

- ✅ Substituição de cards por tabelas em páginas admin
- ✅ Componente de filtros reutilizável (AdminFilters)
- ✅ Busca e ordenação em todas as páginas admin
- ✅ Paginação visual
- ✅ Layout compacto e profissional
- ✅ **Melhorias mobile-first**:
  - Menu hambúrguer com delay para melhor visualização
  - Estilizações responsivas em todas as páginas
  - Tabelas com overflow controlado e scroll otimizado
  - Layout adaptativo para diferentes tamanhos de tela

### Fase 5: Sistema de Autenticação

- ✅ Login de caixa com usuário e senha
- ✅ Login de administrador
- ✅ Proteção de rotas
- ✅ Contextos de autenticação (CaixaContext, AdminContext)
- ✅ Persistência de sessão em localStorage
- ✅ Logout com hard refresh

### Fase 6: Gestão Administrativa Completa

- ✅ CRUD completo de caixas (com visualização de senha)
- ✅ CRUD completo de produtos (com categorias)
- ✅ CRUD completo de fichas (com soft delete)
- ✅ Histórico completo de movimentações de fichas
- ✅ **Sistema de recargas**:
  - Histórico de recargas vinculado a fichas, produtos e caixas
  - Registro de data e valor de cada recarga
  - Visualização de recargas no histórico de fichas
- ✅ Gerenciamento de reservas antecipadas
- ✅ Popup dedicado para configurações de reservas
- ✅ **Visualização detalhada de reservas**:
  - Tabela completa com todas as reservas por QR code
  - Informações detalhadas (nome, CPF, produtos, quantidades, preços)
  - Exibição fora do card para melhor visualização
  - Total geral calculado automaticamente

### Fase 8: Vinculação de Fichas a Reservas

- ✅ **Criação de fichas vinculadas a reservas**:
  - Busca de reservas pendentes por CPF no popup de criação de ficha
  - Validação de saldo mínimo (>= valor total das reservas)
  - Processamento automático de reservas ao criar ficha:
    - Diminuição de estoque dos produtos reservados
    - Criação de movimentações de estoque (saída)
    - Criação de vendas vinculadas à ficha
    - Atualização de status das reservas para "finalizada"
    - Cálculo de saldo restante se recarga > valor total
    - Registro de histórico de recarga inicial
  - Mensagem de sucesso detalhada com informações da vinculação
- ✅ **Endpoint de busca de reservas pendentes**:
  - `GET /api/reservas/pendentes_por_cpf/?cpf=XXX` - Retorna reservas pendentes por CPF
  - Retorna dados do cliente, itens reservados e valor total
- ✅ **Dados de ML sobre reservas no dashboard**:
  - Total de reservas pendentes e finalizadas
  - Taxa de conversão de reservas
  - Top 5 produtos mais reservados
  - Gráfico de tendência dos últimos 7 dias (pendentes vs finalizadas)

### Fase 7: Dashboard com Machine Learning e Melhorias Profissionais

- ✅ **Predições simples de ML**:
  - Média móvel para previsão de demanda por horário
  - Tendência linear para análise de crescimento
  - Previsão de estoque baseada em média de vendas
  - Identificação de produtos em risco (menos de 3 dias de estoque)
  - Identificação de horários de pico
  - Predição de receita futura (3 dias)
  - **Análise de reservas**:
    - Total de reservas pendentes e finalizadas
    - Taxa de conversão de reservas
    - Produtos mais reservados
    - Tendência de reservas dos últimos 7 dias
- ✅ **Melhorias visuais profissionais**:
  - Design executivo com cards com gradientes e sombras
  - Gráfico de tendência (Area Chart) com gradientes
  - Gráfico combinado (barras + linha) para vendas por horário com predições
  - Gráfico de rosca (donut) para categorias com legenda detalhada
  - Gráfico de barras horizontal para top produtos
  - KPIs com indicadores visuais (crescimento, previsões)
  - Ícones nos cards de métricas
  - Mensagens informativas quando não há dados
- ✅ **Exportação completa**:
  - Exportação de todas as vendas com dados completos:
    - Dados da venda (ID, data, hora)
    - Dados do caixa (ID, nome, usuário)
    - Dados da ficha (ID, número, saldo)
    - Dados do produto (ID, nome, categoria, preço unitário)
    - Quantidade e valor total
  - Exportação de predições de demanda
  - Exportação de previsão de estoque
- ✅ **Tratamento robusto para iniciar do zero**:
  - Sistema funciona sem dados pré-registrados
  - Arrays vazios retornados quando não há dados
  - Valores padrão (zeros) para métricas
  - Proteção contra divisão por zero
  - Gráficos exibem mensagens informativas ou dados padrão
  - Exportações condicionais (apenas quando há dados)

## Mudanças Recentes (Sistema de Login e Logout)

### Implementações de Login de Caixa

1. **Modelo Caixa** (`movimentacao/models.py`)

   - Adicionados campos `usuario` e `senha`
   - Índice único em `usuario` para otimização de login

2. **Endpoint de Login** (`movimentacao/views.py`)

   - Novo endpoint `POST /api/caixas/login/`
   - Validação de credenciais
   - Retorna dados do caixa se credenciais corretas

3. **CaixaContext** (`pi-web/src/contexts/CaixaContext.tsx`)

   - Gerenciamento de estado de autenticação
   - Função `login(usuario, senha)` para autenticação
   - Função `logout()` para limpeza de dados
   - Persistência em `localStorage` (`caixa_logged_id`)
   - `useEffect` de inicialização que verifica sessão salva
   - `useEffect` de limpeza automática quando `isLoggedIn === false`
   - Prevenção de recarregamento usando `ref` (`hasInitialized`, `isLoggingOut`)

4. **CaixaLoginPage** (`pi-web/src/pages/CaixaLoginPage/`)

   - Página de login para caixas
   - Formulário com campos de usuário e senha
   - Integração com `CaixaContext`

5. **Proteção de Rotas** (`pi-web/src/router/index.tsx`)

   - Componente `ProtectedCaixaRoute` para rotas que requerem login de caixa
   - Redirecionamento automático para `/caixa-login` se não autenticado
   - Componente `LayoutWithCaixaProtected` que fornece `CaixaProvider`

6. **Menu** (`pi-web/src/router/Layout/components/Menu/index.tsx`)
   - Exibição de informações do caixa no topo do menu
   - Opções condicionais baseadas em `isLoggedIn === true`
   - Verificações diretas no JSX (sem variáveis intermediárias)
   - Logout com hard refresh (`window.location.href`)

### Implementações de Logout

1. **Logout de Caixa**

   - Limpeza de `localStorage` (`caixa_logged_id`, `caixa`)
   - Limpeza de estados (`caixa`, `caixaData`, `isLoggedIn`)
   - Hard refresh usando `window.location.href = "/caixa-login"`
   - Prevenção de race conditions usando `isLoggingOut` ref

2. **Logout de Admin**

   - Limpeza de estado de admin
   - Hard refresh usando `window.location.href = "/"`
   - Desloga caixa automaticamente ao fazer login como admin

3. **Menu**
   - Botão "Sair" aparece apenas quando caixa está logado
   - Botão "Sair do Dashboard" para admin
   - Ambos usam hard refresh para garantir limpeza completa

### Comportamento de Menu

1. **Informações do Caixa**

   - Exibidas apenas quando `isLoggedIn === true`
   - Verificação rigorosa: `hasChecked === true && isLoggedIn === true && caixaData !== undefined`
   - Estilo visual diferenciado (fundo verde)

2. **Opções de Menu**

   - "Vendas" e "Fichas" aparecem apenas quando caixa está logado
   - "Sair" aparece apenas quando caixa está logado
   - Informações persistem mesmo ao navegar para `/admin-login` (se caixa estiver logado)

3. **Opções de Admin**
   - Dashboard, Reservas, Caixas, Produtos, Fichas
   - "Sair do Dashboard" com hard refresh

### Gestão de Estado

1. **CaixaSelector**

   - Verifica `isLoggedIn === true` antes de definir `caixaData`
   - Limpa dados automaticamente se caixa não estiver logado
   - Previne redefinição de dados após logout

2. **useEffect de Limpeza**

   - Monitora `isLoggedIn` e `hasChecked`
   - Limpa dados quando `!isLoggedIn && hasChecked && !isLoggingOut`
   - Previne limpeza durante login ou inicialização

3. **Ordem de Operações no Logout**
   1. Marca `isLoggingOut = true`
   2. Limpa `localStorage`
   3. Chama `deleteStoredCaixaId()`
   4. Limpa estados (`caixa`, `caixaData`)
   5. Define `isLoggedIn = false`
   6. Define `hasChecked = true`
   7. Hard refresh após 300ms

## Estrutura de Rotas

### Rotas Públicas

- `/caixa-login` - Login de caixa
- `/admin-login` - Login de admin
- `/reservas/:qrCode` - Reserva pública (sem layout)

### Rotas Protegidas de Caixa

- `/` - HomePage
- `/vendas` - VendasPage
- `/fichas` - FichasPage

### Rotas Protegidas de Admin

- `/admin-dashboard` - Dashboard
- `/admin-reservas` - Reservas
- `/admin-caixas` - Caixas
- `/admin-produtos` - Produtos
- `/admin-fichas` - Fichas

## Arquivos Modificados/Adicionados

### Backend

- `movimentacao/models.py`:
  - Adicionados campos `usuario` e `senha` em `Caixa`
  - Modelo `Recarga` adicionado para histórico de recargas
- `movimentacao/views.py`:
  - Adicionado endpoint `login` em `CaixaViewSet`
  - Endpoint `recarga` em `FichaViewSet` atualizado para criar `Recarga`
  - Endpoint `historico` em `FichaViewSet` atualizado para incluir recargas
  - **Modificado `FichaViewSet.create()`**:
    - Aceita `cpf_reserva` e `caixa_id` opcionais
    - Busca reservas pendentes por CPF
    - Valida saldo mínimo >= valor total das reservas
    - Processa reservas automaticamente (diminui estoque, cria vendas, atualiza status)
    - Calcula saldo restante se recarga > valor total
  - **Adicionado `ReservaProdutoViewSet.pendentes_por_cpf()`**:
    - Action para buscar reservas pendentes por CPF
    - Retorna dados do cliente e itens reservados
- `movimentacao/serializers.py`:
  - Atualizado `CaixaSerializer` para lidar com senha
  - `RecargaSerializer` adicionado
  - `FichaHistoricoSerializer` atualizado para incluir recargas
- `dashboard/views.py`:
  - Adicionadas predições simples de ML
  - Tratamento robusto de dados vazios
  - Retorno de dados completos de vendas (caixa, ficha, produto, categoria)
  - Arrays sempre inicializados (mesmo vazios)
  - Proteções contra divisão por zero
  - **Adicionados dados de ML sobre reservas**:
    - Total de reservas pendentes e finalizadas
    - Taxa de conversão de reservas
    - Top 5 produtos mais reservados
    - Tendência dos últimos 7 dias (pendentes vs finalizadas)

### Frontend

- `src/contexts/CaixaContext.tsx` - Sistema completo de autenticação de caixa
- `src/pages/CaixaLoginPage/` - Página de login de caixa (nova)
- `src/router/index.tsx` - Proteção de rotas e `LayoutWithCaixaProtected`
- `src/router/Layout/index.tsx` - Lógica de redirecionamento e proteção
- `src/router/Layout/components/Menu/index.tsx` - Exibição condicional e logout
- `src/services/caixaService.ts` - Função `loginCaixa` adicionada
- `src/router/Layout/components/CaixaSelector/index.tsx` - Verificação de login antes de definir dados
- `src/pages/AdminDashboardPage/`:
  - Design executivo profissional
  - Gráficos melhorados (Area Chart, Composed Chart, Bar Chart, Donut Chart)
  - Predições ML visualizadas
  - Mensagens informativas para dados vazios
  - Exportação completa de dados
- `src/components/Popup/PopupFicha/index.tsx`:
  - Mensagens de sucesso estruturadas para recargas
  - Integração com histórico de recargas
- `src/components/Popup/PopupVenda/index.tsx`:
  - Mensagens de sucesso estruturadas para vendas
- `src/components/Popup/PopupNovaFicha/index.tsx`:
  - Mensagens de sucesso estruturadas para criação de fichas
- `src/pages/ReservasAdminPage/`:
  - Visualização detalhada de reservas em tabela
  - Exibição fora do card para melhor visualização
  - Total geral calculado automaticamente
- `src/pages/FichasAdminPage/`:
  - Visualização de histórico de recargas em tabela
  - Histórico completo de movimentações
- `src/components/Popup/PopupNovaFicha/`:
  - Seção para buscar reservas pendentes por CPF
  - Exibição de informações da reserva (cliente, itens, valor total)
  - Validação de saldo mínimo
  - Cálculo e exibição de saldo restante
  - Mensagem de sucesso detalhada com informações da vinculação
- `src/services/reservaService.ts`:
  - Função `getReservasPendentesPorCPF()` para buscar reservas pendentes
  - Tipos TypeScript para `ReservaPendente` e `ReservasPendentesResponse`
- `src/services/fichaService.ts`:
  - Tipo `NovaFicha` atualizado com `cpf_reserva` e `caixa_id` opcionais
- `src/pages/AdminDashboardPage/`:
  - Nova seção "Análise de Reservas" com estatísticas e gráficos
  - Visualização de produtos mais reservados
  - Gráfico de tendência dos últimos 7 dias

## Decisões de Design

1. **Hard Refresh no Logout**

   - Garante limpeza completa de cache e estado
   - Previne problemas de sincronização
   - Solução robusta para garantir funcionamento correto

2. **Verificações Diretas no JSX**

   - Evita problemas com variáveis intermediárias
   - Garante que verificações sejam sempre atuais
   - Mais legível e manutenível

3. **Flags de Controle**

   - `hasInitialized` - Previne recarregamento após logout
   - `isLoggingOut` - Previne race conditions durante logout
   - `hasChecked` - Indica que verificação inicial foi concluída

4. **Prevenção de Recarregamento**
   - `useEffect` inicial executa apenas uma vez
   - Verificação de `isLoggingOut` antes de carregar dados
   - Limpeza automática quando `isLoggedIn === false`

## Detalhes Técnicos das Predições ML

### 1. Predição de Demanda por Horário

- **Método**: Média móvel simples
- **Janela**: 3 períodos anteriores
- **Aplicação**: Previsão para próximas 3 horas
- **Resultado**: Linha tracejada no gráfico de vendas por horário

### 2. Tendência de Vendas

- **Método**: Comparação linear de períodos
- **Período de análise**: Últimos 7 dias vs 7 dias anteriores
- **Cálculo**: `((média_últimos_7 - média_anteriores_7) / média_anteriores_7) * 100`
- **Exibição**: Indicador de crescimento percentual nos KPIs

### 3. Previsão de Estoque

- **Método**: Média de vendas diárias dos últimos 7 dias
- **Cálculo**: `estoque_recomendado = média_diária * 3` (3 dias de estoque)
- **Aplicação**: Tabela de previsão de estoque necessário
- **Alertas**: Produtos com menos de 3 dias de estoque restante

### 4. Horários de Pico

- **Método**: Ordenação simples por quantidade de vendas
- **Resultado**: Top 3 horários com mais vendas
- **Exibição**: Cards com ranking visual

### 5. Predição de Receita

- **Método**: Média de receita diária dos últimos 7 dias
- **Aplicação**: Previsão para próximos 3 dias
- **Exibição**: Card de Receita com previsão

## Tratamento de Dados Vazios (Iniciar do Zero)

### Backend (`dashboard/views.py`)

1. **Proteções contra divisão por zero**:

   - `ticket_medio = float(receita) / total_vendas if total_vendas > 0 else 0`
   - Verificações antes de calcular médias

2. **Arrays sempre inicializados**:

   - `vendas_list = []` - só processa se `vendas.exists()`
   - `categoria_formatada = []` - sempre retorna lista (mesmo vazia)
   - `tendenciaVendas`: arrays vazios quando não há dados
   - `vendas_por_horario`: sempre inicializado com 24 horas em zero

3. **Predições condicionais**:

   - Verificações de `len()` antes de processar
   - Valores padrão quando não há dados suficientes
   - Arrays vazios retornados quando não há histórico

4. **Tratamento de erros**:
   - Try/except ao processar vendas por horário
   - Validação de existência de objetos relacionados

### Frontend (`AdminDashboardPage/index.tsx`)

1. **Gráficos com estados vazios**:

   - Vendas por categoria: mensagem informativa quando vazio
   - Top produtos: mensagem informativa quando vazio
   - Tendência: dados padrão dos últimos 7 dias (zeros) quando não há histórico

2. **Exportação condicional**:

   - Botões de exportação só aparecem quando há dados
   - Verificação `array && array.length > 0` antes de renderizar

3. **Renderização condicional**:
   - Seções de alertas e previsões só aparecem quando há dados
   - Verificações rigorosas antes de mapear arrays

## Melhorias de UI/UX Profissionais

### Design Executivo

- **Cards de KPIs**:

  - Gradiente superior colorido
  - Hover effects com elevação
  - Ícones contextuais
  - Indicadores visuais de crescimento
  - Previsões destacadas

- **Gráficos**:

  - Cores profissionais e consistentes
  - Tooltips estilizados
  - Labels nos eixos
  - Gradientes em gráficos de área
  - Bordas arredondadas

- **Layout**:
  - Grid responsivo para KPIs
  - Gráficos em coluna (tendência e horário full width)
  - Grid para categorias e top produtos
  - Espaçamento harmonioso

### Mensagens Informativas

- Mensagens claras quando não há dados
- Ícones contextuais
- Texto explicativo sobre o que aparecerá quando houver dados

## Próximos Passos Sugeridos

1. **Deploy no Railway**

   - ✅ Configuração de variáveis de ambiente (SECRET_KEY, DATABASE_URL, DEBUG, ALLOWED_HOSTS)
   - ✅ Configuração de PostgreSQL via DATABASE_URL
   - ✅ Configuração de static files (STATIC_ROOT, collectstatic)
   - ✅ Configuração de CORS e CSRF para produção
   - ✅ Procfile configurado para usar PORT do Railway
   - ✅ Runtime Python 3.11.9 configurado
   - ✅ Build script (build_files.sh) configurado
   - ✅ Frontend configurado para usar variáveis de ambiente (VITE_API_BASE_URL)
   - 📝 Documentação de setup (RAILWAY_SETUP.md) criada

2. **Segurança**

   - Implementar hash de senhas (bcrypt)
   - Adicionar tokens JWT
   - Implementar HTTPS

3. **Machine Learning Avançado**

   - Modelos mais sofisticados (regressão linear, séries temporais)
   - Análise de sazonalidade
   - Previsões de longo prazo
   - Recomendações de produtos

4. **Melhorias de UX**

   - Mensagens de erro mais claras
   - Loading states durante login
   - Feedback visual de ações
   - Animações suaves

5. **Testes**

   - Testes unitários para autenticação
   - Testes de integração para fluxo completo
   - Testes E2E para login/logout
   - Testes de predições ML

6. **Documentação**
   - Documentação de API
   - Guia de uso para administradores
   - Guia de desenvolvimento
   - Documentação de predições ML
