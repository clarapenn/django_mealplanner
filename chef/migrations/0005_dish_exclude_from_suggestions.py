# Generated by Django 4.2.6 on 2023-12-12 13:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chef", "0004_alter_dish_options_dish_unique_dish_title_per_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="dish",
            name="exclude_from_suggestions",
            field=models.BooleanField(default=False),
        ),
    ]
