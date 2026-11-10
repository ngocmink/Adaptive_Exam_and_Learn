"""Explicit, transactional import; legacy spreadsheets are never read by API requests."""
import json
import os
import re
from pathlib import Path
import click
from flask.cli import with_appcontext
from openpyxl import load_workbook
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.common.difficulty import parse_difficulty
from app.models import User, Subject, Material, Question, QuestionOption, Assessment, AssessmentQuestion

def rows(path, required):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        iterator = iter(workbook.active.values)
        header = next(iterator, ())
        if not set(required).issubset(header):
            raise ValueError(f'{path.name}: missing required columns: {sorted(set(required) - set(header))}')
        return [(number, dict(zip(header, row))) for number, row in enumerate(iterator, 2) if any(value is not None for value in row)]
    finally:
        workbook.close()

def normalized(value):
    return str(value).strip() if value is not None else ''

def numeric_key(value):
    if isinstance(value, (int, float)):
        return format(value, 'g')
    return normalized(value)

def get_or_create(model, match, defaults=None):
    found = db.session.scalar(select(model).filter_by(**match))
    if found is None:
        found = model(**match, **(defaults or {}))
        db.session.add(found)
        db.session.flush()
    return found

def seed_demo(passwords):
    if any(not passwords.get(role) or len(passwords[role]) < 12 for role in ('admin','teacher','student')):
        raise ValueError('Provide all three DEMO_*_PASSWORD values (at least 12 characters each).')
    users = {}
    for role in ('admin','teacher','student'):
        email = f'{role}@example.test'
        user = db.session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=f'Demo {role}', role=role)
            user.set_password(passwords[role])
            db.session.add(user)
            db.session.flush()
        elif user.role != role:
            raise ValueError('Demo email already belongs to a different role; refusing to change it.')
        users[role] = user
    subject = get_or_create(Subject, {'code': 'DEMO-MATH'}, {'name': 'Demo Mathematics'})
    material = get_or_create(Material, {'subject_id': subject.id, 'title': 'Demo revision notes'},
        {'file_url': 'pdf/GTC1.pdf', 'difficulty': 2, 'author_id': users['teacher'].id})
    questions = []
    for index, (a, b, difficulty) in enumerate(((1, 1, 2), (12, 8, 5.5), (25, 17, 9)), 1):
        content = f'Demo: What is {a} + {b}?'
        q = db.session.scalar(select(Question).filter_by(subject_id=subject.id, content=content))
        if q is None:
            q = Question(subject_id=subject.id, topic='Addition', content=content,
                difficulty=difficulty, explanation=f'{a} + {b} = {a+b}.')
            q.options = [QuestionOption(content=str(value), is_correct=(pos == 0))
                for pos, value in enumerate((a+b, a+b+1, a+b-1, a+b+2))]
            db.session.add(q)
            db.session.flush()
        q.validate_for_use()
        questions.append(q)
    for title, kind in (('Demo fixed quiz', 'quiz'), ('Demo practice', 'practice')):
        assessment = get_or_create(Assessment, {'subject_id': subject.id, 'title': title},
            {'type': kind, 'duration_minutes': 20, 'pass_score': 50, 'created_by': users['teacher'].id})
        for order, q in enumerate(questions, 1):
            get_or_create(AssessmentQuestion, {'assessment_id': assessment.id, 'question_id': q.id}, {'order_num': order, 'points': 1})
    db.session.flush()
    return {'demo_users': 3, 'demo_questions': len(questions), 'demo_assessments': 2}

