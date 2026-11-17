"""Testes de integração: telas, banco, sessão e regras funcionando juntos."""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from loja.models import Cliente, Pedido, Produto

from .fabricas import criar_cliente, criar_produto, criar_usuaria


class LoginObrigatorioTests(TestCase):
    """RNF01: nenhuma tela de negócio abre sem login."""

    def test_telas_redirecionam_para_login(self):
        nomes = ["painel", "estoque", "produto_novo", "clientes", "cliente_novo",
                 "cliente_buscar", "pedidos", "pedido_novo"]
        for nome in nomes:
            with self.subTest(tela=nome):
                resposta = self.client.get(reverse(f"loja:{nome}"))
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta.url.startswith(reverse("login")))

    def test_login_e_logout(self):
        criar_usuaria()
        resposta = self.client.post(reverse("login"), {"username": "loja", "password": "senha-de-teste-123"})
        self.assertRedirects(resposta, reverse("loja:painel"))
        resposta = self.client.post(reverse("logout"))
        self.assertRedirects(resposta, reverse("login"))
        self.assertEqual(self.client.get(reverse("loja:painel")).status_code, 302)

    def test_senha_guardada_com_pbkdf2(self):
        self.assertTrue(criar_usuaria().password.startswith("pbkdf2_sha256$"))


class TelaLogadaMixin:
    def setUp(self):
        super().setUp()
        self.client.force_login(criar_usuaria())


class PainelTests(TelaLogadaMixin, TestCase):
    @override_settings(ESTOQUE_BAIXO_LIMITE=1)
    def test_painel_mostra_resumo(self):
        cliente = criar_cliente()
        vestido = criar_produto(quantidade_estoque=5)
        criar_produto(nome="Saia", tamanho="G", cor="Bege", quantidade_estoque=0)
        self.client.post(reverse("loja:pedido_novo"), {
            "telefone": cliente.telefone, "status": "pago",
            "itens-TOTAL_FORMS": "1", "itens-INITIAL_FORMS": "0",
            "itens-0-produto": vestido.pk, "itens-0-quantidade": "2",
        })
        resposta = self.client.get(reverse("loja:painel"))
        self.assertContains(resposta, "R$ 179,80")
        self.assertContains(resposta, "Mais vendidas no mês")
        self.assertContains(resposta, "Vestido Floral")
        self.assertEqual(resposta.context["estoque_baixo"], 1)


class NovoPedidoFluxoTests(TelaLogadaMixin, TestCase):
    """Fluxo central (RF03): Tela 2 → grava pedido → baixa estoque → Tela 3."""

    def setUp(self):
        super().setUp()
        self.cliente = criar_cliente()
        self.vestido = criar_produto(quantidade_estoque=3)
        self.blusa = criar_produto(nome="Blusa Canelada", tamanho="P", cor="Preta",
                                   preco=Decimal("59.90"), quantidade_estoque=2)

    def dados(self, itens, telefone="(11) 90000-0000", status="aguardando_pagamento"):
        dados = {"telefone": telefone, "status": status,
                 "itens-TOTAL_FORMS": str(len(itens)), "itens-INITIAL_FORMS": "0"}
        for i, (produto, qtd) in enumerate(itens):
            dados[f"itens-{i}-produto"] = produto.pk
            dados[f"itens-{i}-quantidade"] = str(qtd)
        return dados

    def test_tela_abre_com_campos_rotulados(self):
        resposta = self.client.get(reverse("loja:pedido_novo"))
        self.assertContains(resposta, '<label class="form-label" for="id_telefone">Telefone da cliente</label>', html=True)
        self.assertContains(resposta, "Salvar pedido")
        self.assertContains(resposta, "csrfmiddlewaretoken")

    def test_salvar_pedido_baixa_estoque_e_mostra_confirmacao(self):
        resposta = self.client.post(reverse("loja:pedido_novo"), self.dados([(self.vestido, 2)]), follow=True)
        pedido = Pedido.objects.get()
        self.assertRedirects(resposta, reverse("loja:estoque"))
        self.assertContains(resposta, f"Pedido nº {pedido.pk} registrado. Estoque atualizado.")
        self.assertContains(resposta, "antes 3")
        self.vestido.refresh_from_db()
        self.assertEqual(self.vestido.quantidade_estoque, 1)
        self.assertEqual(pedido.cliente, self.cliente)
        self.assertEqual(pedido.total, Decimal("179.80"))

    def test_quantidade_acima_do_estoque_mostra_erro_e_nao_salva(self):
        resposta = self.client.post(reverse("loja:pedido_novo"),
                                    self.dados([(self.vestido, 2), (self.blusa, 3)]))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Só restam 2 unidades do tamanho P. Ajuste a quantidade.")
        self.assertEqual(Pedido.objects.count(), 0)
        self.vestido.refresh_from_db()
        self.assertEqual(self.vestido.quantidade_estoque, 3)

    def test_cliente_nao_cadastrada(self):
        resposta = self.client.post(reverse("loja:pedido_novo"),
                                    self.dados([(self.vestido, 1)], telefone="11911112222"))
        self.assertContains(resposta, "Cliente não encontrada")
        self.assertEqual(Pedido.objects.count(), 0)

    def test_quantidade_negativa_e_barrada_no_servidor(self):
        resposta = self.client.post(reverse("loja:pedido_novo"), self.dados([(self.vestido, -1)]))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_preco_enviado_pelo_formulario_e_ignorado(self):
        dados = self.dados([(self.vestido, 1)])
        dados["itens-0-preco"] = "0.01"
        self.client.post(reverse("loja:pedido_novo"), dados)
        self.assertEqual(Pedido.objects.get().total, Decimal("89.90"))

    def test_busca_de_cliente_por_telefone(self):
        url = reverse("loja:cliente_buscar")
        self.assertEqual(self.client.get(url, {"telefone": "(11) 90000-0000"}).json(),
                         {"encontrada": True, "nome": "Ana Souza"})
        self.assertEqual(self.client.get(url, {"telefone": "11999999999"}).json(), {"encontrada": False})


