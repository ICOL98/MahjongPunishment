"""
麻将惩罚抽取程序 - 不能做 + 惩罚
"""
import random
import json
import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 数据存储文件（始终保存在 app.py 所在目录）
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(_BASE_DIR, "game_data.json")

# 默认玩家名称
PLAYERS = ["HT", "SJ1", "LY", "ZKL"]


def _default_data():
    """默认数据结构"""
    return {
        "phase": "input",
        "current_player_index": 0,
        "current_input_type": "dont_do",
        "player_dont_do": [[], [], [], []],
        "player_punishments": [[], [], [], []],
        "player_dont_do_confirmed": [False, False, False, False],
        "player_punishment_confirmed": [False, False, False, False],
        "shuffled_dont_do": [],
        "shuffled_punishment": [],
        "shuffled_display_order_dont_do": [],
        "shuffled_display_order_punishment": [],
        "used_dont_do": [],
        "used_punishment": [],
        "assigned_punishments": {},
    }


def load_data():
    """加载游戏数据（兼容旧格式）"""
    default = _default_data()
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return default
    # 合并默认值，确保新字段存在
    for k, v in default.items():
        if k not in data:
            data[k] = v
    # 旧格式迁移：若有 player_punishments 但无 player_dont_do，用空列表初始化
    if "player_dont_do" not in data:
        data["player_dont_do"] = [[], [], [], []]
    if "player_punishment_confirmed" not in data:
        data["player_punishment_confirmed"] = [False, False, False, False]
    if "player_dont_do_confirmed" not in data:
        data["player_dont_do_confirmed"] = [False, False, False, False]
    return data


