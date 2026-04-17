from datetime import datetime, time
from app import db
from app.main import bp
from flask import render_template, request, redirect, jsonify
from flask_login import login_required, current_user
from app.main.forms import CreateOrder, CreateNote
from app.models import OrderTypes, Tag, Order, CustomInputs, Note, OrderComments, User
from werkzeug.utils import secure_filename
from config import Config
import os
import subprocess
import random
import speech_recognition as sr
import json


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    title = 'Главная'

    # Я поставил
    orders_iam_creator = current_user.get_orders_iam_creator()

    # Мне поставили
    orders_iam_executor = current_user.get_orders_iam_executor()

    create_order_form = CreateOrder()
    for order_type in OrderTypes.query.all():
        create_order_form.type.choices.append((str(order_type.id), order_type.title))

    create_order_form.executors.choices.append(('0', 'не выбрано'))
    for tag in Tag.query.all():
        create_order_form.executors.choices.append((str(tag.id), tag.name))


    create_note_form = CreateNote()

    if create_order_form.validate_on_submit():
        all_fields = request.form
        custom_fields = {}
        personal_executors = []
        for field in all_fields:
            if 'field' in field.split('-'):
                custom_fields[field.split('-')[0]] = all_fields[field]
            if 'executor' in field.split('-'):
                personal_executors.append(User.query.get(field.split('-')[-1]))

        order = Order()
        order.creator = current_user.id
        order.base_order = create_order_form.baseorder.data
        order.title = create_order_form.title.data
        order.description = create_order_form.description.data
        order.description_sound = create_order_form.file.data
        order.priority = create_order_form.priority.data
        order.type = create_order_form.type.data
        order.interval = create_order_form.interval.data
        order.deadline = create_order_form.deadline.data

        for field in all_fields:
            if 'file_id' in field:
                order.description_sound = f'{all_fields["file_id"]}sound.ogg'
                # print(os.path.join(Config.UPLOAD_FOLDER, f'{all_fields["file_id"]}sound.wav'))

        order.status = 1

        if create_order_form.executors.data != '0':
            tag = Tag.query.filter(Tag.id == create_order_form.executors.data).first()
            for user in tag.users:
                order.executors.append(user)
        if personal_executors:
            for user in personal_executors:
                order.executors.append(user)

        order.reactions = json.dumps(custom_fields)

        db.session.add(order)
        db.session.commit()
        return redirect(request.referrer)

    if create_note_form.validate_on_submit():
        note = Note()
        note.creator = current_user.id
        note.text = create_note_form.text.data

        all_fields = request.form
        for field in all_fields:
            if 'file_id' in field:
                note.sound_file = os.path.join(Config.UPLOAD_FOLDER, f'{all_fields["file_id"]}sound.wav')

        db.session.add(note)
        db.session.commit()
        return redirect(request.referrer)

    return render_template('main/index.html',
                           title=title,
                           create_order_form=create_order_form,
                           create_note_form = create_note_form,
                           orders_iam_creator=orders_iam_creator,
                           orders_iam_executor=orders_iam_executor,
                           custom_inputs=CustomInputs.query.all(),
                           list=list, reversed=reversed)


@bp.route("/get_preset/<id>")
def get_preset(id):
    preset = CustomInputs.query.filter_by(id=id).first()
    return jsonify(preset.preset)

@bp.route('/get_order_json/<id>')
def get_order_json(id):
    order = Order.query.filter_by(id=id).first()
    return jsonify({
            x[0]: [
                g.strftime('%Y-%m-%d %H:%M:%S') if type(g) == datetime else g for g in [x[1]]
                ][0]
            for x in order.__dict__.items() if type(x[1]) == int or type(x[1]) == datetime or type(x[1]) == str or type(x[1]) == list
        })

@bp.route('/recognize_file', methods=['GET', 'POST'])
def recognize_file():
    if request.method == 'POST':
        # print(request.files)
        voice_rec = request.files['audio'] # надо взять аудиофайл из POST запроса
        rand = str(random.randint(100000,1000000))
        filename =  rand + secure_filename(voice_rec.filename)
        voice_rec.save(os.path.join(Config.UPLOAD_FOLDER, filename))
        subprocess.run(['ffmpeg', '-i', os.path.join(Config.UPLOAD_FOLDER, filename), os.path.join(Config.UPLOAD_FOLDER, filename.replace('ogg', 'wav'))])
        with sr.AudioFile(os.path.join(Config.UPLOAD_FOLDER, filename.replace('ogg', 'wav'))) as s:
            r = sr.Recognizer()
            txt = r.listen(s)
            text = r.recognize_google(txt, language = 'ru-RU')
            return jsonify({'stt': text, 'file_id': int(rand)})


@bp.route('/get_note_<note_id>', methods=['GET'])
def get_note(note_id):
    return render_template('main/__noteData.html',
                           note = Note.query.get(note_id))


@bp.route('/get_order_<order_id>', methods=['GET'])
def get_order(order_id):
    comments = OrderComments.query.filter(OrderComments.order == order_id).order_by(OrderComments.creation_date).all()
    derived_orders=Order.query.filter_by(base_order=order_id).all()
    if len(derived_orders) > 0:
        orders_stats = {"ready": len(Order.query.filter_by(base_order=order_id, done=True).all()), "total": len(derived_orders)}
    else:
        orders_stats = {}
    return render_template('main/__orderData.html',
                           order=Order.query.get(order_id),
                           comments=comments,
                           derived_orders=derived_orders,
                           orders_stats=orders_stats,
                           list=list, reversed=reversed,
                           time=datetime.now(), int=int)


@bp.route('/send_comment', methods=['POST'])
def send_comment():
    data = request.form
    order_id = data['order']
    user_id = data['user']
    text = data['text']

    comment = OrderComments()
    comment.user = user_id
    comment.order = order_id
    comment.text = text

    db.session.add(comment)
    db.session.commit()

    return 'ok'


@bp.route('/get_users_<text>', methods=['GET'])
def get_users(text):
    users: User = User.query.filter(User.last_name.contains(text)).all()
    return render_template('main/__executors_list.html',
                           users=users)
