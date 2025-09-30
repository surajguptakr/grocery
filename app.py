from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app, supports_credentials=True)

# Database initialization
def init_db():
    conn = sqlite3.connect('grocery_store.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Customers table
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        email TEXT,
        address TEXT,
        total_borrowed REAL DEFAULT 0,
        total_repaid REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Products table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL,
        low_stock_threshold INTEGER DEFAULT 20,
        unit TEXT DEFAULT 'piece',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Borrow/Repay transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )''')
    
    # Sales table
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        total_amount REAL NOT NULL,
        payment_status TEXT DEFAULT 'paid',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )''')
    
    # Sale items table
    c.execute('''CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    
    # Notifications table
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        customer_id INTEGER,
        message TEXT NOT NULL,
        type TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )''')
    
    # Insert default users
    try:
        c.execute("INSERT INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
                  ('owner', generate_password_hash('owner123'), 'owner', 'Store Owner'))
        c.execute("INSERT INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
                  ('staff1', generate_password_hash('staff123'), 'staff', 'John Staff'))
    except sqlite3.IntegrityError:
        pass
    
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
        ('Sugar (1kg)', 'Grains', 45, 80, 20, 'kg'),
        ('Salt (1kg)', 'Spices', 20, 100, 25, 'kg'),
    ]
    
    for product in sample_products:
        try:
            c.execute("INSERT INTO products (name, category, price, stock, low_stock_threshold, unit) VALUES (?, ?, ?, ?, ?, ?)", product)
        except sqlite3.IntegrityError:
            pass
    
    # Insert sample customers
    sample_customers = [
        ('Rajesh Kumar', '9876543210', 'rajesh@email.com', '123 Main St', 1500, 800),
        ('Priya Sharma', '9876543211', 'priya@email.com', '456 Park Ave', 2000, 2000),
        ('Amit Patel', '9876543212', 'amit@email.com', '789 Gandhi Road', 500, 0),
    ]
    
    for customer in sample_customers:
        try:
            c.execute("INSERT INTO customers (name, phone, email, address, total_borrowed, total_repaid) VALUES (?, ?, ?, ?, ?, ?)", customer)
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()

# Database helper
def get_db():
    conn = sqlite3.connect('grocery_store.db')
    conn.row_factory = sqlite3.Row
    return conn

