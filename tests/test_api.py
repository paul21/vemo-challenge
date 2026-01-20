import pytest
import json
from app import create_app, db
from models import User, Operation

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()

        # Create test users
        internal_user = User(email='test_admin@test.com', is_internal=True)
        internal_user.set_password('test123')

        public_user = User(email='test_user@test.com', is_internal=False)
        public_user.set_password('test123')

        db.session.add_all([internal_user, public_user])
        db.session.commit()

        yield app

        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def get_internal_token(client):
    """Helper to get JWT token for internal user"""
    response = client.post('/api/auth/login/',
                          json={'email': 'test_admin@test.com', 'password': 'test123'})
    return response.json['access_token']

def get_public_token(client):
    """Helper to get JWT token for public user"""
    response = client.post('/public/auth/login/',
                          json={'email': 'test_user@test.com', 'password': 'test123'})
    return response.json['access_token']

def test_internal_login(client):
    """Test internal user login"""
    response = client.post('/api/auth/login/',
                          json={'email': 'test_admin@test.com', 'password': 'test123'})

    assert response.status_code == 200
    assert 'access_token' in response.json
    assert response.json['user']['is_internal'] == True

def test_public_login(client):
    """Test public user login"""
    response = client.post('/public/auth/login/',
                          json={'email': 'test_user@test.com', 'password': 'test123'})

    assert response.status_code == 200
    assert 'access_token' in response.json
    assert response.json['user']['is_internal'] == False

def test_create_internal_operation(client):
    """Test creating operation via internal API"""
    token = get_internal_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    operation_data = {
        'type': 'electricity',
        'amount': 100.0,
        'user_email': 'test@example.com'
    }

    response = client.post('/api/operations/',
                          json=operation_data,
                          headers=headers)

    assert response.status_code == 201
    assert response.json['type'] == 'electricity'
    assert response.json['amount'] == 100.0
    assert response.json['carbon_score'] == 50.0  # electricity factor is 0.5
    assert 'operation_id' in response.json

def test_get_operations(client):
    """Test getting operations list via internal API"""
    token = get_internal_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    # First create an operation
    operation_data = {'type': 'transportation', 'amount': 50.0}
    client.post('/api/operations/', json=operation_data, headers=headers)

    # Then get the list
    response = client.get('/api/operations/', headers=headers)

    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['type'] == 'transportation'

def test_create_public_operation(client):
    """Test creating operation via public API"""
    token = get_public_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    operation_data = {
        'type': 'heating',
        'amount': 75.0,
        'user_email': 'public@example.com'
    }

    response = client.post('/public/operations/',
                          json=operation_data,
                          headers=headers)

    assert response.status_code == 201
    assert response.json['type'] == 'heating'
    assert response.json['amount'] == 75.0
    assert response.json['carbon_score'] == 135.0  # heating factor is 1.8
    assert response.json['user_email'] == 'public@example.com'

def test_public_operation_requires_email(client):
    """Test that public operations require user_email"""
    token = get_public_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    operation_data = {
        'type': 'heating',
        'amount': 75.0
        # Missing user_email
    }

    response = client.post('/public/operations/',
                          json=operation_data,
                          headers=headers)

    assert response.status_code == 400
    assert 'user_email is required' in response.json['error']

def test_operations_endpoint_validation_errors(client):
    """Test various validation errors for operations endpoint"""
    token = get_internal_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    # Test missing required fields
    response = client.post('/api/operations/', json={}, headers=headers)
    assert response.status_code == 400
    assert 'Missing required fields: type, amount' in response.json['error']

    # Test missing type only
    response = client.post('/api/operations/', json={'amount': 100.0}, headers=headers)
    assert response.status_code == 400
    assert 'Missing required fields: type, amount' in response.json['error']

    # Test missing amount only
    response = client.post('/api/operations/', json={'type': 'electricity'}, headers=headers)
    assert response.status_code == 400
    assert 'Missing required fields: type, amount' in response.json['error']

    # Test invalid amount (zero)
    response = client.post('/api/operations/',
                          json={'type': 'electricity', 'amount': 0},
                          headers=headers)
    assert response.status_code == 400
    assert 'Amount must be greater than 0' in response.json['error']

    # Test negative amount
    response = client.post('/api/operations/',
                          json={'type': 'electricity', 'amount': -10.0},
                          headers=headers)
    assert response.status_code == 400
    assert 'Amount must be greater than 0' in response.json['error']

