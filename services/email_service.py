from flask import current_app
from flask_mail import Message
from app import mail

class EmailService:
    """Service to handle email notifications"""
    
    @staticmethod
    def send_operation_confirmation(operation_data: dict):
        """Send confirmation email for a new operation"""
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
