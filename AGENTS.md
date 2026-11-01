# AGENTS.md

Operating guide for AI coding agents working in this repository (`pi-back`).

## Project overview

Django + Django REST Framework backend for the PI (festa junina) stock & voucher
management system: cash registers (`Caixa`), voucher/ficha tokens (`Ficha`),
products (`Produto`), stock movements (`MovimentacaoEstoque`), sales (`Venda`),
advance reservations (`ReservaProduto`) and QR-code based public reservations
(`QRCodeReserva`). It also exposes a dashboard endpoint plus ML demand forecasting.

The frontend lives in the sibling repository `../pi-web` (React + Vite + TS). Keep the
API contract in sync with that repo — see [Web counterpart](#web-counterpart-pi-web).

## Tech stack

- Python 3.12, Django 4.2, Django REST Framework 3.15, django-cors-headers, dj-database-url
- Database: SQLite locally (`db.sqlite3`), PostgreSQL in production via `DATABASE_URL`
- ML: scikit-learn (`dashboard/predictions.py`, `dashboard/synthetic_forecasting.py`)
- QR codes: `qrcode`; PDF (QR label): `reportlab`; images: `Pillow`

## Repository layout

- `projetoIntegrador1/` – Django project config (settings, root URLconf, wsgi/asgi)
- `movimentacao/` – core domain app (models, DRF viewsets, serializers, public reservation endpoints)
- `dashboard/` – analytics API (`/dashboard/data/`) + forecasting modules
- `publico/` – public suggestions app (currently not mounted in the root URLconf; legacy)
- `templates/` – operational/orchestration templates (Bernstein artifacts) — do not hand-edit casually
- `dashboard/fixtures/synthetic_event_history.json` – synthetic festa junina event history fixture
- `movimentacao/management/commands/populate_dev.py` – demo-data command (`--reset`)
- `venv/`, `db.sqlite3`, `static/`, `build_files.sh`, `PYTHONANYWHERE_SETUP.md`

## Commands

Run from the repository root with the virtualenv active:

```bash
python manage.py runserver
python manage.py migrate
python manage.py populate_dev --reset   # demo data for the festa junina scenario
python manage.py test --verbosity=2
python manage.py makemigrations
```

There is no pytest setup — Django's built-in test runner is used (`python manage.py test`).

The frontend is NOT part of this repo; work on it in `/Users/motokiyo/pi-web`.

## Environment variables

`.env.example`:

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `CORS_ALLOWED_ORIGIN_REGEXES`
- `FRONTEND_URL` – public frontend URL used to build QR-code links (`{FRONTEND_URL}/reservas/{codigo}`)
- `ADMIN_USERNAME`, `ADMIN_PASSWORD` – app-level admin credentials (used by `admin_login` and ficha deletion)
- `DATABASE_URL` – Postgres connection string when set (dj-database-url); otherwise SQLite

## API surface

Root URLconf mounts: `movimentacao/`, `dashboard/`, `admin/`.

### `/movimentacao/`

- `CaixaViewSet`: CRUD at `/movimentacao/caixas/` + `POST /movimentacao/caixas/login/`
- `FichaViewSet`: CRUD at `/movimentacao/fichas/`; actions `POST .../recarga/`, `GET .../historico/`; `DELETE .../` performs **soft delete** (body: `{ senha_admin, caixa_id? }`)
- `ProdutoViewSet`: CRUD at `/movimentacao/produtos/` (SearchFilter on `nome`)
- `MovimentacaoEstoqueViewSet`: CRUD at `/movimentacao/movimentacoes-estoque/`
- `VendaViewSet`: CRUD at `/movimentacao/vendas/`
- Reservas: router + `POST /movimentacao/reservas/{id}/confirmar/`, `GET /movimentacao/reservas/pendentes_por_cpf/?cpf=...`
- QR codes: `GET/POST /movimentacao/qr-codes-reserva/`, `GET/PATCH/DELETE .../{id}/`, `GET .../{id}/reservas/`, `POST .../{id}/gerar_pdf/`, `POST /movimentacao/qr-codes-reserva/criar_qr_code/`
- Public (AllowAny): `GET /movimentacao/reservas-publicas/{qr_code}/produtos/`, `POST /movimentacao/reservas-publicas/criar/`, `GET /movimentacao/reservas-publicas/por-cpf/?cpf=...`
- Financial ledger: `GET /movimentacao/movimentacoes-financeiras/`

### `/dashboard/data/`

`GET` returns dashboard aggregates: totals, ticket average, sales per hour/category, top products,
sales details, ML predictions (`predicaoDemanda`, `previsaoDemandaProdutos`, `predicaoReceita3Dias`,
`produtosEstoquePrevisao`, `produtosRiscoEstoque`, `horariosPico`, `tendenciaVendas`, `confiancaPredicoes`, `reservas`).

### `/admin/`

Django admin (standard).

## Domain invariants & conventions

- Stock in/out is modeled through `MovimentacaoEstoque` and must keep `Produto.estoque`
  consistent; mutations run inside `transaction.atomic()` with `select_for_update()` (see
  `MovimentacaoEstoque.save/delete` and `Venda.save`).
- `Venda` is a OneToOne of `MovimentacaoEstoque` (sale side of a stock-out) and atomically
  debits the linked `Ficha.saldo`; historical sale prices are kept (`valor_unitario`/`valor_total`).
- Soft delete for `Ficha` (`is_active`, `deleted_at`, `deleted_by_caixa`); do not hard-delete fichas.
- Reservation uniqueness: `UniqueConstraint(fields=['cpf', 'produto', 'status'], condition=Q(status__in=['pendente','confirmada']))`.
- Dates: `USE_TZ = True`, `TIME_ZONE = 'America/Sao_Paulo`, `LANGUAGE_CODE = 'pt-BR'`.
- Amounts: `Decimal` with `max_digits=10`, `decimal_places=2`.
- Passwords: hashed via `make_password` (`Caixa.set_senha`); legacy plaintext accepted via `is_encoded_password`/`check_password`.
- Admin credential checks use `constant_time_compare` against `settings.ADMIN_USERNAME/PASSWORD`.

## Tests & CI

- Django tests live next to apps: `movimentacao/tests.py`, `dashboard/tests.py`, `dashboard/test_synthetic_history.py`.
- CI (`.github/workflows/ci.yml`) runs `python manage.py test` (Python 3.12, `SECRET_KEY` env) on push/PR to `main`,
  and deploys the backend to PythonAnywhere on push to `main`.
- Changing `requirements.txt` or adding migrations requires a manual step on PythonAnywhere before deploy.

## Deployment

- PythonAnywhere (free plan, SQLite): see `PYTHONANYWHERE_SETUP.md` and `build_files.sh`; CI deploy workflow present.

## Web counterpart (`pi-web`)

When changing request/response shapes consumed by the frontend, update both sides:

- Backend DTO field names (snake_case) vs frontend TypeScript types in `src/services/*`.
- Dashboard responses use camelCase keys (`totalVendas`, `ticketMedio`, ...) — keep stable for the charts.
- Backend `FRONTEND_URL` must match the deployed frontend origin for QR generation.
