import os
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import secrets

app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# CORS - Update after getting your Render URLs
ALLOWED_ORIGINS = [
    'https://grocery-store-frontend.onrender.com',  # Add your actual frontend URL
    'https://*.onrender.com',
    'http://localhost:8000'
]


CORS(app, 
     origins=ALLOWED_ORIGINS,
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# Database initialization
def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Customers table
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        email TEXT,
        address TEXT,
        total_borrowed DECIMAL(10,2) DEFAULT 0,
        total_repaid DECIMAL(10,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Products table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        stock INTEGER NOT NULL,
        low_stock_threshold INTEGER DEFAULT 20,
        unit TEXT DEFAULT 'piece',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        description TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )''')
    
    # Sales table
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER,
        total_amount DECIMAL(10,2) NOT NULL,
        payment_status TEXT DEFAULT 'paid',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )''')
    
    # Sale items table
    c.execute('''CREATE TABLE IF NOT EXISTS sale_items (
        id SERIAL PRIMARY KEY,
        sale_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
    )''')
    
    # Insert default users
    try:
        c.execute("INSERT INTO users (username, password, role, name) VALUES (%s, %s, %s, %s)",
                  ('owner', generate_password_hash('owner123'), 'owner', 'Store Owner'))
        c.execute("INSERT INTO users (username, password, role, name) VALUES (%s, %s, %s, %s)",
                  ('staff1', generate_password_hash('staff123'), 'staff', 'John Staff'))
    except Exception as e:
        print(f"Users already exist or error: {e}")
    
    # Insert sample products
    sample_products = [
        ('Rice (1kg)', 'Grains', 60, 100, 20, 'kg'),
        ('Wheat Flour (1kg)', 'Grains', 45, 80, 15, 'kg'),
        ('Milk (1L)', 'Dairy', 55, 15, 20, 'liter'),
        ('Paneer (200g)', 'Dairy', 80, 25, 10, 'pack'),
        ('Tomatoes (1kg)', 'Vegetables', 40, 50, 15, 'kg'),
        ('Onions (1kg)', 'Vegetables', 35, 60, 20, 'kg'),
        ('Potatoes (1kg)', 'Vegetables', 30, 70, 25, 'kg'),
        ('Bread', 'Bakery', 25, 40, 15, 'piece'),
        ('Biscuits', 'Snacks', 20, 100, 30, 'pack'),
        ('Tea (250g)', 'Beverages', 150, 50, 10, 'pack'),
    ]
    
    for product in sample_products:
        try:
            c.execute("INSERT INTO products (name, category, price, stock, low_stock_threshold, unit) VALUES (%s, %s, %s, %s, %s, %s)", product)
        except Exception as e:
            print(f"Product exists or error: {e}")
    
    # Insert sample customers
    sample_customers = [
        ('Rajesh Kumar', '9876543210', 'rajesh@email.com', '123 Main St', 1500, 800),
        ('Priya Sharma', '9876543211', 'priya@email.com', '456 Park Ave', 2000, 2000),
        ('Amit Patel', '9876543212', 'amit@email.com', '789 Gandhi Road', 500, 0),
    ]
    
    for customer in sample_customers:
        try:
            c.execute("INSERT INTO customers (name, phone, email, address, total_borrowed, total_repaid) VALUES (%s, %s, %s, %s, %s, %s)", customer)
        except Exception as e:
            print(f"Customer exists or error: {e}")
    
    conn.commit()
    conn.close()

# Health check endpoint
@app.route('/')
def home():
    return jsonify({'message': 'Grocery Store API is running!', 'status': 'ok'})

# Authentication APIs
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['role'] = user['role']
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'name': user['name']
            }
        })
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, username, role, name FROM users WHERE id = %s', (session['user_id'],))
        user = c.fetchone()
        conn.close()
        return jsonify({
            'authenticated': True,
            'user': dict(user)
        })
    return jsonify({'authenticated': False}), 401

