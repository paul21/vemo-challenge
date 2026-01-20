import asyncio
from celery import Celery
from flask import current_app
from flask_mail import Message
from app import mail
import redis
import json

# Initialize Celery
celery = Celery('email_service')
celery.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

class EmailService:
    """Async service to handle email notifications with Redis queue"""

    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    @staticmethod
    @celery.task
    def send_operation_confirmation_async(operation_data: dict):
        """Send confirmation email for a new operation asynchronously"""
        try:
            subject = "Transacción recibida – Carbon Snapshot Console"

            body = f"""
Estimado usuario,

Hemos recibido su transacción exitosamente:

- ID de Operación: {operation_data['operation_id']}
- Tipo: {operation_data['type']}
- Cantidad: {operation_data['amount']}
- Puntuación de Carbono: {operation_data['carbon_score']}
- Fecha: {operation_data['created_at']}

Gracias por usar Carbon Snapshot Console.

Saludos,
El equipo de Carbon Snapshot Console
            """

            msg = Message(
                subject=subject,
                recipients=[operation_data['user_email']],
                body=body
            )

            mail.send(msg)
            print(f"Email sent to {operation_data['user_email']}")
            return True

        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    async def queue_email_confirmation(self, operation_data: dict):
        """Queue email confirmation task to Redis"""
        try:
            # Store in Redis queue for processing
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis_client.lpush(
                    'email_queue',
                    json.dumps(operation_data)
                )
            )

            # Trigger Celery task
            self.send_operation_confirmation_async.delay(operation_data)

            print(f"Email queued for {operation_data['user_email']}")
            return True

        except Exception as e:
            print(f"Failed to queue email: {e}")
            return False

    @staticmethod
    def send_operation_confirmation(operation_data: dict):
        """Legacy sync method - queues email for async processing"""
        try:
            service = EmailService()
            # Run the async queue method in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                service.queue_email_confirmation(operation_data)
            )
            loop.close()
            return result
        except Exception as e:
            print(f"Failed to queue email: {e}")
            return False
