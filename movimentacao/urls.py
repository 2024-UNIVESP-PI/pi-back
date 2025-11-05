from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CaixaViewSet,
    FichaViewSet,
    ProdutoViewSet,
    MovimentacaoEstoqueViewSet,
    VendaViewSet,
    ReservaProdutoViewSet
)
from .views_reserva import (
    QRCodeReservaViewSet,
    reserva_publica_produtos,
    criar_reserva_publica,
    reservas_por_cpf
)

router = DefaultRouter()
router.register(r'caixas', CaixaViewSet)
router.register(r'fichas', FichaViewSet)
router.register(r'produtos', ProdutoViewSet)
router.register(r'movimentacoes-estoque', MovimentacaoEstoqueViewSet)
router.register(r'vendas', VendaViewSet)
router.register(r'reservas', ReservaProdutoViewSet, basename='reserva')
router.register(r'qr-codes-reserva', QRCodeReservaViewSet, basename='qr-code-reserva')

urlpatterns = [
    path('', include(router.urls)),
    # Endpoints públicos para reservas
    path('reservas-publicas/<str:qr_code>/produtos/', reserva_publica_produtos, name='reserva-publica-produtos'),
    path('reservas-publicas/criar/', criar_reserva_publica, name='criar-reserva-publica'),
    path('reservas-publicas/por-cpf/', reservas_por_cpf, name='reservas-por-cpf'),
]