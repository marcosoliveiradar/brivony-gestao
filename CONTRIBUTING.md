# Como contribuir

Obrigado pelo interesse no Brivony Gestão! Este é um projeto acadêmico, mas segue práticas de uma equipe de desenvolvimento profissional.

## Fluxo de trabalho

1. Abra uma [issue](https://github.com/marcosoliveiradar/brivony-gestao/issues/new/choose) descrevendo o problema ou a melhoria.
2. Crie uma branch a partir da `main` com um prefixo que indique o tipo:
   - `feat/` nova funcionalidade
   - `fix/` correção de erro
   - `test/` testes
   - `docs/` documentação
   - `ci/` pipeline
3. Faça commits pequenos no padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/):

   ```
   feat: adiciona filtro de pedidos por status
   fix: corrige cálculo do total com itens cancelados
   test: cobre cancelamento de pedido entregue
   ```

4. Rode os testes antes de enviar:

   ```bash
   python manage.py test loja
   ```

5. Abra um Pull Request para a `main` e preencha o checklist de auto-revisão.
6. O PR só entra depois que o CI passar.

## Regras do projeto

- Regras de negócio ficam em `loja/services.py` e são validadas **no servidor**, nunca só na tela.
- Toda mudança de regra vem com teste.
- Nunca envie segredos, senhas ou dados reais de clientes. Use apenas dados fictícios.
- Telas novas seguem o RNF04: rótulo visível, alvos de toque de 44 px, texto de 16 px, contraste de 4,5:1 e alertas com texto + ícone + cor.
