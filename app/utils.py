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

from app.models import User


def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_data_file_path(filename):
    return os.path.join(os.path.dirname(__file__), "data", filename)


def load_users():
    file_path = get_data_file_path("user_info.json")
    try:
        users_data = load_json(file_path)
        return {
            username: User(id=data["id"], username=username, password=data["password"])
            for username, data in users_data.items()
        }
    except FileNotFoundError:
        return {}


def save_users(users):
    file_path = get_data_file_path("user_info.json")
    users_data = {username: user.__dict__ for username, user in users.items()}
    save_json(file_path, users_data)


def create_or_update_symlink(src, dest):
    # 如果软连接已存在且指向的是一个目录，则删除它
    if os.path.islink(dest):
        os.unlink(dest)
    elif os.path.exists(dest):
        # 如果目标位置已经存在且不是软连接，抛出异常或自行处理
        raise Exception(f"The destination {dest} already exists and is not a symlink")

    # 创建新的软连接
    os.symlink(src, dest)
    print(f"Created symlink from {src} to {dest}")
