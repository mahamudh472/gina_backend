from django.db import migrations

MAPPING = {
    'self_discovery': 'identity',
    'relaxation': 'identity',
    'emotional_healing': 'healing',
    'inner_peace': 'healing',
    'self_love': 'emotions',
    'transformation': 'future',
    'grounding': 'everyday_life',
    'focus_clarity': 'everyday_life',
    'energy': 'energy',
    'alltag': 'everyday_life',
    'identitaet': 'identity',
    'emotionen': 'emotions',
    'heilung': 'healing',
    'zukunft': 'future',
    'energie': 'energy',
}

def migrate_categories_forward(apps, schema_editor):
    Meditation = apps.get_model('main', 'Meditation')
    MeditationTemplate = apps.get_model('main', 'MeditationTemplate')
    Music = apps.get_model('main', 'Music')
    MeditationPrompt = apps.get_model('ai_service', 'MeditationPrompt')

    for old_cat, new_cat in MAPPING.items():
        if old_cat != new_cat:
            Meditation.objects.filter(category=old_cat).update(category=new_cat)
            MeditationTemplate.objects.filter(category=old_cat).update(category=new_cat)
            Music.objects.filter(category=old_cat).update(category=new_cat)
            MeditationPrompt.objects.filter(category=old_cat).update(category=new_cat)

def migrate_categories_backward(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0015_alter_meditation_category_and_more'),
        ('ai_service', '0008_alter_meditationprompt_category'),
    ]

    operations = [
        migrations.RunPython(migrate_categories_forward, migrate_categories_backward),
    ]
