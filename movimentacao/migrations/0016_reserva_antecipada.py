# Generated manually for Reserva Antecipada system

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('movimentacao', '0015_ficha_qrcode_reservaproduto'),
    ]

    operations = [
        # Adiciona campos de reserva antecipada ao Produto
        migrations.AddField(
            model_name='produto',
            name='disponivel_reserva',
            field=models.BooleanField(default=False, help_text='Disponível para reserva antecipada'),
        ),
        migrations.AddField(
            model_name='produto',
            name='limite_reserva',
            field=models.PositiveSmallIntegerField(default=2, help_text='Limite de itens por reserva (padrão: 2)'),
        ),
        migrations.AddField(
            model_name='produto',
            name='quantidade_reserva_disponivel',
            field=models.PositiveSmallIntegerField(default=0, help_text='Quantidade disponível para reserva'),
        ),
        # Cria modelo QRCodeReserva
        migrations.CreateModel(
            name='QRCodeReserva',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Código único do QR code', max_length=255, unique=True)),
                ('descricao', models.CharField(blank=True, help_text='Descrição opcional', max_length=200)),
                ('data_expiracao', models.DateTimeField(blank=True, help_text='Data de expiração do QR code', null=True)),
                ('ativo', models.BooleanField(default=True)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'QR Codes de Reserva',
                'ordering': ['-data_criacao'],
            },
        ),
        # Cria tabela ManyToMany para produtos disponíveis
        migrations.CreateModel(
            name='QRCodeReservaProdutosDisponiveis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qrcodereserva', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='movimentacao.qrcodereserva')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='movimentacao.produto')),
            ],
        ),
        # Adiciona índices para QRCodeReserva
        migrations.AddIndex(
            model_name='qrcodereserva',
            index=models.Index(fields=['codigo', 'ativo'], name='movimentac_codigo_ativo_idx'),
        ),
        # Adiciona campos ao ReservaProduto
        migrations.AddField(
            model_name='reservaproduto',
            name='cpf',
            field=models.CharField(help_text='CPF do usuário (chave única para reserva)', max_length=11),
        ),
        migrations.AddField(
            model_name='reservaproduto',
            name='nome_completo',
            field=models.CharField(max_length=200),
        ),
        migrations.AddField(
            model_name='reservaproduto',
            name='qr_code_reserva',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reservas', to='movimentacao.qrcodereserva'),
        ),
        # Torna ficha opcional
        migrations.AlterField(
            model_name='reservaproduto',
            name='ficha',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reservas', to='movimentacao.ficha'),
        ),
        # Adiciona índices para ReservaProduto
        migrations.AddIndex(
            model_name='reservaproduto',
            index=models.Index(fields=['cpf', 'status'], name='movimentac_cpf_status_idx'),
        ),
        migrations.AddIndex(
            model_name='reservaproduto',
            index=models.Index(fields=['qr_code_reserva', 'status'], name='movimentac_qr_code_status_idx'),
        ),
        # Adiciona constraint único para evitar múltiplas reservas do mesmo CPF
        migrations.AddConstraint(
            model_name='reservaproduto',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status__in', ['pendente', 'confirmada'])),
                fields=['cpf', 'produto', 'status'],
                name='unique_reserva_ativa_por_cpf_produto'
            ),
        ),
    ]

