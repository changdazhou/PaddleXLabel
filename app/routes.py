import os
import json
from flask import jsonify
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.utils import load_users, save_users, get_data_file_path,load_json,save_json
from datetime import datetime

bp = Blueprint('main', __name__)
UPLOAD_FOLDER = '/paddle/workspace/ours_images'
PRE_LABEL_FOLDER = '/paddle/workspase/DocOrderLabeler/v1'

LABELED_DATA_INFO = {}
order_info_file = get_data_file_path('order.json')
order_info = load_json(order_info_file)

formula_info_file = get_data_file_path('formula.json')
formula_info = load_json(formula_info_file)

table_info_file = get_data_file_path('table.json')
tabel_info = load_json(table_info_file)

order_image_data = {}
formula_image_data = {}
table_image_data = {}

ALL_DATA_INFO = {}
for case_type in os.listdir(PRE_LABEL_FOLDER):
    case_type_data_info = {}
    for case_dir in os.listdir(os.path.join(PRE_LABEL_FOLDER,case_type)):
        dir_path = os.path.join(PRE_LABEL_FOLDER,case_type,case_dir)
        if not os.path.isdir(dir_path):
            continue
        json_files = sorted([f for f in os.listdir(dir_path) if f.endswith('.json')])
        if json_files:
            json_path = json_files[0]
            json_data = load_json(os.path.join(dir_path,json_path))
            image_name = json_data['input_path'].split('/')[-1]
            case_type_data_info[image_name]= {}
            case_type_data_info[image_name]["pre_label_json"] = os.path.join(dir_path,json_path)
            case_type_data_info[image_name]["order_info"] = order_info.get(image_name,{})
            case_type_data_info[image_name]["formula_info"] = formula_info.get(image_name,{})
            case_type_data_info[image_name]["table_info"] = tabel_info.get(image_name,{})
        else:
            continue
    ALL_DATA_INFO[case_type]=case_type_data_info

@bp.route('/annotate_order')
@login_required
def annotate_order():
    order_image_names = []
    case_types = list(ALL_DATA_INFO.keys())
    for case_type in case_types:
        for image_name, image_info in ALL_DATA_INFO[case_type].items():
            order_image_data[image_name] ={
                "pre_label_json": image_info["pre_label_json"],
                "order_info": image_info["order_info"],
            }
            order_image_names.append(image_name)
    return render_template('annotate_order.html', case_types=case_types, image_names=order_image_names,image_data=order_image_data)

@bp.route('/get_annotation', methods=['GET'])
def get_annotation():
    anno_type = request.args.get('anno_type')
    image_name = request.args.get('image_name')
    if anno_type == "order_info":
        json_path = order_image_data.get(image_name)['pre_label_json']
        labeled_info = order_image_data.get(image_name)["order_info"]
    elif anno_type == "formula_info":
        json_path = formula_image_data.get(image_name)['pre_label_json']
        labeled_info = formula_image_data.get(image_name)["formula_info"]
    elif anno_type == "table_info":
        json_path = table_image_data.get(image_name)['pre_label_json']
        labeled_info = table_image_data.get(image_name)["table_info"]
    
    if json_path and os.path.exists(json_path):
        pre_label_info = load_json(json_path)
        parsing_res_list = []
        for id in range(len(pre_label_info['parsing_res_list'])):
            block_info = pre_label_info['parsing_res_list'][id]
            block_info['id'] = id
            block_info['selected'] = False
            if labeled_info:
                block_info['selected'] = True
                if anno_type == "order_info":
                    block_info['order_id'] = labeled_info[id]["order_id"]
                    block_info['is_concatenated'] = labeled_info[id]["is_concatenated"] 
                elif anno_type == "formula_info" and labeled_info[id]["block_label"]=="formula":
                    block_info['formula_type'] = labeled_info[id]["formula_type"]
                elif anno_type == "table_info" and labeled_info[id]["block_label"]=="table":
                    block_info['line'] = labeled_info[id]["line"]
                    block_info['include_equation'] = labeled_info[id]["include_equation"]
                    block_info['include_photo'] = labeled_info[id]["include_photo"]
            else:
                if anno_type == "order_info":
                    block_info['is_concatenated'] = False
                    block_info['order_id'] = id
                elif anno_type == "formula_info" and block_info["block_label"]=="formula":
                    block_info['formula_type'] = None
                elif anno_type == "table_info" and block_info["block_label"]=="table":
                    block_info['line'] = None
                    block_info['include_equation'] = None
                    block_info['include_photo'] = None
            parsing_res_list.append(block_info)
        data = {
            'parsing_res_list': parsing_res_list
        }
        return jsonify(data)
    else:
        # 如果文件不存在，返回错误信息
        return jsonify({'error': 'File not found'}), 404
    
