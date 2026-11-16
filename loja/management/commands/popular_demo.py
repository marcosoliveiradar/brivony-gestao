"""Cria dados FICTÍCIOS para demonstração e testes de usabilidade.

Uso: python manage.py popular_demo
Nenhum dado real de clientes é usado.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from loja.models import Cliente, Produto

PECAS = [
    ("Vestido Floral", "Vestidos", "M", "Azul", "89.90", 3),
    ("Blusa Canelada", "Blusas", "P", "Preta", "59.90", 2),
    ("Saia Midi", "Saias", "G", "Bege", "79.90", 0),
    ("Calça Pantalona", "Calças", "M", "Preta", "119.90", 6),
    ("Cropped Tricô", "Blusas", "U", "Off-white", "49.90", 8),
]

CLIENTES = [
    ("Ana Souza", "11900000000", "ana.exemplo"),
    ("Bruna Lima", "11900000001", ""),
]


class Command(BaseCommand):
    help = "Popula o banco com peças e clientes fictícios para demonstração."

    def handle(self, *args, **options):
        for nome, categoria, tamanho, cor, preco, qtd in PECAS:
            Produto.objects.get_or_create(
                nome=nome,
                tamanho=tamanho,
                cor=cor,
                defaults={"categoria": categoria, "preco": Decimal(preco), "quantidade_estoque": qtd},
            )
        for nome, telefone, instagram in CLIENTES:
            Cliente.objects.get_or_create(telefone=telefone, defaults={"nome": nome, "instagram": instagram})
        self.stdout.write(self.style.SUCCESS("Dados fictícios criados."))
