"""
麻将惩罚随机抽取程序 - 后端
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


def load_data():
    """加载游戏数据"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "phase": "input",  # input | shuffle_confirm | draw
        "current_player_index": 0,
        "player_punishments": [[], [], [], []],
        "player_confirmed": [False, False, False, False],
        "shuffled_punishments": [],  # 可抽取的惩罚池（抽取时pop）
        "shuffled_display_order": [],  # 完整大列表（用于展示，永远不变）
        "used_punishments": [],  # 累计已抽取过的惩罚（划掉不参与后续抽取）
        "assigned_punishments": {},  # 本轮每人抽到的 {"HT": "惩罚内容", ...}
        "draw_order": 0,  # 当前该谁抽 (0-3)
    }


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
        "player_confirmed": data["player_confirmed"],
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


@app.route("/api/current-punishments")
def api_current_punishments():
    """获取当前输入者的惩罚列表（仅当前玩家可见）"""
    data = load_data()
    idx = data["current_player_index"]
    return jsonify({
        "punishments": data["player_punishments"][idx],
        "player_name": PLAYERS[idx],
    })


@app.route("/api/add-punishment", methods=["POST"])
def api_add_punishment():
    """添加惩罚"""
    data = load_data()
    if data["phase"] != "input":
        return jsonify({"error": "当前不是输入阶段"}), 400
    content = request.json.get("content", "").strip()
    if not content:
        return jsonify({"error": "惩罚内容不能为空"}), 400
    idx = data["current_player_index"]
    data["player_punishments"][idx].append(content)
    save_data(data)
    return jsonify({"punishments": data["player_punishments"][idx]})


@app.route("/api/update-punishment", methods=["POST"])
def api_update_punishment():
    """更新惩罚"""
    data = load_data()
    if data["phase"] != "input":
        return jsonify({"error": "当前不是输入阶段"}), 400
    idx = data["current_player_index"]
    item_idx = request.json.get("index", -1)
    content = request.json.get("content", "").strip()
    if item_idx < 0 or item_idx >= len(data["player_punishments"][idx]):
        return jsonify({"error": "索引无效"}), 400
    if not content:
        return jsonify({"error": "惩罚内容不能为空"}), 400
    data["player_punishments"][idx][item_idx] = content
    save_data(data)
    return jsonify({"punishments": data["player_punishments"][idx]})


@app.route("/api/delete-punishment", methods=["POST"])
def api_delete_punishment():
    """删除惩罚"""
    data = load_data()
    if data["phase"] != "input":
        return jsonify({"error": "当前不是输入阶段"}), 400
    idx = data["current_player_index"]
    item_idx = request.json.get("index", -1)
    if item_idx < 0 or item_idx >= len(data["player_punishments"][idx]):
        return jsonify({"error": "索引无效"}), 400
    data["player_punishments"][idx].pop(item_idx)
    save_data(data)
    return jsonify({"punishments": data["player_punishments"][idx]})


@app.route("/api/confirm", methods=["POST"])
def api_confirm():
    """当前玩家确认惩罚列表"""
    data = load_data()
    if data["phase"] != "input":
        return jsonify({"error": "当前不是输入阶段"}), 400
    idx = data["current_player_index"]
    if len(data["player_punishments"][idx]) == 0:
        return jsonify({"error": "至少需要添加一个惩罚"}), 400
    data["player_confirmed"][idx] = True
    if idx < 3:
        data["current_player_index"] = idx + 1
    else:
        # 所有人确认完毕，进入确认打乱阶段（暂不打乱）
        data["phase"] = "shuffle_confirm"
    save_data(data)
    return jsonify(get_state())


