from flask import Blueprint, render_template, request, redirect, url_for, session, send_file
from flask_jwt_extended import create_access_token, decode_token
from app import db
from models import Operation, User
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from functools import wraps
import io
import logging

backoffice = Blueprint('backoffice', __name__)
logger = logging.getLogger(__name__)


def login_required(f):
    """Decorator to check if user is logged in via session JWT"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('jwt_token')
        if not token:
            return redirect(url_for('backoffice.login'))
        try:
            decoded = decode_token(token)
            if not decoded.get('is_internal', False):
                session.clear()
                return redirect(url_for('backoffice.login'))
        except Exception:
            session.clear()
            return redirect(url_for('backoffice.login'))
        return f(*args, **kwargs)
    return decorated_function


@backoffice.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for backoffice"""
    if request.method == 'GET':
        if session.get('jwt_token'):
            return redirect(url_for('backoffice.operations_list'))
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return render_template('login.html', error='Email and password are required')

    user = User.query.filter_by(email=email, is_internal=True).first()

    if not user or not user.check_password(password):
        logger.warning(f"Failed backoffice login attempt for: {email}")
        return render_template('login.html', error='Invalid credentials')

    token = create_access_token(
        identity=user.email,
        additional_claims={'is_internal': True}
    )
    session['jwt_token'] = token
    session['user_email'] = user.email

    logger.info(f"Backoffice login successful: {email}")
    return redirect(url_for('backoffice.operations_list'))


@backoffice.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('backoffice.login'))


@backoffice.route('/operations/')
@login_required
def operations_list():
    """List all operations"""
    operations = Operation.query.order_by(Operation.created_at.desc()).all()
    return render_template('operations_list.html', operations=operations)


@backoffice.route('/operations/<operation_id>/')
@login_required
def operation_detail(operation_id):
    """View operation details"""
    operation = Operation.query.filter_by(operation_id=operation_id).first()
    if not operation:
        return redirect(url_for('backoffice.operations_list'))
    return render_template('operation_detail.html', operation=operation)


@backoffice.route('/operations/<operation_id>/pdf')
@login_required
def download_pdf(operation_id):
    """Download PDF receipt for operation"""
    operation = Operation.query.filter_by(operation_id=operation_id).first()

    if not operation:
        return redirect(url_for('backoffice.operations_list'))

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, "Carbon Snapshot Console")

    p.setFont("Helvetica", 14)
    p.drawString(50, height - 80, "Comprobante de Operacion")

    p.setFont("Helvetica", 12)
    p.drawString(50, height - 110, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    y_position = height - 150
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_position, "Detalles de la Operacion:")

    y_position -= 30
    p.setFont("Helvetica", 11)

    details = [
        f"ID de Operacion: {operation.operation_id}",
        f"Tipo: {operation.type}",
        f"Cantidad: {operation.amount}",
        f"Puntuacion de Carbono: {operation.carbon_score}",
        f"Email del Usuario: {operation.user_email or 'N/A'}",
        f"Fecha de Creacion: {operation.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    ]

    for detail in details:
        p.drawString(50, y_position, detail)
        y_position -= 20

    p.setFont("Helvetica", 10)
    p.drawString(50, 50, "Este documento fue generado automaticamente por Carbon Snapshot Console")

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"receipt_{operation_id}.pdf",
        mimetype='application/pdf'
    )
