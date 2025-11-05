from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.http import HttpResponse
from django.db import transaction, models
from datetime import timedelta
import uuid
import qrcode
import base64
from io import BytesIO

from .models import QRCodeReserva, ReservaProduto, Produto
from .serializers import (
    QRCodeReservaSerializer,
    ReservaProdutoSerializer,
    ReservaPublicaSerializer,
    ProdutoSerializer
)


class QRCodeReservaViewSet(viewsets.ModelViewSet):
    queryset = QRCodeReserva.objects.all()
    serializer_class = QRCodeReservaSerializer
    
    @action(detail=True, methods=['get'])
    def reservas(self, request, pk=None):
        """Retorna todas as reservas relacionadas a este QR code em formato de tabela"""
        qr_code = self.get_object()
        reservas = ReservaProduto.objects.filter(
            qr_code_reserva=qr_code
        ).select_related('produto').order_by('-data_reserva')
        
        # Retorna lista plana de itens de reserva (uma linha por item)
        resultado = []
        for reserva in reservas:
            preco_total = float(reserva.produto.preco * reserva.quantidade)
            resultado.append({
                'id': reserva.id,
                'nome_completo': reserva.nome_completo,
                'cpf': reserva.cpf,
                'produto': reserva.produto.nome,
                'quantidade': reserva.quantidade,
                'preco_unitario': float(reserva.produto.preco),
                'preco_total': preco_total,
                'status': reserva.status,
                'data_reserva': reserva.data_reserva.isoformat() if reserva.data_reserva else None
            })
        
        return Response(resultado, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def gerar_pdf(self, request, pk=None):
        """Gera PDF do QR code para impressão"""
        qr_code = self.get_object()
        
        try:
            import qrcode
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.utils import ImageReader
        except ImportError:
            return Response(
                {'error': 'Bibliotecas necessárias não instaladas (reportlab)'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Gera imagem do QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_code.codigo)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converte para BytesIO
        buffer_img = BytesIO()
        img.save(buffer_img, format='PNG')
        buffer_img.seek(0)
        
        # Cria PDF
        buffer_pdf = BytesIO()
        p = canvas.Canvas(buffer_pdf, pagesize=letter)
        width, height = letter
        
        # Título
        p.setFont("Helvetica-Bold", 24)
        p.drawString(50, height - 100, "QR Code de Reserva")
        
        # Descrição
        if qr_code.descricao:
            p.setFont("Helvetica", 14)
            p.drawString(50, height - 130, qr_code.descricao)
        
        # Código
        p.setFont("Helvetica", 12)
        p.drawString(50, height - 160, f"Código: {qr_code.codigo}")
        
        # Data de expiração
        if qr_code.data_expiracao:
            p.drawString(50, height - 180, f"Válido até: {qr_code.data_expiracao.strftime('%d/%m/%Y %H:%M')}")
        
        # QR Code (centralizado)
        qr_size = 300
        qr_x = (width - qr_size) / 2
        qr_y = height - 280
        p.drawImage(ImageReader(buffer_img), qr_x, qr_y, width=qr_size, height=qr_size)
        
        # URL
        p.setFont("Helvetica", 10)
        url = f"https://arraia-tech.up.railway.app/reservas/{qr_code.codigo}"
        p.drawString(50, qr_y - 30, f"URL: {url}")
        
        p.showPage()
        p.save()
        
        buffer_pdf.seek(0)
        response = HttpResponse(buffer_pdf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="qr_code_reserva_{qr_code.codigo}.pdf"'
        return response
    
    @action(detail=False, methods=['post'])
    def criar_qr_code(self, request):
        """Cria um novo QR code de reserva"""
        codigo = request.data.get('codigo') or f"RESERVA-{uuid.uuid4().hex[:12].upper()}"
        descricao = request.data.get('descricao', '')
        produtos_ids = request.data.get('produtos_ids', [])
        dias_expiracao = request.data.get('dias_expiracao', 7)
        
        data_expiracao = None
        if dias_expiracao:
            data_expiracao = timezone.now() + timedelta(days=dias_expiracao)
        
        qr_code = QRCodeReserva.objects.create(
            codigo=codigo,
            descricao=descricao,
            data_expiracao=data_expiracao,
            ativo=True
        )
        
        if produtos_ids:
            qr_code.produtos_disponiveis.set(produtos_ids)
        
        serializer = QRCodeReservaSerializer(qr_code)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def reserva_publica_produtos(request, qr_code):
    """Retorna produtos disponíveis para reserva via QR code"""
    try:
        qr = QRCodeReserva.objects.get(codigo=qr_code, ativo=True)
        
        # Verifica expiração
        if qr.data_expiracao and qr.data_expiracao < timezone.now():
            return Response(
                {'error': 'QR code expirado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Produtos disponíveis
        produtos = qr.produtos_disponiveis.filter(disponivel_reserva=True)
        
        produtos_data = []
        for produto in produtos:
            reservas_ativas = ReservaProduto.objects.filter(
                produto=produto,
                status__in=['pendente', 'confirmada']
            ).aggregate(total=models.Sum('quantidade'))['total'] or 0
            
            disponivel = produto.quantidade_reserva_disponivel - reservas_ativas
            
            produtos_data.append({
                'id': produto.id,
                'nome': produto.nome,
                'preco': float(produto.preco),
                'limite_reserva': produto.limite_reserva,
                'disponivel': max(0, disponivel),
                'categoria': produto.categoria,
            })
        
        return Response({
            'qr_code': qr.codigo,
            'descricao': qr.descricao,
            'data_expiracao': qr.data_expiracao,
            'produtos': produtos_data
        })
    except QRCodeReserva.DoesNotExist:
        return Response(
            {'error': 'QR code não encontrado ou inativo'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def criar_reserva_publica(request):
    """Cria reserva pública (sem ficha)"""
    serializer = ReservaPublicaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    nome_completo = data['nome_completo']
    cpf = data['cpf']
    produtos_data = data['produtos']
    qr_code_str = data.get('qr_code', '')
    
    # Valida QR code se fornecido
    qr_code_obj = None
    if qr_code_str:
        try:
            qr_code_obj = QRCodeReserva.objects.get(codigo=qr_code_str, ativo=True)
            if qr_code_obj.data_expiracao and qr_code_obj.data_expiracao < timezone.now():
                return Response(
                    {'error': 'QR code expirado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except QRCodeReserva.DoesNotExist:
            return Response(
                {'error': 'QR code inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Cria reservas
    reservas_criadas = []
    total_geral = 0
    
    for produto_data in produtos_data:
        produto_id = produto_data['produto_id']
        quantidade = produto_data['quantidade']
        
        try:
            produto = Produto.objects.get(id=produto_id, disponivel_reserva=True)
        except Produto.DoesNotExist:
            return Response(
                {'error': f'Produto {produto_id} não encontrado ou não disponível para reserva'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Valida limite por item
        if quantidade > produto.limite_reserva:
            return Response(
                {'error': f'Quantidade excede o limite de {produto.limite_reserva} por item'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verifica disponibilidade
        reservas_ativas = ReservaProduto.objects.filter(
            produto=produto,
            status__in=['pendente', 'confirmada']
        ).aggregate(total=models.Sum('quantidade'))['total'] or 0
        
        disponivel = produto.quantidade_reserva_disponivel - reservas_ativas
        
        if quantidade > disponivel:
            return Response(
                {'error': f'Quantidade indisponível para {produto.nome}. Disponível: {disponivel}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verifica se já existe reserva ativa do mesmo CPF para este produto
        reserva_existente = ReservaProduto.objects.filter(
            cpf=cpf,
            produto=produto,
            status__in=['pendente', 'confirmada']
        ).first()
        
        if reserva_existente:
            return Response(
                {'error': f'Já existe uma reserva ativa para {produto.nome} com este CPF'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cria reserva
        reserva = ReservaProduto.objects.create(
            nome_completo=nome_completo,
            cpf=cpf,
            produto=produto,
            quantidade=quantidade,
            qr_code_reserva=qr_code_obj,
            status='pendente'
        )
        
        reservas_criadas.append({
            'id': reserva.id,
            'produto': produto.nome,
            'quantidade': quantidade,
            'preco_unitario': float(produto.preco),
            'preco_total': float(produto.preco * quantidade)
        })
        
        total_geral += float(produto.preco * quantidade)
    
    return Response({
        'reservas': reservas_criadas,
        'total': total_geral,
        'nome_completo': nome_completo,
        'cpf': cpf,
        'data_reserva': timezone.now().isoformat()
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def reservas_por_cpf(request):
    """Retorna reservas por CPF (para usuário verificar suas reservas)"""
    cpf = request.query_params.get('cpf')
    if not cpf:
        return Response(
            {'error': 'CPF não fornecido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    reservas = ReservaProduto.objects.filter(cpf=cpf, status__in=['pendente', 'confirmada'])
    serializer = ReservaProdutoSerializer(reservas, many=True)
    
    total = sum(float(r['preco_total']) for r in serializer.data)
    
    return Response({
        'reservas': serializer.data,
        'total': total
    })

