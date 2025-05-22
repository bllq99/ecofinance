from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('finanzas', '0001_initial'),
    ]

    operations = [
        # Crear modelo SerieRecurrente
        migrations.CreateModel(
            name='SerieRecurrente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('activa', models.BooleanField(default=True)),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
        ),
        
        # Agregar campos a Transaccion
        migrations.AddField(
            model_name='transaccion',
            name='es_recurrente',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='transaccion',
            name='fecha_fin',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transaccion',
            name='fecha_inicio',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transaccion',
            name='periodicidad',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='transaccion',
            name='serie_recurrente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='finanzas.serierecurrente'),
        ),
        migrations.AddField(
            model_name='transaccion',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='auth.user'),
        ),
        
        # Añadir solo campo usuario a ObjetivoAhorro y Presupuesto (no crear los modelos)
        migrations.AddField(
            model_name='objetivoahorro',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='auth.user'),
        ),
        migrations.AddField(
            model_name='presupuesto',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='auth.user'),
        ),
    ]