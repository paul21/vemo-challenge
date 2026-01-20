from app import create_app, db
from models import User, Operation
from services.carbon_calculator import CarbonCalculatorService

def seed_data():
    """Seed initial data for testing"""
    app = create_app()

    with app.app_context():
        # Clear existing data (but keep the migration tables)
        Operation.query.delete()
        User.query.delete()
        db.session.commit()

        carbon_calculator = CarbonCalculatorService()

        # Create internal users
        internal_user1 = User(
            email='admin@carbonconsole.com',
            is_internal=True
        )
        internal_user1.set_password('admin123')

        internal_user2 = User(
            email='manager@carbonconsole.com',
            is_internal=True
        )
        internal_user2.set_password('manager123')

        # Create public users
        public_user1 = User(
            email='user1@example.com',
            is_internal=False
        )
        public_user1.set_password('user123')

        public_user2 = User(
            email='user2@example.com',
            is_internal=False
        )
        public_user2.set_password('user123')

        # Add users to session
        db.session.add_all([internal_user1, internal_user2, public_user1, public_user2])
        db.session.commit()

        # Create sample operations
        operations_data = [
            {'type': 'electricity', 'amount': 100.0, 'user_email': 'user1@example.com'},
            {'type': 'transportation', 'amount': 50.0, 'user_email': 'user2@example.com'},
            {'type': 'heating', 'amount': 75.0, 'user_email': 'user1@example.com'},
            {'type': 'manufacturing', 'amount': 200.0, 'user_email': None},
            {'type': 'electricity', 'amount': 150.0, 'user_email': 'user2@example.com'},
        ]

        operations = []
        for op_data in operations_data:
            carbon_score = carbon_calculator.calculate_carbon_score(
                op_data['type'],
                op_data['amount']
            )

            operation = Operation(
                type=op_data['type'],
                amount=op_data['amount'],
                carbon_score=carbon_score,
                user_email=op_data['user_email']
            )
            operations.append(operation)

        db.session.add_all(operations)
        db.session.commit()

        print("Seed data created successfully!")
        print("\nInternal Users:")
        print("- admin@carbonconsole.com / admin123")
        print("- manager@carbonconsole.com / manager123")
        print("\nPublic Users:")
        print("- user1@example.com / user123")
        print("- user2@example.com / user123")
        print(f"\nCreated {len(operations)} sample operations")

if __name__ == '__main__':
    seed_data()
