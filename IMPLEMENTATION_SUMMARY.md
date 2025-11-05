# Resumo da Implementação - ArraiáTech

## Visão Geral

Sistema de gerenciamento para evento escolar (ArraiáTech) com funcionalidades de vendas, gestão de fichas, reservas antecipadas e dashboard administrativo.

## Funcionalidades Implementadas

### 1. Sistema de Autenticação

#### Login de Caixa

- **Rota**: `/caixa-login`
- **Funcionalidade**: Sistema de login para caixas com usuário e senha
- **Context**: `CaixaContext` gerencia estado de autenticação do caixa
- **Persistência**: Usa `localStorage` para manter sessão (`caixa_logged_id`)
- **Proteção de Rotas**: Rotas protegidas redirecionam para `/caixa-login` se não autenticado
- **Logout**: Hard refresh (`window.location.href`) para garantir limpeza completa de dados e cache

#### Login de Administrador

- **Rota**: `/admin-login`
- **Funcionalidade**: Sistema de login para administradores (usuário: "admin", senha: "admin123")
- **Context**: `AdminContext` gerencia estado de autenticação do admin
- **Comportamento**: Ao fazer login como admin, o caixa é automaticamente deslogado
- **Logout**: Hard refresh (`window.location.href`) para garantir limpeza completa

### 2. Gestão de Caixas

#### Modelo Caixa

- Campos: `nome`, `usuario`, `senha`
- Index único em `usuario` para login
- Senha armazenada em texto simples (não recomendado para produção)

#### Endpoints API

- `GET /api/caixas/` - Lista todos os caixas
- `POST /api/caixas/` - Cria novo caixa
- `GET /api/caixas/{id}/` - Detalhes do caixa
- `PUT /api/caixas/{id}/` - Atualiza caixa
- `PATCH /api/caixas/{id}/` - Atualização parcial
- `DELETE /api/caixas/{id}/` - Deleta caixa
- `POST /api/caixas/login/` - Login de caixa (retorna dados do caixa se credenciais corretas)

#### Página Administrativa

- **Rota**: `/admin-caixas`
- **Funcionalidades**:
  - Visualização em tabela com busca, ordenação e paginação
  - Criação de novos caixas
  - Edição de caixas (nome, usuário, senha)
  - Visualização de senha com toggle show/hide ou popup de confirmação
  - Exclusão de caixas
- **Estilo**: Layout compacto e profissional

### 3. Gestão de Produtos

#### Modelo Produto

- Campos: `nome`, `preco`, `estoque`, `medida`, `categoria`, `disponivel_para_reserva_antecipada`, `limite_quantidade_reserva`, `data_expiracao_reserva`
- Categorias: doce, salgado, bebida, jogos

#### Endpoints API

- `GET /api/produtos/` - Lista todos os produtos (incluindo fora de estoque para admin)
- `POST /api/produtos/` - Cria novo produto
- `GET /api/produtos/{id}/` - Detalhes do produto
- `PUT /api/produtos/{id}/` - Atualiza produto
- `PATCH /api/produtos/{id}/` - Atualização parcial
- `DELETE /api/produtos/{id}/` - Deleta produto

#### Página Administrativa

- **Rota**: `/admin-produtos`
- **Funcionalidades**:
  - Visualização em tabela com busca, ordenação e paginação
  - Exibição de categoria na listagem
  - Criação de novos produtos com seleção de categoria
  - Edição de produtos
  - Exclusão de produtos
  - Gerenciamento de reservas antecipadas via popup dedicado (`PopupReservasProduto`)
- **Estilo**: Layout compacto e profissional

### 4. Gestão de Fichas

#### Modelo Ficha

- Campos: `numero`, `saldo`, `is_active`, `deleted_at`, `deleted_by_caixa`
- Soft delete: Fichas não são removidas fisicamente, apenas marcadas como deletadas
- Histórico completo de movimentações disponível
- Método `recarga(valor)`: Adiciona valor ao saldo da ficha

#### Modelo Recarga

- Campos: `ficha`, `produto` (opcional), `caixa`, `valor`, `data`, `observacoes`
- Registra histórico completo de recargas de fichas
- Vinculado a ficha, produto (opcional) e caixa
- Data automática de criação
- Observações opcionais para cada recarga

#### Endpoints API

