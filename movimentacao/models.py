from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal

class Caixa(models.Model):
    nome = models.CharField(max_length=200)
    usuario = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="Usuário para login do caixa")
    senha = models.CharField(max_length=255, null=True, blank=True, help_text="Senha (armazenada em texto simples - NÃO recomendado para produção)")
    
    class Meta:
        verbose_name_plural = "Caixas"
        indexes = [
            models.Index(fields=['usuario']),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.usuario})"
    
class Ficha(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    saldo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by_caixa = models.ForeignKey('Caixa', on_delete=models.SET_NULL, null=True, blank=True, related_name='fichas_deletadas')
    
    def __str__(self):
        return f"{self.numero} (Saldo ${self.saldo})"
    
    def recarga(self, valor):
        valor = Decimal(valor)
        if valor <= 0:
            raise ValueError("O valor de recarga deve ser positivo.")
        
        self.saldo += valor
        self.save()


class Produto(models.Model):
    MEDIDA_CHOICES = (
        ('UN', 'Unidade'),
        ('PCT', 'Pacote'),
        ('L', 'Litro'),
        ('KG', 'Quilograma'),
    )

    CATEGORIA_CHOICES = (
        ('bebidas', 'Bebidas'),
        ('doces', 'Doces'),
        ('salgados', 'Salgados'),
        ('jogos', 'Jogos'),
    )
    
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default='doces',
        help_text="Categoria do produto"
    )
    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT, related_name='produtos')
    nome = models.CharField(max_length=100, unique=True)
    medida = models.CharField(max_length=3, choices=MEDIDA_CHOICES)
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    estoque = models.PositiveSmallIntegerField(default=0, editable=False)
    
    # Campos para reserva antecipada
    disponivel_reserva = models.BooleanField(default=False, help_text="Disponível para reserva antecipada")
    limite_reserva = models.PositiveSmallIntegerField(default=2, help_text="Limite de itens por reserva (padrão: 2)")
    quantidade_reserva_disponivel = models.PositiveSmallIntegerField(default=0, help_text="Quantidade disponível para reserva")

    data_criacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nome} (Estoque {self.estoque})"
    
    @property
    def total_reservas_antecipadas(self):
        """Retorna total de reservas antecipadas confirmadas ou pendentes"""
        return self.reservas.filter(
            status__in=['pendente', 'confirmada']
        ).aggregate(
            total=models.Sum('quantidade')
        )['total'] or 0

    def atualizar_estoque(self, novo_estoque):
        self.estoque = novo_estoque
        super().save(update_fields=['estoque'])

class MovimentacaoEstoque(models.Model):
    TIPO_CHOICES = (
        ('E', 'Entrada'),
        ('S', 'Saída'),
    )
    
    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT, related_name='movimentacoes')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes')
    quantidade = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    
    data = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.produto.nome} - {self.tipo} ({self.quantidade})"
    
    class Meta:
        verbose_name_plural = "Movimentações estoque"
    
    def clean(self):
        tipo = self.tipo
        quantidade = self.quantidade
        estoque = self.produto.estoque
        
        # Se tiver pk (movimentação já existe), calcula a diferença da quantidade
        if self.pk:
            movimentacao = self.__class__.objects.get(pk=self.pk)
            diferenca = quantidade - movimentacao.quantidade
            
            # Verifica se pode atualizar movimentação
            if tipo == 'S' and estoque < diferenca:
                raise ValidationError("Estoque insuficiente para aumentar movimentação de saída.")
            elif tipo == 'E' and estoque + diferenca < 0:
                raise ValidationError("Estoque insuficiente para reduzir movimentação de entrada.")
        
        # Se não tiver pk (movimentação nova, ainda não existe)
        else:
            # Verifica se pode criar movimentação
            if tipo == 'S' and estoque < quantidade:
                raise ValidationError("Estoque insuficiente para realizar movimentação de saída.")
            elif tipo == 'E' and estoque + quantidade < 0:
                raise ValidationError("Não é possível ter estoque negativo após a movimentação.")

    def save(self, *args, **kwargs):
        # Antes de salvar, executa validações
        self.full_clean()
        
        tipo = self.tipo
        quantidade = self.quantidade
        estoque = self.produto.estoque
        
        # Se tiver pk (movimentação já existe)
        if self.pk:
            movimentacao = self.__class__.objects.get(pk=self.pk)
            diferenca = quantidade - movimentacao.quantidade
            
            if tipo == 'S':
                estoque -= diferenca
            elif tipo == 'E':
                estoque += diferenca

        # Se não tiver pk (movimentação nova, ainda não existe)
        else:
            if tipo == 'S':
                estoque -= quantidade
            elif tipo == 'E':
                estoque += quantidade

        # Salva a movimentação
        super().save(*args, **kwargs)
        
        # Atualiza o estoque do produto
        self.produto.atualizar_estoque(estoque)
        
    def delete(self, *args, **kwargs):
        tipo = self.tipo
        quantidade = self.quantidade
        estoque = self.produto.estoque
        
        # Se for apagar uma entrada, verifica se há estoque suficiente
        if tipo == 'E':
            if estoque < quantidade:
                raise ValidationError("Estoque insuficiente para apagar movimentação de entrada.")
            estoque -= quantidade
        elif tipo == 'S':
            estoque += quantidade
        
        # Deleta a movimentação
        super().delete(*args, **kwargs)
        
        # Atualiza o estoque do produto
        self.produto.atualizar_estoque(estoque)

