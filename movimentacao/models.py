from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

class Caixa(models.Model):
    nome = models.CharField(max_length=200)
    
    def __str__(self):
        return self.nome
    
class Ficha(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    saldo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    def __str__(self):
        return f"{self.numero} (${self.saldo})"
    
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

    data_criacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nome} ({self.estoque})"

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
    def preco_total(self):
        movimentacao = self.movimentacao
        produto = movimentacao.produto
        return produto.preco * movimentacao.quantidade
    
    def __str__(self):
        return f"{self.movimentacao} - {self.ficha}"
    
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
        