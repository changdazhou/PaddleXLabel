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
import argparse

from app import create_app
from app.routes import init_src_data


def get_args():
    parser = argparse.ArgumentParser("PaddleNLP")
    parser.add_argument(
        "--src_data_folder",
        type=str,
        default="",
        help="The path of source data folder.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8866,
        help="The port number of server.",
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = get_args()
    init_src_data(args.src_data_folder)

    app = create_app()

    print(f"SRC_DATA_FOLDER: {args.src_data_folder}")

    app.run(host="0.0.0.0", port=args.port, debug=True)
