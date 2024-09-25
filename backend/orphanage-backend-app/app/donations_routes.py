from flask import Blueprint, request, jsonify  # type: ignore
import mysql.connector  # type: ignore
from app.config import Config
import jwt

# Secret key for decoding JWT
SECRET_KEY = 'your_secret_key'

# Create a Blueprint for orphan routes
donations = Blueprint('donations', __name__)


# Use the config values for the MySQL connection
db_config = {
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'host': Config.MYSQL_HOST,
    'database': Config.MYSQL_DATABASE
}

# A route for the organization to add donation info 
@donations.route('/add-donation-info', methods=['POST'])
def add_donation_info():
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

        # Get donation data from the request
        data = request.json
        donation_method = data['donation_method']
        donation_details = data['donation_details']

        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Insert donation information into the donations table
        cursor.execute("""
            INSERT INTO donations (orphanage_id, donation_method, donation_details)
            VALUES (%s, %s, %s)
        """, (orphanage_id, donation_method, donation_details))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Donation information added successfully!"}), 201

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# A route that shows the donation information for the organization
@donations.route('/orphanage/<int:orphanage_id>/donations', methods=['GET'])
def get_donation_info(orphanage_id):
    try:
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch the donation information for the orphanage
        cursor.execute("""
            SELECT donation_method, donation_details
            FROM donations
            WHERE orphanage_id = %s
        """, (orphanage_id,))
        donation_info = cursor.fetchone()

        # If no donation information is found, return a 404 error
        if not donation_info:
            return jsonify({"error": "No donation information found for this orphanage"}), 404

        cursor.close()
        conn.close()

        return jsonify(donation_info), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
