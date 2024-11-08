# Generated by Django 4.2.9 on 2024-09-26 21:09

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movimentacao', '0009_produto_caixa'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ficha',
            name='saldo',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator('0.00')]),
        ),
        migrations.AlterField(
            model_name='produto',
            name='preco',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator('0.00')]),
        ),
    ]