class Venda(models.Model):
    movimentacao = models.OneToOneField(MovimentacaoEstoque, on_delete=models.CASCADE)
    ficha = models.ForeignKey(Ficha, on_delete=models.PROTECT, related_name='compras')
    
    @property
    def caixa(self):
        return self.movimentacao.caixa
    
    @property
    def produto(self):
        return self.movimentacao.produto.nome
    
    @property
    def data(self):
        return self.movimentacao.data
    
    @property
    def quantidade(self):
        return self.movimentacao.quantidade
        
    @property
    def preco_total(self):
        movimentacao = self.movimentacao
        produto = movimentacao.produto
        return produto.preco * movimentacao.quantidade
    
    def __str__(self):
        return f"{self.movimentacao} - Ficha {self.ficha}"
    
    def clean(self):
        tipo_movimentacao = self.movimentacao.tipo
        saldo_ficha = self.ficha.saldo
        preco_total = self.preco_total
        
        # Verifica se a movimentação não é de saída
        if tipo_movimentacao != 'S':
            raise ValidationError("A venda só pode ser associada a movimentações de saída.")
        
        # Se a venda existe
        if self.pk:
            venda = self.__class__.objects.get(pk=self.pk)
            diferenca = preco_total - venda.preco_total
            
            # Verifica se tem saldo suficiente para novo valor da compra
            if saldo_ficha - diferenca < 0:
                raise ValidationError("Saldo insuficiente para alterar venda.")
            
        # A venda não exise. Verifica se a ficha tem saldo suficiente
        elif saldo_ficha < preco_total:
            raise ValidationError("Saldo insuficiente para venda.")
    
    def save(self, *args, **kwargs):
        # Antes de salvar, executa validações
        self.full_clean()
        
        preco_total = self.preco_total
        saldo_ficha = self.ficha.saldo
        
        if self.pk:
            venda = self.__class__.objects.get(pk=self.pk)
            diferenca = preco_total - venda.preco_total
            
            # Atualiza saldo da ficha
            saldo_ficha -= diferenca
        else:
            # Reduz saldo da ficha
            saldo_ficha -= preco_total
        
        # Salva novo saldo da ficha
        self.ficha.saldo = saldo_ficha
        self.ficha.save()
        
        # Salva a movimentação
        super().save(*args, **kwargs)


class QRCodeReserva(models.Model):
    """QR Code para reserva antecipada"""
    codigo = models.CharField(max_length=255, unique=True, help_text="Código único do QR code")
    descricao = models.CharField(max_length=200, blank=True, help_text="Descrição opcional")
    data_expiracao = models.DateTimeField(null=True, blank=True, help_text="Data de expiração do QR code")
    ativo = models.BooleanField(default=True)
    produtos_disponiveis = models.ManyToManyField(Produto, related_name='qr_codes_reserva', blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data_criacao']
        verbose_name_plural = "QR Codes de Reserva"
        indexes = [
            models.Index(fields=['codigo', 'ativo']),
        ]
    
    def __str__(self):
        return f"QR Reserva: {self.codigo} - {'Ativo' if self.ativo else 'Inativo'}"


class ReservaProduto(models.Model):
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('finalizada', 'Finalizada'),
    )
    
    # Campos para reserva antecipada (sem ficha inicialmente)
    ficha = models.ForeignKey(Ficha, on_delete=models.CASCADE, related_name='reservas', null=True, blank=True)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='reservas')
    quantidade = models.PositiveSmallIntegerField()
    
    # Informações do usuário (para reserva antecipada)
    nome_completo = models.CharField(max_length=200)
    cpf = models.CharField(max_length=11, unique=False, help_text="CPF do usuário (chave única para reserva)")
    
    # QR Code de origem (se aplicável)
    qr_code_reserva = models.ForeignKey(QRCodeReserva, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservas')
    
    data_reserva = models.DateTimeField(auto_now_add=True)
    data_confirmacao = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    observacoes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-data_reserva']
        verbose_name_plural = "Reservas de Produtos"
        indexes = [
            models.Index(fields=['ficha', 'status']),
            models.Index(fields=['produto', 'status']),
            models.Index(fields=['cpf', 'status']),
            models.Index(fields=['qr_code_reserva', 'status']),
        ]
        # Evitar múltiplas reservas do mesmo CPF para mesmo produto
        constraints = [
            models.UniqueConstraint(
                fields=['cpf', 'produto', 'status'],
                condition=models.Q(status__in=['pendente', 'confirmada']),
                name='unique_reserva_ativa_por_cpf_produto'
            )
        ]
    
    def __str__(self):
        if self.ficha:
            return f"Reserva {self.id} - Ficha {self.ficha.numero} - {self.produto.nome}"
        return f"Reserva {self.id} - {self.nome_completo} ({self.cpf}) - {self.produto.nome}"


class Recarga(models.Model):
    """Modelo para registrar histórico de recargas de fichas"""
    ficha = models.ForeignKey(Ficha, on_delete=models.CASCADE, related_name='recargas')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='recargas', null=True, blank=True, help_text="Produto relacionado à recarga (opcional)")
    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT, related_name='recargas')
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Valor da recarga"
    )
    data = models.DateTimeField(auto_now_add=True, help_text="Data e hora da recarga")
    observacoes = models.TextField(blank=True, help_text="Observações sobre a recarga")
    
    class Meta:
        ordering = ['-data']
        verbose_name_plural = "Recargas"
        indexes = [
            models.Index(fields=['ficha', 'data']),
            models.Index(fields=['caixa', 'data']),
            models.Index(fields=['produto', 'data']),
        ]
    
    def __str__(self):
        return f"Recarga R${self.valor} - Ficha {self.ficha.numero} - {self.caixa.nome} - {self.data.strftime('%d/%m/%Y %H:%M')}"
