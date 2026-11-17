<div align="center">

# 👗 Brivony Gestão

**Pedidos, estoque e clientes de uma loja de roupas em um só lugar, direto do celular.**

[![CI](https://github.com/marcosoliveiradar/brivony-gestao/actions/workflows/ci.yml/badge.svg)](https://github.com/marcosoliveiradar/brivony-gestao/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)
![Cobertura](https://img.shields.io/badge/cobertura-93%25-brightgreen)
[![Licença: MIT](https://img.shields.io/badge/licença-MIT-blue.svg)](LICENSE)

[Sobre](#-sobre) · [Telas](#-telas) · [Funcionalidades](#-funcionalidades) · [Arquitetura](#-arquitetura) · [Como rodar](#-como-rodar) · [Testes e CI](#-testes-e-integração-contínua) · [Contribuir](#-como-contribuir)

</div>

---

## 📌 Sobre

A **Brivony** é uma loja de roupas de Bom Jesus dos Perdões (SP) que vende pelo Instagram e pelo WhatsApp. Os pedidos eram anotados à mão, o que levava a vender peça que já não tinha no tamanho, esquecer pagamentos pendentes e não saber o que repor.

O **Brivony Gestão** é o MVP que resolve isso: a dona registra a venda em segundos pelo celular, o estoque baixa sozinho e o painel mostra o que precisa de atenção.

> Projeto da disciplina **Projeto de Software — Experiência Prática III**, alinhado ao **ODS 8 (Trabalho decente e crescimento econômico)**. Todos os dados usados em testes, exemplos e imagens são **fictícios**.

## 📱 Telas

<p align="center">
  <img src="docs/img/telas.png" alt="Telas Painel, Novo pedido com alerta de estoque insuficiente e Estoque após o pedido" width="900">
</p>

| Painel | Novo pedido | Estoque |
|---|---|---|
| Resumo do mês, pedidos pendentes, alerta de estoque baixo e mais vendidas. | Busca a cliente pelo telefone, mostra o disponível e impede vender mais do que existe. | Confirma o pedido, mostra a baixa ("antes 2") e sinaliza o que repor. |

## ✨ Funcionalidades

| Requisito | O que faz |
|---|---|
| **RF01** Cadastro de peças | Nome, categoria, tamanho (PP a Único), cor, preço, estoque e foto. Peças são retiradas do catálogo, nunca apagadas, para não perder o histórico. |
| **RF02** Cadastro de clientes | Telefone único; aceita digitar com máscara e guarda só os números. |
| **RF03** Registrar pedido | Baixa o estoque automaticamente numa **transação atômica**. Se faltar peça, nada é gravado e aparece "Só restam 2 unidades do tamanho P. Ajuste a quantidade." |
| **RF04** Status do pedido | Aguardando pagamento → Pago → Separado → Entregue. |
| **RF05** Cancelamento | Devolve as peças ao estoque. Pedido entregue não pode ser cancelado. |
| **RF06** Painel | Vendido no mês, pedidos pendentes, peças com estoque baixo e as 3 mais vendidas. |

**Requisitos não funcionais**

- 🔒 **RNF01 Acesso:** login obrigatório em todas as telas; senhas com PBKDF2.
- 🛡️ **RNF02 Segurança (OWASP):** ORM, validação no servidor, CSRF, escape de HTML, `DEBUG` desligado por padrão, segredos em variáveis de ambiente. Preço e estoque vêm sempre do banco, nunca do formulário.
- ⚡ **RNF03 Desempenho:** CSS e ícones servidos pelo próprio sistema (sem CDN), comprimidos pelo WhiteNoise.
- ♿ **RNF04 Acessibilidade:** botão **A+** que aumenta o texto de todo o sistema, botões de 44×44 px, texto de 16 px, contraste mínimo de 4,5:1, rótulo visível em todo campo e alertas com **texto + ícone + cor**.

## 🏗️ Arquitetura

Monolito cliente-servidor no padrão **MVT** (Model–View–Template) do Django.

```mermaid
flowchart LR
    U["📱 Navegador do celular"] -- HTTPS --> W["Gunicorn + WhiteNoise"]
    W --> V["Views (loja/views.py)<br/>login obrigatório"]
    V --> F["Forms<br/>validação no servidor"]
    V --> S["Regras de negócio<br/>(loja/services.py)"]
    S --> M["Models (ORM)"]
    M --> DB[("PostgreSQL 16")]
    V --> T["Templates + Bootstrap 5.3"]
```

```mermaid
erDiagram
    CLIENTE ||--o{ PEDIDO : faz
    PEDIDO ||--|{ ITEM_PEDIDO : contem
    PRODUTO ||--o{ ITEM_PEDIDO : aparece_em
    PRODUTO {
        string nome
        string tamanho
        string cor
        decimal preco
        int quantidade_estoque
        bool ativo
    }
    CLIENTE {
        string nome
        string telefone "único"
        string instagram
    }
    PEDIDO {
        string status
        decimal total
        datetime criado_em
    }
    ITEM_PEDIDO {
        int quantidade
        decimal preco_unitario
    }
```

<details>
<summary><b>Estrutura de pastas</b></summary>

```
config/                    Configurações do projeto (settings, urls, wsgi)
loja/
  models.py                Produto, Cliente, Pedido, ItemPedido
  services.py              Regras de negócio (pedido, cancelamento, painel)
  forms.py                 Formulários com validação no servidor
  views.py                 Telas (todas exigem login)
  templates/loja/          HTML das telas
  management/commands/     popular_demo (dados fictícios)
  tests/                   Testes unitários e de integração
static/                    CSS, JavaScript e Bootstrap local
templates/                 Layout base e tela de login
docs/img/                  Imagens do README
.github/                   CI, modelos de PR e de issue
```
</details>

## 🚀 Como rodar

**Pré-requisitos:** Python 3.12 e, opcionalmente, PostgreSQL 16 (sem ele, o sistema usa SQLite).

```bash
git clone https://github.com/marcosoliveiradar/brivony-gestao.git
cd brivony-gestao
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # ajuste os valores
python manage.py migrate
python manage.py createsuperuser   # usuário de acesso
python manage.py popular_demo      # opcional: peças e clientes fictícios
python manage.py runserver
```

Acesse **http://127.0.0.1:8000** e entre com o usuário criado.

<details>
<summary><b>Variáveis de ambiente</b></summary>

| Variável | Para que serve | Padrão |
|---|---|---|
| `DJANGO_SECRET_KEY` | Chave secreta (obrigatória com DEBUG desligado) | — |
| `DJANGO_DEBUG` | `True` só em desenvolvimento | `False` |
| `DJANGO_ALLOWED_HOSTS` | Domínios aceitos, separados por vírgula | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origens HTTPS confiáveis em produção | — |
| `DATABASE_URL` | Ex.: `postgres://usuario:senha@host:5432/banco` | SQLite local |
| `ESTOQUE_BAIXO_LIMITE` | A partir de quantas unidades a peça entra em "Estoque baixo" | `1` |
</details>

<details>
<summary><b>Produção</b></summary>

```bash
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

Com `DJANGO_DEBUG=False`, os cookies de sessão e CSRF ficam restritos a HTTPS.
</details>

## 🧪 Testes e Integração Contínua

```bash
python manage.py test loja              # todos os testes
coverage run manage.py test loja && coverage report
```

| Tipo | Arquivo | O que verifica |
|---|---|---|
| Unitário | `test_models.py` | Unicidade, preço > 0, telefone, sinalização de estoque |
| Unitário | `test_services.py` | Baixa de estoque, atomicidade, mensagem de estoque, status, cancelamento, painel |
| Integração | `test_views.py` | Login obrigatório, fluxo completo do pedido, escape de HTML, CSRF, redirecionamento seguro |

A cada push e pull request, o **GitHub Actions** sobe um PostgreSQL 16 real, roda `check --deploy`, confere migrações, faz o build dos estáticos e executa os testes exigindo **cobertura mínima de 85%** ([ver execuções](https://github.com/marcosoliveiradar/brivony-gestao/actions)).

## 🔀 Fluxo de desenvolvimento

- Cada funcionalidade nasce numa branch (`feat/`, `fix/`, `test/`, `docs/`, `ci/`) e entra na `main` por **[Pull Request](https://github.com/marcosoliveiradar/brivony-gestao/pulls?q=is%3Apr)** com checklist de auto-revisão.
- Commits no padrão **[Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/)**.
- Histórico de versões no [CHANGELOG](CHANGELOG.md).

## 🗺️ Próximos passos

- [ ] Rodadas de validação de usabilidade com a loja parceira
- [ ] Relatório de vendas por período
- [ ] Foto da peça na tela de novo pedido
- [ ] Publicação em servidor com HTTPS

## 🤝 Como contribuir

Veja o [guia de contribuição](CONTRIBUTING.md). Erros e sugestões podem ser registrados em [Issues](https://github.com/marcosoliveiradar/brivony-gestao/issues/new/choose).

## 📄 Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE).

---

<div align="center">
Feito por <a href="https://github.com/marcosoliveiradar">@marcosoliveiradar</a> para a Brivony 💜
</div>
