# Generated by Django 4.2.9 on 2024-10-14 20:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('movimentacao', '0010_alter_ficha_saldo_alter_produto_preco'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movimentacaoestoque',
            name='caixa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimentacoes', to='movimentacao.caixa'),
        ),
        migrations.AlterField(
            model_name='produto',
            name='caixa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='produtos', to='movimentacao.caixa'),
        ),
        migrations.AlterField(
            model_name='produto',
            name='unidade',
            field=models.CharField(choices=[('UN', 'Unidade'), ('PCT', 'Pacote'), ('L', 'Litro'), ('KG', 'Quilograma')], max_length=3),
        ),
        migrations.CreateModel(
            name='Venda',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ficha', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='compras', to='movimentacao.ficha')),
                ('movimentacao', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='movimentacao.movimentacaoestoque')),
            ],
        ),
    ]