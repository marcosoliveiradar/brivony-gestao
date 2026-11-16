# Brivony Gestão

![CI](https://github.com/marcosoliveiradar/brivony-gestao/actions/workflows/ci.yml/badge.svg)

MVP de gestão de **pedidos, estoque e clientes** para a Brivony, loja de roupas que vende pelo Instagram e pelo WhatsApp. Hoje os pedidos são anotados à mão, o que causa venda de peça sem estoque e retrabalho. O sistema concentra tudo em um só lugar, pensado para uso pelo celular.

Projeto da disciplina **Projeto de Software (Experiência Prática III)**, alinhado ao **ODS 8 — Trabalho decente e crescimento econômico**.

> Todos os dados usados em testes, exemplos e prints são **fictícios**.

## Funcionalidades

| Requisito | Descrição | Onde |
|---|---|---|
| RF01 | Cadastro de peças (nome, categoria, tamanho, cor, preço, estoque, foto). Peças são inativadas, nunca excluídas | Tela Estoque |
| RF02 | Cadastro de clientes com telefone único | Tela Clientes |
| RF03 | Registro de pedido com baixa automática de estoque em transação atômica. Quantidade acima do estoque é recusada com a mensagem "Só restam N unidades..." | Tela Novo pedido |
| RF04 | Status do pedido: aguardando pagamento, pago, separado, entregue | Detalhe do pedido |
| RF05 | Cancelamento devolve as peças ao estoque | Detalhe do pedido |
| RF06 | Painel: vendido no mês, pedidos pendentes, estoque baixo e mais vendidas | Tela Painel |

Requisitos não funcionais atendidos:

- **RNF01 Segurança de acesso:** todas as telas exigem login (`LoginRequiredMixin`); senhas com PBKDF2 (padrão do Django).
- **RNF02 Proteção de entradas (OWASP):** consultas pelo ORM, validação no servidor, CSRF, escape automático dos templates, `DEBUG` desligado por padrão, segredos em variáveis de ambiente, `.env` fora do Git. Preço e estoque vêm sempre do banco, nunca do formulário.
- **RNF04 Acessibilidade:** botões com no mínimo 44×44 px, texto de 16 px, contraste mínimo de 4,5:1, rótulos visíveis em todos os campos e alertas com texto + ícone + cor.

## Tecnologias

Python 3.12 · Django 5.1 · Bootstrap 5.3 · PostgreSQL 16 (psycopg 3) · Gunicorn · WhiteNoise · Django TestCase · GitHub Actions.

Arquitetura **cliente-servidor monolítica no padrão MVT** (Model–View–Template).

```
config/                 Configurações do projeto Django
loja/
  models.py             Produto, Cliente, Pedido, ItemPedido
  services.py           Regras de negócio (pedido, cancelamento, painel)
  forms.py              Formulários com validação no servidor
  views.py              Telas (todas exigem login)
  templates/loja/       HTML das telas
  tests/                Testes unitários e de integração
static/                 CSS e JavaScript
templates/              Layout base e tela de login
.github/workflows/ci.yml  Pipeline de Integração Contínua
```

## Como rodar localmente

Pré-requisitos: Python 3.12 e, opcionalmente, PostgreSQL 16.

```bash
git clone https://github.com/marcosoliveiradar/brivony-gestao.git
cd brivony-gestao
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # ajuste os valores
# Sem DATABASE_URL no .env, o sistema usa SQLite automaticamente.

python manage.py migrate
python manage.py createsuperuser # cria o usuário de acesso
python manage.py popular_demo    # opcional: peças e clientes fictícios
python manage.py runserver
```

Acesse http://127.0.0.1:8000 e entre com o usuário criado.

### Variáveis de ambiente

| Variável | Para que serve | Padrão |
|---|---|---|
| `DJANGO_SECRET_KEY` | Chave secreta (obrigatória com DEBUG desligado) | — |
| `DJANGO_DEBUG` | `True` só em desenvolvimento | `False` |
| `DJANGO_ALLOWED_HOSTS` | Domínios aceitos, separados por vírgula | `localhost,127.0.0.1` |
| `DATABASE_URL` | Ex.: `postgres://usuario:senha@host:5432/banco` | SQLite local |
| `ESTOQUE_BAIXO_LIMITE` | Quantidade a partir da qual a peça entra em "Estoque baixo" | `1` |

## Testes

```bash
python manage.py test loja            # roda todos os testes
coverage run manage.py test loja      # com cobertura
coverage report
```

- **Unitários** (`test_models.py`, `test_services.py`): validam modelos e regras de negócio isoladas, como baixa de estoque, mensagem de estoque insuficiente, atomicidade, cancelamento e números do painel.
- **Integração** (`test_views.py`): percorrem as telas de ponta a ponta com o cliente de testes do Django, incluindo login obrigatório, fluxo completo do novo pedido, escape de HTML, CSRF e redirecionamentos seguros.

## Integração Contínua

A cada push e pull request para `main`, o GitHub Actions (`.github/workflows/ci.yml`):

1. instala Python 3.12 e as dependências;
2. sobe um PostgreSQL 16 de verdade;
3. roda `manage.py check --deploy` e verifica migrações pendentes;
4. faz o build dos arquivos estáticos (`collectstatic`);
5. executa os testes com cobertura mínima de 85%.

## Fluxo de trabalho no Git

- Cada funcionalidade é feita em uma branch (`feat/...`, `test/...`, `ci/...`) e entra na `main` por **Pull Request** com checklist de auto-revisão.
- Commits seguem o padrão **Conventional Commits**: `feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`.

## Produção

```bash
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

Com `DJANGO_DEBUG=False`, os cookies de sessão e CSRF ficam restritos a HTTPS.
