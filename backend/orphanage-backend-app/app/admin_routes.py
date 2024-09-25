from flask import Blueprint, request, jsonify # type: ignore
import mysql.connector # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash
from app.config import Config
import jwt
from datetime import datetime, timedelta, timezone


# Secret key for signing JWT (store it securely, e.g., in environment variables)
SECRET_KEY = 'your_secret_key'


# Create a Blueprint for authentication routes
admin = Blueprint('admin', __name__)

# Use the config values for the MySQL connection
db_config = {
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'host': Config.MYSQL_HOST,
    'database': Config.MYSQL_DATABASE
}

# admin login
@admin.route('/admin/login', methods=['POST'])
def admin_login():
    try:
        # Get the request data (email and password)
        data = request.json
        email = data['email']
        password = data['password']

        # Connect to the database to authenticate the user
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch the user details based on email
        cursor.execute("SELECT * FROM users WHERE email = %s AND role = 'admin'", (email,))
        user = cursor.fetchone()

        # Check if the user exists and the password is correct
        if user and check_password_hash(user['password'], password):
            # Create JWT token with the admin's role
            token = jwt.encode({
                'user_id': user['id'],
                'role': user['role'],  # Ensure 'role' is 'admin'
                'exp': datetime.now(timezone.utc) + timedelta(hours=48) # Token expiration
            }, SECRET_KEY)

            return jsonify({"token": token}), 200

        else:
            return jsonify({"error": "Invalid credentials or not an admin"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# admin verify
@admin.route('/orphanage/verify', methods=['POST'])
def verify_orphanage():
    try:
        # Get the token from the Authorization header to check if the user is admin
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        # Decode the token to verify if the user is admin
        try:
            decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_role = decoded_token['role']
            if user_role != 'admin':
                return jsonify({"error": "Unauthorized"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        # Get the request data
        data = request.json
        orphanage_id = data['orphanage_id']
        status = data['status']  # 'approved' or 'rejected'
        rejection_reason = data.get('rejection_reason', None)  # Optional field, only required if rejected

        # Validate status
        if status not in ['approved', 'rejected']:
            return jsonify({"error": "Invalid status. Must be 'approved' or 'rejected'."}), 400

        # If the status is 'rejected', a rejection_reason must be provided
        if status == 'rejected' and not rejection_reason:
            return jsonify({"error": "Rejection reason is required for rejected status."}), 400

        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Update the orphanage status and rejection_reason (if rejected)
        cursor.execute("""
            UPDATE orphanage_verification 
            SET status = %s, rejection_reason = %s 
            WHERE orphanage_id = %s
        """, (status, rejection_reason, orphanage_id))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": f"Orphanage {status} successfully!"}), 200

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# get all orphanages requests
@admin.route('/orphanages-requests', methods=['GET'])
def get_all_orphanages():
    try:
        # Get the token from the Authorization header
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        # Decode the token to verify if the user is an admin
        try:
            decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_role = decoded_token['role']

            # Ensure the user is an admin
            if user_role != 'admin':
                return jsonify({"error": "Unauthorized: Admins only"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        # Connect to the database to retrieve all orphanages with their status
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch all orphanages and their statuses from orphanage_verification table
        # Join with users table to get orphanage name and email
        cursor.execute("""
            SELECT o.orphanage_id, u.name, u.email, o.address, 
                   o.registration_certificate_number, 
                   o.operating_license_number, o.license_expiration_date, 
                   o.manager_national_id, o.tax_id, o.bank_account_details, 
                   o.status, o.rejection_reason
            FROM orphanage_verification o
            JOIN users u ON o.orphanage_id = u.id  -- Assuming orphanage_id corresponds to the user ID
        """)
        orphanages = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(orphanages), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# get orphanage by id 
@admin.route('/orphanages-requests/<int:orphanage_id>', methods=['GET'])
def get_orphanage_by_id(orphanage_id):
    try:
        # Get the token from the Authorization header
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        # Decode the token to verify if the user is an admin
        try:
            decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_role = decoded_token['role']

            # Ensure the user is an admin
            if user_role != 'admin':
                return jsonify({"error": "Unauthorized: Admins only"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        # Connect to the database to retrieve details for the specific orphanage
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch orphanage details from orphanage_verification and users table by orphanage_id
        cursor.execute("""
            SELECT o.orphanage_id, u.name, u.email, o.address, 
                   o.registration_certificate_number, 
                   o.operating_license_number, o.license_expiration_date, 
                   o.manager_national_id, o.tax_id, o.bank_account_details, 
                   o.status, o.rejection_reason
            FROM orphanage_verification o
            JOIN users u ON o.orphanage_id = u.id  -- Assuming orphanage_id links to users table
            WHERE o.orphanage_id = %s
        """, (orphanage_id,))
        orphanage = cursor.fetchone()

        cursor.close()
        conn.close()

        if orphanage:
            return jsonify(orphanage), 200
        else:
            return jsonify({"error": "Orphanage not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
