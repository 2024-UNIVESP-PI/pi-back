from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

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
        validators=[MinValueValidator(0)]
    )
    
    def __str__(self):
        return f"{self.numero} (${self.saldo})"

class Produto(models.Model):
    UNIDADE_CHOICES = (
        ('UN', 'Unidade'),
        ('PCT', 'Pacote'),
        ('L', 'Litros'),
        ('KG', 'Quilograma'),
    )

    nome = models.CharField(max_length=100, unique=True)
    unidade = models.CharField(max_length=3, choices=UNIDADE_CHOICES)
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    estoque = models.PositiveSmallIntegerField(default=0, editable=False)

    data_criacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nome} ({self.estoque})"

    def atualizar_estoque(self, novo_estoque):
        # entradas = self.movimentacoes.filter(tipo='E').aggregate(Sum('quantidade'))['quantidade__sum'] or 0
        # saidas = self.movimentacoes.filter(tipo='S').aggregate(Sum('quantidade'))['quantidade__sum'] or 0
        # self.estoque = entradas - saidas
        self.estoque = novo_estoque
        super().save(update_fields=['estoque'])

class MovimentacaoEstoque(models.Model):
    TIPO_CHOICES = (
        ('E', 'Entrada'),
        ('S', 'Saída'),
    )
    
    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes')
    quantidade = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    
    data = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.produto.nome} - {self.tipo} ({self.quantidade})"
    
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
