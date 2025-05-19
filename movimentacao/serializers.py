from rest_framework import serializers
from .models import Caixa, Ficha, Produto, MovimentacaoEstoque, Venda

class CaixaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caixa
        fields = '__all__'

class FichaSerializer(serializers.ModelSerializer):
    saldo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False
    )
    
    class Meta:
        model = Ficha
        fields = '__all__'

class RecargaFichaSerializer(serializers.Serializer):
    valor = serializers.DecimalField(max_digits=10, decimal_places=2)
 
class ProdutoSerializer(serializers.ModelSerializer):
    estoque = serializers.IntegerField(required=False)
    preco = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False
    )
    categoria = serializers.CharField()

    class Meta:
        model = Produto
        fields = '__all__'
        # extra_kwargs = {
        #     'estoque': {'read_only': True},
        # }

    def create(self, validated_data):
        # Pega o valor de estoque inicial, se fornecido
        estoque = validated_data.pop('estoque', 0)
        
        # Cria o produto
        produto = Produto.objects.create(**validated_data)
        
        # Se houver um valor de estoque inicial, cria uma movimentação de entrada
        if estoque > 0:
            MovimentacaoEstoque.objects.create(
                produto=produto,
                quantidade=estoque,
                tipo='E',
                caixa=produto.caixa
            )
        return produto

class MovimentacaoEstoqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimentacaoEstoque
        fields = '__all__'
        
class MovimentacaoVendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimentacaoEstoque
        fields = ['caixa', 'produto', 'quantidade', 'data']
        extra_kwargs = {
            'data': {'read_only': True},
        }
        
class VendaSerializer(serializers.ModelSerializer):
    movimentacao = MovimentacaoVendaSerializer()
    preco_total = serializers.ReadOnlyField()

    class Meta:
        model = Venda
        fields = '__all__'
    
    def create(self, validated_data):
        movimentacao_data = validated_data.pop('movimentacao')
        movimentacao_data['tipo'] = 'S'
        movimentacao = MovimentacaoEstoque.objects.create(**movimentacao_data)
        venda = Venda.objects.create(movimentacao=movimentacao, **validated_data)
        return venda
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['ficha'] = FichaSerializer(instance.ficha).data
        return representation
