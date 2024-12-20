# Generated by Django 5.1.3 on 2024-12-10 04:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0003_preplotshotpoints_source_number'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='preplotline',
            options={'ordering': ['preplot']},
        ),
        migrations.AddField(
            model_name='preplotline',
            name='completed',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='preplotline',
            name='force_completed',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='preplotline',
            name='loaded',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='preplotline',
            name='preplot',
            field=models.IntegerField(db_index=True),
        ),
        migrations.AddIndex(
            model_name='preplotline',
            index=models.Index(fields=['preplot', 'loaded'], name='planner_pre_preplot_f3a69f_idx'),
        ),
        migrations.AddIndex(
            model_name='preplotline',
            index=models.Index(fields=['preplot', 'completed'], name='planner_pre_preplot_90c372_idx'),
        ),
    ]
