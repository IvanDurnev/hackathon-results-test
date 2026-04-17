from app import db
from app.main import bp
from flask import render_template, redirect, url_for, request
from flask_login import current_user, login_required
from app.models import Regulation, RegulationVersion, BaseDoc, RegulationApplication, Comment
from app.main.forms import RenameRegulationForm, AddBaseDocumentLink
from hashlib import md5
import json, secrets
import re
import os


@bp.route('/', methods=['GET','POST'])
@login_required
def index():
    title = 'КАНБАЛА'
    users_regulations: Regulation = Regulation.query.filter(Regulation.creator==current_user.id).all()
    return render_template('main/index.html',
                           title=title,
                           user=current_user,
                           users_regulations=users_regulations)


@bp.route('/create_regulation', methods=['GET', 'POST'])
@login_required
def regulation_create():
    regulation = Regulation()
    regulation.creator = current_user.id
    db.session.add(regulation)
    db.session.commit()
    regulation.short_name = f'Новый регламент {regulation.id}'
    regulation_version = RegulationVersion()
    regulation_version.version_number = 1
    regulation_version.status = 'Черновик'
    regulation_version.data = json.dumps({})
    regulation_version.regulation_id = regulation.id
    db.session.add(regulation_version)
    db.session.commit()
    return redirect(url_for('main.regulation_show', regulation_version_id=regulation_version.id))


@bp.route('/reg/<regid>/remove/<section>/<paragraph>', methods=['DELETE'])
def removeparagraph(regid, section, paragraph=-1):
    entry = RegulationVersion.query.get(regid)
    data = json.loads(entry.data)
    data.pop(f"paragraph_{section}_{paragraph}")
    counter = 1
    l = sorted([x for x in data.keys() if x.startswith(f'paragraph_{section}_')])
    print(l)
    for i in l:
        if i.split("_")[-1] != str(counter):
            data[f"paragraph_{section}_{counter}"] = data[i]
            del data[i]
        counter += 1
    entry.data = json.dumps(data)
    db.session.merge(entry)
    db.session.commit()
    return Response("200")


@bp.route('/show_regulation_<regulation_version_id>', methods=['GET', 'POST'])
@login_required
def regulation_show(regulation_version_id):
    regulation_version: RegulationVersion = RegulationVersion.query.get(regulation_version_id)
    data = json.loads(regulation_version.data)
    rename_regulation_form = RenameRegulationForm()
    add_document_link = AddBaseDocumentLink()

    if rename_regulation_form.validate_on_submit():
        regulation_version.parent_regulation().short_name = rename_regulation_form.name.data
        db.session.commit()
        return redirect(request.referrer)

    if add_document_link.validate_on_submit():
        new_doc = BaseDoc()
        new_doc.link = add_document_link.link.data
        new_doc.regulation_id = regulation_version.parent_regulation().id
        db.session.add(new_doc)
        db.session.commit()
        return redirect(request.referrer)

    return render_template('main/regulation_editor.html',
                           title='Редактор регламента',
                           regulation_version=regulation_version,
                           data=data, 
                           applications=RegulationApplication.get_applications_by_doc(regulation_version.parent_regulation().id),
                           rename_regulation_form=rename_regulation_form,
                           add_document_link=add_document_link,
                           regulation_base_documents=regulation_version.parent_regulation().get_base_documents())


@bp.route('/add_regulation_application/<id>', methods=['POST'])
@login_required
def add_application(id):
    doc = request.files['uploaded_application']
    filename = secrets.token_hex(8)+doc.filename
    if not os.path.exists('app/static/applications/'):
        os.makedirs('app/static/applications/')
    doc.save('app/static/applications/'+filename)
    entry = RegulationApplication(regulation_id=id, filename=filename, filename_orig=doc.filename)
    db.session.add(entry)
    db.session.commit()
    return redirect(request.referrer)
    # db.

@bp.route('/show_regulation_comment_mode_<regulation_version_id>', methods=['GET', 'POST'])
def show_regulation_comment_mode(regulation_version_id):
    regulation_version: RegulationVersion = RegulationVersion.query.get(regulation_version_id)
    data = json.loads(regulation_version.data)
    comments = regulation_version.get_comments()
    return render_template('main/regulation_comments.html',
                           title='Редактор регламента',
                           regulation_version=regulation_version,
                           data=data,
                           regulation_base_documents=regulation_version.parent_regulation().get_base_documents(),
                           current_user=current_user,
                           comments=comments)

@bp.route('/save_regulation_<regulation_version_id>', methods=['POST'])
@login_required
def regulation_save(regulation_version_id):
    data = json.loads(json.dumps(request.form))
    regulation_version: RegulationVersion = RegulationVersion.query.get(regulation_version_id)
    regulation_version_data = json.loads(regulation_version.data)
    for item in data:
        regulation_version_data[item] = data[item]
    regulation_version.data = json.dumps(regulation_version_data)
    # regulation_version.parent_regulation().base_document = data['header_base_doc']
    db.session.commit()
    return redirect(request.referrer)


@bp.route('/editor_add_chapter_<regulation_version_id>', methods=['GET', 'POST'])
@login_required
def editor_add_chapter(regulation_version_id):
    regulation_version: RegulationVersion = RegulationVersion.query.get(regulation_version_id)
    regulation_version_data = json.loads(regulation_version.data)
    chapters_count = 0
    for item in regulation_version_data:
        if re.match('chapter_\d', item):
            chapters_count += 1
    regulation_version_data[f'chapter_{chapters_count+1}'] = ''
    regulation_version.data = json.dumps(regulation_version_data)
    db.session.commit()
    return redirect(request.referrer)


@bp.route('/add_paragraph_<regulation_version_id>_<chapter_number>')
def add_paragraph(regulation_version_id, chapter_number):
    regulation_version: RegulationVersion = RegulationVersion.query.get(regulation_version_id)
    regulation_version_data = json.loads(regulation_version.data)

    paragraph_count = 0
    for item in regulation_version_data:
        if re.match(f'paragraph_{chapter_number}_\d', item):
            paragraph_count += 1
    regulation_version_data[f'paragraph_{chapter_number}_{paragraph_count+1}'] = ''
    regulation_version.data = json.dumps(regulation_version_data)
    db.session.commit()
    return redirect(request.referrer)


@bp.route('/save_comment_<user_id>_<regulation_version_id>', methods=['POST'])
def save_comment(user_id, regulation_version_id):
    data = json.loads(json.dumps(request.form))
    for item in data:
        if re.match('comment', item):
            paragraph = item.split('_')[-2]+'_'+item.split('_')[-1]
            comment = Comment()
            comment.user_id = user_id
            comment.regulation_version_id = regulation_version_id
            comment.paragraph = paragraph
            comment.text = data[item]
            db.session.add(comment)
            db.session.commit()
    return redirect(request.referrer)