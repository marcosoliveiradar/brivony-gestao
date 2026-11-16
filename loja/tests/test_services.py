"""Testes unitários das regras de negócio (RF03, RF04, RF05, RF06)."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from loja import services
from loja.models import Pedido

from .fabricas import criar_cliente, criar_produto


class CriarPedidoTests(TestCase):
    def setUp(self):
        self.cliente = criar_cliente()
        self.vestido = criar_produto(quantidade_estoque=3)
        self.blusa = criar_produto(nome="Blusa Canelada", tamanho="P", cor="Preta",
                                   preco=Decimal("59.90"), quantidade_estoque=2)

    def test_registra_pedido_e_baixa_estoque(self):
        pedido = services.criar_pedido(self.cliente, [(self.vestido.pk, 2), (self.blusa.pk, 1)])
        self.vestido.refresh_from_db()
        self.blusa.refresh_from_db()
        self.assertEqual(self.vestido.quantidade_estoque, 1)
        self.assertEqual(self.blusa.quantidade_estoque, 1)
        self.assertEqual(pedido.total, Decimal("239.70"))
        self.assertEqual(pedido.itens.count(), 2)

    def test_preco_vem_do_cadastro(self):
        pedido = services.criar_pedido(self.cliente, [(self.vestido.pk, 1)])
        self.assertEqual(pedido.itens.get().preco_unitario, Decimal("89.90"))

    def test_rejeita_quantidade_acima_do_estoque_com_mensagem(self):
        with self.assertRaises(services.EstoqueInsuficiente) as ctx:
            services.criar_pedido(self.cliente, [(self.blusa.pk, 3)])
        self.assertEqual(
            ctx.exception.erros_por_produto[self.blusa.pk],
            "Só restam 2 unidades do tamanho P. Ajuste a quantidade.",
        )

    def test_falha_em_um_item_nao_grava_nada(self):
        with self.assertRaises(services.EstoqueInsuficiente):
            services.criar_pedido(self.cliente, [(self.vestido.pk, 2), (self.blusa.pk, 3)])
        self.vestido.refresh_from_db()
        self.assertEqual(self.vestido.quantidade_estoque, 3)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_itens_repetidos_sao_somados(self):
        with self.assertRaises(services.EstoqueInsuficiente):
            services.criar_pedido(self.cliente, [(self.blusa.pk, 2), (self.blusa.pk, 1)])

    def test_quantidade_zero_ou_negativa_e_rejeitada(self):
        for qtd in (0, -1):
            with self.assertRaises(ValidationError):
                services.criar_pedido(self.cliente, [(self.vestido.pk, qtd)])

    def test_pedido_vazio_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            services.criar_pedido(self.cliente, [])

    def test_peca_inativa_nao_pode_ser_vendida(self):
        self.vestido.ativo = False
        self.vestido.save()
        with self.assertRaises(services.EstoqueInsuficiente):
            services.criar_pedido(self.cliente, [(self.vestido.pk, 1)])

    def test_mensagem_no_singular_e_esgotada(self):
        self.blusa.quantidade_estoque = 1
        self.assertEqual(services.mensagem_estoque(self.blusa, 2),
                         "Só resta 1 unidade do tamanho P. Ajuste a quantidade.")
        self.blusa.quantidade_estoque = 0
        self.assertIn("esgotada", services.mensagem_estoque(self.blusa, 1))


class StatusECancelamentoTests(TestCase):
    def setUp(self):
        self.produto = criar_produto(quantidade_estoque=5)
        self.pedido = services.criar_pedido(criar_cliente(), [(self.produto.pk, 2)])

    def test_alterar_status(self):
        services.alterar_status(self.pedido, Pedido.Status.PAGO)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.Status.PAGO)

    def test_status_invalido(self):
        with self.assertRaises(ValidationError):
            services.alterar_status(self.pedido, "qualquer")

    def test_cancelar_devolve_estoque(self):
        services.alterar_status(self.pedido, Pedido.Status.CANCELADO)
        self.produto.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 5)
        self.assertTrue(self.pedido.cancelado)

    def test_nao_cancela_duas_vezes(self):
        services.cancelar_pedido(self.pedido)
        with self.assertRaises(ValidationError):
            services.cancelar_pedido(self.pedido)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 5)

    def test_pedido_cancelado_nao_volta_a_outro_status(self):
        services.cancelar_pedido(self.pedido)
        with self.assertRaises(ValidationError):
            services.alterar_status(self.pedido, Pedido.Status.PAGO)

    def test_pedido_entregue_nao_pode_ser_cancelado(self):
        services.alterar_status(self.pedido, Pedido.Status.ENTREGUE)
        with self.assertRaises(ValidationError):
            services.cancelar_pedido(self.pedido)


@override_settings(ESTOQUE_BAIXO_LIMITE=1)
class ResumoPainelTests(TestCase):
    def test_numeros_do_painel(self):
        cliente = criar_cliente()
        vestido = criar_produto(quantidade_estoque=10)
        blusa = criar_produto(nome="Blusa", tamanho="P", cor="Preta", preco=Decimal("50.00"),
                              quantidade_estoque=10)
        criar_produto(nome="Saia", tamanho="G", cor="Bege", quantidade_estoque=0)

        pago = services.criar_pedido(cliente, [(vestido.pk, 2)], Pedido.Status.PAGO)  # 179,80
        services.criar_pedido(cliente, [(blusa.pk, 1)])  # aguardando: não conta como vendido
        cancelado = services.criar_pedido(cliente, [(blusa.pk, 5)], Pedido.Status.PAGO)
        services.cancelar_pedido(cancelado)
        antigo = services.criar_pedido(cliente, [(blusa.pk, 1)], Pedido.Status.ENTREGUE)
        Pedido.objects.filter(pk=antigo.pk).update(criado_em=timezone.now() - timedelta(days=40))

        resumo = services.resumo_painel()
        self.assertEqual(resumo["vendido_mes"], pago.total)
        self.assertEqual(resumo["pedidos_pendentes"], 2)
        self.assertEqual(resumo["estoque_baixo"], 1)
        self.assertEqual(resumo["mais_vendidas"][0]["produto__nome"], "Vestido Floral")
        self.assertEqual(resumo["mais_vendidas"][0]["unidades"], 2)
        nomes = [m["produto__nome"] for m in resumo["mais_vendidas"]]
        self.assertEqual(nomes, ["Vestido Floral", "Blusa"])

    def test_painel_vazio(self):
        resumo = services.resumo_painel()
        self.assertEqual(resumo["vendido_mes"], Decimal("0.00"))
        self.assertEqual(resumo["mais_vendidas"], [])
