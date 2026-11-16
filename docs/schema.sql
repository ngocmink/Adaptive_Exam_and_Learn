-- Adaptive Exam and Learn current application schema
-- Generated from SQLAlchemy models; target revision 20261115_01.
-- For review or a new EMPTY database only. Not a live database dump.
-- Existing installations must use Flask-Migrate, not run this file.
-- No credentials, user data or proposed future integrity changes included.
BEGIN;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE users (
	id SERIAL NOT NULL,
	email VARCHAR(254) NOT NULL,
	password_hash TEXT NOT NULL,
	full_name VARCHAR(200) NOT NULL,
	phone VARCHAR(40),
	role VARCHAR(20) DEFAULT 'student' NOT NULL,
	study_type VARCHAR(30),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_users PRIMARY KEY (id),
	CONSTRAINT ck_users_role CHECK (role IN ('student','teacher','admin')),
	CONSTRAINT ck_users_normalized_email CHECK (email = lower(trim(email)) AND length(email) > 0),
	CONSTRAINT ck_users_study_type CHECK (study_type IS NULL OR study_type IN ('visual','auditory','reading','kinesthetic')),
	CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE subjects (
	id SERIAL NOT NULL,
	code VARCHAR(100) NOT NULL,
	name VARCHAR(200) NOT NULL,
	description TEXT,
	is_active BOOLEAN DEFAULT true NOT NULL,
	CONSTRAINT pk_subjects PRIMARY KEY (id),
	CONSTRAINT uq_subjects_code UNIQUE (code)
);

CREATE TABLE materials (
	id SERIAL NOT NULL,
	subject_id INTEGER NOT NULL,
	title VARCHAR(300) NOT NULL,
	description TEXT,
	file_url TEXT NOT NULL,
	difficulty NUMERIC DEFAULT '5.5' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_materials PRIMARY KEY (id),
	CONSTRAINT ck_materials_difficulty CHECK (difficulty BETWEEN 1 AND 10),
	CONSTRAINT uq_materials_id_subject UNIQUE (id, subject_id),
	CONSTRAINT fk_materials_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT
);

CREATE INDEX ix_materials_subject_id ON materials (subject_id);

CREATE TABLE questions (
	id SERIAL NOT NULL,
	subject_id INTEGER NOT NULL,
	topic VARCHAR(200),
	content TEXT NOT NULL,
	difficulty NUMERIC DEFAULT '5.5' NOT NULL,
	explanation TEXT,
	is_active BOOLEAN DEFAULT true NOT NULL,
	CONSTRAINT pk_questions PRIMARY KEY (id),
	CONSTRAINT ck_questions_difficulty CHECK (difficulty BETWEEN 1 AND 10),
	CONSTRAINT uq_questions_id_subject UNIQUE (id, subject_id),
	CONSTRAINT fk_questions_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT
);

CREATE INDEX ix_questions_subject_difficulty_topic ON questions (subject_id, difficulty, topic);

CREATE INDEX ix_questions_subject_id ON questions (subject_id);

CREATE TABLE assessments (
	id SERIAL NOT NULL,
	subject_id INTEGER NOT NULL,
	title VARCHAR(300) NOT NULL,
	description TEXT,
	type VARCHAR(20) DEFAULT 'quiz' NOT NULL,
	duration_minutes INTEGER NOT NULL,
	pass_score INTEGER DEFAULT '50' NOT NULL,
	created_by INTEGER,
	is_active BOOLEAN DEFAULT true NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_assessments PRIMARY KEY (id),
	CONSTRAINT ck_assessments_type CHECK (type IN ('quiz','exam','practice')),
	CONSTRAINT ck_assessments_duration CHECK (duration_minutes > 0),
	CONSTRAINT ck_assessments_pass_score CHECK (pass_score BETWEEN 0 AND 100),
	CONSTRAINT fk_assessments_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT,
	CONSTRAINT fk_assessments_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_assessments_created_by ON assessments (created_by);

CREATE INDEX ix_assessments_subject_id ON assessments (subject_id);

CREATE TABLE lessons (
	id SERIAL NOT NULL,
	subject_id INTEGER NOT NULL,
	code VARCHAR(100) NOT NULL,
	title VARCHAR(300) NOT NULL,
	objectives TEXT,
	content TEXT,
	order_num INTEGER DEFAULT '1' NOT NULL,
	status VARCHAR(20) DEFAULT 'draft' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_lessons PRIMARY KEY (id),
	CONSTRAINT uq_lessons_subject_code UNIQUE (subject_id, code),
	CONSTRAINT uq_lessons_id_subject UNIQUE (id, subject_id),
	CONSTRAINT ck_lessons_order CHECK (order_num > 0),
	CONSTRAINT ck_lessons_nonempty CHECK (length(trim(code)) > 0 AND length(trim(title)) > 0),
	CONSTRAINT ck_lessons_status CHECK (status IN ('draft','published','archived')),
	CONSTRAINT fk_lessons_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT
);

CREATE INDEX ix_lessons_subject_id ON lessons (subject_id);

CREATE TABLE question_options (
	id SERIAL NOT NULL,
	question_id INTEGER NOT NULL,
	content TEXT NOT NULL,
	is_correct BOOLEAN DEFAULT false NOT NULL,
	CONSTRAINT pk_question_options PRIMARY KEY (id),
	CONSTRAINT uq_question_options_id_question UNIQUE (id, question_id),
	CONSTRAINT fk_question_options_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
);

CREATE INDEX ix_question_options_question_id ON question_options (question_id);

CREATE UNIQUE INDEX uq_question_options_one_correct ON question_options (question_id) WHERE is_correct;

CREATE TABLE assessment_questions (
	id SERIAL NOT NULL,
	assessment_id INTEGER NOT NULL,
	question_id INTEGER NOT NULL,
	order_num INTEGER NOT NULL,
	points FLOAT DEFAULT '1' NOT NULL,
	CONSTRAINT pk_assessment_questions PRIMARY KEY (id),
	CONSTRAINT uq_assessment_questions_question UNIQUE (assessment_id, question_id),
	CONSTRAINT uq_assessment_questions_order UNIQUE (assessment_id, order_num),
	CONSTRAINT ck_assessment_questions_order CHECK (order_num > 0),
	CONSTRAINT ck_assessment_questions_points CHECK (points > 0 AND points < 'Infinity'::float8),
	CONSTRAINT fk_assessment_questions_assessment_id_assessments FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE CASCADE,
	CONSTRAINT fk_assessment_questions_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE RESTRICT
);

CREATE INDEX ix_assessment_questions_assessment_id ON assessment_questions (assessment_id);

CREATE INDEX ix_assessment_questions_question_id ON assessment_questions (question_id);

CREATE TABLE attempts (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	assessment_id INTEGER NOT NULL,
	score FLOAT,
	total_questions INTEGER DEFAULT '0' NOT NULL,
	correct_answers INTEGER DEFAULT '0' NOT NULL,
	start_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	submit_time TIMESTAMP WITH TIME ZONE,
	status VARCHAR(20) DEFAULT 'in_progress' NOT NULL,
	CONSTRAINT pk_attempts PRIMARY KEY (id),
	CONSTRAINT ck_attempts_status CHECK (status IN ('in_progress','completed','abandoned')),
	CONSTRAINT ck_attempts_counts CHECK (total_questions >= 0 AND correct_answers >= 0 AND correct_answers <= total_questions),
	CONSTRAINT ck_attempts_score CHECK (score IS NULL OR (score >= 0 AND score < 'Infinity'::float8)),
	CONSTRAINT ck_attempts_times CHECK (submit_time IS NULL OR submit_time >= start_time),
	CONSTRAINT fk_attempts_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_attempts_assessment_id_assessments FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT
);

CREATE INDEX ix_attempts_assessment_id ON attempts (assessment_id);

CREATE INDEX ix_attempts_user_id ON attempts (user_id);

CREATE TABLE learning_rules (
	id SERIAL NOT NULL,
	subject_id INTEGER NOT NULL,
	trigger_condition VARCHAR(300) NOT NULL,
	recommended_action TEXT NOT NULL,
	target_material_id INTEGER,
	CONSTRAINT pk_learning_rules PRIMARY KEY (id),
	CONSTRAINT fk_learning_rules_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT,
	CONSTRAINT fk_learning_rules_target_material_id_materials FOREIGN KEY(target_material_id) REFERENCES materials (id) ON DELETE RESTRICT
);

CREATE INDEX ix_learning_rules_subject_id ON learning_rules (subject_id);

CREATE INDEX ix_learning_rules_target_material_id ON learning_rules (target_material_id);

CREATE TABLE lesson_materials (
	id SERIAL NOT NULL,
	lesson_id INTEGER NOT NULL,
	material_id INTEGER NOT NULL,
	subject_id INTEGER NOT NULL,
	order_num INTEGER DEFAULT '1' NOT NULL,
	CONSTRAINT pk_lesson_materials PRIMARY KEY (id),
	CONSTRAINT fk_lesson_materials_lesson_id_lessons FOREIGN KEY(lesson_id, subject_id) REFERENCES lessons (id, subject_id) ON DELETE RESTRICT,
	CONSTRAINT fk_lesson_materials_material_id_materials FOREIGN KEY(material_id, subject_id) REFERENCES materials (id, subject_id) ON DELETE RESTRICT,
	CONSTRAINT uq_lesson_materials_pair UNIQUE (lesson_id, material_id),
	CONSTRAINT ck_lesson_materials_order CHECK (order_num > 0)
);

CREATE INDEX ix_lesson_materials_lesson_id ON lesson_materials (lesson_id);

CREATE INDEX ix_lesson_materials_material_id ON lesson_materials (material_id);

CREATE TABLE question_lessons (
	id SERIAL NOT NULL,
	question_id INTEGER NOT NULL,
	lesson_id INTEGER NOT NULL,
	subject_id INTEGER NOT NULL,
	CONSTRAINT pk_question_lessons PRIMARY KEY (id),
	CONSTRAINT fk_question_lessons_question_id_questions FOREIGN KEY(question_id, subject_id) REFERENCES questions (id, subject_id) ON DELETE RESTRICT,
	CONSTRAINT fk_question_lessons_lesson_id_lessons FOREIGN KEY(lesson_id, subject_id) REFERENCES lessons (id, subject_id) ON DELETE RESTRICT,
	CONSTRAINT uq_question_lessons_pair UNIQUE (question_id, lesson_id)
);

CREATE INDEX ix_question_lessons_lesson_id ON question_lessons (lesson_id);

CREATE INDEX ix_question_lessons_question_id ON question_lessons (question_id);

CREATE TABLE attempt_answers (
	id SERIAL NOT NULL,
	attempt_id INTEGER NOT NULL,
	question_id INTEGER NOT NULL,
	selected_option_id INTEGER,
	is_correct BOOLEAN,
	CONSTRAINT pk_attempt_answers PRIMARY KEY (id),
	CONSTRAINT uq_attempt_answers_attempt_id UNIQUE (attempt_id, question_id),
	CONSTRAINT fk_attempt_answers_selected_option_id_question_options FOREIGN KEY(selected_option_id, question_id) REFERENCES question_options (id, question_id) ON DELETE RESTRICT,
	CONSTRAINT fk_attempt_answers_attempt_id_attempts FOREIGN KEY(attempt_id) REFERENCES attempts (id) ON DELETE CASCADE,
	CONSTRAINT fk_attempt_answers_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE RESTRICT
);

CREATE INDEX ix_attempt_answers_question_id ON attempt_answers (question_id);

CREATE INDEX ix_attempt_answers_selected_option_id ON attempt_answers (selected_option_id);

CREATE INDEX ix_attempt_answers_attempt_id ON attempt_answers (attempt_id);

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version (version_num) VALUES ('20261115_01');
COMMIT;
