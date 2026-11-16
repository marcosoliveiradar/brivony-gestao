"""Testes unitários dos modelos (RF01, RF02)."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from loja.models import Cliente, ItemPedido, Pedido, Produto

from .fabricas import criar_cliente, criar_produto


class ProdutoTests(TestCase):
    def test_str_mostra_nome_tamanho_e_cor(self):
        produto = criar_produto()
        self.assertEqual(str(produto), "Vestido Floral · M · Azul")

    def test_nome_tamanho_cor_devem_ser_unicos(self):
        criar_produto()
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_produto()

    def test_mesmo_nome_com_outro_tamanho_e_permitido(self):
        criar_produto()
        criar_produto(tamanho=Produto.Tamanho.G)
        self.assertEqual(Produto.objects.count(), 2)

    def test_preco_zero_e_rejeitado_na_validacao(self):
        produto = Produto(nome="Saia", tamanho="P", cor="Bege", preco=Decimal("0"), quantidade_estoque=1)
        with self.assertRaises(ValidationError) as ctx:
            produto.full_clean()
        self.assertIn("preco", ctx.exception.message_dict)

    def test_preco_negativo_e_barrado_pelo_banco(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_produto(preco=Decimal("-1.00"))

    @override_settings(ESTOQUE_BAIXO_LIMITE=1)
    def test_sinalizacao_de_estoque(self):
        self.assertTrue(criar_produto(nome="A", quantidade_estoque=0).esgotado)
        baixo = criar_produto(nome="B", quantidade_estoque=1)
        self.assertTrue(baixo.estoque_baixo)
        self.assertFalse(baixo.esgotado)
        normal = criar_produto(nome="C", quantidade_estoque=2)
        self.assertFalse(normal.estoque_baixo)
        self.assertFalse(normal.precisa_reposicao)


class ClienteTests(TestCase):
    def test_telefone_e_salvo_so_com_digitos(self):
        cliente = criar_cliente(telefone="(11) 90000-0000")
        self.assertEqual(cliente.telefone, "11900000000")
        self.assertEqual(cliente.telefone_formatado, "(11) 90000-0000")

    def test_telefone_unico(self):
        criar_cliente()
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_cliente(nome="Outra", telefone="11900000000")

    def test_telefone_com_letras_e_invalido(self):
        cliente = Cliente(nome="Teste", telefone="11abc")
        with self.assertRaises(ValidationError):
            cliente.full_clean()


class PedidoTests(TestCase):
    def test_subtotal_e_total(self):
        pedido = Pedido.objects.create(cliente=criar_cliente())
        ItemPedido.objects.create(
            pedido=pedido, produto=criar_produto(), quantidade=2, preco_unitario=Decimal("89.90")
        )
        self.assertEqual(pedido.itens.get().subtotal, Decimal("179.80"))
        self.assertEqual(pedido.recalcular_total(), Decimal("179.80"))

    def test_status_inicial_e_aguardando_pagamento(self):
        pedido = Pedido.objects.create(cliente=criar_cliente())
        self.assertEqual(pedido.status, Pedido.Status.AGUARDANDO_PAGAMENTO)


class PopularDemoTests(TestCase):
    def test_cria_dados_ficticios_sem_duplicar(self):
        from django.core.management import call_command
        from io import StringIO

        call_command("popular_demo", stdout=StringIO())
        call_command("popular_demo", stdout=StringIO())
        self.assertEqual(Produto.objects.count(), 5)
        self.assertEqual(Cliente.objects.count(), 2)