- `GET /api/fichas/` - Lista todas as fichas (incluindo deletadas para admin)
- `POST /api/fichas/` - Cria nova ficha (aceita `cpf_reserva` e `caixa_id` opcionais para vincular a reservas)
- `GET /api/fichas/{id}/` - Detalhes da ficha
- `PUT /api/fichas/{id}/` - Atualiza ficha
- `PATCH /api/fichas/{id}/` - Atualização parcial
- `DELETE /api/fichas/{id}/` - Deleta ficha (requer senha de admin)
- `POST /api/fichas/{id}/recarga/` - Recarrega ficha (registra histórico de recarga)
- `GET /api/fichas/{id}/historico/` - Histórico completo da ficha (movimentações, vendas, recargas, deleções)

#### Página Administrativa

- **Rota**: `/admin-fichas`
- **Funcionalidades**:
  - Visualização em tabela com busca, ordenação e paginação
  - Criação de novas fichas
  - Exclusão de fichas (requer senha de admin)
  - Visualização de histórico completo (popup com detalhes de todas as movimentações):
    - Histórico de vendas (produto, quantidade, valor, caixa, data/hora)
    - Histórico de recargas (valor, produto, caixa, data, observações)
    - Histórico de deleções (quem deletou e quando)
  - Exibição de fichas deletadas com informações de quem deletou e quando

#### Página de Caixa

- **Rota**: `/fichas`
- **Funcionalidades**:
  - Visualização de fichas ativas
  - Recarga de fichas (com histórico vinculado a produto e caixa)
  - Visualização de saldo
  - Mensagens de sucesso estruturadas para recargas
  - **Criação de fichas vinculadas a reservas**:
    - Busca de reservas pendentes por CPF
    - Exibição de informações da reserva (cliente, itens, valor total)
    - Validação de saldo mínimo (>= valor total das reservas)
    - Processamento automático ao criar ficha:
      - Diminuição de estoque dos produtos
      - Criação de vendas
      - Atualização de status das reservas para "finalizada"
      - Cálculo de saldo restante se recarga > valor total

### 5. Sistema de Vendas

#### Modelo Venda, MovimentacaoEstoque e Recarga

- **Venda**: Registra produto, quantidade, valor, ficha, caixa, data/hora
- **MovimentacaoEstoque**: Registra movimentações de entrada/saída de estoque
- **Recarga**: Registra recargas de fichas vinculadas a:
  - Ficha (obrigatório)
  - Produto (opcional)
  - Caixa (obrigatório)
  - Valor, data, observações
- Estoque é automaticamente atualizado ao realizar vendas

#### Página de Vendas

- **Rota**: `/vendas`
- **Funcionalidades**:
  - Seleção de ficha
  - Seleção de produtos
  - Registro de vendas
  - Atualização de estoque em tempo real
  - Mensagens de sucesso estruturadas e profissionais

### 6. Sistema de Reservas Antecipadas

#### Modelos

- `ReservaAntecipada`: Reserva principal com CPF, nome do usuário, data de criação
- `ReservaProduto`: Produtos reservados com quantidade e valor

#### Endpoints API

- `GET /api/reservas/` - Lista todas as reservas
- `POST /api/reservas/` - Cria nova reserva
- `GET /api/reservas/{id}/` - Detalhes da reserva
- `GET /api/reservas/gerar-qr-code/` - Gera QR code para impressão
- `GET /api/reservas/validar-reserva/{cpf}/` - Valida reserva por CPF
- `GET /api/reservas/pendentes_por_cpf/?cpf=XXX` - Busca reservas pendentes por CPF (para vinculação a ficha)

#### Página Pública de Reservas

- **Rota**: `/reservas/:qrCode`
- **Funcionalidade**: Página pública para usuários fazerem reservas antecipadas
- **Características**:
  - Design diferente do sistema interno
  - Formulário com CPF e nome completo
  - Seleção de produtos disponíveis para reserva
  - Limite de quantidade por produto (padrão: 2)
  - Exibição de resumo com preços individuais e total
  - Geração de screenshot para retirada no evento

#### Página Administrativa de Reservas

- **Rota**: `/admin-reservas`
- **Funcionalidades**:
  - Visualização de todas as reservas
  - Geração de QR codes para impressão
  - Download de PDF com QR codes
  - Controle de disponibilidade de produtos para reserva
  - Configuração de limites de quantidade e datas de expiração
  - **Visualização detalhada de reservas**:
    - Tabela completa com todas as reservas por QR code
    - Exibição fora do card para melhor visualização
    - Informações detalhadas: nome, CPF, produtos, quantidades, preços unitários, subtotais
    - Status de cada reserva (pendente, confirmada, cancelada, finalizada)
    - Total geral calculado automaticamente
    - Data e hora de cada reserva