class PedidoStatusTelaTests(TelaLogadaMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.produto = criar_produto(quantidade_estoque=4)
        from loja import services
        self.pedido = services.criar_pedido(criar_cliente(), [(self.produto.pk, 3)])

    def test_mudar_status(self):
        url = reverse("loja:pedido_status", args=[self.pedido.pk])
        resposta = self.client.post(url, {"status": "separado"}, follow=True)
        self.assertContains(resposta, "agora está “Separado”")
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, "separado")

    def test_cancelar_pela_tela_devolve_estoque(self):
        url = reverse("loja:pedido_status", args=[self.pedido.pk])
        resposta = self.client.post(url, {"status": "cancelado"}, follow=True)
        self.assertContains(resposta, "As peças voltaram ao estoque")
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 4)

    def test_lista_de_pedidos_pendentes(self):
        resposta = self.client.get(reverse("loja:pedidos"), {"status": "pendentes"})
        self.assertContains(resposta, f"Pedido nº {self.pedido.pk}")

    def test_status_so_por_post(self):
        resposta = self.client.get(reverse("loja:pedido_status", args=[self.pedido.pk]))
        self.assertEqual(resposta.status_code, 405)


class EstoqueTelaTests(TelaLogadaMixin, TestCase):
    @override_settings(ESTOQUE_BAIXO_LIMITE=1)
    def test_filtro_e_selos(self):
        criar_produto(nome="Saia Midi", tamanho="G", cor="Bege", quantidade_estoque=0)
        criar_produto(nome="Vestido Floral", quantidade_estoque=1)
        criar_produto(nome="Calça Pantalona", quantidade_estoque=6)
        resposta = self.client.get(reverse("loja:estoque"), {"filtro": "baixo"})
        self.assertContains(resposta, "Esgotado")
        self.assertContains(resposta, "Estoque baixo")
        self.assertNotContains(resposta, "Calça Pantalona")

    def test_cadastrar_peca(self):
        resposta = self.client.post(reverse("loja:produto_novo"), {
            "nome": "Cropped Tricô", "tamanho": "U", "cor": "Off-white",
            "preco": "49.90", "quantidade_estoque": "8",
        })
        self.assertRedirects(resposta, reverse("loja:estoque"))
        self.assertTrue(Produto.objects.filter(nome="Cropped Tricô").exists())

    def test_cadastro_com_preco_zero_mostra_erro(self):
        resposta = self.client.post(reverse("loja:produto_novo"), {
            "nome": "Peça", "tamanho": "P", "cor": "Azul", "preco": "0", "quantidade_estoque": "1",
        })
        self.assertContains(resposta, "O preço deve ser maior que zero.")
        self.assertFalse(Produto.objects.exists())

    def test_peca_duplicada_mostra_erro(self):
        criar_produto()
        resposta = self.client.post(reverse("loja:produto_novo"), {
            "nome": "Vestido Floral", "tamanho": "M", "cor": "Azul", "preco": "10", "quantidade_estoque": "1",
        })
        self.assertContains(resposta, "Já existe uma peça com esse nome, tamanho e cor.")

    def test_inativar_em_vez_de_excluir(self):
        produto = criar_produto()
        resposta = self.client.post(reverse("loja:produto_inativar", args=[produto.pk]), follow=True)
        self.assertContains(resposta, "retirada do catálogo")
        produto.refresh_from_db()
        self.assertFalse(produto.ativo)
        self.assertTrue(Produto.objects.filter(pk=produto.pk).exists())
        self.assertNotIn(produto, resposta.context["produtos"])


