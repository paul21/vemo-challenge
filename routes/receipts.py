from flask import Blueprint, send_file, jsonify
from flask_jwt_extended import jwt_required
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from app import db
from models import Operation
import io
from datetime import datetime

receipts = Blueprint('receipts', __name__)

@receipts.route('/operations/<operation_id>/receipt/', methods=['GET'])
@jwt_required()
def download_receipt(operation_id):
    """Generate and download PDF receipt for an operation"""
    try:
        operation = Operation.query.filter_by(operation_id=operation_id).first()

        if not operation:
            return jsonify({'error': 'Operation not found'}), 404

        # Create PDF in memory
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Header
        p.setFont("Helvetica-Bold", 20)
        p.drawString(50, height - 50, "Carbon Snapshot Console")

        # Subtitle
        p.setFont("Helvetica", 14)
        p.drawString(50, height - 80, "Comprobante de Operación")

        # Date
        p.setFont("Helvetica", 12)
        p.drawString(50, height - 110, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Operation details
        y_position = height - 150
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_position, "Detalles de la Operación:")

        y_position -= 30
        p.setFont("Helvetica", 11)

        details = [
            f"ID de Operación: {operation.operation_id}",
            f"Tipo: {operation.type}",
            f"Cantidad: {operation.amount}",
            f"Puntuación de Carbono: {operation.carbon_score}",
            f"Email del Usuario: {operation.user_email or 'N/A'}",
            f"Fecha de Creación: {operation.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        ]

        for detail in details:
            p.drawString(50, y_position, detail)
            y_position -= 20

        # Footer
        p.setFont("Helvetica-Italic", 10)
        p.drawString(50, 50, "Este documento fue generado automáticamente por Carbon Snapshot Console")

        p.showPage()
        p.save()

        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"receipt_{operation_id}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500
