import os
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS 설정 강화
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

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

def create_employees_table():
    """employees 테이블 생성"""
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if not connection:
            logger.error("Database connection failed during table creation")
            return False
        
        cursor = connection.cursor()
        
        # employees 테이블 생성 쿼리
        create_table_query = """
        CREATE TABLE IF NOT EXISTS employees (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            department VARCHAR(100) DEFAULT 'Unknown',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(create_table_query)
        logger.info("employees table created successfully or already exists")
        
        # 인덱스 생성 (성능 향상을 위해)
        create_index_query = """
        CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(email);
        """
        cursor.execute(create_index_query)
        
        create_index_query2 = """
        CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department);
        """
        cursor.execute(create_index_query2)
        
        logger.info("employees table indexes created successfully")
        return True
        
    except Error as e:
        logger.error(f"Error creating employees table: {e}")
        return False
    
    finally:
        close_db_connection(connection, cursor)

def initialize_database():
    """데이터베이스 초기화"""
    logger.info("Initializing database...")
    
    if create_employees_table():
        logger.info("Database initialization completed successfully")
    else:
        logger.error("Database initialization failed")

@app.route("/")
def main():
    return "Welcome!"

# UI 라우트 추가
@app.route('/ui')
def ui():
    return render_template('index.html')

@app.route('/how-are-you')
def hello():
    return 'I am good, how about you?'

@app.route('/init-db')
def init_database():
    """데이터베이스 초기화 엔드포인트"""
    try:
        if create_employees_table():
            return jsonify({"message": "Database initialized successfully"}), 200
        else:
            return jsonify({"error": "Database initialization failed"}), 500
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return jsonify({"error": "Database initialization failed"}), 500

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

@app.route('/add-employee', methods=['POST'])
def add_employee():
    """직원 데이터 추가"""
    connection = None
    cursor = None
    
    try:
        # 요청 데이터 검증
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        name = data.get('name')
        email = data.get('email')
        department = data.get('department', 'Unknown')
        
        if not name or not email:
            return jsonify({"error": "Name and email are required"}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = connection.cursor()
        
        # 직원 데이터 삽입
        insert_query = """
            INSERT INTO employees (name, email, department) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (name, email, department))
        
        # 삽입된 직원의 ID 가져오기
        employee_id = cursor.lastrowid
        
        logger.info(f"Added employee: {name} ({email}) with ID: {employee_id}")
        
        return jsonify({
            "message": "Employee added successfully",
            "employee_id": employee_id,
            "name": name,
            "email": email,
            "department": department
        }), 201
        
    except mysql.connector.IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        return jsonify({"error": "Email already exists"}), 409
    
    except Error as e:
        logger.error(f"Database query error: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
    finally:
        close_db_connection(connection, cursor)

@app.route('/add-employee-simple', methods=['GET'])
def add_employee_simple():
    """간단한 직원 데이터 추가 (GET 요청으로 테스트용)"""
    connection = None
    cursor = None
    
    try:
        # URL 파라미터에서 데이터 가져오기
        name = request.args.get('name', 'Test User')
        email = request.args.get('email', f'test{len(str(hash(name)))}@example.com')
        department = request.args.get('department', 'IT')
        
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = connection.cursor()
        
        # 직원 데이터 삽입
        insert_query = """
            INSERT INTO employees (name, email, department) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (name, email, department))
        
        # 삽입된 직원의 ID 가져오기
        employee_id = cursor.lastrowid
        
        logger.info(f"Added employee: {name} ({email}) with ID: {employee_id}")
        
        return jsonify({
            "message": "Employee added successfully",
            "employee_id": employee_id,
            "name": name,
            "email": email,
            "department": department
        }), 201
        
    except mysql.connector.IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        return jsonify({"error": "Email already exists"}), 409
    
    except Error as e:
        logger.error(f"Database query error: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    finally:
        close_db_connection(connection, cursor)

@app.route('/add-multiple-employees', methods=['POST'])
def add_multiple_employees():
    """여러 직원 데이터 한 번에 추가"""
    connection = None
    cursor = None
    
    try:
        data = request.get_json()
        if not data or 'employees' not in data:
            return jsonify({"error": "No employees data provided"}), 400
        
        employees = data['employees']
        if not isinstance(employees, list):
            return jsonify({"error": "Employees must be a list"}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = connection.cursor()
        
        # 여러 직원 데이터 삽입
        insert_query = """
            INSERT INTO employees (name, email, department) 
            VALUES (%s, %s, %s)
        """
        
        employee_data = []
        for emp in employees:
            if not emp.get('name') or not emp.get('email'):
                continue
            employee_data.append((
                emp['name'],
                emp['email'],
                emp.get('department', 'Unknown')
            ))
        
        if not employee_data:
            return jsonify({"error": "No valid employee data provided"}), 400
        
        cursor.executemany(insert_query, employee_data)
        
        logger.info(f"Added {len(employee_data)} employees")
        
        return jsonify({
            "message": f"Successfully added {len(employee_data)} employees",
            "count": len(employee_data)
        }), 201
        
    except mysql.connector.IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        return jsonify({"error": "One or more emails already exist"}), 409
    
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
    # 애플리케이션 시작 시 데이터베이스 초기화
    initialize_database()
    
    # 개발 환경에서만 debug=True 사용
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)