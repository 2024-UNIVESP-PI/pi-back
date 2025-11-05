# Generated manually for QR Code system implementation

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('movimentacao', '0014_alter_movimentacaoestoque_options_produto_categoria'),
    ]

    operations = [
        # Adiciona campos QR code à Ficha
        migrations.AddField(
            model_name='ficha',
            name='qr_code',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='ficha',
            name='qr_code_generated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ficha',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        # Cria índice para qr_code
        migrations.AddIndex(
            model_name='ficha',
            index=models.Index(fields=['qr_code'], name='movimentac_qr_code_idx'),
        ),
        # Cria modelo ReservaProduto
        migrations.CreateModel(
            name='ReservaProduto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade', models.PositiveSmallIntegerField()),
                ('data_reserva', models.DateTimeField(auto_now_add=True)),
                ('data_confirmacao', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('confirmada', 'Confirmada'), ('cancelada', 'Cancelada'), ('finalizada', 'Finalizada')], default='pendente', max_length=20)),
                ('observacoes', models.TextField(blank=True)),
                ('ficha', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservas', to='movimentacao.ficha')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservas', to='movimentacao.produto')),
            ],
            options={
                'verbose_name_plural': 'Reservas de Produtos',
                'ordering': ['-data_reserva'],
            },
        ),
        # Adiciona índices para ReservaProduto
        migrations.AddIndex(
            model_name='reservaproduto',
            index=models.Index(fields=['ficha', 'status'], name='movimentac_ficha_i_status_idx'),
        ),
        migrations.AddIndex(
            model_name='reservaproduto',
            index=models.Index(fields=['produto', 'status'], name='movimentac_produto_status_idx'),
        ),
    ]