### 7. Dashboard Administrativo

#### Endpoints API

- `GET /api/dashboard/data/` - Dados agregados do dashboard com predições ML e análise de reservas

#### Métricas Exibidas

- **KPIs Principais**:

  - Total de vendas (com indicador de crescimento percentual)
  - Receita total (com previsão de 3 dias)
  - Clientes ativos
  - Ticket médio

- **Gráficos**:

  - Tendência de vendas (últimos 7 dias) - Area Chart com gradientes
  - Vendas por horário (com predições ML) - Composed Chart (barras + linha)
  - Distribuição de vendas por categoria - Donut Chart com legenda detalhada
  - Top produtos mais vendidos - Bar Chart horizontal

- **Predições ML**:

  - Predição de demanda por horário (média móvel)
  - Tendência de crescimento (comparação de períodos)
  - Previsão de estoque necessário (baseado em média de vendas)
  - Produtos em risco de estoque (menos de 3 dias restantes)
  - Horários de pico (top 3)
  - Predição de receita futura (3 dias)
  - **Análise de reservas**:
    - Total de reservas pendentes e finalizadas
    - Taxa de conversão de reservas
    - Top 5 produtos mais reservados
    - Tendência dos últimos 7 dias (pendentes vs finalizadas)

- **Exportação**:
  - Exportação de vendas por horário
  - Exportação de vendas por categoria
  - Exportação de top produtos
  - Exportação de vendas detalhadas
  - **Exportação completa de todas as vendas** (com dados de caixa, ficha, produto, categoria)
  - Exportação de predições de demanda
  - Exportação de previsão de estoque

#### Página

- **Rota**: `/admin-dashboard`
- **Funcionalidades**:
  - Visualização de métricas em tempo real com design executivo
  - Gráficos interativos profissionais (Recharts)
  - Predições de Machine Learning para tomada de decisões
  - Exportação completa de dados em CSV
  - Mensagens informativas quando não há dados
  - Sistema funciona corretamente sem dados pré-registrados
- **Design**:
  - Layout profissional com cards com gradientes
  - Ícones contextuais nos KPIs
  - Indicadores visuais de crescimento
  - Cores profissionais e consistentes
  - Responsivo e mobile-first

### 8. Menu e Navegação

#### Menu Lateral

- **Informações do Caixa**: Exibidas apenas quando caixa está logado
- **Opções de Caixa**: Vendas, Fichas (apenas quando logado)
- **Opções de Admin**: Dashboard, Reservas Antecipadas, Gerenciar Caixas, Gerenciar Produtos, Gerenciar Fichas
- **Logout**: Botões de sair com hard refresh para garantir limpeza completa

#### Comportamento de Menu

- Informações do caixa só aparecem quando `isLoggedIn === true`
- Menu verifica diretamente `caixaContext.isLoggedIn === true` no JSX
- Não depende de variáveis intermediárias que podem ter valores desatualizados

### 9. Proteção de Rotas

#### Rotas Protegidas de Caixa

- `/` - HomePage
- `/vendas` - VendasPage
- `/fichas` - FichasPage
- Redirecionam para `/caixa-login` se não autenticado

#### Rotas Protegidas de Admin

- `/admin-dashboard` - Dashboard
- `/admin-reservas` - Reservas
- `/admin-caixas` - Caixas
- `/admin-produtos` - Produtos
- `/admin-fichas` - Fichas
- Redirecionam para `/admin-login` se não autenticado

#### Rotas Públicas

- `/caixa-login` - Login de caixa
- `/admin-login` - Login de admin
- `/reservas/:qrCode` - Reserva pública (sem layout)

### 10. Contextos e Estado

#### CaixaContext

- Gerencia estado de autenticação do caixa
- Persistência em `localStorage` (`caixa_logged_id`)
- Funções: `login()`, `logout()`
- Estados: `isLoggedIn`, `hasChecked`, `caixaData`, `caixa`
- `useEffect` de limpeza automática quando `isLoggedIn === false`
- Prevenção de recarregamento após logout usando `ref` (`hasInitialized`)

#### AdminContext

- Gerencia estado de autenticação do admin
- Funções: `login()`, `logout()`
- Estado: `isAdmin`

### 11. Melhorias de UI/UX

#### Layout de Tabelas

- Substituição de cards por tabelas em páginas administrativas
- Busca, ordenação e paginação
- Layout compacto e profissional

#### Barra de Filtros

- Componente `AdminFilters` reutilizável
- Busca horizontal ocupando mais espaço
- Filtros compactos ocupando menos espaço vertical