@bp.route('/api/current_user')
@login_required
def api_current_user():
    return jsonify({'username': current_user.username})

@bp.route('/save', methods=['POST'])
@login_required
def save_annotation():
    anno_type = request.args.get('anno_type')
    data = request.json
    image_name = data.get('imageName')  # 注意这里和前端保持一致
    annotations = data.get('annotations')

    if not image_name or annotations is None:
        return jsonify({"status": "error", "message": "缺少必要参数"}), 400

    # 如果annotations是字符串，尝试解析为dict
    if isinstance(annotations, str):
        try:
            annotations = json.loads(annotations)
        except Exception as e:
            return jsonify({"status": "error", "message": "annotations JSON解析失败: " + str(e)}), 400
    
    sorted_annotations = sorted(annotations, key=lambda x: x['id'])
    for i, annotation in enumerate(sorted_annotations):
        annotation.pop("selected", None)
        annotation["label_user"] = current_user.username
        annotation["label_time"] = datetime.now().isoformat()

    save_data = {image_name: sorted_annotations}
    if anno_type == "order_info":
        global order_image_data
        order_image_data[image_name]["order_info"] = sorted_annotations
        try:
            order_info = load_json(order_info_file)
            order_info.update(save_data)
            save_json(order_info_file, order_info)
        except Exception as e:
            return jsonify({"status": "error", "message": "结果保存失败：" + str(e)}), 400
    elif anno_type == "formula_info":
        global formula_image_data
        formula_image_data[image_name]["formula_info"] = sorted_annotations
        try:
            formula_info = load_json(formula_info_file)
            formula_info.update(save_data)
            save_json(formula_info_file, formula_info)
        except Exception as e:
            return jsonify({"status": "error", "message": "结果保存失败：" + str(e)}), 400
    elif anno_type == "table_info":
        global table_image_data
        table_image_data[image_name]["table_info"] = sorted_annotations
        try:
            table_info = load_json(table_info_file)
            table_info.update(save_data)
            save_json(table_info_file, table_info)
        except Exception as e:
            return jsonify({"status": "error", "message": "结果保存失败：" + str(e)}), 400

    return jsonify({"status": "success", "message": "保存成功"})


@bp.route('/images/<filename>')
def images(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        
        if username in users:
            flash('User already exists')
        else:
            user_id = len(users) + 1
            new_user = User(user_id, username, generate_password_hash(password))
            users[username] = new_user
            save_users(users)
            flash('User registered successfully')
            return redirect(url_for('main.login'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        
        user = users.get(username)
        # password_=generate_password_hash(password)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.menu', case_type=case_type, myImage=image_name, username=username))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@bp.route('/menu')
@login_required
def menu():
    return render_template('menu.html')

@bp.route('/annotate_formula')
@login_required
def annotate_formula():
    formula_image_names = []
    case_types = ["table_with_formula","with_chinese_formula","with_handwrited_formula"]
    formula_info_file = get_data_file_path('formula.json')
    formula_info = load_json(formula_info_file)
    for case_type in case_types:
        for image_name, image_info in ALL_DATA_INFO[case_type].items():
            formula_image_data[image_name] ={
                "pre_label_json": image_info["pre_label_json"],
                "formula_info": formula_info.get(image_name,[]),
            }
            pre_label_anno = load_json(image_info["pre_label_json"])
            with_formula = False
            for anno in pre_label_anno['parsing_res_list']:
                if anno["block_label"] == "formula":
                    with_formula = True
                    break
            if with_formula:
                formula_image_names.append(image_name)
    return render_template('annotate_formula.html', case_types=case_types, image_names=formula_image_names,image_data=formula_image_data)

@bp.route('/annotate_table')
@login_required
def annotate_table():
    table_image_names = []
    case_types = ["table_with_formula","with_chinese_formula","with_handwrited_formula"]
    table_info_file = get_data_file_path('table.json')
    table_info = load_json(table_info_file)
    for case_type in case_types:
        for image_name, image_info in ALL_DATA_INFO[case_type].items():
            table_image_data[image_name] ={
                "pre_label_json": image_info["pre_label_json"],
                "table_info": table_info.get(image_name,[]),
            }
            pre_label_anno = load_json(image_info["pre_label_json"])
            with_table = False
            for anno in pre_label_anno['parsing_res_list']:
                if anno["block_label"] == "table":
                    with_table = True
                    break
            if with_table:
                table_image_names.append(image_name)
    return render_template('annotate_table.html', case_types=case_types, image_names=table_image_names,image_data=table_image_data)


@bp.route('/')
@login_required
def index():
    return redirect(url_for('main.login'))
