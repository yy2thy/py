import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context

app = Flask(__name__, static_folder='.')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD_TXT_FILE = os.path.join(BASE_DIR, "leaderboard.txt")
PW_TXT_FILE = os.path.join(BASE_DIR, "pw.txt")

file_lock = threading.Lock()
update_condition = threading.Condition()
leaderboard_version = 0


def notify_clients():
    global leaderboard_version
    with update_condition:
        leaderboard_version += 1
        update_condition.notify_all()


def verify_teacher_password(input_pwd: str) -> bool:
    if not input_pwd or not os.path.exists(PW_TXT_FILE):
        return False
    try:
        with open(PW_TXT_FILE, "r", encoding="utf-8") as f:
            stored_pw = f.read().strip()
        return bool(stored_pw) and (input_pwd == stored_pw)
    except Exception:
        return False


def read_leaderboard_from_txt() -> dict:
    with file_lock:
        if not os.path.exists(LEADERBOARD_TXT_FILE):
            initial = {"students": {}, "updated_at": ""}
            with open(LEADERBOARD_TXT_FILE, "w", encoding="utf-8") as f:
                json.dump(initial, f, ensure_ascii=False, indent=2)
            return initial
        try:
            with open(LEADERBOARD_TXT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else {"students": {}, "updated_at": ""}
        except Exception:
            return {"students": {}, "updated_at": ""}


def write_leaderboard_to_txt(data: dict):
    with file_lock:
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        temp_file = LEADERBOARD_TXT_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, LEADERBOARD_TXT_FILE)
    notify_clients()


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    data = read_leaderboard_from_txt()
    resp = jsonify({
        "status": "ok",
        "data": data.get("students", {}),
        "updated_at": data.get("updated_at", ""),
        "version": leaderboard_version
    })
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/api/leaderboard/stream")
def stream_leaderboard():
    """Server-Sent Events endpoint pushing real-time updates to all open leaderboards"""
    def event_stream():
        local_ver = leaderboard_version
        yield f"data: {json.dumps({'version': local_ver})}\n\n"
        while True:
            with update_condition:
                update_condition.wait_for(lambda: leaderboard_version != local_ver, timeout=15.0)
                current_ver = leaderboard_version
            if current_ver != local_ver:
                local_ver = current_ver
                yield f"data: {json.dumps({'version': local_ver})}\n\n"
            else:
                yield ": keepalive\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@app.route("/api/progress", methods=["POST"])
def save_student_progress():
    payload = request.get_json(silent=True) or {}
    student_id = payload.get("student_id")
    record = payload.get("record")

    if not student_id or not isinstance(record, dict):
        return jsonify({"status": "error", "message": "無效的學生資料格式"}), 400

    data = read_leaderboard_from_txt()
    data["students"][student_id] = record
    write_leaderboard_to_txt(data)

    return jsonify({"status": "ok", "version": leaderboard_version})


@app.route("/api/admin/export-txt", methods=["POST"])
def export_leaderboard_txt():
    payload = request.get_json(silent=True) or {}
    if not verify_teacher_password(payload.get("password", "")):
        return jsonify({"status": "error", "message": "教師密碼錯誤（與 pw.txt 不符）"}), 403

    data = read_leaderboard_from_txt()
    students = data.get("students", {})

    lines = [
        "==========================================================",
        "香港道教聯合會圓玄學院第二中學 - 中三 Python 練習排行榜紀錄",
        f"匯出時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "==========================================================",
        "排名\t班別\t學號\t完成題數\tSkip題數\t總嘗試次數\t最後更新時間",
        "----------------------------------------------------------"
    ]

    sorted_list = sorted(
        students.values(),
        key=lambda s: (-len(s.get("solved", [])), s.get("totalAttempts", 0))
    )

    for idx, s in enumerate(sorted_list, start=1):
        cls_name = s.get("className", "")
        stu_no = str(s.get("studentNo", "")).zfill(2)
        solved_cnt = len(s.get("solved", []))
        skip_cnt = len(s.get("skipped", []))
        attempts = s.get("totalAttempts", 0)
        last_time = s.get("lastUpdated", "-")
        lines.append(f"{idx}\t{cls_name}\t{stu_no}\t{solved_cnt}\t\t{skip_cnt}\t\t{attempts}\t\t{last_time}")

    lines.append("==========================================================")
    return Response(
        "\n".join(lines),
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=leaderboard_report.txt"}
    )


@app.route("/api/admin/clear", methods=["POST"])
def clear_leaderboard():
    payload = request.get_json(silent=True) or {}
    if not verify_teacher_password(payload.get("password", "")):
        return jsonify({"status": "error", "message": "教師密碼錯誤（與 pw.txt 不符）"}), 403

    write_leaderboard_to_txt({"students": {}})
    return jsonify({"status": "ok", "message": "已成功清除 leaderboard.txt 內的所有學生紀錄"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True, debug=False)
