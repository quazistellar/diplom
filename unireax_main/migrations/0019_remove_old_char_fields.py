import django.db.models.deletion
from django.db import migrations, models


def set_default_post_type(apps, schema_editor):
    """Устанавливает тип поста по умолчанию для существующих записей"""
    CoursePost = apps.get_model('unireax_main', 'CoursePost')
    PostType = apps.get_model('unireax_main', 'PostType')
    
    try:
        default_type = PostType.objects.get(code='announcement')
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE course_post SET post_type_id = %s WHERE post_type_id IS NULL",
                [default_type.id]
            )
    except PostType.DoesNotExist:
        pass


def set_default_status(apps, schema_editor):
    """Устанавливает статус по умолчанию для существующих заявок"""
    TeacherApplication = apps.get_model('unireax_main', 'TeacherApplication')
    ApplicationStatus = apps.get_model('unireax_main', 'ApplicationStatus')
    
    try:
        default_status = ApplicationStatus.objects.get(code='pending')
        TeacherApplication.objects.filter(status_id__isnull=True).update(status_id=default_status.id)
    except ApplicationStatus.DoesNotExist:
        pass


def drop_old_columns(apps, schema_editor):
    """Удаляет старые varchar колонки"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'course_post' AND column_name = 'post_type' AND data_type = 'character varying'
                ) THEN
                    ALTER TABLE course_post DROP COLUMN post_type;
                END IF;
            END $$;
        """)
        
        cursor.execute("""
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'teacher_application' AND column_name = 'status' AND data_type = 'character varying'
                ) THEN
                    ALTER TABLE teacher_application DROP COLUMN status;
                END IF;
            END $$;
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('unireax_main', '0018_applicationstatus_posttype_and_more'),
    ]

    operations = [
        migrations.RunPython(set_default_post_type),
        migrations.RunPython(set_default_status),
        
        migrations.RunPython(drop_old_columns),
        
        migrations.AlterField(
            model_name='teacherapplication',
            name='status',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='applications',
                to='unireax_main.applicationstatus',
                verbose_name='Статус'
            ),
        ),
        migrations.AlterField(
            model_name='coursepost',
            name='post_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='posts',
                to='unireax_main.posttype',
                verbose_name='Тип поста',
                db_column='post_type_id' 
            ),
        ),
    ]