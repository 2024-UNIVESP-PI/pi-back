from django.db import models
from django.core.validators import RegexValidator

# Validator para número de telefone
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{10}$',
    message="O número de telefone deve ser inserido no formato: '+999999999'. Até 10 dígitos permitidos."
)

class Sugestao(models.Model):
    SITUACAO_CHOICES = [
        ('pendente', 'Pendente'),
        ('avaliada', 'Avaliada'),
    ]

    nome = models.CharField(max_length=100)
    telefone = models.CharField(validators=[phone_regex], max_length=17)  # Adicionando campo telefone com validação
    sugestao = models.TextField(max_length=200)
    data_sugestao = models.DateTimeField(auto_now_add=True)
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default='pendente')  # Adicionando campo situação
    
    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Sugestões"
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()  # Convertendo o nome para maiúsculo
        super(Sugestao, self).save(*args, **kwargs)
    
