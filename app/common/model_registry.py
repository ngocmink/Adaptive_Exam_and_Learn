from importlib import import_module


MODEL_MODULES = {
    "User": "app.models.user",
    "Subject": "app.models.subject",
    "Material": "app.models.material",
    "Question": "app.models.question",
    "QuestionOption": "app.models.question",
    "Assessment": "app.models.assessment",
    "AssessmentQuestion": "app.models.assessment",
    "Attempt": "app.models.assessment",
    "AttemptAnswer": "app.models.assessment",
    "LearningRule": "app.models.assessment",
}


class DatabaseModelsPending(RuntimeError):
    pass


def get_model(model_name):
    """Load models lazily so the app can start while DB models are unfinished."""
    module_name = MODEL_MODULES.get(model_name)
    if module_name is None:
        raise DatabaseModelsPending(f"Chưa khai báo vị trí model {model_name}.")

    try:
        module = import_module(module_name)
        return getattr(module, model_name)
    except (ImportError, AttributeError) as exc:
        raise DatabaseModelsPending(
            f"Model {model_name} chưa được tạo. Nhờ người phụ trách database hoàn thiện app/models/"
        ) from exc


def load_available_models():
    """Import model modules that exist; missing DB-owned modules may be added later."""
    for module_name in set(MODEL_MODULES.values()):
        try:
            import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name != module_name:
                raise
