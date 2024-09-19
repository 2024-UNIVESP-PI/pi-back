from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('transparencia/', views.transparencia, name="transparencia"),
    path('sugestao/', views.criar_sugestao, name='criar_sugestao'),
    path('sucesso/', views.sucesso, name='sucesso'),
]