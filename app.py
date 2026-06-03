import sqlite3
import os
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static')
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'homevault.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS room (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS category (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            purchase_date TEXT DEFAULT '',
            price REAL DEFAULT 0,
            room_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS item_category (
            item_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (item_id, category_id),
            FOREIGN KEY (item_id) REFERENCES item(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE CASCADE
        );
    ''')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ===== Room CRUD =====

@app.route('/api/rooms', methods=['GET'])
def list_rooms():
    conn = get_db()
    rooms = conn.execute('SELECT * FROM room ORDER BY created_at DESC').fetchall()
    result = []
    for r in rooms:
        item_count = conn.execute('SELECT COUNT(*) as c FROM item WHERE room_id=?', (r['id'],)).fetchone()['c']
        result.append({**dict(r), 'item_count': item_count})
    conn.close()
    return jsonify(result)


@app.route('/api/rooms', methods=['POST'])
def create_room():
    data = request.json
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '房间名称不能为空'}), 400
    conn = get_db()
    cur = conn.execute('INSERT INTO room (name, description) VALUES (?, ?)',
                       (data['name'].strip(), data.get('description', '')))
    conn.commit()
    room = conn.execute('SELECT * FROM room WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(room)), 201


@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    conn = get_db()
    room = conn.execute('SELECT * FROM room WHERE id=?', (room_id,)).fetchone()
    if not room:
        conn.close()
        return jsonify({'error': '房间不存在'}), 404
    items = conn.execute('SELECT * FROM item WHERE room_id=?', (room_id,)).fetchall()
    conn.close()
    return jsonify({**dict(room), 'items': [dict(i) for i in items]})


@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
def update_room(room_id):
    data = request.json
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '房间名称不能为空'}), 400
    conn = get_db()
    conn.execute('UPDATE room SET name=?, description=? WHERE id=?',
                 (data['name'].strip(), data.get('description', ''), room_id))
    conn.commit()
    room = conn.execute('SELECT * FROM room WHERE id=?', (room_id,)).fetchone()
    conn.close()
    if not room:
        return jsonify({'error': '房间不存在'}), 404
    return jsonify(dict(room))


@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    conn = get_db()
    conn.execute('DELETE FROM room WHERE id=?', (room_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})


# ===== Category CRUD =====

@app.route('/api/categories', methods=['GET'])
def list_categories():
    conn = get_db()
    categories = conn.execute('SELECT * FROM category ORDER BY created_at DESC').fetchall()
    result = []
    for c in categories:
        item_count = conn.execute('SELECT COUNT(*) as cnt FROM item_category WHERE category_id=?', (c['id'],)).fetchone()['cnt']
        result.append({**dict(c), 'item_count': item_count})
    conn.close()
    return jsonify(result)


@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.json
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '分类名称不能为空'}), 400
    conn = get_db()
    cur = conn.execute('INSERT INTO category (name, description) VALUES (?, ?)',
                       (data['name'].strip(), data.get('description', '')))
    conn.commit()
    cat = conn.execute('SELECT * FROM category WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(cat)), 201


@app.route('/api/categories/<int:cat_id>', methods=['GET'])
def get_category(cat_id):
    conn = get_db()
    cat = conn.execute('SELECT * FROM category WHERE id=?', (cat_id,)).fetchone()
    if not cat:
        conn.close()
        return jsonify({'error': '分类不存在'}), 404
    items = conn.execute('''
        SELECT i.* FROM item i
        JOIN item_category ic ON i.id = ic.item_id
        WHERE ic.category_id = ?
    ''', (cat_id,)).fetchall()
    conn.close()
    return jsonify({**dict(cat), 'items': [dict(i) for i in items]})


@app.route('/api/categories/<int:cat_id>', methods=['PUT'])
def update_category(cat_id):
    data = request.json
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '分类名称不能为空'}), 400
    conn = get_db()
    conn.execute('UPDATE category SET name=?, description=? WHERE id=?',
                 (data['name'].strip(), data.get('description', ''), cat_id))
    conn.commit()
    cat = conn.execute('SELECT * FROM category WHERE id=?', (cat_id,)).fetchone()
    conn.close()
    if not cat:
        return jsonify({'error': '分类不存在'}), 404
    return jsonify(dict(cat))


@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    conn = get_db()
    conn.execute('DELETE FROM category WHERE id=?', (cat_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})


# ===== Item CRUD =====

@app.route('/api/items', methods=['GET'])
def list_items():
    conn = get_db()
    items = conn.execute('''
        SELECT i.*, r.name as room_name FROM item i
        LEFT JOIN room r ON i.room_id = r.id
        ORDER BY i.created_at DESC
    ''').fetchall()
    result = []
    for item in items:
        cats = conn.execute('''
            SELECT c.id, c.name FROM category c
            JOIN item_category ic ON c.id = ic.category_id
            WHERE ic.item_id = ?
        ''', (item['id'],)).fetchall()
        result.append({**dict(item), 'categories': [dict(c) for c in cats]})
    conn.close()
    return jsonify(result)


@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.json
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '物品名称不能为空'}), 400
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO item (name, description, purchase_date, price, room_id) VALUES (?, ?, ?, ?, ?)',
        (data['name'].strip(), data.get('description', ''),
         data.get('purchase_date', ''), data.get('price', 0),
         data.get('room_id') or None))
    item_id = cur.lastrowid
    category_ids = data.get('category_ids', [])
    for cat_id in category_ids:
        conn.execute('INSERT OR IGNORE INTO item_category (item_id, category_id) VALUES (?, ?)',
                     (item_id, cat_id))
    conn.commit()
    item = conn.execute('SELECT * FROM item WHERE id=?', (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(item)), 201


@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    conn = get_db()
    item = conn.execute('''
        SELECT i.*, r.name as room_name FROM item i
        LEFT JOIN room r ON i.room_id = r.id
        WHERE i.id=?
    ''', (item_id,)).fetchone()
    if not item:
        conn.close()
        return jsonify({'error': '物品不存在'}), 404
    cats = conn.execute('''
        SELECT c.id, c.name FROM category c
        JOIN item_category ic ON c.id = ic.category_id
        WHERE ic.item_id = ?
    ''', (item_id,)).fetchall()
    conn.close()
    return jsonify({**dict(item), 'categories': [dict(c) for c in cats]})


@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.json
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '物品名称不能为空'}), 400
    conn = get_db()
    conn.execute('''
        UPDATE item SET name=?, description=?, purchase_date=?, price=?, room_id=?
        WHERE id=?
    ''', (data['name'].strip(), data.get('description', ''),
          data.get('purchase_date', ''), data.get('price', 0),
          data.get('room_id') or None, item_id))
    conn.execute('DELETE FROM item_category WHERE item_id=?', (item_id,))
    for cat_id in data.get('category_ids', []):
        conn.execute('INSERT OR IGNORE INTO item_category (item_id, category_id) VALUES (?, ?)',
                     (item_id, cat_id))
    conn.commit()
    item = conn.execute('SELECT * FROM item WHERE id=?', (item_id,)).fetchone()
    conn.close()
    if not item:
        return jsonify({'error': '物品不存在'}), 404
    return jsonify(dict(item))


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_db()
    conn.execute('DELETE FROM item WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
