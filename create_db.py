from app import app
from models import db, User, ParkingLot, ParkingSpot
import string
import random

def create_default_admin():
    """Create default admin user if not exists"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created (username: admin, password: admin123)")
    else:
        print("ℹ️  Admin user already exists")

def generate_spot_number(lot_id, spot_index):
    """Generate spot number like A1, A2, B1, B2, etc."""
    section = chr(65 + (spot_index - 1) // 10)  # A, B, C, etc.
    number = ((spot_index - 1) % 10) + 1
    return f"{section}{number}"

def seed_demo_data():
    """Seed demo parking lots and spots"""
    if ParkingLot.query.first():
        print("ℹ️  Demo data already exists")
        return
    
    # Create demo parking lots
    lots_data = [
        {
            'prime_location_name': 'Central Mall Parking',
            'address': '123 Main Street, Downtown Area',
            'pincode': '123456',
            'price_per_hour': 25.0,
            'maximum_number_of_spots': 15
        },
        {
            'prime_location_name': 'City Center Garage',
            'address': '456 Park Avenue, Midtown District',
            'pincode': '654321',
            'price_per_hour': 20.0,
            'maximum_number_of_spots': 12
        },
        {
            'prime_location_name': 'Airport Parking Zone',
            'address': '789 Airport Road, Terminal 1',
            'pincode': '789012',
            'price_per_hour': 30.0,
            'maximum_number_of_spots': 20
        },
        {
            'prime_location_name': 'Shopping Complex Parking',
            'address': '321 Market Street, Commercial Area',
            'pincode': '456789',
            'price_per_hour': 18.0,
            'maximum_number_of_spots': 10
        }
    ]
    
    for lot_data in lots_data:
        lot = ParkingLot(**lot_data)
        db.session.add(lot)
        db.session.commit()
        
        # Create spots for this lot
        for i in range(1, lot.maximum_number_of_spots + 1):
            spot_number = generate_spot_number(lot.id, i)
            spot = ParkingSpot(lot_id=lot.id, spot_number=spot_number, status='A')
            db.session.add(spot)
        
        print(f"✅ Created {lot.prime_location_name} with {lot.maximum_number_of_spots} spots")
    
    db.session.commit()
    print("✅ Demo parking lots and spots created successfully")

def create_demo_users():
    """Create some demo users"""
    demo_users = [
        {'username': 'user1', 'password': 'password123'},
        {'username': 'user2', 'password': 'password123'},
        {'username': 'user3', 'password': 'password123'},
        {'username': 'user4', 'password': 'password123'},
        {'username': 'user5', 'password': 'password123'}
    ]
    
    for user_data in demo_users:
        if not User.query.filter_by(username=user_data['username']).first():
            user = User(username=user_data['username'])
            user.set_password(user_data['password'])
            db.session.add(user)
            print(f"✅ Created demo user: {user_data['username']}")
    
    db.session.commit()

def main():
    """Main function to set up the database"""
    with app.app_context():
        print("🚀 Setting up Vehicle Parking App Database...")
        print("=" * 50)
        
        # Create all tables
        db.create_all()
        print("✅ Database tables created")
        
        # Create admin user
        create_default_admin()
        
        # Create demo users
        create_demo_users()
        
        # Seed demo data
        seed_demo_data()
        
        print("\n" + "=" * 50)
        print("🎉 Database setup completed successfully!")
        print("\n📋 Login Credentials:")
        print("   Admin: username=admin, password=admin123")
        print("   Demo Users: username=user1/user2/user3/user4/user5")
        print("   Demo Password: password123")
        print("\n🚀 Run 'python app.py' to start the application")
        print("🌐 Visit: http://localhost:5000")

if __name__ == '__main__':
    main()
