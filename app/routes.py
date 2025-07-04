# Copyright (c) 2024 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import shutil
from datetime import datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user
from werkzeug.security import generate_password_hash

from app.models import User
from app.utils import (
    create_or_update_symlink,
    get_data_file_path,
    load_json,
    load_users,
    save_json,
    save_users,
)

bp = Blueprint("main", __name__)
order_image_data = {}
formula_image_data = {}
table_image_data = {}

SRC_DATA_FOLDER = None
PRE_LABEL_FOLDER = None
IMGAREA_FOLDER = None


def init_src_data(src_folder):
    global SRC_DATA_FOLDER, PRE_LABEL_FOLDER, IMGAREA_FOLDER
    SRC_DATA_FOLDER = src_folder

    IMGAREA_FOLDER = os.path.join(SRC_DATA_FOLDER, "images")
    PRE_LABEL_FOLDER = os.path.join(SRC_DATA_FOLDER, "jsons")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    static_dir = os.path.join(base_dir, "static")

    dst_image_dir = os.path.abspath(os.path.join(static_dir, "images"))

    if os.path.exists(dst_image_dir):
        os.system(f"rm -rf {dst_image_dir}")

    os.symlink(IMGAREA_FOLDER, dst_image_dir)


@bp.route("/annotate_order")
@login_required
def annotate_order():
    order_image_names = []
    order_info_file = get_data_file_path("order.json")
    order_info = load_json(order_info_file)
    create_or_update_symlink(
        os.path.abspath(IMGAREA_FOLDER), os.path.abspath("app/static/images")
    )
    for image_name in os.listdir(IMGAREA_FOLDER):
        order_image_data[image_name] = {
            "pre_label_json": os.path.splitext(image_name)[0] + "_res.json",
            "order_info": order_info.get(image_name, []),
        }
        order_image_names.append(image_name)
    return render_template(
        "annotate_order.html",
        image_names=order_image_names,
        image_data=order_image_data,
    )


@bp.route("/get_annotation", methods=["GET"])
def get_annotation():
    anno_type = request.args.get("anno_type")
    image_name = request.args.get("image_name")
    if anno_type == "order_info":
        json_path = order_image_data.get(image_name)["pre_label_json"]
        order_info_file = get_data_file_path("order.json")
        order_info = load_json(order_info_file)
        labeled_info = order_info.get(image_name, [])
    elif anno_type == "formula_info":
        json_path = formula_image_data.get(image_name)["pre_label_json"]
        formula_info_file = get_data_file_path("formula.json")
        formula_info = load_json(formula_info_file)
        labeled_info = formula_info.get(image_name)
    elif anno_type == "table_info":
        json_path = table_image_data.get(image_name)["pre_label_json"]
        table_info_file = get_data_file_path("table.json")
        table_info = load_json(table_info_file)
        labeled_info = table_info.get(image_name)
    json_path = os.path.join(PRE_LABEL_FOLDER, json_path)
    if json_path and os.path.exists(json_path):
        pre_label_info = load_json(json_path)
        parsing_res_list = []
        pre_label_ids = range(len(pre_label_info["parsing_res_list"]))
        labeled_ids = []
        if labeled_info:
            labeled_ids = set([label_info["id"] for label_info in labeled_info])
        for id in pre_label_ids:
            block_info = pre_label_info["parsing_res_list"][id]
            block_info["id"] = id
            if labeled_info:
                labeled_block_info = None
                for label_info in labeled_info:
                    if label_info["id"] == id:
                        labeled_block_info = label_info
                        break
                if labeled_block_info is None:
                    continue
                if id in labeled_ids:
                    labeled_ids.remove(id)
                block_info = labeled_block_info
            else:
                if anno_type == "order_info":
                    block_info["is_concatenated"] = False
                    block_info["order_id"] = id
                elif (
                    anno_type == "formula_info"
                    and block_info["block_label"] == "formula"
                ):
                    block_info["formula_type"] = None
                    block_info["include_chinese"] = False
                elif anno_type == "table_info" and block_info["block_label"] == "table":
                    block_info["line"] = None
                    block_info["include_equation"] = None
                    block_info["include_photo"] = None
            parsing_res_list.append(block_info)
        if labeled_info and len(labeled_ids) > 0:
            for id in labeled_ids:
                labeled_block_info = None
                for label_info in labeled_info:
                    if label_info["id"] == id:
                        labeled_block_info = label_info
                        break
                if labeled_block_info is None:
                    continue
                block_info = labeled_block_info
                parsing_res_list.append(block_info)
        data = {"parsing_res_list": parsing_res_list}
        return jsonify(data)
    else:
        # 如果文件不存在，返回错误信息
        return jsonify({"error": "File not found"}), 404


