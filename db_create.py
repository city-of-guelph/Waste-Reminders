from app import app, db, Role, User, encrypt_password, user_datastore

def build_sample_db():

    app.logger.info('Initializing DB for first run')
    
    with app.app_context():
        admin_role = Role(name='admin')
        db.session.add(admin_role)
        db.session.commit()

        test_user = user_datastore.create_user(
            first_name='Admin',
            user_name='admin',
            password=encrypt_password('admin'),
            roles=[admin_role]
        )

        db.session.commit()
    return

#create the database and the db tables
db.create_all()

#create initial roles and admin user
build_sample_db()
