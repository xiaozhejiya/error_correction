from db.crud.questions import delete_question
from db.migrate import _ensure_default_question_project
from db.models import Project, Question, RagDocumentChunk, UploadBatch, User


def test_ensure_default_question_project_creates_immutable_default_project(db):
    user = User(email="u@example.com", username="u", password_hash="x")
    db.add(user)
    db.commit()

    project, changed = _ensure_default_question_project(db, user.id, "默认错题库")
    db.commit()

    saved = db.query(Project).filter(Project.id == project.id).one()
    assert changed is True
    assert saved.is_default is True
    assert saved.project_type == "question"


def test_ensure_default_question_project_upgrades_existing_project_to_default(db):
    user = User(email="u2@example.com", username="u2", password_hash="x")
    db.add(user)
    db.commit()

    project = Project(
        user_id=user.id,
        name="默认错题库",
        project_type="question",
        is_default=False,
    )
    db.add(project)
    db.commit()

    same_project, changed = _ensure_default_question_project(db, user.id, "默认错题库")
    db.commit()

    saved = db.query(Project).filter(Project.id == project.id).one()
    assert same_project.id == project.id
    assert changed is True
    assert saved.is_default is True


def test_delete_question_removes_empty_batch_in_same_operation(db):
    user = User(email="u3@example.com", username="u3", password_hash="x")
    db.add(user)
    db.commit()

    batch = UploadBatch(
        user_id=user.id,
        project_id=None,
        original_filename="a.pdf",
        subject="数学",
        file_path="/tmp/a.pdf",
    )
    db.add(batch)
    db.flush()

    batch_id = batch.id

    question = Question(
        user_id=user.id,
        project_id=None,
        batch_id=batch_id,
        content_hash="hash-1",
        question_type="选择题",
        content_json='[{"block_type":"text","content":"题目"}]',
    )
    db.add(question)
    db.commit()

    chunk = RagDocumentChunk(
        user_id=user.id,
        project_id=None,
        source_type="question",
        source_id=question.id,
        chunk_index=0,
        content="题目",
        vector_json="[0.1,0.2]",
    )
    db.add(chunk)
    db.commit()

    assert delete_question(db, question.id, user_id=user.id) is True
    assert db.query(Question).filter(Question.id == question.id).first() is None
    assert db.query(RagDocumentChunk).filter(RagDocumentChunk.source_id == question.id).first() is None
    assert db.query(UploadBatch).filter(UploadBatch.id == batch_id).first() is None