def save_data(data):
    """保存游戏数据"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_state():
    """获取当前游戏状态"""
    data = load_data()
    return {
        "phase": data["phase"],
        "current_player_index": data["current_player_index"],
        "current_player_name": PLAYERS[data["current_player_index"]],
        "current_input_type": data.get("current_input_type", "dont_do"),
        "player_dont_do_confirmed": data.get("player_dont_do_confirmed", [False]*4),
        "player_punishment_confirmed": data.get("player_punishment_confirmed", [False]*4),
        "players": PLAYERS,
    }


@app.route("/")
def index():
    """主页面"""
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    """获取当前状态"""
    return jsonify(get_state())


@app.route("/api/current-items")
def api_current_items():
    """获取当前输入者的列表（不能做 或 惩罚）"""
    data = load_data()
    idx = data["current_player_index"]
    itype = data.get("current_input_type", "dont_do")
    if itype == "dont_do":
        items = data["player_dont_do"][idx]
    else:
        items = data["player_punishments"][idx]
    return jsonify({
        "items": items,
        "player_name": PLAYERS[idx],
        "input_type": itype,
    })


@app.route("/api/add-item", methods=["POST"])
def api_add_item():
    """添加项（不能做 或 惩罚）"""
    data = load_data()
    if data["phase"] != "input":
        return jsonify({"error": "当前不是输入阶段"}), 400
    content = request.json.get("content", "").strip()
    itype = request.json.get("type", "dont_do")
    if not content:
        return jsonify({"error": "内容不能为空"}), 400
    idx = data["current_player_index"]
    if itype == "dont_do":
        data["player_dont_do"][idx].append(content)
        items = data["player_dont_do"][idx]
    else:
        data["player_punishments"][idx].append(content)
        items = data["player_punishments"][idx]
    save_data(data)
    return jsonify({"items": items})


@app.route("/api/update-item", methods=["POST"])
def api_update_item():
    """更新项"""
    data = load_data()
    if data["phase"] != "input":
        return jsonify({"error": "当前不是输入阶段"}), 400
    idx = data["current_player_index"]
    itype = request.json.get("type", "dont_do")
    item_idx = request.json.get("index", -1)
    content = request.json.get("content", "").strip()
    arr = data["player_dont_do"][idx] if itype == "dont_do" else data["player_punishments"][idx]
    if item_idx < 0 or item_idx >= len(arr):
        return jsonify({"error": "索引无效"}), 400
    if not content:
        return jsonify({"error": "内容不能为空"}), 400
    arr[item_idx] = content
    save_data(data)
    return jsonify({"items": arr})


@app.route("/api/delete-item", methods=["POST"])
def api_delete_item():
    """删除项"""
    data = load_data()
    if data["phase"] != "input":
        return jsonify({"error": "当前不是输入阶段"}), 400
    idx = data["current_player_index"]
    itype = request.json.get("type", "dont_do")
    item_idx = request.json.get("index", -1)
    arr = data["player_dont_do"][idx] if itype == "dont_do" else data["player_punishments"][idx]
    if item_idx < 0 or item_idx >= len(arr):
        return jsonify({"error": "索引无效"}), 400
    arr.pop(item_idx)
    save_data(data)
    return jsonify({"items": arr})


@app.route("/api/confirm", methods=["POST"])
def api_confirm():
    """当前玩家确认当前列表"""
    data = load_data()
    if data["phase"] != "input":
        return jsonify({"error": "当前不是输入阶段"}), 400
    idx = data["current_player_index"]
    itype = data.get("current_input_type", "dont_do")
    if itype == "dont_do":
        arr = data["player_dont_do"][idx]
        if len(arr) == 0:
            return jsonify({"error": "至少需要添加一个「不能做」"}), 400
        data["player_dont_do_confirmed"][idx] = True
        data["current_input_type"] = "punishment"
    else:
        arr = data["player_punishments"][idx]
        if len(arr) == 0:
            return jsonify({"error": "至少需要添加一个「惩罚」"}), 400
        data["player_punishment_confirmed"][idx] = True
        data["current_input_type"] = "dont_do"
        if idx < 3:
            data["current_player_index"] = idx + 1
        else:
            data["phase"] = "shuffle_confirm"
    save_data(data)
    return jsonify(get_state())


@app.route("/api/draw", methods=["POST"])
def api_draw():
    """抽取：从不能做和惩罚各随机一个"""
    data = load_data()
    if data["phase"] != "draw":
        return jsonify({"error": "当前不是抽取阶段"}), 400
    player_name = request.json.get("player_name", "").strip()
    if player_name not in PLAYERS:
        return jsonify({"error": "无效的玩家名称"}), 400
    if player_name in data["assigned_punishments"]:
        prev = data["assigned_punishments"][player_name]
        return jsonify({
            "error": "你已经抽取过了",
            "dont_do": prev["dont_do"],
            "punishment": prev["punishment"],
        }), 400
    if not data["shuffled_dont_do"] or not data["shuffled_punishment"]:
        return jsonify({"error": "没有可抽取的内容"}), 400
    dont_do = data["shuffled_dont_do"].pop()
    punishment = data["shuffled_punishment"].pop()
    data["assigned_punishments"][player_name] = {"dont_do": dont_do, "punishment": punishment}
    data.setdefault("used_dont_do", []).append(dont_do)
    data.setdefault("used_punishment", []).append(punishment)
    save_data(data)
    return jsonify({"dont_do": dont_do, "punishment": punishment, "player_name": player_name})


@app.route("/api/confirm-shuffle", methods=["POST"])
def api_confirm_shuffle():
    """确认并打乱顺序"""
    data = load_data()
    if data["phase"] != "shuffle_confirm":
        return jsonify({"error": "当前不是确认打乱阶段"}), 400
    all_dont_do = []
    all_punishment = []
    for i in range(4):
        all_dont_do.extend(data["player_dont_do"][i])
        all_punishment.extend(data["player_punishments"][i])
    random.shuffle(all_dont_do)
    random.shuffle(all_punishment)
    data["shuffled_dont_do"] = list(all_dont_do)
    data["shuffled_punishment"] = list(all_punishment)
    data["shuffled_display_order_dont_do"] = list(all_dont_do)
    data["shuffled_display_order_punishment"] = list(all_punishment)
    data["used_dont_do"] = []
    data["used_punishment"] = []
    data["phase"] = "draw"
    save_data(data)
    return jsonify(get_state())


@app.route("/api/punishment-summary")
def api_punishment_summary():
    """惩罚汇总"""
    data = load_data()
    if data["phase"] == "shuffle_confirm":
        summary = []
        for i, name in enumerate(PLAYERS):
            dlist = data["player_dont_do"][i]
            plist = data["player_punishments"][i]
            summary.append({
                "player_name": name,
                "dont_do_count": len(dlist),
                "punishment_count": len(plist),
                "dont_do_masked": [{"masked": "*" * 5} for _ in dlist],
                "punishment_masked": [{"masked": "*" * 5} for _ in plist],
            })
        return jsonify({"mode": "per_player", "summary": summary})
    if data["phase"] == "draw":
        used_d = set(data.get("used_dont_do") or [])
        used_p = set(data.get("used_punishment") or [])
        display_d = data.get("shuffled_display_order_dont_do") or []
        display_p = data.get("shuffled_display_order_punishment") or []
        combined_d = [{"masked": "*" * 5, "drawn": x in used_d} for x in display_d]
        combined_p = [{"masked": "*" * 5, "drawn": x in used_p} for x in display_p]
        return jsonify({
            "mode": "combined",
            "combined_dont_do": combined_d,
            "combined_punishment": combined_p,
            "total_dont_do": len(display_d),
            "total_punishment": len(display_p),
            "used_dont_do_count": len(used_d),
            "used_punishment_count": len(used_p),
        })
    return jsonify({"error": "当前阶段无法获取汇总"}), 400


@app.route("/api/my-punishment")
def api_my_punishment():
    """根据姓名查看自己的惩罚"""
    player_name = request.args.get("name", "").strip()
    if not player_name:
        return jsonify({"error": "请输入姓名"}), 400
    data = load_data()
    if player_name not in data["assigned_punishments"]:
        return jsonify({"error": "未找到该玩家的记录，请确认姓名正确"}), 404
    obj = data["assigned_punishments"][player_name]
    return jsonify({
        "player_name": player_name,
        "dont_do": obj["dont_do"],
        "punishment": obj["punishment"],
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """重置游戏"""
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    return jsonify(get_state())


@app.route("/api/redraw", methods=["POST"])
def api_redraw():
    """重新抽取"""
    data = load_data()
    if data["phase"] != "draw":
        return jsonify({"error": "当前不是抽取阶段"}), 400
    all_d = []
    all_p = []
    for i in range(4):
        all_d.extend(data["player_dont_do"][i])
        all_p.extend(data["player_punishments"][i])
    used_d = set(data.get("used_dont_do") or [])
    used_p = set(data.get("used_punishment") or [])
    avail_d = [x for x in all_d if x not in used_d]
    avail_p = [x for x in all_p if x not in used_p]
    if len(avail_d) < len(PLAYERS) or len(avail_p) < len(PLAYERS):
        return jsonify({
            "error": f"「不能做」或「惩罚」剩余不足{len(PLAYERS)}条，游戏结束。可点击「重新开始游戏」。"
        }), 400
    random.shuffle(avail_d)
    random.shuffle(avail_p)
    data["shuffled_dont_do"] = list(avail_d)
    data["shuffled_punishment"] = list(avail_p)
    data["assigned_punishments"] = {}
    save_data(data)
    return jsonify(get_state())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
