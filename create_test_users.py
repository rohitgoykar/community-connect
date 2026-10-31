# create_test_users.py - Run this to create test users

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_test_users():
    with app.app_context():
        # Create Blood Donor (matches "Need A+ blood")
        donor = User.query.filter_by(username='blood_donor').first()
        if not donor:
            donor = User(
                username='blood_donor',
                password=generate_password_hash('donor123'),
                email='donor@test.com',
                name='John Donor',
                contact='9876543210',
                location='Mumbai',
                blood_group='A+',  # Matches your post!
                skills='',
                trust_score=85,
                is_active=True
            )
            db.session.add(donor)
            print("✓ Created Blood Donor (A+)")
        
        # Create Mechanic (matches "Need mechanic")
        mechanic = User.query.filter_by(username='mechanic_pro').first()
        if not mechanic:
            mechanic = User(
                username='mechanic_pro',
                password=generate_password_hash('mechanic123'),
                email='mechanic@test.com',
                name='Mike Mechanic',
                contact='9876543222',
                location='Mumbai',
                blood_group='O+',
                skills='mechanic,plumber,electrician',  # Matches your post!
                trust_score=90,
                is_active=True
            )
            db.session.add(mechanic)
            print("✓ Created Mechanic Professional")
        
        # Create Real Estate Agent (matches "Need house near mumbai")
        agent = User.query.filter_by(username='real_estate_agent').first()
        if not agent:
            agent = User(
                username='real_estate_agent',
                password=generate_password_hash('agent123'),
                email='agent@test.com',
                name='Sarah Agent',
                contact='9876543333',
                location='Mumbai',  # Matches your post location!
                blood_group='B+',
                interests='real estate,property',
                trust_score=95,
                is_active=True
            )
            db.session.add(agent)
            print("✓ Created Real Estate Agent")
        
        db.session.commit()
        print("\n✅ Test users created successfully!")
        print("\n📋 Login credentials:")
        print("   blood_donor / donor123")
        print("   mechanic_pro / mechanic123")
        print("   real_estate_agent / agent123")

if __name__ == '__main__':
    create_test_users()