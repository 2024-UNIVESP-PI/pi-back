from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CaixaViewSet,
    FichaViewSet,
    ProdutoViewSet,
    MovimentacaoEstoqueViewSet,
    VendaViewSet
)

router = DefaultRouter()
router.register(r'caixas', CaixaViewSet)
router.register(r'fichas', FichaViewSet)
router.register(r'produtos', ProdutoViewSet)
router.register(r'movimentacoes-estoque', MovimentacaoEstoqueViewSet)
router.register(r'vendas', VendaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]