def test_operations_endpoint_unauthorized_access(client):
    """Test that unauthorized users cannot access operations endpoint"""
    # Test without token
    response = client.get('/api/operations/')
    assert response.status_code == 401

    response = client.post('/api/operations/', json={'type': 'electricity', 'amount': 100.0})
    assert response.status_code == 401

    # Test with public user token (should be denied)
    public_token = get_public_token(client)
    headers = {'Authorization': f'Bearer {public_token}'}

    response = client.get('/api/operations/', headers=headers)
    assert response.status_code == 403
    assert 'Access denied. Internal access required.' in response.json['error']

    response = client.post('/api/operations/',
                          json={'type': 'electricity', 'amount': 100.0},
                          headers=headers)
    assert response.status_code == 403
    assert 'Access denied. Internal access required.' in response.json['error']

def test_operations_endpoint_different_types(client):
    """Test operations endpoint with different operation types"""
    token = get_internal_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    test_cases = [
        {'type': 'electricity', 'amount': 100.0, 'expected_score': 50.0},
        {'type': 'transportation', 'amount': 50.0, 'expected_score': 115.0},
        {'type': 'heating', 'amount': 75.0, 'expected_score': 135.0},
        {'type': 'manufacturing', 'amount': 25.0, 'expected_score': 80.0},
        {'type': 'unknown_type', 'amount': 100.0, 'expected_score': 100.0},  # uses default factor
    ]

    for case in test_cases:
        response = client.post('/api/operations/',
                              json={'type': case['type'], 'amount': case['amount']},
                              headers=headers)

        assert response.status_code == 201
        assert response.json['type'] == case['type']
        assert response.json['amount'] == case['amount']
        assert response.json['carbon_score'] == case['expected_score']
        assert 'operation_id' in response.json
        assert 'created_at' in response.json

def test_operations_endpoint_with_user_email(client):
    """Test operations endpoint with optional user_email field"""
    token = get_internal_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    # Test with user_email
    operation_data = {
        'type': 'electricity',
        'amount': 100.0,
        'user_email': 'test@example.com'
    }

    response = client.post('/api/operations/', json=operation_data, headers=headers)
    assert response.status_code == 201
    assert response.json['user_email'] == 'test@example.com'

    # Test without user_email (should be None)
    operation_data = {
        'type': 'transportation',
        'amount': 50.0
    }

    response = client.post('/api/operations/', json=operation_data, headers=headers)
    assert response.status_code == 201
    assert response.json['user_email'] is None

def test_get_operations_empty_list(client):
    """Test getting operations when none exist"""
    token = get_internal_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    response = client.get('/api/operations/', headers=headers)
    assert response.status_code == 200
    assert response.json == []

def test_get_operations_multiple_items(client):
    """Test getting operations with multiple items"""
    token = get_internal_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    # Create multiple operations
    operations = [
        {'type': 'electricity', 'amount': 100.0},
        {'type': 'transportation', 'amount': 50.0},
        {'type': 'heating', 'amount': 75.0}
    ]

    for op in operations:
        client.post('/api/operations/', json=op, headers=headers)

    # Get the list
    response = client.get('/api/operations/', headers=headers)
    assert response.status_code == 200
    assert len(response.json) == 3

    # Verify ordering (should be by created_at desc, so newest first)
    assert response.json[0]['type'] == 'heating'
    assert response.json[1]['type'] == 'transportation'
    assert response.json[2]['type'] == 'electricity'

def test_internal_login_validation_errors(client):
    """Test internal login validation errors"""
    # Test missing email and password
    response = client.post('/api/auth/login/', json={})
    assert response.status_code == 400
    assert 'Missing email or password' in response.json['error']

    # Test missing email only
    response = client.post('/api/auth/login/', json={'password': 'test123'})
    assert response.status_code == 400
    assert 'Missing email or password' in response.json['error']

    # Test missing password only
    response = client.post('/api/auth/login/', json={'email': 'test_admin@test.com'})
    assert response.status_code == 400
    assert 'Missing email or password' in response.json['error']

