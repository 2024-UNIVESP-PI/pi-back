from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Caixa, Ficha, Produto, MovimentacaoEstoque

class CaixaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome')
    # list_filter = ()
    search_fields = ('nome',)

admin.site.register(Caixa, CaixaAdmin)

class FichaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'saldo')
    # list_filter = ()
    search_fields = ('numero',)

admin.site.register(Ficha, FichaAdmin)

class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'estoque', 'medida', 'preco', 'caixa')
    list_filter = ('medida',)
    search_fields = ('nome',)

admin.site.register(Produto, ProdutoAdmin)

class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('produto', 'tipo', 'quantidade', 'caixa')
    list_filter = ('tipo',)
    search_fields = ('produto__nome',)
    
    # Sobrescreve a ação de deleção em massa
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            tipo = obj.tipo
            quantidade = obj.quantidade
            estoque = obj.produto.estoque
            
            if tipo == 'E':
                if estoque < quantidade:
                    self.message_user(
                        request, 
                        f"Estoque insuficiente para apagar movimentação de entrada {obj}.",
                        level=messages.ERROR
                    )
                    continue # Pula a exclusão deste objeto e vai para o próximo
            
            try:
                obj.delete()
            except Exception as e:
                self.message_user(
                    request, 
                    f"Erro ao excluir {obj}: {e}", 
                    level=messages.ERROR
                )

admin.site.register(MovimentacaoEstoque, MovimentacaoEstoqueAdmin)
