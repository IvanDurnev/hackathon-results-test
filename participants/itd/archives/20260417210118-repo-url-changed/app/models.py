from app import db, login, Config
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import jwt
from time import time


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


user_tag = db.Table('user_tag',
                    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                    )

order_executor = db.Table('order_executor',
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                      db.Column('order_id', db.Integer, db.ForeignKey('order.id'))
                      )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tg_id = db.Column(db.Integer, index=True)
    username = db.Column(db.String(64), index=True)
    email = db.Column(db.String(100), index=True)
    phone = db.Column(db.String(18), index=True, unique=True)
    private_number = db.Column(db.String(20), default='')
    is_bot = db.Column(db.Boolean, index=True)
    first_name = db.Column(db.String(64), index=True)
    position = db.Column(db.String(64))
    last_name = db.Column(db.String(64), index=True)
    additional_code = db.Column(db.String(64), index=True)
    language_code = db.Column(db.String(5), index=True, default='ru')
    password_hash = db.Column(db.String(128))
    status = db.Column(db.String(30), index=True, default='')
    role = db.Column(db.String(12), index=True)
    group = db.Column(db.Integer, db.ForeignKey('group.id'), index=True, default=1)
    registered = db.Column(db.DateTime, index=True, nullable=True, default=datetime.now())
    priority = db.Column(db.Integer)
    boss = db.Column(db.Integer, db.ForeignKey('user.id'))

    tags = db.relationship('Tag',
                           secondary=user_tag,
                           lazy='subquery',
                           backref=db.backref('tags', lazy=True))

    def set_unsubscribed(self):
        self.unsubscribed = True
        db.session.commit()

    def set_subscribed(self):
        self.unsubscribed = False
        db.session.commit()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_group(self):
        if self.group:
            return Group.query.filter_by(id=self.group).first()

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {
                'reset_password': self.id,
                'exp': time() + expires_in
            },
            Config.SECRET_KEY,
            algorithm='HS256').decode('utf-8')

    def get_orders_iam_creator(self):
        return Order.query.filter(Order.creator == self.id).all()

    def get_orders_iam_executor(self):
        return Order.query.filter(Order.executors.contains(self)).all()

    def get_notes(self):
        return Note.query.filter(Note.creator == self.id).all()

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def set_item(self, item, value):
        if item in self.__dict__:
            setattr(self, item, value)
            db.session.commit()
        else:
            raise Exception('WrongItem')


    def __repr__(self):
        return f'{self.first_name} {self.last_name}'


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(30), index=True)
    users = db.relationship('User', backref='users', lazy=True)

    def __repr__(self):
        return self.name


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(30), index=True)
    description = db.Column(db.String(128), index=True)
    users = db.relationship('User',
                              secondary=user_tag,
                              lazy='subquery',
                              backref=db.backref('tag_users', lazy=True))


class MainMenuItems(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String(30))
    callback = db.Column(db.String(30))
    enabled = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, unique=True)


class OrderTypes(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(30))
    description = db.Column(db.String(100))
    color = db.Column(db.String(6))


class OrderComments(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user = db.Column(db.Integer, db.ForeignKey('user.id'))
    order = db.Column(db.Integer, db.ForeignKey('order.id'))
    creation_date = db.Column(db.DateTime, default=datetime.now())
    text = db.Column(db.String(2048))

    def get_user(self):
        return User.query.get(self.user)


class OrderStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(30))
    description = db.Column(db.String(100))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    base_order = db.Column(db.Integer, db.ForeignKey('order.id'))
    creation_date = db.Column(db.DateTime, default=datetime.now())
    creator = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(512))
    description = db.Column(db.String(4096))
    description_sound = db.Column(db.String(1024))
    priority = db.Column(db.Integer, default=1)
    type = db.Column(db.Integer, db.ForeignKey('order_types.id'))
    interval = db.Column(db.Integer, default=0)
    deadline = db.Column(db.DateTime)
    done = db.Column(db.Boolean, default=False)
    reactions = db.Column(db.JSON, default={})
    status = db.Column(db.Integer, db.ForeignKey('order_status.id'), default=1)
    executors = db.relationship('User',
                                secondary=order_executor,
                                lazy='subquery',
                                backref=db.backref('executors', lazy=True))

    def get_comments(self):
        return OrderComments.query.filter(OrderComments.order == self.id).order_by(OrderComments.creation_date).all()

    def get_creator(self):
        return User.query.get(self.creator)

    def get_status(self):
        return OrderStatus.query.get(self.status)

class CustomInputs(db.Model):
    """
    Structure
    [
        {
            "name": string,
            "type": enum one of (checkbox|file|text)
        }
    ]

    Example
        [{"name": "I am pony", "type": "checkbox"}]
    """

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    preset_name = db.Column(db.String(64), nullable=False)
    preset = db.Column(db.JSON, default=[])

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String(4096))
    sound_file = db.Column(db.String(1024))
    creator = db.Column(db.Integer, db.ForeignKey('user.id'))
    creation_date = db.Column(db.DateTime, default=datetime.now())