class ClienteTelaTests(TelaLogadaMixin, TestCase):
    def test_cadastrar_cliente_e_voltar_ao_pedido(self):
        url = reverse("loja:cliente_novo") + "?next=" + reverse("loja:pedido_novo")
        resposta = self.client.post(url, {"nome": "Bruna Lima", "telefone": "(11) 90000-0001",
                                          "next": reverse("loja:pedido_novo")})
        self.assertRedirects(resposta, reverse("loja:pedido_novo") + "?telefone=11900000001")
        self.assertEqual(Cliente.objects.get().telefone, "11900000001")

    def test_redirecionamento_externo_e_ignorado(self):
        resposta = self.client.post(reverse("loja:cliente_novo"), {
            "nome": "Carla", "telefone": "11900000002", "next": "https://site-malicioso.example/",
        })
        self.assertRedirects(resposta, reverse("loja:clientes"))

    def test_telefone_duplicado(self):
        criar_cliente()
        resposta = self.client.post(reverse("loja:cliente_novo"), {"nome": "Outra", "telefone": "11900000000"})
        self.assertContains(resposta, "Já existe uma cliente com esse telefone.")

    def test_texto_digitado_e_escapado(self):
        criar_cliente(nome="<script>alert(1)</script>")
        resposta = self.client.get(reverse("loja:clientes"))
        self.assertNotContains(resposta, "<script>alert(1)</script>")
        self.assertContains(resposta, "&lt;script&gt;")


class TextoMaiorTests(TelaLogadaMixin, TestCase):
    """RNF04: botão "A+" de texto maior presente e acessível nas telas."""

    def test_botao_aparece_com_estado_para_leitor_de_tela(self):
        for nome in ["painel", "estoque", "pedido_novo", "clientes", "pedidos"]:
            with self.subTest(tela=nome):
                resposta = self.client.get(reverse(f"loja:{nome}"))
                self.assertContains(resposta, "data-texto-maior")
                self.assertContains(resposta, 'aria-pressed="false"')
                # Em produção o nome ganha um hash (acessibilidade.1a2b3c.js), então confere só o início.
                self.assertContains(resposta, "/static/js/acessibilidade.")

    def test_botao_tambem_no_login(self):
        self.client.logout()
        self.assertContains(self.client.get(reverse("login")), "data-texto-maior")


class SaudeTests(TestCase):
    """Rota usada pelo health check do Render e pelo monitor de disponibilidade."""

    def test_responde_ok_sem_login(self):
        resposta = self.client.get(reverse("loja:saude"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok", "banco": "ok"})

    def test_aceita_head(self):
        self.assertEqual(self.client.head(reverse("loja:saude")).status_code, 200)

    def test_banco_fora_do_ar_retorna_503(self):
        from unittest import mock

        with mock.patch("loja.views.connection.cursor", side_effect=Exception("sem banco")):
            resposta = self.client.get(reverse("loja:saude"))
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta.json()["status"], "erro")

    def test_nao_expoe_dados_da_loja(self):
        criar_cliente()
        self.assertNotContains(self.client.get(reverse("loja:saude")), "Ana")
