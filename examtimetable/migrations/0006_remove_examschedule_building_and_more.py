from django.db import migrations, models
from datetime import datetime

def migrate_times(apps, schema_editor):
    ExamSchedule = apps.get_model('examtimetable', 'ExamSchedule')
    for exam in ExamSchedule.objects.all():
        save_needed = False
        if exam.exam_date:
            if exam.start_time:
                exam.start_time_tmp = datetime.combine(exam.exam_date, exam.start_time)
                save_needed = True
            if exam.end_time:
                exam.end_time_tmp = datetime.combine(exam.exam_date, exam.end_time)
                save_needed = True
        if save_needed:
            exam.save()

class Migration(migrations.Migration):

    dependencies = [
        ('examtimetable', '0005_examschedule_examtimetab_institu_6cadef_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='examschedule',
            name='start_time_tmp',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='examschedule',
            name='end_time_tmp',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(migrate_times, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='examschedule',
            name='start_time',
        ),
        migrations.RemoveField(
            model_name='examschedule',
            name='end_time',
        ),
        migrations.RenameField(
            model_name='examschedule',
            old_name='start_time_tmp',
            new_name='start_time',
        ),
        migrations.RenameField(
            model_name='examschedule',
            old_name='end_time_tmp',
            new_name='end_time',
        ),
        migrations.RemoveField(model_name='examschedule', name='building'),
        migrations.RemoveField(model_name='examschedule', name='campus'),
        migrations.RemoveField(model_name='examschedule', name='course_name'),
        migrations.RemoveField(model_name='examschedule', name='datetime_str'),
        migrations.RemoveField(model_name='examschedule', name='day'),
        migrations.RemoveField(model_name='examschedule', name='exam_date'),
        migrations.RemoveField(model_name='examschedule', name='exam_type'),
        migrations.RemoveField(model_name='examschedule', name='instructions'),
        migrations.RemoveField(model_name='examschedule', name='invigilator'),
        migrations.RemoveField(model_name='examschedule', name='location'),
        migrations.RemoveField(model_name='examschedule', name='room'),
    ]