#### Menu Lateral

- Informações do caixa destacadas no topo
- Estilo visual diferenciado (verde para caixa, azul para itens ativos)
- Opções condicionais baseadas em autenticação

## Tecnologias Utilizadas

### Backend

- Django 4.x
- Django REST Framework
- SQLite (desenvolvimento)
- qrcode (Python) - para geração de QR codes
- reportlab - para geração de PDFs

### Frontend

- React 18.x
- TypeScript
- Vite
- React Router DOM
- Axios
- SCSS
- Recharts (gráficos)
- React Icons

## Arquitetura

### Estrutura de Pastas

#### Backend (`pi-back/`)

```
movimentacao/
  - models.py (Caixa, Ficha, Produto, Venda, MovimentacaoEstoque, Recarga, ReservaAntecipada, ReservaProduto)
  - views.py (ViewSets e endpoints, incluindo login de caixa e recarga de fichas)
  - serializers.py (incluindo RecargaSerializer)
  - urls.py
  - views_reserva.py (endpoints específicos de reservas)

dashboard/
  - views.py (endpoint de dashboard com predições ML e tratamento de dados vazios)

publico/
  - models.py (Sugestao)
```

#### Frontend (`pi-web/`)

```
src/
  - contexts/
    - AdminContext.tsx
    - CaixaContext.tsx
  - pages/
    - AdminLoginPage/
    - CaixaLoginPage/
    - AdminDashboardPage/ (com predições ML e design executivo)
    - AdminCaixasPage/
    - AdminProdutosPage/
    - AdminFichasPage/ (com histórico de recargas)
    - AdminReservasPage/ (com visualização detalhada de reservas)
    - ReservaPublicaPage/
    - HomePage/
    - VendasPage/
    - FichasPage/
  - components/
    - AdminFilters/
    - Popup/
      - PopupReservasProduto/
      - PopupFicha/ (com mensagens de sucesso estruturadas)
      - PopupVenda/ (com mensagens de sucesso estruturadas)
      - PopupNovaFicha/ (com mensagens de sucesso estruturadas)
  - services/
    - caixaService.ts
    - produtoService.ts
    - fichaService.ts (com histórico de recargas)
    - reservaService.ts
    - dashboardService.ts
  - hooks/
    - useDashboard.ts (com tipos para predições ML)
```

## Segurança e Autenticação

### Login de Caixa

- Autenticação via API (`/api/caixas/login/`)
- Validação de usuário e senha no backend
- Sessão persistida em `localStorage`
- Logout com hard refresh para garantir limpeza completa

### Login de Admin

- Autenticação local (frontend)
- Credenciais: usuário "admin", senha "admin123"
- Logout com hard refresh

### Proteção de Rotas

- Rotas protegidas verificam autenticação antes de renderizar
- Redirecionamento automático para páginas de login
- Contextos verificam estado de autenticação

## Deploy

### Railway

- Configuração via `Procfile`
- Build script: `build_files.sh`
- Runtime: Python 3.11.9 (definido em `runtime.txt`)
- **Configurações necessárias**:
  - Variável de ambiente `DATABASE_URL` (PostgreSQL do Railway - fornecida automaticamente)
  - Variável de ambiente `SECRET_KEY` (chave secreta do Django - obrigatória)
  - Variável de ambiente `DEBUG=False` para produção (opcional, padrão: False)
  - Variável de ambiente `ALLOWED_HOSTS` configurada para domínio do Railway (opcional)
  - Variável de ambiente `CSRF_TRUSTED_ORIGINS` com domínios do Railway (opcional)
  - `CORS_ALLOW_ALL_ORIGINS=True` configurado (ou restringir com `CORS_ALLOWED_ORIGINS`)
  - `STATIC_ROOT` configurado para coletar arquivos estáticos (`staticfiles/`)
  - `STATIC_URL` configurado para `/static/`
  - Migrations executadas automaticamente no build (`build_files.sh`)
  - `Procfile` configurado para usar `$PORT` do Railway
  - Build script (`build_files.sh`) executado automaticamente
- **Frontend**:
  - Variável de ambiente `VITE_API_BASE_URL` configurada para URL do backend
  - Build gera arquivos estáticos em `dist/`
  - Servidor usa `http-server-spa` para servir arquivos estáticos
- **Documentação**:
  - `RAILWAY_SETUP.md` criado com instruções detalhadas de deploy
  - `railway.json` criado com configurações do Railway

## Machine Learning Implementado

### Predições Simples

