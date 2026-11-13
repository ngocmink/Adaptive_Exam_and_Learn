# Subject / chapter / lesson database hierarchy

Migration 20261114_01 adds four tables without assigning or deleting existing
content: chapters, lessons, lesson_materials and question_lessons.

- Subject -> ordered chapters -> ordered lessons.
- Chapter codes are unique within a subject; lesson codes within a chapter.
- Status is draft/published/archived. Rows start as draft.
- One material or question can support multiple lessons in the SAME subject.
- Composite foreign keys enforce subject consistency, including subsequent
  changes to a parent subject. Existing materials/questions receive additional
  (id, subject_id) unique keys; their original IDs and API fields are unchanged.
- Material/question link pairs cannot repeat. Display order must be positive;
  equal order values are allowed during reordering; sort by order_num then id.
- Deletion is restricted while content is referenced. Archive content instead.

Example after flushing the subject/material/question rows:

```python
chapter = Chapter(subject_id=subject.id, code='CALC', title='Calculus')
db.session.add(chapter)
db.session.flush()
lesson = Lesson(chapter_id=chapter.id, subject_id=subject.id,
                code='DERIVATIVES', title='Derivatives', order_num=1)
db.session.add(lesson)
db.session.flush()
db.session.add(LessonMaterial.link(lesson, material))
db.session.add(QuestionLesson.link(question, lesson))
db.session.commit()
```

Use reviewed subject/chapter/lesson codes to organize actual content. The old
free-text Question.topic remains for compatibility; no automatic mapping is
attempted. Do not create invented chapters/lessons in the shared database.
Updating content imports to accept these codes and implementing hierarchy
management/list screens are subsequent work, not supplied by schema migration.
Existing tests/assessments remain subject-level; no lesson-test linkage is
assumed. Published question versioning and attempt deadlines remain separate
future migrations.

Apply with `flask --app app:create_app db upgrade` only after verifying the
destination. Back up shared data first. The downgrade deletes NEW hierarchy
content, so it is only suitable for disposable test DBs or planned restores.
