from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FichaViewSet, ProdutoViewSet, MovimentacaoEstoqueViewSet

router = DefaultRouter()
router.register(r'fichas', FichaViewSet)
router.register(r'produtos', ProdutoViewSet)
router.register(r'movimentacao-estoque', MovimentacaoEstoqueViewSet)

urlpatterns = [
    path('', include(router.urls)),
]