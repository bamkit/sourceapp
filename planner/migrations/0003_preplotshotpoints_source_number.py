# Generated by Django 5.1.3 on 2024-12-08 03:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0002_sequence_filename'),
    ]

    operations = [
        migrations.AddField(
            model_name='preplotshotpoints',
            name='source_number',
            field=models.CharField(blank=True, max_length=1, null=True),
        ),
    ]
