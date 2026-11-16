from django.contrib import admin

from .models import Cliente, ItemPedido, Pedido, Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tamanho", "cor", "preco", "quantidade_estoque", "ativo")
    list_filter = ("ativo", "tamanho", "categoria")
    search_fields = ("nome", "cor")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "instagram")
    search_fields = ("nome", "telefone", "instagram")


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ("produto", "quantidade", "preco_unitario")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "status", "total", "criado_em")
    list_filter = ("status",)
    inlines = [ItemPedidoInline]
    # Status e estoque são alterados pelas telas do sistema, que aplicam as regras.
    readonly_fields = ("cliente", "status", "total")
