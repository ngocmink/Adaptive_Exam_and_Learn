# Lessons directly under subjects

The content hierarchy is Subject → Lesson → Materials and Questions.
Each lesson represents the chapter-sized teaching unit chosen by the team.
There is no separate Chapter model. Materials have no uploader/author account
relationship. Assessment.created_by is unchanged. Source authorship and permission
information should still be collected separately; uploader identity is not the
original PDF author's identity.

## Relationships

- Lesson.subject_id references subjects.id.
- Lesson codes are unique within a subject.
- Lessons are ordered by order_num, then id; duplicate order values are allowed.
- Materials and questions can support multiple lessons in the same subject.
- Composite foreign keys prevent cross-subject content links.
- Material responses no longer contain author_id or author_name. Shared staff
  management permissions remain unchanged.

```python
from app.extensions import db
from app.models import Lesson, LessonMaterial, QuestionLesson

lesson = Lesson(subject_id=subject.id, code='LIMITS',
                title='Giới hạn', order_num=1)
db.session.add(lesson)
db.session.flush()
db.session.add(LessonMaterial.link(lesson, material))
db.session.add(QuestionLesson.link(question, lesson))
db.session.commit()
```

## Upgrade to 20261115_01

Back up the target database before running `flask db upgrade`.
Deploy the matching code together with the migration; the old code expects
chapters and material author columns and is incompatible with the new schema.
Do not run the migration against a database still serving requests from old code.

The migration preserves lesson IDs, material IDs and all content links. Lesson
order is flattened by old chapter order/id, then old lesson order/id. If lesson
codes collide within a subject, the lowest lesson ID keeps its code; subsequent
duplicates receive a deterministic ~ID suffix (with a counter if necessary),
within the 100-character limit. Compare lesson codes before/after and update
external collection workbooks accordingly.

The migration removes chapter rows, chapter metadata and material author IDs.
These removed attributes are recoverable only from the backup. Automatic
downgrade intentionally refuses to invent the deleted information.

This change does not implement the separate grading, timing, snapshot, account
deactivation or adaptive-learning proposals. It adds no lesson UI or endpoints.
