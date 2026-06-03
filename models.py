from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()

item_category = db.Table(
    'item_category',
    db.Column('item_id', db.Integer, db.ForeignKey('item.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('Item', backref='room', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'item_count': len(self.items)
        }


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'item_count': db.session.query(item_category).filter(
                item_category.c.category_id == self.id
            ).count()
        }


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    price = db.Column(db.Float, nullable=True)
    warranty_expires = db.Column(db.Date, nullable=True)
    warranty_notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    categories = db.relationship('Category', secondary=item_category, lazy='subquery',
                                 backref=db.backref('items', lazy=True))
    attachments = db.relationship('Attachment', backref='item', lazy=True, cascade='all, delete-orphan')

    @property
    def warranty_status(self):
        if not self.warranty_expires:
            return 'none'
        today = date.today()
        if self.warranty_expires < today:
            return 'expired'
        delta = (self.warranty_expires - today).days
        if delta <= 30:
            return 'expiring_soon'
        return 'active'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'room_id': self.room_id,
            'room_name': self.room.name if self.room else None,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'price': self.price,
            'warranty_expires': self.warranty_expires.isoformat() if self.warranty_expires else None,
            'warranty_notes': self.warranty_notes,
            'warranty_status': self.warranty_status,
            'categories': [{'id': c.id, 'name': c.name} for c in self.categories],
            'attachments': [a.to_dict() for a in self.attachments],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), default='')
    file_size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat()
        }
