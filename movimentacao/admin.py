from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Produto, Venda, Caixa

class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('id' , 'nome', 'unidade', 'quantidade_inicial' , 'preco', 'vendas', 'saldo', 'arrecadacao', 'data_criacao')

admin.site.register(Produto, ProdutoAdmin)

class CaixaAdmin(admin.ModelAdmin):
    list_display = ('id' , 'caixa')

admin.site.register(Caixa, CaixaAdmin)

class VendaAdmin(admin.ModelAdmin):
    list_display = ('id','produto', 'quantidade', 'caixa' , 'data')
    list_filter = ('caixa', 'produto')

    def save_model(self, request, obj, form, change):
        try:
            produto = Produto.objects.get(id=obj.produto.id)
            novo_saldo = produto.saldo - obj.quantidade
            produto.saldo = novo_saldo
            produto.save()
            obj.saldo = novo_saldo
            super().save_model(request, obj, form, change)
            messages.success(request, f'Saldo de {obj.produto}: {novo_saldo}')
        except ValidationError as e:
            self.message_user(request, f"Erro: {e}", level='ERROR')

admin.site.register(Venda, VendaAdmin)
