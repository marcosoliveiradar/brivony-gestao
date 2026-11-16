from django.urls import path

from . import views

app_name = "loja"

urlpatterns = [
    path("estoque/", views.EstoqueView.as_view(), name="estoque"),
    path("estoque/nova/", views.ProdutoCreateView.as_view(), name="produto_novo"),
    path("estoque/<int:pk>/editar/", views.ProdutoUpdateView.as_view(), name="produto_editar"),
    path("estoque/<int:pk>/inativar/", views.ProdutoInativarView.as_view(), name="produto_inativar"),
    path("clientes/", views.ClienteListView.as_view(), name="clientes"),
    path("clientes/nova/", views.ClienteCreateView.as_view(), name="cliente_novo"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente_editar"),
    path("clientes/buscar/", views.BuscarClienteView.as_view(), name="cliente_buscar"),
]
