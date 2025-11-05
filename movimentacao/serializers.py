from rest_framework import serializers
from .models import Caixa, Ficha, Produto, MovimentacaoEstoque, Venda, ReservaProduto, QRCodeReserva, Recarga

class CaixaSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(required=False, allow_blank=True, read_only=False)
    senha_atual = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Caixa
        fields = '__all__'
    
    def to_representation(self, instance):
        """Retorna senha na representação (para admin)"""
        representation = super().to_representation(instance)
        # Inclui senha diretamente do modelo
        if hasattr(instance, 'senha') and instance.senha:
            representation['senha'] = instance.senha
        return representation
    
    def create(self, validated_data):
        """Cria caixa com senha"""
        senha = validated_data.pop('senha', '')
        if not senha:
            raise serializers.ValidationError({'senha': 'Senha é obrigatória ao criar caixa'})
        caixa = Caixa.objects.create(**validated_data, senha=senha)
        return caixa
    
    def update(self, instance, validated_data):
        """Atualiza caixa, mantendo senha se não fornecida"""
        senha = validated_data.pop('senha', None)
        if senha:
            instance.senha = senha
        elif 'senha' in validated_data:
            # Se senha foi enviada vazia, não atualiza
            validated_data.pop('senha', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class FichaSerializer(serializers.ModelSerializer):
    saldo = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False
    )
    deleted_by_caixa_nome = serializers.CharField(source='deleted_by_caixa.nome', read_only=True)
    
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
    total_reservas_antecipadas = serializers.ReadOnlyField()

    class Meta:
        model = Produto
        fields = '__all__'

    def create(self, validated_data):
        estoque = validated_data.pop('estoque', 0)
        produto = Produto.objects.create(**validated_data)
        if estoque > 0:
            MovimentacaoEstoque.objects.create(
                produto=produto,
                quantidade=estoque,
                tipo='E',
                caixa=produto.caixa
            )
        return produto

    def update(self, instance, validated_data):
        estoque_novo = validated_data.pop('estoque', None)

        # Atualiza os demais campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Se a quantidade de estoque foi informada, trata movimentação
        if estoque_novo is not None and estoque_novo != instance.estoque:
            diferenca = estoque_novo - instance.estoque
            tipo_mov = 'E' if diferenca > 0 else 'S'
            MovimentacaoEstoque.objects.create(
                produto=instance,
                quantidade=abs(diferenca),
                tipo=tipo_mov,
                caixa=instance.caixa
            )
            instance.estoque = estoque_novo

        instance.save()
        return instance

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
    produto_nome = serializers.CharField(source='movimentacao.produto.nome', read_only=True)
    caixa_nome = serializers.CharField(source='movimentacao.caixa.nome', read_only=True)
    quantidade = serializers.IntegerField(source='movimentacao.quantidade', read_only=True)
    data = serializers.DateTimeField(source='movimentacao.data', read_only=True)

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

class RecargaSerializer(serializers.ModelSerializer):
    """Serializer para histórico de recargas"""
    produto_nome = serializers.CharField(source='produto.nome', read_only=True, allow_null=True)
    caixa_nome = serializers.CharField(source='caixa.nome', read_only=True)
    ficha_numero = serializers.IntegerField(source='ficha.numero', read_only=True)
    
    class Meta:
        model = Recarga
        fields = ['id', 'ficha', 'ficha_numero', 'produto', 'produto_nome', 'caixa', 'caixa_nome', 'valor', 'data', 'observacoes']


class FichaHistoricoSerializer(serializers.Serializer):
    """Serializer para histórico completo de uma ficha"""
    ficha = FichaSerializer()
    vendas = VendaSerializer(many=True)
    recargas = RecargaSerializer(many=True)


class ReservaProdutoSerializer(serializers.ModelSerializer):
    ficha_info = FichaSerializer(source='ficha', read_only=True)
    produto_info = ProdutoSerializer(source='produto', read_only=True)
    preco_total = serializers.SerializerMethodField()
    
    class Meta:
        model = ReservaProduto
        fields = '__all__'
    
    def get_preco_total(self, obj):
        return float(obj.produto.preco * obj.quantidade)


class ReservaPublicaSerializer(serializers.Serializer):
    """Serializer para criação de reservas públicas (sem ficha)"""
    nome_completo = serializers.CharField(max_length=200)
    cpf = serializers.CharField(max_length=11, min_length=11)
    produtos = serializers.ListField(
        child=serializers.DictField()
    )
    qr_code = serializers.CharField(required=False, allow_blank=True)
    
    def validate_produtos(self, value):
        """Valida estrutura dos produtos"""
        for produto_data in value:
            if 'produto_id' not in produto_data or 'quantidade' not in produto_data:
                raise serializers.ValidationError("Cada produto deve ter 'produto_id' e 'quantidade'")
            if produto_data['quantidade'] <= 0:
                raise serializers.ValidationError("Quantidade deve ser maior que zero")
        return value
    
    def validate_cpf(self, value):
        """Valida CPF básico (apenas formato numérico)"""
        if not value.isdigit():
            raise serializers.ValidationError("CPF deve conter apenas números")
        if len(value) != 11:
            raise serializers.ValidationError("CPF deve ter 11 dígitos")
        return value


class QRCodeReservaSerializer(serializers.ModelSerializer):
    produtos_disponiveis = ProdutoSerializer(many=True, read_only=True)
    produtos_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Produto.objects.all(),
        source='produtos_disponiveis',
        write_only=True,
        required=False
    )
    qr_image = serializers.SerializerMethodField()
    
    class Meta:
        model = QRCodeReserva
        fields = '__all__'
    
    def get_qr_image(self, obj):
        """Gera imagem do QR code em base64"""
        try:
            import qrcode
            import base64
            from io import BytesIO
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(obj.codigo)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            image_base64 = base64.b64encode(buffer.read()).decode()
            return f'data:image/png;base64,{image_base64}'
        except ImportError:
            return None
