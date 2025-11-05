from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django.db.models.functions import Lower
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import Caixa, Ficha, Produto, MovimentacaoEstoque, Venda, ReservaProduto, Recarga
from .serializers import (
    CaixaSerializer,
    FichaSerializer,
    RecargaFichaSerializer,
    ProdutoSerializer,
    MovimentacaoEstoqueSerializer,
    VendaSerializer,
    ReservaProdutoSerializer,
)

class CaixaViewSet(viewsets.ModelViewSet):
    queryset = Caixa.objects.all()
    serializer_class = CaixaSerializer
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Endpoint para login de caixa"""
        usuario = request.data.get('usuario')
        senha = request.data.get('senha')
        
        if not usuario or not senha:
            return Response(
                {"detail": "Usuário e senha são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            caixa = Caixa.objects.get(usuario=usuario)
            if caixa.senha == senha:
                serializer = CaixaSerializer(caixa)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"detail": "Usuário ou senha inválidos."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except Caixa.DoesNotExist:
            return Response(
                {"detail": "Usuário ou senha inválidos."},
                status=status.HTTP_401_UNAUTHORIZED
            )

class FichaViewSet(viewsets.ModelViewSet):
    queryset = Ficha.objects.all().order_by('numero')
    # serializer_class = FichaSerializer
    
    def get_serializer_class(self):
        if self.action == 'recarga':
            return RecargaFichaSerializer
        if self.action == 'historico':
            from .serializers import FichaHistoricoSerializer
            return FichaHistoricoSerializer
        return FichaSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Cria ficha com possibilidade de vincular a reservas"""
        numero = request.data.get('numero')
        saldo_inicial = Decimal(str(request.data.get('saldo', 0)))
        cpf_reserva = request.data.get('cpf_reserva', None)
        caixa_id = request.data.get('caixa_id')
        
        # Valida caixa
        if not caixa_id:
            return Response(
                {"detail": "ID do caixa é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            caixa = Caixa.objects.get(id=caixa_id)
        except Caixa.DoesNotExist:
            return Response(
                {"detail": "Caixa não encontrado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Se houver CPF de reserva, busca reservas pendentes
        reservas_ids = []
        valor_total_reserva = Decimal('0.00')
        
        if cpf_reserva:
            reservas_pendentes = ReservaProduto.objects.filter(
                cpf=cpf_reserva,
                status='pendente',
                ficha__isnull=True
            ).select_related('produto')
            
            if not reservas_pendentes.exists():
                return Response(
                    {"detail": f"Nenhuma reserva pendente encontrada para o CPF {cpf_reserva}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calcula valor total das reservas
            for reserva in reservas_pendentes:
                preco_total = Decimal(str(reserva.produto.preco)) * reserva.quantidade
                valor_total_reserva += preco_total
                reservas_ids.append(reserva.id)
            
            # Valida que o saldo inicial seja >= valor total das reservas
            if saldo_inicial < valor_total_reserva:
                return Response(
                    {
                        "detail": f"O saldo inicial deve ser no mínimo R$ {valor_total_reserva:.2f} (valor total das reservas).",
                        "valor_total_reserva": float(valor_total_reserva),
                        "saldo_inicial": float(saldo_inicial)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Cria a ficha
        ficha = Ficha.objects.create(numero=numero, saldo=saldo_inicial)
        
        # Se houver reservas, processa elas
        if reservas_ids:
            reservas_pendentes = ReservaProduto.objects.filter(id__in=reservas_ids)
            
            # Processa cada reserva
            for reserva in reservas_pendentes:
                # Valida estoque
                if reserva.produto.estoque < reserva.quantidade:
                    # Reverte criação da ficha
                    ficha.delete()
                    return Response(
                        {"detail": f"Estoque insuficiente para {reserva.produto.nome}. Disponível: {reserva.produto.estoque}, Necessário: {reserva.quantidade}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Cria movimentação de estoque (saída)
                movimentacao = MovimentacaoEstoque.objects.create(
                    caixa=caixa,
                    produto=reserva.produto,
                    quantidade=reserva.quantidade,
                    tipo='S'
                )
                
                # Cria venda
                Venda.objects.create(
                    movimentacao=movimentacao,
                    ficha=ficha
                )
                
                # Vincula reserva à ficha e atualiza status
                reserva.ficha = ficha
                reserva.status = 'finalizada'
                reserva.data_confirmacao = timezone.now()
                reserva.save()
            
            # Calcula saldo restante após processar reservas
            saldo_restante = saldo_inicial - valor_total_reserva
            if saldo_restante > 0:
                ficha.saldo = saldo_restante
                ficha.save()
            
            # Registra recarga inicial (se houver saldo restante ou se foi recarga maior)
            if saldo_inicial > valor_total_reserva:
                Recarga.objects.create(
                    ficha=ficha,
                    caixa=caixa,
                    valor=saldo_inicial,
                    observacoes=f"Ficha criada vinculada a reservas. Valor total reservas: R$ {valor_total_reserva:.2f}"
                )
        
        serializer = self.get_serializer(ficha)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Deletar ficha com verificação de senha admin"""
        senha_admin = request.data.get('senha_admin')
        if not senha_admin:
            return Response({"detail": "Senha de administrador é obrigatória."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verifica senha admin (hardcoded por enquanto - admin123)
        if senha_admin != "admin123":
            return Response({"detail": "Senha de administrador incorreta."}, status=status.HTTP_401_UNAUTHORIZED)
        
        ficha = self.get_object()
        caixa_id = request.data.get('caixa_id')  # ID do caixa que está deletando
        
        # Marca como deletada ao invés de deletar fisicamente
        ficha.deleted_at = timezone.now()
        if caixa_id:
            try:
                from .models import Caixa
                ficha.deleted_by_caixa = Caixa.objects.get(id=caixa_id)
            except Caixa.DoesNotExist:
                pass
        ficha.is_active = False
        ficha.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def historico(self, request, pk=None):
        """Retorna histórico completo da ficha"""
        ficha = self.get_object()
        vendas = Venda.objects.filter(ficha=ficha).order_by('-movimentacao__data')
        recargas = Recarga.objects.filter(ficha=ficha).order_by('-data')
        
        serializer = self.get_serializer({
            'ficha': ficha,
            'vendas': vendas,
            'recargas': recargas,
        })
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def recarga(self, request, pk=None):
        serializer = RecargaFichaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ficha = self.get_object()
        valor_recarga = request.data.get('valor')
        produto_id = request.data.get('produto_id')  # Opcional
        caixa_id = request.data.get('caixa_id')  # Obrigatório para registrar histórico

        if valor_recarga is None:
            return Response({"detail": "O valor de recarga é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Realiza a recarga
            ficha.recarga(valor_recarga)
            
            # Registra o histórico de recarga
            if caixa_id:
                try:
                    caixa = Caixa.objects.get(id=caixa_id)
                    produto = None
                    if produto_id:
                        try:
                            produto = Produto.objects.get(id=produto_id)
                        except Produto.DoesNotExist:
                            pass  # Produto é opcional
                    
                    Recarga.objects.create(
                        ficha=ficha,
                        produto=produto,
                        caixa=caixa,
                        valor=valor_recarga,
                        observacoes=request.data.get('observacoes', '')
                    )
                except Caixa.DoesNotExist:
                    pass  # Se não encontrar o caixa, não registra histórico mas continua com a recarga
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = FichaSerializer(ficha)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all().order_by(Lower('nome'))
    serializer_class = ProdutoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']
    
    def get_queryset(self):
        """Retorna todos os produtos, incluindo os sem estoque"""
        queryset = Produto.objects.all().order_by(Lower('nome'))
        return queryset

class MovimentacaoEstoqueViewSet(viewsets.ModelViewSet):
    queryset = MovimentacaoEstoque.objects.all()
    serializer_class = MovimentacaoEstoqueSerializer

class VendaViewSet(viewsets.ModelViewSet):
    queryset = Venda.objects.all()
    serializer_class = VendaSerializer


class ReservaProdutoViewSet(viewsets.ModelViewSet):
    queryset = ReservaProduto.objects.all()
    serializer_class = ReservaProdutoSerializer
    
    def get_queryset(self):
        queryset = ReservaProduto.objects.all()
        ficha_id = self.request.query_params.get('ficha', None)
        status_filter = self.request.query_params.get('status', None)
        
        if ficha_id:
            queryset = queryset.filter(ficha_id=ficha_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def pendentes_por_cpf(self, request):
        """Retorna reservas pendentes por CPF (sem ficha vinculada)"""
        cpf = request.query_params.get('cpf')
        if not cpf:
            return Response(
                {"detail": "CPF é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reservas = ReservaProduto.objects.filter(
            cpf=cpf,
            status='pendente',
            ficha__isnull=True
        ).select_related('produto').order_by('-data_reserva')
        
        if not reservas.exists():
            return Response(
                {"detail": "Nenhuma reserva pendente encontrada para este CPF."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calcula total
        valor_total = Decimal('0.00')
        itens = []
        
        for reserva in reservas:
            preco_total = Decimal(str(reserva.produto.preco)) * reserva.quantidade
            valor_total += preco_total
            
            itens.append({
                'id': reserva.id,
                'produto': reserva.produto.nome,
                'produto_id': reserva.produto.id,
                'quantidade': reserva.quantidade,
                'preco_unitario': float(reserva.produto.preco),
                'preco_total': float(preco_total),
                'data_reserva': reserva.data_reserva.isoformat() if reserva.data_reserva else None,
            })
        
        # Retorna dados do cliente também
        primeira_reserva = reservas.first()
        
        return Response({
            'nome_completo': primeira_reserva.nome_completo,
            'cpf': primeira_reserva.cpf,
            'itens': itens,
            'valor_total': float(valor_total),
            'quantidade_itens': len(itens)
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """Confirma reserva e converte em venda"""
        reserva = self.get_object()
        if reserva.status != 'pendente':
            return Response({'error': 'Reserva já processada'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Valida saldo e estoque
        preco_total = reserva.produto.preco * reserva.quantidade
        if reserva.ficha.saldo < preco_total:
            return Response({'error': 'Saldo insuficiente'}, status=status.HTTP_400_BAD_REQUEST)
        
        if reserva.produto.estoque < reserva.quantidade:
            return Response({'error': 'Estoque insuficiente'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Cria venda
        movimentacao = MovimentacaoEstoque.objects.create(
            caixa=reserva.produto.caixa,
            produto=reserva.produto,
            quantidade=reserva.quantidade,
            tipo='S'
        )
        venda = Venda.objects.create(
            movimentacao=movimentacao,
            ficha=reserva.ficha
        )
        
        reserva.status = 'confirmada'
        reserva.data_confirmacao = timezone.now()
        reserva.save()
        
        return Response(VendaSerializer(venda).data, status=status.HTTP_200_OK)

