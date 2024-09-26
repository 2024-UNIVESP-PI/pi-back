from rest_framework import viewsets
from .models import Ficha, Produto, MovimentacaoEstoque
from .serializers import FichaSerializer, ProdutoSerializer, MovimentacaoEstoqueSerializer

class FichaViewSet(viewsets.ModelViewSet):
    queryset = Ficha.objects.all()
    serializer_class = FichaSerializer
    
class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    
class MovimentacaoEstoqueViewSet(viewsets.ModelViewSet):
    queryset = MovimentacaoEstoque.objects.all()
    serializer_class = MovimentacaoEstoqueSerializer