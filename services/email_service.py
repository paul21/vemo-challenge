import asyncio
from celery import Celery
from flask import current_app
from flask_mail import Message
from app import mail
import redis
import json
import logging

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
        self.logger = logging.getLogger(__name__)

    @staticmethod
    @celery.task
    def send_operation_confirmation_async(operation_data: dict):
        """Send confirmation email for a new operation asynchronously"""
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"Sending confirmation email for operation: {operation_data.get('operation_id')}")

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
            logger.info(f"Email sent successfully to {operation_data['user_email']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {operation_data.get('user_email', 'unknown')}: {str(e)}")
            return False

    async def queue_email_confirmation(self, operation_data: dict):
        """Queue email confirmation task to Redis"""
        try:
            self.logger.info(f"Queuing email confirmation for operation: {operation_data.get('operation_id')}")

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

            self.logger.info(f"Email queued successfully for {operation_data['user_email']}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to queue email for {operation_data.get('user_email', 'unknown')}: {str(e)}")
            return False

    @staticmethod
    def send_operation_confirmation(operation_data: dict):
        """Legacy sync method - queues email for async processing"""
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"Initiating email confirmation for operation: {operation_data.get('operation_id')}")

            service = EmailService()
            # Run the async queue method in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                service.queue_email_confirmation(operation_data)
            )
            loop.close()

            if result:
                logger.info(f"Email confirmation process completed for operation: {operation_data.get('operation_id')}")
            else:
                logger.warning(f"Email confirmation process failed for operation: {operation_data.get('operation_id')}")

            return result
        except Exception as e:
            logger.error(f"Failed to queue email confirmation for operation {operation_data.get('operation_id', 'unknown')}: {str(e)}")
            return False
