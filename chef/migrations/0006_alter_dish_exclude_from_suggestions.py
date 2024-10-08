# Generated by Django 4.2.6 on 2023-12-12 13:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chef", "0005_dish_exclude_from_suggestions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dish",
            name="exclude_from_suggestions",
            field=models.BooleanField(
                default=False,
                help_text="Meals marked with this, such as away days or dinner out will not be automatically suggested.",
            ),
        ),
    ]