def test_internal_login_invalid_credentials(client):
    """Test internal login with invalid credentials"""
    # Test wrong email
    response = client.post('/api/auth/login/',
                          json={'email': 'wrong@test.com', 'password': 'test123'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

    # Test wrong password
    response = client.post('/api/auth/login/',
                          json={'email': 'test_admin@test.com', 'password': 'wrong'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

    # Test both wrong
    response = client.post('/api/auth/login/',
                          json={'email': 'wrong@test.com', 'password': 'wrong'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

def test_internal_login_public_user_denied(client):
    """Test that public users cannot login via internal endpoint"""
    response = client.post('/api/auth/login/',
                          json={'email': 'test_user@test.com', 'password': 'test123'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

def test_internal_login_response_structure(client):
    """Test internal login response structure and JWT claims"""
    response = client.post('/api/auth/login/',
                          json={'email': 'test_admin@test.com', 'password': 'test123'})

    assert response.status_code == 200
    assert 'access_token' in response.json
    assert 'user' in response.json

    # Check user structure
    user = response.json['user']
    assert 'id' in user
    assert 'email' in user
    assert 'is_internal' in user
    assert 'created_at' in user
    assert user['email'] == 'test_admin@test.com'
    assert user['is_internal'] == True

def test_public_login_validation_errors(client):
    """Test public login validation errors"""
    # Test missing email and password
    response = client.post('/public/auth/login/', json={})
    assert response.status_code == 400
    assert 'Missing email or password' in response.json['error']

    # Test missing email only
    response = client.post('/public/auth/login/', json={'password': 'test123'})
    assert response.status_code == 400
    assert 'Missing email or password' in response.json['error']

    # Test missing password only
    response = client.post('/public/auth/login/', json={'email': 'test_user@test.com'})
    assert response.status_code == 400
    assert 'Missing email or password' in response.json['error']

def test_public_login_invalid_credentials(client):
    """Test public login with invalid credentials"""
    # Test wrong email
    response = client.post('/public/auth/login/',
                          json={'email': 'wrong@test.com', 'password': 'test123'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

    # Test wrong password
    response = client.post('/public/auth/login/',
                          json={'email': 'test_user@test.com', 'password': 'wrong'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

    # Test both wrong
    response = client.post('/public/auth/login/',
                          json={'email': 'wrong@test.com', 'password': 'wrong'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

def test_public_login_internal_user_denied(client):
    """Test that internal users cannot login via public endpoint"""
    response = client.post('/public/auth/login/',
                          json={'email': 'test_admin@test.com', 'password': 'test123'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

def test_public_login_response_structure(client):
    """Test public login response structure and JWT claims"""
    response = client.post('/public/auth/login/',
                          json={'email': 'test_user@test.com', 'password': 'test123'})

    assert response.status_code == 200
    assert 'access_token' in response.json
    assert 'user' in response.json

    # Check user structure
    user = response.json['user']
    assert 'id' in user
    assert 'email' in user
    assert 'is_internal' in user
    assert 'created_at' in user
    assert user['email'] == 'test_user@test.com'
    assert user['is_internal'] == False

def test_login_endpoints_case_sensitivity(client):
    """Test that login is case sensitive for email"""
    # Test internal login with uppercase email
    response = client.post('/api/auth/login/',
                          json={'email': 'TEST_ADMIN@TEST.COM', 'password': 'test123'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

    # Test public login with uppercase email
    response = client.post('/public/auth/login/',
                          json={'email': 'TEST_USER@TEST.COM', 'password': 'test123'})
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['error']

def test_login_jwt_token_format(client):
    """Test that JWT tokens are properly formatted"""
    # Get internal token
    response = client.post('/api/auth/login/',
                          json={'email': 'test_admin@test.com', 'password': 'test123'})
    internal_token = response.json['access_token']

    # Get public token
    response = client.post('/public/auth/login/',
                          json={'email': 'test_user@test.com', 'password': 'test123'})
    public_token = response.json['access_token']

    # Check tokens are strings and not empty
    assert isinstance(internal_token, str)
    assert len(internal_token) > 0
    assert isinstance(public_token, str)
    assert len(public_token) > 0

    # Check tokens are different (different users)
    assert internal_token != public_token
