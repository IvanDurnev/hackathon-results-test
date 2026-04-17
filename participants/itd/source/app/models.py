from app import db, login, Config
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from time import time


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    regulation_version_id = db.Column(db.Integer, db.ForeignKey('regulation_version.id'))
    paragraph = db.Column(db.String(50))
    created = db.Column(db.DateTime, default=datetime.now())
    text = db.Column(db.String(2048))

    def get_commentator(self):
        return User.query.get(self.user_id)

    def get_regulation_version(self):
        return RegulationVersion.query.get(self.regulation_version_id)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    username = db.Column(db.String(64), index=True)
    organization = db.Column(db.String(256))
    position = db.Column(db.String(256))
    email = db.Column(db.String(256))
    password_hash = db.Column(db.String(128))
    userpic = db.Column(db.Binary)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {
                'reset_password': self.id,
                'exp': time() + expires_in
            },
            Config.SECRET_KEY,
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def __repr__(self):
        return f'{self.first_name} {self.last_name}'


class BaseDoc(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    link = db.Column(db.String(1024))
    hash = db.Column(db.String(512))
    regulation_id = db.Column(db.Integer, db.ForeignKey('regulation.id'))


class Regulation(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    short_name = db.Column(db.String(512))
    description = db.Column(db.String(2048))
    creator = db.Column(db.Integer, db.ForeignKey('user.id'))
    created = db.Column(db.DateTime, default=datetime.now())


    def get_versions(self):
        return RegulationVersion.query.filter(RegulationVersion.regulation_id==self.id).all()


    def get_base_documents(self):
        return BaseDoc.query.filter(BaseDoc.regulation_id==self.id).all()


class RegulationVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    regulation_id = db.Column(db.Integer, db.ForeignKey('regulation.id'))
    version_number = db.Column(db.Integer)
    status = db.Column(db.String(20))
    data = db.Column(db.JSON)
    created = db.Column(db.DateTime, default=datetime.now())

    def parent_regulation(self):
        return Regulation.query.get(self.regulation_id)

    def get_comments(self):
        return Comment.query.filter(Comment.regulation_version_id==self.id).all()


class UserRegulation(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    regulation_version_id = db.Column(db.Integer, db.ForeignKey('regulation_version.id'))
    mode = db.Column(db.String(20))
    comments_data = db.Column(db.JSON)


class RegulationApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    regulation_id = db.Column(db.Integer, db.ForeignKey('regulation.id'))
    filename = db.Column(db.String(64))
    filename_orig = db.Column(db.String(128))

    @staticmethod
    def get_applications_by_doc(id):
        return RegulationApplication.query.filter_by(regulation_id=id).all()