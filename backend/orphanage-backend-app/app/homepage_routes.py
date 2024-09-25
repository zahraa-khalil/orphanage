from flask import Blueprint, request, jsonify  # type: ignore
import mysql.connector  # type: ignore
from app.config import Config
import jwt

# Secret key for decoding JWT
SECRET_KEY = 'your_secret_key'

# Create a Blueprint for orphan routes
homePage = Blueprint('homePage', __name__)

# Use the config values for the MySQL connection
db_config = {
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'host': Config.MYSQL_HOST,
    'database': Config.MYSQL_DATABASE
}

@homePage.route('/children', methods=['GET'])
def get_all_children():
    try:
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Query to fetch all children from approved orphanages only
        cursor.execute("""
            SELECT c.id, c.name, c.age, c.image_url, c.about, c.orphanage_id, o.name as orphanage_name
            FROM children c
            JOIN users o ON c.orphanage_id = o.id
            JOIN orphanage_verification ov ON c.orphanage_id = ov.orphanage_id
            WHERE ov.status = 'approved'
        """)

        children = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(children), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@homePage.route('/children/<int:child_id>', methods=['GET'])
def get_child_by_id(child_id):
    try:
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Query to fetch child details by child_id, joining with orphanage (if needed)
        cursor.execute("""
            SELECT c.id, c.name, c.age, c.image_url, c.about, c.orphanage_id, o.name as orphanage_name
            FROM children c
            JOIN users o ON c.orphanage_id = o.id
            WHERE c.id = %s
        """, (child_id,))

        child = cursor.fetchone()

        # If no child is found, return a 404 error
        if not child:
            return jsonify({"error": "Child not found"}), 404

        # Fetch the hobbies associated with the child (if needed)
        cursor.execute("""
            SELECT h.name FROM hobbies h
            JOIN child_hobbies ch ON h.id = ch.hobby_id
            WHERE ch.child_id = %s
        """, (child_id,))
        hobbies = cursor.fetchall()

        # Add hobbies to the child data
        child['hobbies'] = [hobby['name'] for hobby in hobbies]

        cursor.close()
        conn.close()

        return jsonify(child), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Guest Insert the their interest into the adoption_sponsorship_requests table
@homePage.route('/express-interest', methods=['POST'])
def express_interest():
    try:
        # Get the request data
        data = request.json
        orphanage_id = data['orphanage_id']  # Mandatory field
        guest_name = data['guest_name']
        guest_email = data['guest_email']
        interest_type = data['interest_type']  # 'adoption' or 'sponsorship'
        message = data.get('message', '')  # Optional message
        child_id = data.get('child_id', None)  # Optional child_id, default is None

        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Insert the guest's interest into the adoption_sponsorship_requests table
        cursor.execute("""
            INSERT INTO adoption_sponsorship_requests (child_id, orphanage_id, guest_name, guest_email, interest_type, message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (child_id, orphanage_id, guest_name, guest_email, interest_type, message))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Interest request submitted successfully!"}), 201

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
