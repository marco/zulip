# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0236_remove_illegal_characters_email_full'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='realm',
            name='zoom_api_key',
        ),
        migrations.RemoveField(
            model_name='realm',
            name='zoom_api_secret',
        ),
        migrations.RemoveField(
            model_name='realm',
            name='zoom_user_id',
        ),
    ]