1. **Predição de Demanda por Horário**

   - Método: Média móvel simples (janela de 3 períodos)
   - Aplicação: Previsão para próximas 3 horas
   - Visualização: Linha tracejada no gráfico de vendas por horário

2. **Tendência de Vendas**

   - Método: Comparação linear de períodos
   - Período: Últimos 7 dias vs 7 dias anteriores
   - Resultado: Percentual de crescimento/decrescimento

3. **Previsão de Estoque**

   - Método: Média de vendas diárias dos últimos 7 dias
   - Cálculo: `estoque_recomendado = média_diária * 3`
   - Alertas: Produtos com menos de 3 dias de estoque restante

4. **Horários de Pico**

   - Método: Ordenação simples por quantidade de vendas
   - Resultado: Top 3 horários com mais vendas

5. **Predição de Receita**
   - Método: Média de receita diária dos últimos 7 dias
   - Aplicação: Previsão para próximos 3 dias

## Tratamento de Dados Vazios

### Sistema Funciona do Zero

O sistema foi testado e preparado para funcionar corretamente sem dados pré-registrados:

1. **Backend**:

   - Proteções contra divisão por zero
   - Arrays sempre inicializados (mesmo vazios)
   - Valores padrão (zeros) para métricas
   - Tratamento de erros com try/except

2. **Frontend**:

   - Mensagens informativas quando não há dados
   - Gráficos exibem dados padrão ou mensagens
   - Exportações condicionais (apenas quando há dados)
   - Renderização condicional de seções

3. **Gráficos**:
   - Funcionam com arrays vazios
   - Exibem mensagens informativas quando não há dados
   - Dados padrão para tendência (últimos 7 dias com zeros)

## Funcionalidades Recentes (Vinculação de Fichas a Reservas)

### Sistema de Vinculação de Fichas a Reservas

- **Criação de fichas vinculadas**:
  - Busca de reservas pendentes por CPF no popup de criação de ficha
  - Validação de saldo mínimo (>= valor total das reservas)
  - Processamento automático:
    - Diminuição de estoque dos produtos reservados
    - Criação de movimentações de estoque (saída)
    - Criação de vendas vinculadas à ficha
    - Atualização de status das reservas para "finalizada"
    - Cálculo de saldo restante se recarga > valor total
    - Registro de histórico de recarga inicial
- **Endpoint de busca**: `GET /api/reservas/pendentes_por_cpf/?cpf=XXX`
- **Dados de ML sobre reservas no dashboard**:
  - Estatísticas de reservas (pendentes, finalizadas, taxa de conversão)
  - Top 5 produtos mais reservados
  - Gráfico de tendência dos últimos 7 dias

## Melhorias Futuras

1. **Segurança**:

   - Hash de senhas (bcrypt ou similar)
   - Tokens JWT para autenticação
   - HTTPS em produção

2. **Machine Learning Avançado**:

   - Modelos mais sofisticados (regressão linear, séries temporais)
   - Análise de sazonalidade
   - Previsões de longo prazo
   - Recomendações de produtos baseadas em ML

3. **Performance**:

   - Paginação em endpoints de listagem
   - Cache de dados frequentes
   - Otimização de queries com `select_related` e `prefetch_related`
   - Lazy loading de gráficos

4. **PWA**:

   - Service workers
   - Offline support
   - Instalação como app

5. **Acessibilidade**:
   - Conformidade WCAG
   - Suporte a leitores de tela
   - Navegação por teclado

## Notas Importantes

- Senhas de caixa armazenadas em texto plano (NÃO recomendado para produção)
- Hard refresh necessário no logout para garantir limpeza completa de cache e estado
- Sistema de reservas antecipadas separado do sistema de vendas
- QR codes apenas para reservas, não para vendas/fichas
- Soft delete implementado para fichas (mantém histórico)
- **Sistema preparado para iniciar do zero**: Funciona corretamente sem dados pré-registrados
- **Predições ML são simples**: Média móvel e comparações lineares (não modelos complexos)
- **Exportação completa**: Inclui todos os dados relacionados (caixa, ficha, produto, categoria)
- **Histórico de recargas**: Vinculado a fichas, produtos e caixas com data e observações
- **Visualização de reservas**: Tabela detalhada fora do card para melhor visualização
- **Mensagens de sucesso**: Estruturadas e profissionais para vendas e recargas
- **Vinculação de fichas a reservas**: Sistema completo de criação de fichas vinculadas a reservas pendentes
- **Dados de ML sobre reservas**: Análise de reservas no dashboard com estatísticas e gráficos
