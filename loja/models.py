"""Modelos do Brivony Gestão: peças, clientes e pedidos."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q

telefone_validator = RegexValidator(
    regex=r"^\d{10,11}$",
    message="Informe o telefone com DDD, só números (10 ou 11 dígitos).",
)


def somente_digitos(valor):
    return "".join(c for c in (valor or "") if c.isdigit())


class Produto(models.Model):
    """Peça de roupa à venda (RF01)."""

    class Tamanho(models.TextChoices):
        PP = "PP", "PP"
        P = "P", "P"
        M = "M", "M"
        G = "G", "G"
        GG = "GG", "GG"
        UNICO = "U", "Único"

    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=60, blank=True)
    tamanho = models.CharField(max_length=2, choices=Tamanho.choices)
    cor = models.CharField(max_length=40)
    preco = models.DecimalField(
        "preço",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"), "O preço deve ser maior que zero.")],
    )
    quantidade_estoque = models.PositiveIntegerField("quantidade em estoque", default=0)
    foto = models.ImageField(upload_to="produtos/", blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome", "tamanho", "cor"]
        verbose_name = "peça"
        constraints = [
            models.UniqueConstraint(
                fields=["nome", "tamanho", "cor"],
                name="produto_unico_nome_tamanho_cor",
                violation_error_message="Já existe uma peça com esse nome, tamanho e cor.",
            ),
            models.CheckConstraint(condition=Q(preco__gt=0), name="produto_preco_positivo"),
            models.CheckConstraint(
                condition=Q(quantidade_estoque__gte=0), name="produto_estoque_nao_negativo"
            ),
        ]

    def __str__(self):
        return f"{self.nome} · {self.get_tamanho_display()} · {self.cor}"

    @property
    def esgotado(self):
        return self.quantidade_estoque == 0

    @property
    def estoque_baixo(self):
        return 0 < self.quantidade_estoque <= settings.ESTOQUE_BAIXO_LIMITE

    @property
    def precisa_reposicao(self):
        return self.quantidade_estoque <= settings.ESTOQUE_BAIXO_LIMITE


class Cliente(models.Model):
    """Cliente identificada pelo telefone, que é único (RF02)."""

    nome = models.CharField(max_length=100)
    telefone = models.CharField(
        max_length=11,
        unique=True,
        validators=[telefone_validator],
        help_text="DDD + número, só dígitos.",
        error_messages={"unique": "Já existe uma cliente com esse telefone."},
    )
    instagram = models.CharField(max_length=60, blank=True)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    observacoes = models.TextField("observações", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.telefone = somente_digitos(self.telefone)
        super().save(*args, **kwargs)

    @property
    def telefone_formatado(self):
        t = self.telefone
        if len(t) == 11:
            return f"({t[:2]}) {t[2:7]}-{t[7:]}"
        if len(t) == 10:
            return f"({t[:2]}) {t[2:6]}-{t[6:]}"
        return t


class Pedido(models.Model):
    """Venda feita pelo Instagram ou WhatsApp (RF03, RF04, RF05)."""

    class Status(models.TextChoices):
        AGUARDANDO_PAGAMENTO = "aguardando_pagamento", "Aguardando pagamento"
        PAGO = "pago", "Pago"
        SEPARADO = "separado", "Separado"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    STATUS_PENDENTES = (Status.AGUARDANDO_PAGAMENTO, Status.PAGO, Status.SEPARADO)
    STATUS_VENDIDOS = (Status.PAGO, Status.SEPARADO, Status.ENTREGUE)

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.AGUARDANDO_PAGAMENTO
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em", "-id"]

    def __str__(self):
        return f"Pedido nº {self.pk}"

    @property
    def cancelado(self):
        return self.status == self.Status.CANCELADO

    def recalcular_total(self):
        self.total = sum((item.subtotal for item in self.itens.all()), Decimal("0.00"))
        return self.total


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="itens_pedido")
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Preço copiado da peça no momento da venda; não muda se o cadastro mudar.
    preco_unitario = models.DecimalField("preço unitário", max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "item do pedido"
        verbose_name_plural = "itens do pedido"
        constraints = [
            models.CheckConstraint(condition=Q(quantidade__gte=1), name="item_quantidade_minima"),
        ]

    def __str__(self):
        return f"{self.quantidade} × {self.produto}"

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade
