from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid


class User(db.Model):
    """
    Usuario del sistema.
    is_internal=True: usuario de backoffice (puede ver todas las operaciones)
    is_internal=False: usuario publico (solo puede crear operaciones)
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'is_internal': self.is_internal,
            'created_at': self.created_at.isoformat()
        }

class Operation(db.Model):
    """
    Registro de actividad con huella de carbono.
    carbon_score se calcula automaticamente segun type y amount.
    user_email es opcional para operaciones internas, obligatorio para publicas.
    """
    __tablename__ = 'operations'

    id = db.Column(db.Integer, primary_key=True)
    operation_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    type = db.Column(db.String(100), nullable=False)  # electricity, transportation, heating, manufacturing
    amount = db.Column(db.Float, nullable=False)
    carbon_score = db.Column(db.Float, nullable=False)  # Calculado por CarbonCalculatorService
    user_email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Operation, self).__init__(**kwargs)
        if not self.operation_id:
            self.operation_id = str(uuid.uuid4())

    def to_dict(self):
        return {
            'operation_id': self.operation_id,
            'type': self.type,
            'amount': self.amount,
            'carbon_score': self.carbon_score,
            'user_email': self.user_email,
            'created_at': self.created_at.isoformat()
        }
