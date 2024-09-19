from django.http import HttpResponse
from .models import Sugestao
from .forms import SugestaoForm
from django.shortcuts import render, redirect
from django.views.generic import ListView
from movimentacao.models import Produto
# Create your views here.

def transparencia(request):
    produtos_list = Produto.objects.all()  # Obtém todos os produtos do banco de dados
    total_saldo_inicial = sum([produto.quantidade_inicial for produto in produtos_list])
    total_vendas = sum([produto.vendas for produto in produtos_list])
    total_saldo = sum([produto.saldo for produto in produtos_list])
    total_arrecadacao = sum([produto.arrecadacao for produto in produtos_list])
    return render(request, 'transparencia.html', {
        'produtos_list': produtos_list,
        'total_saldo_inicial': total_saldo_inicial,
        'total_vendas': total_vendas,
        'total_saldo': total_saldo,
        'total_arrecadacao': total_arrecadacao
    })


def criar_sugestao(request):
    if request.method == 'POST':
        form = SugestaoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('sucesso')  # Redireciona para uma página de sucesso após salvar
    else:
        form = SugestaoForm()
    return render(request, 'sugestao_form.html', {'form': form})

def sucesso(request):
    return render(request, 'sucesso.html')


def index(request):
    return render(request, 'publico_index.html')
