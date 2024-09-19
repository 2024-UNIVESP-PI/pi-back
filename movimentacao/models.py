from django.db import models
from django.core.exceptions import ValidationError

class Produto(models.Model):
    UNIDADE_CHOICES = (
        ('UN', 'Unidade'),
        ('PCT', 'Pacote'),
        ('L', 'Litros'),
        ('KG', 'Quilograma'),
    )

    nome = models.CharField(max_length=100, unique=True)
    unidade = models.CharField(max_length=20, choices=UNIDADE_CHOICES, blank=False)
    quantidade_inicial = models.IntegerField(default=0)
    saldo = models.IntegerField(default=0, editable=False)
    vendas = models.IntegerField(default=0, editable=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    arrecadacao = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)


    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.pk:  # Se o produto está sendo criado
            self.saldo = self.quantidade_inicial
        else:
            self.saldo = self.quantidade_inicial - self.vendas
        self.arrecadacao = self.vendas * self.preco
        super().save(*args, **kwargs)
        
class Caixa(models.Model):
    caixa = models.CharField(max_length=200)
    def __str__(self):
        return self.caixa      

class Venda(models.Model):
    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(auto_now_add=True)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    
    def __str__(self):
        return f"{self.produto.nome}"

    def clean(self):
        if self.quantidade > self.produto.saldo:
            raise ValidationError(f'Quantidade inválida, saldo insuficiente. Saldo atual do produto: {self.produto.saldo}')

    def save(self, *args, **kwargs):
        self.full_clean()  # Chama o método clean() antes de salvar
        self.saldo = self.produto.saldo  # Atualiza o saldo
        super().save(*args, **kwargs)
        # Após salvar, atualiza o saldo do produto e o total de vendas
        self.produto.vendas += self.quantidade
        self.produto.save()