def import_legacy(directory, include_users=False):
    directory = Path(directory)
    subjects = {}
    imported_questions = {}
    counts = {'subjects': 0, 'materials': 0, 'questions': 0, 'users': 0}
    for rownum, row in rows(directory / 'tailieu.xlsx', ('Type','Subject','Doc')):
        key = numeric_key(row['Type'])
        name = normalized(row['Subject'])
        # Remove only known legacy LaTeX wrappers; preserve the actual subject text.
        name = name.replace('\\(', '').replace('\\)', '').replace('\\textbf{', '').rstrip('}')
        file_url = normalized(row['Doc']).replace('\\', '/')
        if not key or not name or not file_url or '..' in Path(file_url).parts or not file_url.startswith(('pdf/', 'uploads/materials/')):
            raise ValueError(f'tailieu.xlsx row {rownum}: invalid subject or local document path.')
        if key in subjects:
            raise ValueError(f'tailieu.xlsx row {rownum}: duplicate Type mapping.')
        subject = get_or_create(Subject, {'code': f'LEGACY-{key}'}, {'name': name})
        subjects[key] = subject
        get_or_create(Material, {'subject_id': subject.id, 'title': name, 'file_url': file_url}, {'difficulty': 5.5})
        counts['subjects'] += 1
        counts['materials'] += 1
    required = ('Type','Question','Option 1','Option 2','Option 3','Option 4','Correct Answer','Difficulty')
    for rownum, row in rows(directory / 'quiz.xlsx', required):
        key = numeric_key(row['Type'])
        level = parse_difficulty(row['Difficulty'])
        if key not in subjects:
            raise ValueError(f'quiz.xlsx row {rownum}: unmapped subject.')
        options = [normalized(row[f'Option {i}']) for i in range(1, 5)]
        correct = normalized(row['Correct Answer'])
        content = normalized(row['Question'])
        if not content or not all(options) or len(set(options)) != 4 or options.count(correct) != 1:
            raise ValueError(f'quiz.xlsx row {rownum}: require content, four distinct options and one matching answer.')
        subject = subjects[key]
        q = db.session.scalar(select(Question).filter_by(subject_id=subject.id, content=content))
        if q is None:
            q = Question(subject_id=subject.id, topic=normalized(row.get('Topic')) or None,
                content=content, difficulty=level, explanation=normalized(row.get('Explanation')) or None)
            q.options = [QuestionOption(content=value, is_correct=(value == correct)) for value in options]
            db.session.add(q)
            db.session.flush()
        elif q.difficulty != level or [(o.content, o.is_correct) for o in q.options] != [(value, value == correct) for value in options]:
            raise ValueError(f'quiz.xlsx row {rownum}: conflicts with existing question; no overwrite performed.')
        q.validate_for_use()
        imported_questions.setdefault(key, []).append(q)
        counts['questions'] += 1
    for key, questions in imported_questions.items():
        subject = subjects[key]
        assessment = get_or_create(Assessment, {'subject_id': subject.id, 'title': f'Legacy sample: {subject.name}'},
            {'type': 'quiz', 'duration_minutes': 30, 'pass_score': 50})
        for order, q in enumerate(dict.fromkeys(questions), 1):
            get_or_create(AssessmentQuestion, {'assessment_id': assessment.id, 'question_id': q.id}, {'order_num': order, 'points': 1})
    if include_users:
        for rownum, row in rows(directory / 'users.xlsx', ('email','name','password')):
            email = normalized(row['email']).lower()
            stored = normalized(row['password'])
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                raise ValueError(f'users.xlsx row {rownum}: invalid email.')
            if not re.fullmatch(r'(?:scrypt:[0-9]+:[0-9]+:[0-9]+|pbkdf2:sha256:[0-9]+)\$[^$]+\$[0-9a-f]+', stored):
                raise ValueError(f'users.xlsx row {rownum}: unsupported hash or plaintext password; import rejected.')
            # Legacy IDs and roles are deliberately not trusted. IDs are allocated by PostgreSQL.
            study = normalized(row.get('studytype')).lower()
            if study not in ('visual','auditory','reading','kinesthetic'):
                study = None
            get_or_create(User, {'email': email}, {'full_name': normalized(row['name']) or 'Imported student',
                'password_hash': stored, 'phone': normalized(row.get('phone')) or None, 'study_type': study, 'role': 'student'})
            counts['users'] += 1
    db.session.flush()
    return counts

def reset_sequences():
    # Imports use generated IDs, so no reset is normally needed. This supports a
    # one-off maintenance command after an explicit-ID migration, with table locks.
    for table in sorted(db.metadata.tables.values(), key=lambda item: item.name):
        db.session.execute(text(f'LOCK TABLE "{table.name}" IN ACCESS EXCLUSIVE MODE'))
        db.session.execute(text(f"SELECT setval(pg_get_serial_sequence(:table_name, 'id'), COALESCE(MAX(id), 0) + 1, false) FROM \"{table.name}\""), {'table_name': table.name})

@click.command('seed')
@with_appcontext
def seed_command():
    """Create repeatable synthetic demo content; passwords come from environment."""
    try:
        summary = seed_demo({role: os.getenv(f'DEMO_{role.upper()}_PASSWORD') for role in ('admin','teacher','student')})
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise click.ClickException('Database rejected the operation; no import changes were committed. Check schema and input constraints.') from None
    except Exception as error:
        db.session.rollback()
        raise click.ClickException(str(error)) from error
    click.echo(json.dumps(summary))

@click.command('import-excel')
@click.option('--directory', type=click.Path(exists=True, file_okay=False), default='seed_data', show_default=True)
@click.option('--include-users', is_flag=True, help='Explicitly opt in to importing private legacy users (students only).')
@click.option('--reset-sequences', is_flag=True, help='Maintenance mode: briefly locks all model tables. Stop writers first.')
@with_appcontext
def import_command(directory, include_users, reset_sequences):
    """Import known Excel layouts atomically. Errors roll back the entire import."""
    try:
        result = import_legacy(directory, include_users)
        if reset_sequences:
            globals()['reset_sequences']()
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise click.ClickException('Database rejected the operation; no import changes were committed. Check schema and input constraints.') from None
    except Exception as error:
        db.session.rollback()
        raise click.ClickException(str(error)) from error
    click.echo(json.dumps(result))
