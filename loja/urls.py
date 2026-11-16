from django.urls import path

from . import views

app_name = "loja"

urlpatterns = [
    path("", views.PainelView.as_view(), name="painel"),
    path("estoque/", views.EstoqueView.as_view(), name="estoque"),
    path("estoque/nova/", views.ProdutoCreateView.as_view(), name="produto_novo"),
    path("estoque/<int:pk>/editar/", views.ProdutoUpdateView.as_view(), name="produto_editar"),
    path("estoque/<int:pk>/inativar/", views.ProdutoInativarView.as_view(), name="produto_inativar"),
    path("clientes/", views.ClienteListView.as_view(), name="clientes"),
    path("clientes/nova/", views.ClienteCreateView.as_view(), name="cliente_novo"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente_editar"),
    path("clientes/buscar/", views.BuscarClienteView.as_view(), name="cliente_buscar"),
    path("pedidos/", views.PedidoListView.as_view(), name="pedidos"),
    path("pedidos/novo/", views.NovoPedidoView.as_view(), name="pedido_novo"),
    path("pedidos/<int:pk>/", views.PedidoDetailView.as_view(), name="pedido_detalhe"),
    path("pedidos/<int:pk>/status/", views.PedidoStatusView.as_view(), name="pedido_status"),
]
