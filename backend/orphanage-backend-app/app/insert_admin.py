# from werkzeug.security import generate_password_hash
# import mysql.connector



# # Use the config values for the MySQL connection
# db_config = {
#     'user': 'fatma',
#     'password': '',
#     'host': 'localhost',
#     'database': 'orphanage_db'
# }


# conn = mysql.connector.connect(**db_config)
# cursor = conn.cursor()

# # Admin credentials
# admin_name = "Admin"
# admin_email = "admin@info.com"
# admin_password = "123456"  # This is the plain password

# # Hash the password
# hashed_password = generate_password_hash(admin_password, method='pbkdf2:sha256', salt_length=16)

# # Insert the admin into the users table
# insert_query = """
#     INSERT INTO users (name, email, password, role)
#     VALUES (%s, %s, %s, %s)
# """
# cursor.execute(insert_query, (admin_name, admin_email, hashed_password, 'admin'))

# # Commit the changes
# conn.commit()

# # Close the connection
# cursor.close()
# conn.close()

# print("Admin user created successfully!")