from django import forms
from .models import Sugestao

class SugestaoForm(forms.ModelForm):
    class Meta:
        model = Sugestao
        fields = 'nome', 'telefone','sugestao',