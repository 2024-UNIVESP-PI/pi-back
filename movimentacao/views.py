from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django.db.models.functions import Lower
from .models import Caixa, Ficha, Produto, MovimentacaoEstoque, Venda
from .serializers import (
    CaixaSerializer,
    FichaSerializer,
    RecargaFichaSerializer,
    ProdutoSerializer,
    MovimentacaoEstoqueSerializer,
    VendaSerializer,
)

class CaixaViewSet(viewsets.ModelViewSet):
    queryset = Caixa.objects.all()
    serializer_class = CaixaSerializer

class FichaViewSet(viewsets.ModelViewSet):
    queryset = Ficha.objects.all()
    # serializer_class = FichaSerializer
    
    def get_serializer_class(self):
        if self.action == 'recarga':
            return RecargaFichaSerializer
        return FichaSerializer
    
    @action(detail=True, methods=['post'])
    def recarga(self, request, pk=None):
        serializer = RecargaFichaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ficha = self.get_object()
        valor_recarga = request.data.get('valor')

        if valor_recarga is None:
            return Response({"detail": "O valor de recarga é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ficha.recarga(valor_recarga)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = FichaSerializer(ficha)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all().order_by(Lower('nome'))
    serializer_class = ProdutoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']

class MovimentacaoEstoqueViewSet(viewsets.ModelViewSet):
    queryset = MovimentacaoEstoque.objects.all()
    serializer_class = MovimentacaoEstoqueSerializer

class VendaViewSet(viewsets.ModelViewSet):
    queryset = Venda.objects.all()
    serializer_class = VendaSerializer

