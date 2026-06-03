import os
import uuid
import csv
import io
from datetime import datetime, date
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from models import db, Room, Category, Item, Attachment, item_category

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "homevault.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

db.init_app(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


# ==================== Room API ====================

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = Room.query.order_by(Room.created_at.desc()).all()
    return jsonify([r.to_dict() for r in rooms])


@app.route('/api/rooms', methods=['POST'])
def create_room():
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '房间名称不能为空'}), 400
    room = Room(name=data['name'].strip(), description=data.get('description', '').strip())
    db.session.add(room)
    db.session.commit()
    return jsonify(room.to_dict()), 201


@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    room = Room.query.get_or_404(room_id)
    return jsonify(room.to_dict())


@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
def update_room(room_id):
    room = Room.query.get_or_404(room_id)
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '房间名称不能为空'}), 400
    room.name = data['name'].strip()
    room.description = data.get('description', '').strip()
    db.session.commit()
    return jsonify(room.to_dict())


@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    for item in room.items:
        item.room_id = None
    db.session.delete(room)
    db.session.commit()
    return jsonify({'message': '删除成功'})


# ==================== Category API ====================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.order_by(Category.created_at.desc()).all()
    return jsonify([c.to_dict() for c in categories])


@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '分类名称不能为空'}), 400
    category = Category(name=data['name'].strip(), description=data.get('description', '').strip())
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@app.route('/api/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    category = Category.query.get_or_404(category_id)
    return jsonify(category.to_dict())


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    category = Category.query.get_or_404(category_id)
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '分类名称不能为空'}), 400
    category.name = data['name'].strip()
    category.description = data.get('description', '').strip()
    db.session.commit()
    return jsonify(category.to_dict())


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'message': '删除成功'})


# ==================== Item API ====================

@app.route('/api/items', methods=['GET'])
def get_items():
    query = Item.query

    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(Item.name.ilike(f'%{search}%'))

    room_id = request.args.get('room_id')
    if room_id:
        query = query.filter(Item.room_id == int(room_id))

    category_id = request.args.get('category_id')
    if category_id:
        query = query.join(item_category).filter(item_category.c.category_id == int(category_id))

    items = query.order_by(Item.created_at.desc()).all()
    return jsonify([item.to_dict() for item in items])


@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '物品名称不能为空'}), 400

    item = Item(
        name=data['name'].strip(),
        description=data.get('description', '').strip(),
        room_id=data.get('room_id') or None,
        price=data.get('price') if data.get('price') else None,
        warranty_notes=data.get('warranty_notes', '').strip()
    )

    if data.get('purchase_date'):
        item.purchase_date = date.fromisoformat(data['purchase_date'])
    if data.get('warranty_expires'):
        item.warranty_expires = date.fromisoformat(data['warranty_expires'])

    category_ids = data.get('category_ids', [])
    if category_ids:
        categories = Category.query.filter(Category.id.in_(category_ids)).all()
        item.categories = categories

    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify(item.to_dict())


@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    item = Item.query.get_or_404(item_id)
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '物品名称不能为空'}), 400

    item.name = data['name'].strip()
    item.description = data.get('description', '').strip()
    item.room_id = data.get('room_id') or None
    item.price = data.get('price') if data.get('price') else None
    item.warranty_notes = data.get('warranty_notes', '').strip()
    item.updated_at = datetime.utcnow()

    if data.get('purchase_date'):
        item.purchase_date = date.fromisoformat(data['purchase_date'])
    else:
        item.purchase_date = None

    if data.get('warranty_expires'):
        item.warranty_expires = date.fromisoformat(data['warranty_expires'])
    else:
        item.warranty_expires = None

    category_ids = data.get('category_ids', [])
    categories = Category.query.filter(Category.id.in_(category_ids)).all() if category_ids else []
    item.categories = categories

    db.session.commit()
    return jsonify(item.to_dict())


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    for attachment in item.attachments:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': '删除成功'})


@app.route('/api/items/export', methods=['GET'])
def export_items():
    query = Item.query

    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(Item.name.ilike(f'%{search}%'))

    room_id = request.args.get('room_id')
    if room_id:
        query = query.filter(Item.room_id == int(room_id))

    category_id = request.args.get('category_id')
    if category_id:
        query = query.join(item_category).filter(item_category.c.category_id == int(category_id))

    items = query.order_by(Item.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['名称', '描述', '房间', '分类', '购买日期', '价格', '保修截止日期', '保修备注'])

    for item in items:
        writer.writerow([
            item.name,
            item.description,
            item.room.name if item.room else '',
            ', '.join(c.name for c in item.categories),
            item.purchase_date.isoformat() if item.purchase_date else '',
            item.price if item.price else '',
            item.warranty_expires.isoformat() if item.warranty_expires else '',
            item.warranty_notes
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'homevault_export_{date.today().isoformat()}.csv'
    )


# ==================== Attachment API ====================

@app.route('/api/items/<int:item_id>/attachments', methods=['POST'])
def upload_attachment(item_id):
    item = Item.query.get_or_404(item_id)

    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型'}), 400

    original_filename = secure_filename(file.filename)
    if not original_filename:
        original_filename = file.filename

    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4().hex}.{ext}"

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)

    file_size = os.path.getsize(filepath)

    attachment = Attachment(
        item_id=item_id,
        filename=unique_filename,
        original_filename=file.filename,
        file_type=file.content_type or '',
        file_size=file_size
    )
    db.session.add(attachment)
    db.session.commit()

    return jsonify(attachment.to_dict()), 201


@app.route('/api/attachments/<int:attachment_id>/download', methods=['GET'])
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        attachment.filename,
        download_name=attachment.original_filename
    )


@app.route('/api/attachments/<int:attachment_id>/preview', methods=['GET'])
def preview_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        attachment.filename,
        mimetype=attachment.file_type
    )


@app.route('/api/attachments/<int:attachment_id>', methods=['DELETE'])
def delete_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(attachment)
    db.session.commit()
    return jsonify({'message': '删除成功'})


# ==================== Dashboard API ====================

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    total_items = Item.query.count()
    total_rooms = Room.query.count()
    total_categories = Category.query.count()

    today = date.today()
    from sqlalchemy import and_
    expiring_items = Item.query.filter(
        and_(
            Item.warranty_expires != None,
            Item.warranty_expires >= today,
            Item.warranty_expires <= date.fromordinal(today.toordinal() + 30)
        )
    ).all()

    expired_items = Item.query.filter(
        and_(
            Item.warranty_expires != None,
            Item.warranty_expires < today
        )
    ).all()

    return jsonify({
        'total_items': total_items,
        'total_rooms': total_rooms,
        'total_categories': total_categories,
        'expiring_soon': [item.to_dict() for item in expiring_items],
        'expired': [item.to_dict() for item in expired_items]
    })


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
