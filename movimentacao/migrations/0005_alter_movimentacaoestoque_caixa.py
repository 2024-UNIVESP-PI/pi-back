# Generated by Django 4.2.9 on 2024-09-25 20:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('movimentacao', '0004_ficha_movimentacaoestoque_caixa'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movimentacaoestoque',
            name='caixa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='movimentacao.caixa'),
        ),
    ]
