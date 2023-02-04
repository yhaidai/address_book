# Generated by Django 4.0.8 on 2023-02-04 02:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0002_contactgroup_contact_user_alter_contact_uuid_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactgroup',
            name='contacts',
            field=models.ManyToManyField(related_name='contact_groups', related_query_name='contact_group', to='contacts.contact'),
        ),
    ]
