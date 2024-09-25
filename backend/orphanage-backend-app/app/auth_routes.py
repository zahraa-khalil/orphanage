from flask import Blueprint, request, jsonify # type: ignore
import mysql.connector # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash
from app.config import Config
import jwt
from datetime import datetime, timedelta, timezone


# Secret key for signing JWT (store it securely, e.g., in environment variables)
SECRET_KEY = 'your_secret_key'


# Create a Blueprint for authentication routes
auth = Blueprint('auth', __name__)

# Use the config values for the MySQL connection
db_config = {
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'host': Config.MYSQL_HOST,
    'database': Config.MYSQL_DATABASE
}

# Registration Route
@auth.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        name = data['name']
        email = data['email']
        password = data['password']
        role = data.get('role', 'orphanage')

        # Hash the password using pbkdf2:sha256
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Insert user into the database
        cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)", 
                        (name, email, hashed_password, role))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "User registered successfully!"}), 201

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Login Route
@auth.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data['email']
        password = data['password']

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Check if the user exists in the database
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user is None:
            return jsonify({"error": "User not found"}), 404

        # Check if the password is correct
        if check_password_hash(user['password'], password):
            # Generate JWT token with orphanage_id
            token = jwt.encode({
                'orphanage_id': user['id'],  # Include orphanage ID in the token
                'exp': datetime.now(timezone.utc) + timedelta(hours=48)  # Token expiration time (1 hour)
            }, SECRET_KEY, algorithm="HS256")

            return jsonify({"message": "Login successful!", "token": token}), 200
        else:
            return jsonify({"error": "Incorrect password"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# Route to orphanage to setup account
@auth.route('/setup-account', methods=['POST'])
def setup_orphanage_account():
    try:
        # Get the token from the Authorization header
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        # Decode the token to get the orphanage_id
        try:
            decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            orphanage_id = decoded_token['orphanage_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        # Get the request data
        data = request.json
        governorate = data['governorate']  # Updated to represent governorates like Cairo, Giza, etc.
        address = data['address']
        registration_certificate_number = data['registration_certificate_number']
        operating_license_number = data['operating_license_number']
        license_expiration_date = data['license_expiration_date']  # Expecting a string date (e.g., '2024-12-31')
        manager_national_id = data['manager_national_id']
        tax_id = data['tax_id']
        bank_account_details = data['bank_account_details']

        # Validate required fields
        if not governorate or not address or not registration_certificate_number or not operating_license_number \
                or not license_expiration_date or not manager_national_id or not tax_id or not bank_account_details:
            return jsonify({"error": "All fields are required"}), 400

        # Convert license_expiration_date to a proper date format
        try:
            license_expiration_date = datetime.strptime(license_expiration_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format for license_expiration_date. Expected format: YYYY-MM-DD"}), 400

        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Insert the verification data into the orphanage_verification table
        cursor.execute("""
            INSERT INTO orphanage_verification (orphanage_id, governorate, address, registration_certificate_number, 
                                                operating_license_number, license_expiration_date, manager_national_id, 
                                                tax_id, bank_account_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (orphanage_id, governorate, address, registration_certificate_number, operating_license_number,
              license_expiration_date, manager_national_id, tax_id, bank_account_details))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Orphanage verification data submitted successfully!"}), 201

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth.route('/orphanage-account', methods=['GET'])
def get_orphanage_account():
    try:
        # Get the token from the Authorization header
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        # Decode the token to get orphanage_id
        try:
            decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            orphanage_id = decoded_token['orphanage_id']  # Assuming orphanage_id is stored in the token
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        # Connect to the database to retrieve orphanage account data
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch orphanage account setup data from the orphanage_verification table
        cursor.execute("""
            SELECT address, registration_certificate_number, operating_license_number, 
                   license_expiration_date, manager_national_id, tax_id, bank_account_details,
                   status, rejection_reason, governorate
            FROM orphanage_verification
            WHERE orphanage_id = %s
        """, (orphanage_id,))
        orphanage_account = cursor.fetchone()

        cursor.close()
        conn.close()

        if orphanage_account:
            return jsonify(orphanage_account), 200
        else:
            return jsonify({"error": "No account data found for this orphanage"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

