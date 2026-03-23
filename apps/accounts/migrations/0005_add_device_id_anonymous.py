# Generated migration for device_id and anonymous user support

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_user_options'),
    ]

    operations = [
        # Add device_id field
        migrations.AddField(
            model_name='user',
            name='device_id',
            field=models.CharField(
                default=uuid.uuid4,
                max_length=36,
                unique=True,
                db_index=True,
                help_text='Unique device identifier for anonymous users'
            ),
        ),
        # Add is_anonymous field
        migrations.AddField(
            model_name='user',
            name='is_anonymous',
            field=models.BooleanField(
                default=True,
                help_text='True for device-based anonymous users, False for authenticated users'
            ),
        ),
        # Make email nullable and non-unique for anonymous users
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        # Make username nullable and non-unique for anonymous users
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(
                blank=True,
                max_length=30,
                null=True,
                unique=True,
                validators=['apps.core.validators.validate_username_format']
            ),
        ),
        # Make name optional
        migrations.AlterField(
            model_name='user',
            name='name',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        # Change USERNAME_FIELD to device_id (requires custom command)
        # This is handled by the model definition
        # Add indexes
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['device_id'], name='accounts_use_device__db5e3f_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['is_anonymous'], name='accounts_use_is_ano_a1b2c3_idx'),
        ),
    ]
