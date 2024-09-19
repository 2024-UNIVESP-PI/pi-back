from django.http import HttpResponse

from django.shortcuts import render

# Create your views here.

def movimentacao(request):
    print('produtos')
    return render(request, 'movimentacao.html')
    
