from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from app import db
from models import Operation, User
from services.carbon_calculator import CarbonCalculatorService
from services.email_service import EmailService

public_api = Blueprint('public_api', __name__)
carbon_calculator = CarbonCalculatorService()
email_service = EmailService()

@public_api.route('/auth/login/', methods=['POST'])
def public_login():
    """Login for public users"""
    try:
        data = request.get_json()

        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Missing email or password'}), 400

        user = User.query.filter_by(email=data['email'], is_internal=False).first()

        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Create JWT with public user flag
        additional_claims = {'is_internal': False}
        access_token = create_access_token(
            identity=user.email,
            additional_claims=additional_claims
        )

        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@public_api.route('/operations/', methods=['POST'])
@jwt_required()
def create_public_operation():
    """Create a new operation from public API"""
    try:
        # Verify user is public (not internal)
        claims = get_jwt()
        if claims.get('is_internal', False):
            return jsonify({'error': 'This endpoint is for public users only'}), 403

        data = request.get_json()

        # Validate required fields
        if not data or 'type' not in data or 'amount' not in data:
            return jsonify({'error': 'Missing required fields: type, amount'}), 400

        if data['amount'] <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400

        # user_email is required for public operations
        user_email = data.get('user_email')
        if not user_email:
            return jsonify({'error': 'user_email is required for public operations'}), 400

        # Calculate carbon score
        carbon_score = carbon_calculator.calculate_carbon_score(
            data['type'],
            data['amount']
        )

        # Create operation
        operation = Operation(
            type=data['type'],
            amount=data['amount'],
            carbon_score=carbon_score,
            user_email=user_email
        )

        db.session.add(operation)
        db.session.commit()

        # Send confirmation email
        email_service.send_operation_confirmation(operation.to_dict())

        return jsonify(operation.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
