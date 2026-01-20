from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from models import Operation, User
from services.carbon_calculator import CarbonCalculatorService

internal_api = Blueprint('internal_api', __name__)
carbon_calculator = CarbonCalculatorService()

@internal_api.route('/operations/', methods=['POST'])
@jwt_required()
def create_operation():
    """Create a new operation (internal API)"""
    try:
        # Verify user is internal
        claims = get_jwt()
        if not claims.get('is_internal', False):
            return jsonify({'error': 'Access denied. Internal access required.'}), 403

        data = request.get_json()

        # Validate required fields
        if not data or 'type' not in data or 'amount' not in data:
            return jsonify({'error': 'Missing required fields: type, amount'}), 400

        if data['amount'] <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400

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
            user_email=data.get('user_email')
        )

        db.session.add(operation)
        db.session.commit()

        return jsonify(operation.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@internal_api.route('/operations/', methods=['GET'])
@jwt_required()
def get_operations():
    """Get all operations (internal API)"""
    try:
        # Verify user is internal
        claims = get_jwt()
        if not claims.get('is_internal', False):
            return jsonify({'error': 'Access denied. Internal access required.'}), 403

        operations = Operation.query.order_by(Operation.created_at.desc()).all()
        return jsonify([op.to_dict() for op in operations]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@internal_api.route('/auth/login/', methods=['POST'])
def internal_login():
    """Login for internal users"""
    from flask_jwt_extended import create_access_token

    try:
        data = request.get_json()

        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Missing email or password'}), 400

        user = User.query.filter_by(email=data['email'], is_internal=True).first()

        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Create JWT with internal flag
        additional_claims = {'is_internal': True}
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