# Authentication APIs
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
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
        user = conn.execute('SELECT id, username, role, name FROM users WHERE id = ?', 
                           (session['user_id'],)).fetchone()
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
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    if search:
        query += ' AND name LIKE ?'
        params.append(f'%{search}%')
    
    query += ' ORDER BY category, name'
    products = conn.execute(query, params).fetchall()
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
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (data['name'], data['category'], data['price'], data['stock'], 
               data.get('low_stock_threshold', 20), data.get('unit', 'piece')))
    conn.commit()
    product_id = c.lastrowid
    conn.close()
    
    return jsonify({'success': True, 'id': product_id})

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    if session.get('role') not in ['owner', 'staff']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    conn = get_db()
    conn.execute('''UPDATE products SET name=?, category=?, price=?, stock=?, 
                    low_stock_threshold=?, unit=? WHERE id=?''',
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
    conn.execute('DELETE FROM products WHERE id=?', (product_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/products/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    categories = conn.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()
    conn.close()
    return jsonify([c['category'] for c in categories])

@app.route('/api/products/low-stock', methods=['GET'])
def get_low_stock():
    conn = get_db()
    products = conn.execute('''SELECT * FROM products 
                               WHERE stock <= low_stock_threshold 
                               ORDER BY stock ASC''').fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

# Customers APIs
@app.route('/api/customers', methods=['GET'])
def get_customers():
    conn = get_db()
    customers = conn.execute('SELECT * FROM customers ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(c) for c in customers])

@app.route('/api/customers', methods=['POST'])
def add_customer():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO customers (name, phone, email, address)
                 VALUES (?, ?, ?, ?)''',
              (data['name'], data['phone'], data.get('email'), data.get('address')))
    conn.commit()
    customer_id = c.lastrowid
    conn.close()
    
    return jsonify({'success': True, 'id': customer_id})

@app.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    conn = get_db()
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (customer_id,)).fetchone()
    
    if not customer:
        conn.close()
        return jsonify({'error': 'Customer not found'}), 404
    
    transactions = conn.execute('''SELECT * FROM transactions 
                                   WHERE customer_id=? 
                                   ORDER BY created_at DESC''', 
                                (customer_id,)).fetchall()
    conn.close()
    
    return jsonify({
        'customer': dict(customer),
        'transactions': [dict(t) for t in transactions]
    })

# Transactions APIs (Borrow/Repay)
@app.route('/api/transactions/borrow', methods=['POST'])
def add_borrow():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    # Add transaction
    c.execute('''INSERT INTO transactions (customer_id, transaction_type, amount, description, created_by)
                 VALUES (?, 'borrow', ?, ?, ?)''',
              (data['customer_id'], data['amount'], data.get('description'), session.get('user_id')))
    
    # Update customer balance
    c.execute('''UPDATE customers SET total_borrowed = total_borrowed + ? 
                 WHERE id = ?''', (data['amount'], data['customer_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/transactions/repay', methods=['POST'])
def add_repayment():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    # Add transaction
    c.execute('''INSERT INTO transactions (customer_id, transaction_type, amount, description, created_by)
                 VALUES (?, 'repay', ?, ?, ?)''',
              (data['customer_id'], data['amount'], data.get('description'), session.get('user_id')))
    
    # Update customer balance
    c.execute('''UPDATE customers SET total_repaid = total_repaid + ? 
                 WHERE id = ?''', (data['amount'], data['customer_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# Sales APIs
@app.route('/api/sales', methods=['POST'])
def create_sale():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    # Create sale
    c.execute('''INSERT INTO sales (customer_id, total_amount, payment_status, created_by)
                 VALUES (?, ?, ?, ?)''',
              (data.get('customer_id'), data['total_amount'], 
               data.get('payment_status', 'paid'), session.get('user_id')))
    sale_id = c.lastrowid
    
    # Add sale items and update stock
    for item in data['items']:
        c.execute('''INSERT INTO sale_items (sale_id, product_id, quantity, price)
                     VALUES (?, ?, ?, ?)''',
                  (sale_id, item['product_id'], item['quantity'], item['price']))
        
        c.execute('UPDATE products SET stock = stock - ? WHERE id = ?',
                  (item['quantity'], item['product_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'sale_id': sale_id})

# Analytics APIs
@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    conn = get_db()
    
    # Total sales today
    today_sales = conn.execute('''SELECT COALESCE(SUM(total_amount), 0) as total
                                  FROM sales 
                                  WHERE DATE(created_at) = DATE('now')''').fetchone()
    
    # Total outstanding debt
    outstanding = conn.execute('''SELECT COALESCE(SUM(total_borrowed - total_repaid), 0) as total
                                  FROM customers''').fetchone()
    
    # Low stock count
    low_stock_count = conn.execute('''SELECT COUNT(*) as count
                                      FROM products 
                                      WHERE stock <= low_stock_threshold''').fetchone()
    
    # Total customers
    customer_count = conn.execute('SELECT COUNT(*) as count FROM customers').fetchone()
    
    # Recent transactions
    recent_transactions = conn.execute('''SELECT t.*, c.name as customer_name
                                          FROM transactions t
                                          JOIN customers c ON t.customer_id = c.id
                                          ORDER BY t.created_at DESC
                                          LIMIT 10''').fetchall()
    
    conn.close()
    
    return jsonify({
        'today_sales': today_sales['total'],
        'outstanding_debt': outstanding['total'],
        'low_stock_count': low_stock_count['count'],
        'customer_count': customer_count['count'],
        'recent_transactions': [dict(t) for t in recent_transactions]
    })

# Notifications API
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    conn = get_db()
    notifications = conn.execute('''SELECT * FROM notifications 
                                    WHERE user_id = ? OR user_id IS NULL
                                    ORDER BY created_at DESC 
                                    LIMIT 50''', 
                                 (session.get('user_id'),)).fetchall()
    conn.close()
    return jsonify([dict(n) for n in notifications])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)