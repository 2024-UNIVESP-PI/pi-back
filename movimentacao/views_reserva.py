from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.utils.timezone import localtime
from django.http import HttpResponse
from django.db import transaction, models
from django.conf import settings
from datetime import timedelta
import uuid
import qrcode
import base64
from io import BytesIO
import os

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
    
    def update(self, request, *args, **kwargs):
        """Atualiza QR code com suporte para data_inicio e data_expiracao"""
        instance = self.get_object()
        data = request.data.copy()
        
        # Processa data_inicio se fornecida
        if 'data_inicio' in data and data['data_inicio']:
            try:
                from django.utils.dateparse import parse_datetime
                data_inicio_str = data['data_inicio']
                data_inicio = parse_datetime(data_inicio_str)
                if not data_inicio:
                    data_inicio = timezone.datetime.fromisoformat(data_inicio_str.replace('Z', '+00:00'))
                    if timezone.is_naive(data_inicio):
                        data_inicio = timezone.make_aware(data_inicio)
                data['data_inicio'] = data_inicio
            except (ValueError, AttributeError) as e:
                return Response(
                    {'error': f'Data de início inválida: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Processa data_expiracao se fornecida
        if 'data_expiracao' in data and data['data_expiracao']:
            try:
                from django.utils.dateparse import parse_datetime
                data_expiracao_str = data['data_expiracao']
                data_expiracao = parse_datetime(data_expiracao_str)
                if not data_expiracao:
                    data_expiracao = timezone.datetime.fromisoformat(data_expiracao_str.replace('Z', '+00:00'))
                    if timezone.is_naive(data_expiracao):
                        data_expiracao = timezone.make_aware(data_expiracao)
                data['data_expiracao'] = data_expiracao
            except (ValueError, AttributeError) as e:
                return Response(
                    {'error': f'Data de expiração inválida: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Valida que data_inicio < data_expiracao se ambos existirem
        data_inicio = data.get('data_inicio') or instance.data_inicio
        data_expiracao = data.get('data_expiracao') or instance.data_expiracao
        if data_inicio and data_expiracao and data_inicio >= data_expiracao:
            return Response(
                {'error': 'Data de início deve ser anterior à data de expiração'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().update(request, *args, **kwargs)
    
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
            from reportlab.lib.colors import HexColor
            from reportlab.lib import colors
        except ImportError:
            return Response(
                {'error': 'Bibliotecas necessárias não instaladas (reportlab)'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Obtém URL base do frontend (usa variável de ambiente ou fallback)
        frontend_url = os.getenv('FRONTEND_URL', 'https://arraiatech.up.railway.app')
        # Remove barra final se houver
        frontend_url = frontend_url.rstrip('/')
        # Em desenvolvimento local, usa localhost
        if settings.DEBUG and 'localhost' in str(request.get_host()):
            frontend_url = 'http://localhost:8080'
        
        # URL completa para o QR code
        qr_url = f"{frontend_url}/reservas/{qr_code.codigo}"
        
        # Gera imagem do QR code com URL completa
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converte para BytesIO
        buffer_img = BytesIO()
        img.save(buffer_img, format='PNG')
        buffer_img.seek(0)
        
        # Cores temáticas de festa junina
        cor_laranja = HexColor('#FF8C42')
        cor_amarelo = HexColor('#FFD700')
        cor_vermelho = HexColor('#DC143C')
        cor_verde = HexColor('#228B22')
        cor_branco = colors.white
        cor_preto = colors.black
        
        # Cria PDF
        buffer_pdf = BytesIO()
        p = canvas.Canvas(buffer_pdf, pagesize=letter)
        width, height = letter
        
        # Margens para impressão segura (1 inch = 72 points)
        margin = 72
        y_start = height - margin
        
        # Fundo decorativo - bandeirinhas no topo
        bandeirinha_height = 40
        bandeirinha_width = 60
        x_pos = margin
        while x_pos < width - margin:
            # Alterna cores das bandeirinhas
            cores_bandeirinhas = [cor_laranja, cor_amarelo, cor_vermelho, cor_verde]
            cor_atual = cores_bandeirinhas[(int(x_pos / bandeirinha_width)) % len(cores_bandeirinhas)]
            
            # Desenha bandeirinha (triângulo)
            path = p.beginPath()
            path.moveTo(x_pos, height - margin)
            path.lineTo(x_pos + bandeirinha_width, height - margin)
            path.lineTo(x_pos + bandeirinha_width / 2, height - margin + bandeirinha_height)
            path.close()
            p.setFillColor(cor_atual)
            p.setStrokeColor(cor_atual)
            p.drawPath(path, fill=1, stroke=0)
            
            x_pos += bandeirinha_width
        
        y_start = height - margin - bandeirinha_height - 30
        
        # Título estilizado com cores de festa junina
        p.setFont("Helvetica-Bold", 36)
        title_text = "🎉 QR CODE - FESTA JUNINA 🎉"
        title_width = p.stringWidth(title_text, "Helvetica-Bold", 36)
        
        # Sombra/contorno do título
        p.setFillColor(cor_laranja)
        p.drawString((width - title_width) / 2 + 2, y_start - 2, title_text)
        p.setFillColor(cor_preto)
        p.drawString((width - title_width) / 2, y_start, title_text)
        
        y_start -= 60
        
        # Descrição (se houver) - estilizada
        if qr_code.descricao:
            p.setFont("Helvetica-Bold", 18)
            p.setFillColor(cor_vermelho)
            
            # Quebra linha se necessário
            desc_lines = []
            desc_width = p.stringWidth(qr_code.descricao, "Helvetica-Bold", 18)
            if desc_width > (width - 2 * margin):
                words = qr_code.descricao.split()
                current_line = ""
                for word in words:
                    test_line = f"{current_line} {word}".strip()
                    test_width = p.stringWidth(test_line, "Helvetica-Bold", 18)
                    if test_width > (width - 2 * margin):
                        if current_line:
                            desc_lines.append(current_line)
                        current_line = word
                    else:
                        current_line = test_line
                if current_line:
                    desc_lines.append(current_line)
            else:
                desc_lines = [qr_code.descricao]
            
            for line in desc_lines:
                line_width = p.stringWidth(line, "Helvetica-Bold", 18)
                p.drawString((width - line_width) / 2, y_start, line)
                y_start -= 28
        
        # Linha decorativa
        p.setStrokeColor(cor_laranja)
        p.setLineWidth(3)
        p.line(margin, y_start + 10, width - margin, y_start + 10)
        y_start -= 20
        
        # Código - estilizado
        p.setFont("Helvetica-Bold", 16)
        p.setFillColor(cor_preto)
        codigo_text = f"🔑 Código: {qr_code.codigo}"
        codigo_width = p.stringWidth(codigo_text, "Helvetica-Bold", 16)
        p.drawString((width - codigo_width) / 2, y_start, codigo_text)
        y_start -= 35
        
        # Data de início (se houver) - convertida para timezone de Brasília
        if qr_code.data_inicio:
            p.setFont("Helvetica", 14)
            p.setFillColor(HexColor('#666666'))
            # Converte para timezone de Brasília antes de formatar
            data_inicio_brasilia = localtime(qr_code.data_inicio)
            inicio_text = f"📅 Início: {data_inicio_brasilia.strftime('%d/%m/%Y às %H:%M')}"
            inicio_width = p.stringWidth(inicio_text, "Helvetica", 14)
            p.drawString((width - inicio_width) / 2, y_start, inicio_text)
            y_start -= 25
        
        # Data de expiração - estilizada - convertida para timezone de Brasília
        if qr_code.data_expiracao:
            p.setFont("Helvetica-Bold", 14)
            p.setFillColor(cor_vermelho)
            # Converte para timezone de Brasília antes de formatar
            data_expiracao_brasilia = localtime(qr_code.data_expiracao)
            expiracao_text = f"⏰ Válido até: {data_expiracao_brasilia.strftime('%d/%m/%Y às %H:%M')}"
            expiracao_width = p.stringWidth(expiracao_text, "Helvetica-Bold", 14)
            p.drawString((width - expiracao_width) / 2, y_start, expiracao_text)
            y_start -= 40
        
        # QR Code (centralizado, maior) com decoração
        qr_size = 350  # Aumentado para melhor leitura
        qr_x = (width - qr_size) / 2
        qr_y = y_start - qr_size - 30
        
        # Garante que não ultrapasse o limite inferior
        if qr_y < margin + 50:
            qr_size = min(qr_size, y_start - margin - 50)
            qr_x = (width - qr_size) / 2
            qr_y = y_start - qr_size - 30
        
        # Borda decorativa ao redor do QR code
        border_width = 8
        p.setStrokeColor(cor_laranja)
        p.setFillColor(cor_branco)
        p.setLineWidth(border_width)
        # Retângulo externo
        p.rect(qr_x - border_width - 10, qr_y - border_width - 10, 
               qr_size + 2 * (border_width + 10), 
               qr_size + 2 * (border_width + 10), 
               fill=0, stroke=1)
        
        # Decoração nos cantos (bandeirinhas pequenas)
        decor_size = 20
        cores_decor = [cor_amarelo, cor_vermelho, cor_verde]
        for i, (corner_x, corner_y) in enumerate([
            (qr_x - border_width - 10, qr_y + qr_size + border_width),
            (qr_x + qr_size + border_width, qr_y + qr_size + border_width),
            (qr_x - border_width - 10, qr_y - border_width - 10),
            (qr_x + qr_size + border_width, qr_y - border_width - 10)
        ]):
            p.setFillColor(cores_decor[i % len(cores_decor)])
            p.circle(corner_x, corner_y, decor_size, fill=1, stroke=0)
        
        # Desenha o QR code
        p.drawImage(ImageReader(buffer_img), qr_x, qr_y, width=qr_size, height=qr_size)
        
        # Linha decorativa antes da URL
        p.setStrokeColor(cor_amarelo)
        p.setLineWidth(2)
        p.line(margin, qr_y - 40, width - margin, qr_y - 40)
        
        # URL abaixo do QR code (centrada, estilizada)
        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(HexColor('#4169E1'))
        url_text = f"🌐 {qr_url}"
        url_width = p.stringWidth(url_text, "Helvetica-Bold", 12)
        
        # Se a URL for muito longa, quebra em múltiplas linhas
        if url_width > (width - 2 * margin):
            url_parts = []
            current_part = "🌐 "
            remaining_url = qr_url
            while remaining_url:
                test_text = f"{current_part}{remaining_url[:35]}"
                test_width = p.stringWidth(test_text, "Helvetica-Bold", 12)
                if test_width > (width - 2 * margin) and current_part != "🌐 ":
                    url_parts.append(current_part)
                    current_part = remaining_url[:35]
                    remaining_url = remaining_url[35:]
                else:
                    current_part = test_text
                    remaining_url = remaining_url[35:] if len(remaining_url) > 35 else ""
            if current_part:
                url_parts.append(current_part)
            
            url_y = qr_y - 60
            for part in url_parts:
                part_width = p.stringWidth(part, "Helvetica-Bold", 12)
                p.drawString((width - part_width) / 2, url_y, part)
                url_y -= 20
        else:
            p.drawString((width - url_width) / 2, qr_y - 60, url_text)
        
        # Rodapé decorativo
        footer_y = margin + 20
        p.setFont("Helvetica", 10)
        p.setFillColor(HexColor('#666666'))
        footer_text = "🎪 ArraiáTech - Sistema de Reservas Antecipadas 🎪"
        footer_width = p.stringWidth(footer_text, "Helvetica", 10)
        p.drawString((width - footer_width) / 2, footer_y, footer_text)
        
        # Bandeirinhas no rodapé
        footer_y_bandeirinhas = margin
        x_pos = margin
        while x_pos < width - margin:
            cores_bandeirinhas = [cor_verde, cor_amarelo, cor_vermelho, cor_laranja]
            cor_atual = cores_bandeirinhas[(int(x_pos / bandeirinha_width)) % len(cores_bandeirinhas)]
            
            path = p.beginPath()
            path.moveTo(x_pos, footer_y_bandeirinhas)
            path.lineTo(x_pos + bandeirinha_width, footer_y_bandeirinhas)
            path.lineTo(x_pos + bandeirinha_width / 2, footer_y_bandeirinhas - bandeirinha_height)
            path.close()
            p.setFillColor(cor_atual)
            p.setStrokeColor(cor_atual)
            p.drawPath(path, fill=1, stroke=0)
            
            x_pos += bandeirinha_width
        
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
        
        # Aceita data_inicio e data_expiracao (ou data_fim) diretamente, ou fallback para dias_expiracao
        data_inicio_str = request.data.get('data_inicio')
        data_expiracao_str = request.data.get('data_expiracao') or request.data.get('data_fim')
        dias_expiracao = request.data.get('dias_expiracao')
        
        data_inicio = None
        data_expiracao = None
        
        # Processa data_inicio
        if data_inicio_str:
            try:
                from django.utils.dateparse import parse_datetime
                data_inicio = parse_datetime(data_inicio_str)
                if not data_inicio:
                    # Tenta parse como string ISO
                    data_inicio = timezone.datetime.fromisoformat(data_inicio_str.replace('Z', '+00:00'))
                    if timezone.is_naive(data_inicio):
                        data_inicio = timezone.make_aware(data_inicio)
            except (ValueError, AttributeError) as e:
                return Response(
                    {'error': f'Data de início inválida: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Processa data_expiracao/data_fim
        if data_expiracao_str:
            try:
                from django.utils.dateparse import parse_datetime
                data_expiracao = parse_datetime(data_expiracao_str)
                if not data_expiracao:
                    # Tenta parse como string ISO
                    data_expiracao = timezone.datetime.fromisoformat(data_expiracao_str.replace('Z', '+00:00'))
                    if timezone.is_naive(data_expiracao):
                        data_expiracao = timezone.make_aware(data_expiracao)
            except (ValueError, AttributeError) as e:
                return Response(
                    {'error': f'Data de expiração inválida: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif dias_expiracao:
            # Fallback para dias_expiracao (compatibilidade)
            data_base = data_inicio if data_inicio else timezone.now()
            data_expiracao = data_base + timedelta(days=dias_expiracao)
        
        # Valida que data_inicio < data_expiracao se ambos existirem
        if data_inicio and data_expiracao and data_inicio >= data_expiracao:
            return Response(
                {'error': 'Data de início deve ser anterior à data de expiração'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        qr_code = QRCodeReserva.objects.create(
            codigo=codigo,
            descricao=descricao,
            data_inicio=data_inicio,
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
        
        agora = timezone.now()
        
        # Verifica se ainda não começou
        if qr.data_inicio and qr.data_inicio > agora:
            return Response(
                {'error': 'QR code ainda não está ativo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verifica expiração
        if qr.data_expiracao and qr.data_expiracao < agora:
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
            'data_inicio': qr.data_inicio,
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
            agora = timezone.now()
            
            # Verifica se ainda não começou
            if qr_code_obj.data_inicio and qr_code_obj.data_inicio > agora:
                return Response(
                    {'error': 'QR code ainda não está ativo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verifica expiração
            if qr_code_obj.data_expiracao and qr_code_obj.data_expiracao < agora:
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

