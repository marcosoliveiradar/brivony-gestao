"""Funções auxiliares para criar dados fictícios nos testes."""
from decimal import Decimal

from django.contrib.auth import get_user_model

from loja.models import Cliente, Produto


def criar_produto(**kwargs):
    dados = {
        "nome": "Vestido Floral",
        "tamanho": Produto.Tamanho.M,
        "cor": "Azul",
        "preco": Decimal("89.90"),
        "quantidade_estoque": 3,
    }
    dados.update(kwargs)
    return Produto.objects.create(**dados)


def criar_cliente(**kwargs):
    dados = {"nome": "Ana Souza", "telefone": "11900000000"}
    dados.update(kwargs)
    return Cliente.objects.create(**dados)


def criar_usuaria(username="loja", password="senha-de-teste-123"):
    return get_user_model().objects.create_user(username=username, password=password)
