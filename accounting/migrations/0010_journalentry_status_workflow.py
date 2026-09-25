from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def mark_existing_entries_posted(apps, schema_editor):
    JournalEntry = apps.get_model('accounting', 'JournalEntry')
    JournalEntry.objects.all().update(status='POSTED')


class Migration(migrations.Migration):
    dependencies = [
        ('accounting', '0009_rebuild_chart_of_accounts'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='journalentry', name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('POSTED', 'Posted'), ('REVERSED', 'Reversed')], default='DRAFT', max_length=10),
        ),
        migrations.AddField(
            model_name='journalentry', name='posted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='journalentry', name='reversed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='journalentry', name='posted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='posted_journal_entries', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='journalentry', name='reversed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reversed_journal_entries', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(mark_existing_entries_posted, migrations.RunPython.noop),
    ]
