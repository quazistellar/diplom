from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('unireax_main', '0019_remove_old_char_fields'),  
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE practical_assignment
                ADD CONSTRAINT practical_assignment_grading_check
                CHECK (
                    (grading_type = 'points' AND max_score > 0 AND (passing_score IS NULL OR passing_score <= max_score)) OR
                    (grading_type = 'pass_fail' AND max_score IS NULL AND passing_score IS NULL)
                );
            """,
            reverse_sql="""
                ALTER TABLE practical_assignment
                DROP CONSTRAINT IF EXISTS practical_assignment_grading_check;
            """
        ),
        
        migrations.RunSQL(
            sql="""
                ALTER TABLE test
                ADD CONSTRAINT test_grading_check
                CHECK (
                    (grading_form = 'points' AND passing_score >= 0) OR
                    (grading_form = 'pass_fail' AND passing_score IS NULL)
                );
            """,
            reverse_sql="""
                ALTER TABLE test
                DROP CONSTRAINT IF EXISTS test_grading_check;
            """
        ),
    ]