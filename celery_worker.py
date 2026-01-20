from celery import Celery
from app import create_app, mail
from services.email_service import EmailService

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# Create Flask app and initialize Celery
flask_app = create_app()
celery = make_celery(flask_app)

@celery.task(bind=True)
def send_email_task(self, operation_data):
    """Background task to send emails"""
    try:
        return EmailService.send_operation_confirmation_async(operation_data)
    except Exception as e:
        print(f"Email task failed: {e}")
        return False
