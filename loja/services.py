"""Regras de negócio do pedido e do painel.

Ficam aqui, fora das views, para serem testadas de forma isolada (testes unitários)
e reaproveitadas pelas telas (testes de integração).
"""
from collections import OrderedDict
from datetime import datetime, time
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from .models import Cliente, ItemPedido, Pedido, Produto


class EstoqueInsuficiente(ValidationError):
    """Uma ou mais peças não têm unidades suficientes.

    ``erros_por_produto`` mapeia o id da peça para a mensagem exibida junto ao item.
    """

    def __init__(self, erros_por_produto):
        self.erros_por_produto = erros_por_produto
        super().__init__(list(erros_por_produto.values()))


def mensagem_estoque(produto, pedido_qtd):
    disponivel = produto.quantidade_estoque
    if disponivel == 0:
        return f"{produto.nome} tamanho {produto.get_tamanho_display()} está esgotada."
    unidade = "unidade" if disponivel == 1 else "unidades"
    verbo = "Só resta" if disponivel == 1 else "Só restam"
    return (
        f"{verbo} {disponivel} {unidade} do tamanho {produto.get_tamanho_display()}. "
        "Ajuste a quantidade."
    )


def _agrupar_itens(itens):
    """Soma quantidades repetidas da mesma peça e valida os valores recebidos."""
    agrupados = OrderedDict()
    for produto_id, quantidade in itens:
        quantidade = int(quantidade)
        if quantidade < 1:
            raise ValidationError("A quantidade de cada peça deve ser pelo menos 1.")
        agrupados[int(produto_id)] = agrupados.get(int(produto_id), 0) + quantidade
    if not agrupados:
        raise ValidationError("Adicione pelo menos uma peça ao pedido.")
    return agrupados


@transaction.atomic
def criar_pedido(cliente, itens, status=Pedido.Status.AGUARDANDO_PAGAMENTO):
    """Registra o pedido e baixa o estoque numa única transação (RF03).

    ``itens`` é uma lista de pares ``(produto_id, quantidade)``. Preço e estoque
    vêm sempre do banco, nunca do formulário. Se qualquer peça não tiver estoque,
    nada é gravado.
    """
    if status == Pedido.Status.CANCELADO:
        raise ValidationError("Um pedido novo não pode começar cancelado.")
    agrupados = _agrupar_itens(itens)

    # select_for_update trava as linhas até o fim da transação, evitando que dois
    # pedidos simultâneos vendam a mesma última unidade.
    produtos = {
        p.pk: p
        for p in Produto.objects.select_for_update().filter(pk__in=agrupados.keys()).order_by("pk")
    }

    erros = OrderedDict()
    for produto_id, quantidade in agrupados.items():
        produto = produtos.get(produto_id)
        if produto is None or not produto.ativo:
            erros[produto_id] = "Esta peça não está mais disponível para venda."
        elif quantidade > produto.quantidade_estoque:
            erros[produto_id] = mensagem_estoque(produto, quantidade)
    if erros:
        raise EstoqueInsuficiente(erros)

    pedido = Pedido.objects.create(cliente=cliente, status=status)
    total = Decimal("0.00")
    for produto_id, quantidade in agrupados.items():
        produto = produtos[produto_id]
        ItemPedido.objects.create(
            pedido=pedido, produto=produto, quantidade=quantidade, preco_unitario=produto.preco
        )
        Produto.objects.filter(pk=produto_id).update(
            quantidade_estoque=F("quantidade_estoque") - quantidade
        )
        total += produto.preco * quantidade
    pedido.total = total
    pedido.save(update_fields=["total"])
    return pedido


@transaction.atomic
def cancelar_pedido(pedido):
    """Cancela o pedido e devolve as peças ao estoque (RF05)."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if pedido.status == Pedido.Status.CANCELADO:
        raise ValidationError("Este pedido já está cancelado.")
    if pedido.status == Pedido.Status.ENTREGUE:
        raise ValidationError("Pedido entregue não pode ser cancelado.")
    for item in pedido.itens.all():
        Produto.objects.filter(pk=item.produto_id).update(
            quantidade_estoque=F("quantidade_estoque") + item.quantidade
        )
    pedido.status = Pedido.Status.CANCELADO
    pedido.save(update_fields=["status", "atualizado_em"])
    return pedido


def alterar_status(pedido, novo_status):
    """Atualiza o status do pedido (RF04). Cancelar devolve o estoque."""
    if novo_status not in Pedido.Status.values:
        raise ValidationError("Status inválido.")
    if novo_status == Pedido.Status.CANCELADO:
        return cancelar_pedido(pedido)
    if pedido.status == Pedido.Status.CANCELADO:
        raise ValidationError("Pedido cancelado não pode mudar de status.")
    pedido.status = novo_status
    pedido.save(update_fields=["status", "atualizado_em"])
    return pedido


def buscar_cliente_por_telefone(telefone):
    digitos = "".join(c for c in (telefone or "") if c.isdigit())
    if not digitos:
        return None
    return Cliente.objects.filter(telefone=digitos).first()


def inicio_do_mes(agora=None):
    agora = timezone.localtime(agora or timezone.now())
    return timezone.make_aware(datetime.combine(agora.date().replace(day=1), time.min))


def resumo_painel(agora=None):
    """Números do Painel (RF06)."""
    inicio = inicio_do_mes(agora)
    pedidos_mes = Pedido.objects.filter(criado_em__gte=inicio)
    vendido_mes = (
        pedidos_mes.filter(status__in=Pedido.STATUS_VENDIDOS).aggregate(s=Sum("total"))["s"]
        or Decimal("0.00")
    )
    pendentes = Pedido.objects.filter(status__in=Pedido.STATUS_PENDENTES).count()
    estoque_baixo = Produto.objects.filter(
        ativo=True, quantidade_estoque__lte=settings.ESTOQUE_BAIXO_LIMITE
    ).count()
    mais_vendidas = (
        ItemPedido.objects.filter(pedido__criado_em__gte=inicio)
        .exclude(pedido__status=Pedido.Status.CANCELADO)
        .values("produto__nome")
        .annotate(unidades=Sum("quantidade"), pedidos=Count("pedido", distinct=True))
        .order_by("-unidades", "produto__nome")[:3]
    )
    return {
        "vendido_mes": vendido_mes,
        "pedidos_pendentes": pendentes,
        "estoque_baixo": estoque_baixo,
        "mais_vendidas": list(mais_vendidas),
    }


def produtos_para_venda():
    return Produto.objects.filter(ativo=True).filter(Q(quantidade_estoque__gt=0))
