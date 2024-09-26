from django.contrib import admin
from publico import models
# Register your models here.

@admin.register(models.Sugestao)

class SugestaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'telefone', 'situacao', 'sugestao', 'data_sugestao')
    list_filter = ('situacao', 'data_sugestao')
    list_per_page = 10  # Define o número de sugestões exibidas por página
    ordering = ('-id',)  # Ordena as sugestões pela data, da mais nova para a mais antiga
    readonly_fields = ('nome', 'telefone', 'sugestao', 'data_sugestao')