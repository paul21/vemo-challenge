from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from app import db
from models import Operation, User
from services.carbon_calculator import CarbonCalculatorService
from services.email_service import EmailService
import logging

public_api = Blueprint('public_api', __name__)
carbon_calculator = CarbonCalculatorService()
email_service = EmailService()
logger = logging.getLogger(__name__)

@public_api.route('/auth/login/', methods=['POST'])
def public_login():
    """Login for public users"""
    try:
        logger.info("Public login attempt")
        data = request.get_json()

        if not data or 'email' not in data or 'password' not in data:
            logger.warning("Missing email or password in public login request")
            return jsonify({'error': 'Missing email or password'}), 400

        user = User.query.filter_by(email=data['email'], is_internal=False).first()
        logger.debug(f"Looking for public user with email: {data['email']}")

        if not user or not user.check_password(data['password']):
            logger.warning(f"Invalid credentials for email: {data['email']}")
            return jsonify({'error': 'Invalid credentials'}), 401

        # Create JWT with public user flag
        additional_claims = {'is_internal': False}
        access_token = create_access_token(
            identity=user.email,
            additional_claims=additional_claims
        )

        logger.info(f"Public user logged in successfully: {user.email}")
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error in public login: {str(e)}")
        return jsonify({'error': str(e)}), 500

@public_api.route('/operations/', methods=['POST'])
@jwt_required()
def create_public_operation():
    """Create a new operation from public API"""
    try:
        # Verify user is public (not internal)
        claims = get_jwt()
        if claims.get('is_internal', False):
            logger.warning("Internal user attempted to access public endpoint")
            return jsonify({'error': 'This endpoint is for public users only'}), 403

        user_email = get_jwt_identity()
        logger.info(f"Creating public operation for user: {user_email}")

        data = request.get_json()

        # Validate required fields
        if not data or 'type' not in data or 'amount' not in data:
            logger.warning("Missing required fields in public operation request")
            return jsonify({'error': 'Missing required fields: type, amount'}), 400

        if data['amount'] <= 0:
            logger.warning(f"Invalid amount provided: {data['amount']}")
            return jsonify({'error': 'Amount must be greater than 0'}), 400

        # user_email is required for public operations
        operation_user_email = data.get('user_email')
        if not operation_user_email:
            logger.warning("user_email is required for public operations")
            return jsonify({'error': 'user_email is required for public operations'}), 400

        # Calculate carbon score
        carbon_score = carbon_calculator.calculate_carbon_score(
            data['type'],
            data['amount']
        )
        logger.debug(f"Calculated carbon score: {carbon_score} for type: {data['type']}, amount: {data['amount']}")

        # Create operation
        operation = Operation(
            type=data['type'],
            amount=data['amount'],
            carbon_score=carbon_score,
            user_email=operation_user_email
        )

        db.session.add(operation)
        db.session.commit()
        logger.info(f"Public operation created successfully with ID: {operation.operation_id}")

        # Send confirmation email
        email_service.send_operation_confirmation(operation.to_dict())
        logger.info(f"Confirmation email queued for operation: {operation.operation_id}")

        return jsonify(operation.to_dict()), 201

    except Exception as e:
        logger.error(f"Error creating public operation: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