# Products APIs
@app.route('/api/products', methods=['GET'])
def get_products():
    category = request.args.get('category')
    search = request.args.get('search')
    
    conn = get_db()
    c = conn.cursor()
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if category:
        query += ' AND category = %s'
        params.append(category)
    
    if search:
        query += ' AND name ILIKE %s'
        params.append(f'%{search}%')
    
    query += ' ORDER BY category, name'
    c.execute(query, params)
    products = c.fetchall()
    conn.close()
    
    return jsonify([dict(p) for p in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    if session.get('role') not in ['owner', 'staff']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO products (name, category, price, stock, low_stock_threshold, unit)
                 VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
              (data['name'], data['category'], data['price'], data['stock'], 
               data.get('low_stock_threshold', 20), data.get('unit', 'piece')))
    product_id = c.fetchone()['id']
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': product_id})

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    if session.get('role') not in ['owner', 'staff']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('''UPDATE products SET name=%s, category=%s, price=%s, stock=%s, 
                    low_stock_threshold=%s, unit=%s WHERE id=%s''',
                 (data['name'], data['category'], data['price'], data['stock'],
                  data['low_stock_threshold'], data['unit'], product_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    if session.get('role') != 'owner':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM products WHERE id=%s', (product_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/products/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT DISTINCT category FROM products ORDER BY category')
    categories = c.fetchall()
    conn.close()
    return jsonify([c['category'] for c in categories])

@app.route('/api/products/low-stock', methods=['GET'])
def get_low_stock():
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT * FROM products 
                 WHERE stock <= low_stock_threshold 
                 ORDER BY stock ASC''')
    products = c.fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

# Customers APIs
@app.route('/api/customers', methods=['GET'])
def get_customers():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM customers ORDER BY name')
    customers = c.fetchall()
    conn.close()
    return jsonify([dict(c) for c in customers])

@app.route('/api/customers', methods=['POST'])
def add_customer():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO customers (name, phone, email, address)
                 VALUES (%s, %s, %s, %s) RETURNING id''',
              (data['name'], data['phone'], data.get('email'), data.get('address')))
    customer_id = c.fetchone()['id']
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': customer_id})

@app.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM customers WHERE id=%s', (customer_id,))
    customer = c.fetchone()
    
    if not customer:
        conn.close()
        return jsonify({'error': 'Customer not found'}), 404
    
    c.execute('''SELECT * FROM transactions 
                 WHERE customer_id=%s 
                 ORDER BY created_at DESC''', (customer_id,))
    transactions = c.fetchall()
    conn.close()
    
    return jsonify({
        'customer': dict(customer),
        'transactions': [dict(t) for t in transactions]
    })

# Transactions APIs
@app.route('/api/transactions/borrow', methods=['POST'])
def add_borrow():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''INSERT INTO transactions (customer_id, transaction_type, amount, description, created_by)
                 VALUES (%s, 'borrow', %s, %s, %s)''',
              (data['customer_id'], data['amount'], data.get('description'), session.get('user_id')))
    
    c.execute('''UPDATE customers SET total_borrowed = total_borrowed + %s 
                 WHERE id = %s''', (data['amount'], data['customer_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/transactions/repay', methods=['POST'])
def add_repayment():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''INSERT INTO transactions (customer_id, transaction_type, amount, description, created_by)
                 VALUES (%s, 'repay', %s, %s, %s)''',
              (data['customer_id'], data['amount'], data.get('description'), session.get('user_id')))
    
    c.execute('''UPDATE customers SET total_repaid = total_repaid + %s 
                 WHERE id = %s''', (data['amount'], data['customer_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# Analytics APIs
@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''SELECT COALESCE(SUM(total_amount), 0) as total
                 FROM sales 
                 WHERE DATE(created_at) = CURRENT_DATE''')
    today_sales = c.fetchone()
    
    c.execute('''SELECT COALESCE(SUM(total_borrowed - total_repaid), 0) as total
                 FROM customers''')
    outstanding = c.fetchone()
    
    c.execute('''SELECT COUNT(*) as count
                 FROM products 
                 WHERE stock <= low_stock_threshold''')
    low_stock_count = c.fetchone()
    
    c.execute('SELECT COUNT(*) as count FROM customers')
    customer_count = c.fetchone()
    
    c.execute('''SELECT t.*, c.name as customer_name
                 FROM transactions t
                 JOIN customers c ON t.customer_id = c.id
                 ORDER BY t.created_at DESC
                 LIMIT 10''')
    recent_transactions = c.fetchall()
    
    conn.close()
    
    return jsonify({
        'today_sales': float(today_sales['total']),
        'outstanding_debt': float(outstanding['total']),
        'low_stock_count': low_stock_count['count'],
        'customer_count': customer_count['count'],
        'recent_transactions': [dict(t) for t in recent_transactions]
    })

if __name__ == '__main__':
    if DATABASE_URL:
        init_db()
    port = int(os.environ.get('PORT', 5000))   # default is now 5000
    app.run(host='0.0.0.0', port=port)
