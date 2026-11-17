# Changelog

Todas as mudanças relevantes do projeto ficam registradas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado

- Botão "A+" que aumenta todo o texto do sistema de 16 px para 20 px e lembra a escolha no aparelho (RNF04) (#6).

## [0.1.0] - 2026-11-16

Primeira versão do MVP.

### Adicionado

- Pipeline de Integração Contínua no GitHub Actions com PostgreSQL 16 e cobertura mínima de 85% (#1).
- Modelos de peça, cliente, pedido e item do pedido, com regras protegidas também no banco (#2).
- Registro de pedido com baixa automática de estoque em transação atômica e mensagem "Só restam N unidades..." (RF03) (#2).
- Mudança de status e cancelamento com devolução ao estoque (RF04, RF05) (#2).
- Painel com vendido no mês, pendentes, estoque baixo e mais vendidas (RF06) (#2, #3).
- Telas Painel, Novo pedido, Estoque, Clientes e Pedidos, com login obrigatório e foco em acessibilidade (#3).
- Testes unitários e de integração (#2, #3).
- README, licença, guia de contribuição e modelos de issue e PR (#4, #5).

### Corrigido

- Pedido cancelado podia voltar para outro status porque a regra lia o pedido desatualizado da memória (#2).

[Não lançado]: https://github.com/marcosoliveiradar/brivony-gestao/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/marcosoliveiradar/brivony-gestao/releases/tag/v0.1.0