@bp.route("/api/current_user")
@login_required
def api_current_user():
    return jsonify({"username": current_user.username})


@bp.route("/save", methods=["POST"])
@login_required
def save_annotation():
    anno_type = request.args.get("anno_type")
    data = request.json
    image_name = data.get("imageName")  # 注意这里和前端保持一致
    annotations = data.get("annotations")
    labeled_image_num = data.get("labeled_image_num")

    if not image_name or annotations is None:
        return jsonify({"status": "error", "message": "缺少必要参数"}), 400

    # 如果annotations是字符串，尝试解析为dict
    if isinstance(annotations, str):
        try:
            annotations = json.loads(annotations)
        except Exception as e:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "annotations JSON解析失败: " + str(e),
                    }
                ),
                400,
            )

    sorted_annotations = sorted(annotations, key=lambda x: x["id"])
    now = datetime.now() + timedelta(hours=8)
    data_time = now.strftime("%Y-%m-%d-%H-%M")
    for i, annotation in enumerate(sorted_annotations):
        annotation.pop("selected", None)
        annotation["label_user"] = current_user.username
        annotation["label_time"] = str(data_time)

    back_up_dir = get_data_file_path(f"backup")
    if not os.path.exists(back_up_dir):
        os.makedirs(back_up_dir)

    save_data = {image_name: sorted_annotations}
    if anno_type == "order_info":
        global order_image_data
        try:
            order_info_file = get_data_file_path("order.json")
            backup_order_info_file = os.path.join(
                back_up_dir, f"order_backup_{data_time}.json"
            )
            order_info = load_json(order_info_file)
            if len(order_info) != labeled_image_num:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"标注数量与实际不匹配，请检查！",
                        }
                    ),
                    400,
                )
            order_image_data[image_name]["order_info"] = sorted_annotations
            order_info.update(save_data)
            save_json(order_info_file, order_info)
            save_json(backup_order_info_file, order_info)
        except Exception as e:
            return (
                jsonify({"status": "error", "message": "结果保存失败：" + str(e)}),
                400,
            )
    elif anno_type == "formula_info":
        global formula_image_data
        formula_image_data[image_name]["formula_info"] = sorted_annotations
        try:
            formula_info_file = get_data_file_path("formula.json")
            formula_info = load_json(formula_info_file)
            formula_info.update(save_data)
            save_json(formula_info_file, formula_info)
        except Exception as e:
            return (
                jsonify({"status": "error", "message": "结果保存失败：" + str(e)}),
                400,
            )
    elif anno_type == "table_info":
        global table_image_data
        table_image_data[image_name]["table_info"] = sorted_annotations
        try:
            table_info_file = get_data_file_path("table.json")
            table_info = load_json(table_info_file)
            table_info.update(save_data)
            save_json(table_info_file, table_info)
        except Exception as e:
            return (
                jsonify({"status": "error", "message": "结果保存失败：" + str(e)}),
                400,
            )

    return jsonify({"status": "success", "message": "保存成功"})


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()

        if username in users:
            flash("User already exists")
        else:
            user_id = len(users) + 1
            new_user = User(user_id, username, generate_password_hash(password))
            users[username] = new_user
            save_users(users)
            flash("User registered successfully")
            return redirect(url_for("main.login"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()

        user = users.get(username)
        # password_=generate_password_hash(password)
        if user and user.check_password(password):
            login_user(user)
            return jsonify(
                {
                    "success": True,
                    "redirect_url": url_for("main.menu", username=username),
                }
            )
        else:
            return jsonify({"success": False, "message": "Invalid credentials"})
    return render_template("login.html")


@bp.route("/menu")
@login_required
def menu():
    return render_template("menu.html")

@bp.route("/load_history")
@login_required
def load_history():
    history_dir = get_data_file_path("backup")
    history_files = [f for f in os.listdir(history_dir) if f.endswith(".json")]
    history_files.sort(reverse=True)
    print(history_files)
    return jsonify({"history_files": history_files})

@bp.route('/load_selected_history', methods=['GET'])
@login_required
def load_selected_history():
    file_name = request.args.get('file_name')
    history_dir = get_data_file_path("backup")
    file_path = os.path.join(history_dir, file_name)
    base_labeled_file_path = get_data_file_path("order.json")
    now = datetime.now() + timedelta(hours=8)
    data_time = now.strftime("%Y-%m-%d-%H-%M")
    base_labeled_file_path_backup = os.path.join(history_dir, f"load_backup_backup_{data_time}.json")
    if os.path.exists(file_path):
        print(f"Loading selected history file {file_name} ...")
        shutil.copyfile(base_labeled_file_path, base_labeled_file_path_backup)
        shutil.copyfile(file_path, base_labeled_file_path)
        return jsonify("Success"), 200
    else:
        return jsonify("Failed"), 400


@bp.route("/annotate_formula")
@login_required
def annotate_formula():
    formula_image_names = []
    formula_info_file = get_data_file_path("formula.json")
    formula_info = load_json(formula_info_file)
    for image_name in os.listdir(IMGAREA_FOLDER):
        pre_label_file_name = os.path.splitext(image_name)[0] + "_res.json"
        formula_image_data[image_name] = {
            "pre_label_json": pre_label_file_name,
            "formula_info": formula_info.get(image_name, []),
        }
        pre_label_file_path = os.path.join(PRE_LABEL_FOLDER, pre_label_file_name)
        pre_label_anno = load_json(pre_label_file_path)
        if pre_label_anno:
            with_formula = False
            for anno in pre_label_anno["parsing_res_list"]:
                if anno["block_label"] == "formula":
                    with_formula = True
                    break
            if with_formula:
                formula_image_names.append(image_name)
    return render_template(
        "annotate_formula.html",
        image_names=formula_image_names,
        image_data=formula_image_data,
    )


@bp.route("/annotate_table")
@login_required
def annotate_table():
    table_image_names = []
    case_types = [
        "table_with_formula",
        "with_chinese_formula",
        "with_handwrited_formula",
    ]
    table_info_file = get_data_file_path("table.json")
    table_info = load_json(table_info_file)

    for image_name in os.listdir(IMGAREA_FOLDER):
        pre_label_file_name = os.path.splitext(image_name)[0] + "_res.json"
        table_image_data[image_name] = {
            "pre_label_json": pre_label_file_name,
            "table_info": table_info.get(image_name, []),
        }
        pre_label_file_path = os.path.join(PRE_LABEL_FOLDER, pre_label_file_name)
        pre_label_anno = load_json(pre_label_file_path)
        if pre_label_anno:
            with_table = False
            for anno in pre_label_anno["parsing_res_list"]:
                if anno["block_label"] == "table":
                    with_table = True
                    break
            if with_table:
                table_image_names.append(image_name)
    return render_template(
        "annotate_table.html",
        case_types=case_types,
        image_names=table_image_names,
        image_data=table_image_data,
    )


@bp.route("/get-colors", methods=["GET"])
def get_default_colors():
    try:
        colors_data = load_json(get_data_file_path("colors.json"))
        return jsonify(colors_data)
    except json.JSONDecodeError:
        return jsonify({"error": "Error parsing JSON"}), 500


@bp.route("/save-colors", methods=["POST"])
def update_default_colors():
    try:
        new_data = request.get_json()
        if not new_data:
            return jsonify({"error": "Invalid data"}), 400

        save_json(get_data_file_path("colors.json"), new_data)

        return jsonify({"message": "Configuration updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/")
@login_required
def index():
    return redirect(url_for("main.login"))
