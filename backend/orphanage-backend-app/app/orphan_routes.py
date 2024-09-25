from flask import Blueprint, request, jsonify  # type: ignore
import mysql.connector  # type: ignore
from app.config import Config
import jwt


# Secret key for decoding JWT
SECRET_KEY = 'your_secret_key'

# Create a Blueprint for orphan routes
orphans = Blueprint('orphans', __name__)

# Use the config values for the MySQL connection
db_config = {
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'host': Config.MYSQL_HOST,
    'database': Config.MYSQL_DATABASE
}

@orphans.route('/orphanage-status', methods=['GET'])
def get_orphanage_status():
    try:
        # Get the token from the Authorization header
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        # Decode the token to get orphanage_id
        try:
            decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            orphanage_id = decoded_token['orphanage_id']  # Corrected key name
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        # Connect to the database to check the orphanage's verification status
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch orphanage status from orphanage_verification table
        cursor.execute("""
            SELECT status, rejection_reason
            FROM orphanage_verification
            WHERE orphanage_id = %s
        """, (orphanage_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return jsonify(result), 200
        else:
            return jsonify({"error": "Orphanage not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Route to add children for a specific orphanage
@orphans.route('/add-child', methods=['POST'])
def add_child():
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

        # Get the child data from the POST request
        data = request.json
        name = data['name']
        age = data['age']
        image_url = data.get('image_url', '')  # Optional field
        about = data.get('about', '')  # Optional about field
        hobby_ids = data.get('hobbies', [])  # List of hobby IDs

        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Insert the child into the children table, linking them to the orphanage
        cursor.execute("""
            INSERT INTO children (orphanage_id, name, age, image_url, about)
            VALUES (%s, %s, %s, %s, %s)
        """, (orphanage_id, name, age, image_url, about))

        # Get the last inserted child ID
        child_id = cursor.lastrowid

        # Insert the hobbies for the child into the child_hobbies table
        if hobby_ids:
            for hobby_id in hobby_ids:
                cursor.execute("INSERT INTO child_hobbies (child_id, hobby_id) VALUES (%s, %s)", (child_id, hobby_id))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Child added successfully with hobbies!"}), 201

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to get all children for a specific orphanage
@orphans.route('/get-children', methods=['GET'])
def get_children():
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

        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch all children connected to this orphanage
        cursor.execute("SELECT * FROM children WHERE orphanage_id = %s", (orphanage_id,))
        children = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(children), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to get child for a specific orphanage by id
@orphans.route('/child/<int:child_id>', methods=['GET'])
def get_child_by_id(child_id):
    try:
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch the child details by ID
        cursor.execute("SELECT * FROM children WHERE id = %s", (child_id,))
        child = cursor.fetchone()

        # If the child does not exist, return a 404 error
        if not child:
            return jsonify({"error": "Child not found"}), 404

        # Fetch the hobbies linked to this child
        cursor.execute("""
            SELECT h.name FROM hobbies h
            JOIN child_hobbies ch ON h.id = ch.hobby_id
            WHERE ch.child_id = %s
        """, (child_id,))
        hobbies = cursor.fetchall()

        # Add the hobbies to the child's data
        child['hobbies'] = [hobby['name'] for hobby in hobbies]

        cursor.close()
        conn.close()

        return jsonify(child), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Route to get all hobbies
@orphans.route('/hobbies', methods=['GET'])
def get_hobbies():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch all hobbies from the hobbies table
        cursor.execute("SELECT * FROM hobbies")
        hobbies = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(hobbies), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to get all guest express-interest submissions related to this orphanage
@orphans.route('/submissions', methods=['GET'])
def get_orphanage_submissions():
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

        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch all express-interest submissions related to this orphanage
        cursor.execute("""
            SELECT r.id, r.child_id, c.name AS child_name, r.guest_name, r.guest_email, r.interest_type, r.message, r.created_at
            FROM adoption_sponsorship_requests r
            LEFT JOIN children c ON r.child_id = c.id
            WHERE r.orphanage_id = %s
        """, (orphanage_id,))

        submissions = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(submissions), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