@app.route("/api/draw", methods=["POST"])
def api_draw():
    """抽取惩罚"""
    data = load_data()
    if data["phase"] != "draw":
        return jsonify({"error": "当前不是抽取阶段"}), 400
    player_name = request.json.get("player_name", "").strip()
    if player_name not in PLAYERS:
        return jsonify({"error": "无效的玩家名称"}), 400
    if player_name in data["assigned_punishments"]:
        return jsonify({
            "error": "你已经抽取过了",
            "punishment": data["assigned_punishments"][player_name],
        }), 400
    if not data["shuffled_punishments"]:
        return jsonify({"error": "没有可抽取的惩罚"}), 400
    # 从池中分配一个给该玩家，并加入已使用列表（划掉，不参与后续抽取）
    punishment = data["shuffled_punishments"].pop()
    data["assigned_punishments"][player_name] = punishment
    if "used_punishments" not in data:
        data["used_punishments"] = []
    data["used_punishments"].append(punishment)
    save_data(data)
    return jsonify({"punishment": punishment, "player_name": player_name})


@app.route("/api/confirm-shuffle", methods=["POST"])
def api_confirm_shuffle():
    """确认并打乱顺序，进入抽取阶段"""
    data = load_data()
    if data["phase"] != "shuffle_confirm":
        return jsonify({"error": "当前不是确认打乱阶段"}), 400
    all_punishments = []
    for plist in data["player_punishments"]:
        all_punishments.extend(plist)
    random.shuffle(all_punishments)
    data["shuffled_punishments"] = list(all_punishments)
    data["shuffled_display_order"] = list(all_punishments)
    data["used_punishments"] = []
    data["phase"] = "draw"
    save_data(data)
    return jsonify(get_state())


@app.route("/api/acknowledge", methods=["POST"])
def api_acknowledge():
    """已知晓（确认已看到抽到的惩罚）"""
    # 此接口可选，前端点击已知晓后可以隐藏结果
    # 数据已在 draw 时记录
    return jsonify({"ok": True})


@app.route("/api/punishment-summary")
def api_punishment_summary():
    """获取惩罚汇总
    - shuffle_confirm 阶段: 按人分别显示（含数量）
    - draw 阶段: 打乱后的大列表（不含谁添加的，含已抽取划掉）
    """
    data = load_data()
    if data["phase"] == "shuffle_confirm":
        summary = []
        for i, name in enumerate(PLAYERS):
            plist = data["player_punishments"][i]
            masked_items = [{"masked": "*" * 5, "drawn": False} for _ in plist]
            summary.append({
                "player_name": name,
                "count": len(plist),
                "masked_items": masked_items,
            })
        return jsonify({"mode": "per_player", "summary": summary})
    if data["phase"] == "draw":
        used_set = set(data.get("used_punishments") or [])
        display_order = data.get("shuffled_display_order")
        if not display_order:
            all_p = []
            for plist in data["player_punishments"]:
                all_p.extend(plist)
            display_order = all_p
        combined = [{"masked": "*" * 5, "drawn": p in used_set} for p in display_order]
        return jsonify({
            "mode": "combined",
            "combined_items": combined,
            "total_count": len(display_order),
            "used_count": len(used_set),
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
        return jsonify({"error": "未找到该玩家的惩罚记录，请确认姓名正确"}), 404
    return jsonify({
        "player_name": player_name,
        "punishment": data["assigned_punishments"][player_name],
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """重置游戏（用于重新开始，全部清零）"""
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    return jsonify(get_state())


@app.route("/api/redraw", methods=["POST"])
def api_redraw():
    """重新抽取惩罚（大列表不变，划掉的保留显示，从未划掉的中打乱重新抽取）"""
    data = load_data()
    if data["phase"] != "draw":
        return jsonify({"error": "当前不是抽取阶段"}), 400
    all_punishments = []
    for plist in data["player_punishments"]:
        all_punishments.extend(plist)
    used_set = set(data.get("used_punishments") or [])
    available = [p for p in all_punishments if p not in used_set]
    if len(available) < len(PLAYERS):
        return jsonify({
            "error": f"剩余可抽取的惩罚不足{len(PLAYERS)}条，游戏结束。可点击「重新开始游戏」从头录入。"
        }), 400
    random.shuffle(available)
    data["shuffled_punishments"] = list(available)
    data["assigned_punishments"] = {}
    save_data(data)
    return jsonify(get_state())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
