from app import app
from models import db, Users, Parking_lots,Parking_spots

#create default admin
def default_admin():
    admin=Users.query.filter_by(U_name='admin').first()
    if not admin:
        #add details about admin
        admin=Users(U_name='admin',
                    Fullname='Administrator',
                    P_address='Company HQ',
                    pincode=226102,
                    isadmin=True)
        admin.set_pass('admin123') #password set for admin
        db.session.add(admin)
        db.session.commit()
        print("Default admin is (username=admin, password:admin123)")
    else:
        print("Admin exists")

#adding spot number of the parking lot:: A1 ,A2 etc
def create_spot_no(lot_id,spot_index):
    section= chr(65 + (spot_index -1)//10) #Capital Alphabets
    num= ((spot_index -1)%10)+1
    
    return f"{section}{num}"

def seed_demo_data():   #check if there is at least one row in Parking_lots returns first row else none
    if Parking_lots.query.first():
        print("Demo data exist")
        return
    
    #Now creating demo parking lot if no user present add demo data
    lots_data=[
        {
            'location_name' : 'KCC Airport',
            'address': 'KCC Airport, Transport Nagar Lucknow',
            'pincode': 226006,
            'hourly_rate': 10.00,
            'max_spots':15
        }
    ]

    for lot_data in lots_data:
        lot=Parking_lots(**lot_data)
        db.session.add(lot)
        db.session.commit()

    #create spots for this lot
        for i in range (1,lot.max_spots+1):
            spot_no=create_spot_no(lot.PL_id,i)
            spot=Parking_spots(lot_id=lot.id,spot_num=spot_no, occupancy_status='A')
            db.session.add(spot)
        print(f"Created {lot.location_name} with {lot.max_spots} spots")
    db.session.commit()
    print("demo lots and spots are created")


#create some demo users   
def demo_users():
    demousers=[
        { 'U_name': 'Abhishek', 'password':'Abhi@123', 'Fullname':'Abhishek Yadav', 'P_address':'tedhi Pulia, Lucknow', 'pincode':'226101'},
        { 'U_name': 'Raju','password':'Raju@123' , 'Fullname':'Raju Yadav', 'P_address':'tedhi Pulia, Lucknow', 'pincode':'226101'}
    ]

    for user_data in demousers:
        if not Users.query.filter_by(U_name=user_data['U_name']).first():     #prevents duplicacy if the program is run again and again
            user=Users(
                U_name=user_data['U_name'],
                Fullname=user_data['Fullname'],
                P_address= user_data['P_address'],
                pincode=int(user_data['pincode']), 
                isadmin=False)
            user.set_pass(user_data['password'])
            db.session.add(user)
            print(f"demo user is created {user_data['U_name']}")

    db.session.commit()

def main():
    with app.app_context():
        print('setting up Vehicle Parking Database')
        print("-" * 50)

        db.create_all()
        print('database table created')

        default_admin()

        demo_users()

        seed_demo_data()

        print("\n" + "-" * 50)
        print("Database setup successfull!")
        print("\n Login Credentials:")
        print("   Admin: username=admin, password=admin123")
        print("   Demo Users: username=Abhishek/Raju")
        print("   Demo Password: Abhi@123/Raju@123")
        print("\n to start the app type 'python app.py' in cmd")
        print("http://localhost:5000")

if __name__ =='__main__':
    main()