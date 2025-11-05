# Configuração para Deploy no Railway

## Variáveis de Ambiente Necessárias

Configure as seguintes variáveis de ambiente no Railway:

1. **SECRET_KEY** (obrigatório)

   - Chave secreta do Django para produção
   - Gere uma nova chave: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
   - Exemplo: `django-insecure-jsoka*xk5w4x@u#b2^t5yrm=ve0x4!$9#6n&gwy&sxi7zcru60`

2. **DATABASE_URL** (obrigatório)

   - URL do banco PostgreSQL fornecida pelo Railway
   - Formato: `postgresql://user:password@host:port/dbname`
   - O Railway fornece automaticamente quando você adiciona um serviço PostgreSQL

3. **DEBUG** (opcional, recomendado)

   - Defina como `False` para produção
   - Padrão: `False`

4. **ALLOWED_HOSTS** (opcional)

   - Hosts permitidos separados por vírgula
   - Padrão: `localhost,127.0.0.1,api-arraiatech.up.railway.app`
   - Adicione o domínio do seu serviço Railway
   - **IMPORTANTE**: Adicione o domínio fornecido pelo Railway após o deploy

5. **CSRF_TRUSTED_ORIGINS** (opcional)

   - Origins confiáveis para CSRF separados por vírgula
   - Padrão: `https://arraia-tech.up.railway.app,https://api-arraiatech.up.railway.app,http://localhost:8080,http://127.0.0.1:8080`
   - Adicione o domínio do seu frontend Railway
   - **IMPORTANTE**: Adicione o domínio do frontend para permitir requisições

6. **FRONTEND_URL** (opcional, recomendado para QR codes)
   - URL base do frontend para geração de QR codes
   - Padrão: `https://arraiatech.up.railway.app`
   - Use esta variável para que os QR codes apontem para a URL correta
   - Exemplo: `https://arraiatech.up.railway.app` (sem barra final)

## Passos para Deploy

1. **Criar projeto no Railway**

   - Acesse https://railway.app
   - Crie um novo projeto
   - Adicione um serviço PostgreSQL

2. **Configurar variáveis de ambiente**

   - Adicione `SECRET_KEY` (gere uma nova chave única para produção)
   - Adicione `DATABASE_URL` (o Railway fornece automaticamente quando você adiciona PostgreSQL)
   - Adicione `DEBUG=False`
   - Adicione `ALLOWED_HOSTS` com o domínio do seu serviço (você pode adicionar depois de ver o domínio)
   - Adicione `CSRF_TRUSTED_ORIGINS` com o domínio do frontend (você pode adicionar depois de fazer deploy do frontend)

3. **Conectar repositório Git**

   - Conecte seu repositório ao Railway
   - O Railway detectará automaticamente o `Procfile` e `requirements.txt`

4. **Build e Deploy**

   - O Railway executará automaticamente o `build_files.sh`:
     - `pip install -r requirements.txt`
     - `python manage.py migrate`
     - `python manage.py collectstatic --noinput`
   - Em seguida, o Railway executará o `Procfile`:
     - `gunicorn projetoIntegrador1.wsgi:application --bind 0.0.0.0:$PORT --log-file -`
   - O Railway define automaticamente a variável `PORT`

5. **Configurar domínio**
   - No Railway, vá em Settings > Networking
   - Gere um domínio customizado ou use o domínio `.railway.app` fornecido
   - Anote a URL do serviço (será algo como `https://seu-servico.up.railway.app`)
   - Adicione o domínio em `ALLOWED_HOSTS` (variável de ambiente)
   - Adicione o domínio do frontend em `CSRF_TRUSTED_ORIGINS` (variável de ambiente)
   - Faça o deploy novamente após adicionar as variáveis

## Configuração de CORS

O projeto está configurado com `CORS_ALLOW_ALL_ORIGINS = True` para desenvolvimento.
Para produção, considere restringir os origins adicionando a variável de ambiente `CORS_ALLOWED_ORIGINS`:

```
CORS_ALLOWED_ORIGINS=https://arraia-tech.up.railway.app,https://seu-dominio-frontend.com
```

Ou mantenha `CORS_ALLOW_ALL_ORIGINS = True` se preferir (não recomendado para produção).

## Banco de Dados

O Railway usa PostgreSQL automaticamente quando você adiciona um serviço PostgreSQL.
O `dj-database-url` detecta automaticamente a `DATABASE_URL` e configura o banco.

## Arquivos Estáticos

Os arquivos estáticos são coletados durante o build através do `collectstatic`.
O Railway serve os arquivos estáticos automaticamente.

## Migrations

As migrations são executadas automaticamente durante o build através do `build_files.sh`.
Certifique-se de que todas as migrations estão commitadas no repositório.

## Troubleshooting

### Erro de conexão com banco

- Verifique se `DATABASE_URL` está configurada corretamente
- Verifique se o serviço PostgreSQL está ativo no Railway

### Erro de static files

- Verifique se `STATIC_ROOT` está configurado corretamente
- Verifique se `collectstatic` está sendo executado no build

### Erro de CORS

- Verifique se o domínio do frontend está em `CORS_ALLOWED_ORIGINS` ou `CORS_ALLOW_ALL_ORIGINS=True`
- Verifique se `CSRF_TRUSTED_ORIGINS` inclui o domínio do frontend

### Erro de ALLOWED_HOSTS

- Verifique se o domínio do Railway está em `ALLOWED_HOSTS`
- Adicione o domínio fornecido pelo Railway
- Verifique se a variável de ambiente `ALLOWED_HOSTS` está configurada corretamente

### Erro de CSRF

- Verifique se o domínio do frontend está em `CSRF_TRUSTED_ORIGINS`
- Adicione o domínio do frontend fornecido pelo Railway
- Verifique se a variável de ambiente `CSRF_TRUSTED_ORIGINS` está configurada corretamente

### Erro de porta

- O Railway define automaticamente a variável `PORT`
- O `Procfile` usa `$PORT` para definir a porta do Gunicorn
- Verifique se o `Procfile` está correto: `web: gunicorn projetoIntegrador1.wsgi:application --bind 0.0.0.0:$PORT --log-file -`

## Checklist de Deploy

Antes de fazer deploy, verifique:

- [ ] Serviço PostgreSQL adicionado no Railway
- [ ] Variável `SECRET_KEY` configurada (gere uma nova chave para produção)
- [ ] Variável `DATABASE_URL` configurada (fornecida automaticamente pelo Railway)
- [ ] Variável `DEBUG=False` configurada
- [ ] Variável `ALLOWED_HOSTS` configurada com o domínio do Railway
- [ ] Variável `CSRF_TRUSTED_ORIGINS` configurada com o domínio do frontend
- [ ] Todas as migrations estão commitadas
- [ ] `Procfile` está correto
- [ ] `requirements.txt` está atualizado
- [ ] `runtime.txt` está configurado (Python 3.11.9)
- [ ] `build_files.sh` está configurado e executável
