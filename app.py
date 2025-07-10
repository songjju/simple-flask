import os
from flask import Flask, jsonify
import mysql.connector
from mysql.connector import Error
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# MySQL 설정
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_DATABASE_HOST', 'localhost'),
    'user': os.environ.get('MYSQL_DATABASE_USER', 'db_user'),
    'password': os.environ.get('MYSQL_DATABASE_PASSWORD', 'Passw0rd'),
    'database': os.environ.get('MYSQL_DATABASE_DB', 'employee_db'),
    'port': int(os.environ.get('MYSQL_DATABASE_PORT', '3306')),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True,
    'connection_timeout': 10
}

def get_db_connection():
    """MySQL 연결을 생성하고 반환"""
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        logger.error(f"Database connection error: {e}")
        return None

def close_db_connection(connection, cursor=None):
    """MySQL 연결을 안전하게 닫기"""
    try:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
    except Error as e:
        logger.error(f"Error closing database connection: {e}")

@app.route("/")
def main():
    return "Welcome!"

@app.route('/how-are-you')
def hello():
    return 'I am good, how about you?'

@app.route('/read-from-database')
def read():
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM employees")
        
        # 모든 결과를 한 번에 가져오기
        rows = cursor.fetchall()
        
        if not rows:
            return jsonify({"message": "No employees found"}), 404
        
        # 첫 번째 컬럼만 추출
        result = [str(row[0]) for row in rows]
        
        return ",".join(result)
        
    except Error as e:
        logger.error(f"Database query error: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    finally:
        close_db_connection(connection, cursor)

@app.route('/read-from-database-json')
def read_json():
    """JSON 형태로 직원 데이터 반환"""
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM employees")
        
        rows = cursor.fetchall()
        
        if not rows:
            return jsonify({"message": "No employees found"}), 404
        
        return jsonify({"employees": rows})
        
    except Error as e:
        logger.error(f"Database query error: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    finally:
        close_db_connection(connection, cursor)

@app.route('/health')
def health_check():
    """애플리케이션 상태 확인"""
    connection = None
    
    try:
        connection = get_db_connection()
        if connection:
            return jsonify({"status": "healthy", "database": "connected"})
        else:
            return jsonify({"status": "unhealthy", "database": "disconnected"}), 500
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
    
    finally:
        if connection:
            close_db_connection(connection)

if __name__ == "__main__":
    # 개발 환경에서만 debug=True 사용
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)