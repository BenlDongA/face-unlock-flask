import base64
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import os

app = Flask(__name__)

# Thư mục lưu ảnh
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../known_faces"))
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Kết nối MongoDB
client = MongoClient("mongodb+srv://cuong123:cuong123@cluster0.htvcj.mongodb.net/")
db = client["face_unlock"]
collection = db["users"]

# Kiểm tra định dạng file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    users = list(collection.find({}, {"_id": 0}))  # Lấy toàn bộ người dùng
    return render_template('index.html', users=users)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    name = request.form.get('name')

    if file and allowed_file(file.filename) and name:
        filename = secure_filename(f"{name}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Lưu vào MongoDB
        collection.insert_one({"name": name, "filename": filename})

    return redirect(url_for('index'))

@app.route('/upload_webcam', methods=['POST'])
def upload_webcam():
    data = request.get_json()
    name = data.get("name")
    image_data = data.get("image")

    if not name or not image_data:
        return jsonify({"error": "Thiếu dữ liệu"}), 400

    header, encoded = image_data.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    filename = secure_filename(name) + ".jpg"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(filepath, "wb") as f:
        f.write(img_bytes)

    # Lưu vào MongoDB
    collection.insert_one({"name": name, "filename": filename})
    return jsonify({"message": "OK"})

@app.route('/delete/<username>', methods=['GET'])
def delete_user(username):
    # Xoá ảnh khỏi thư mục
    for ext in ALLOWED_EXTENSIONS:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{username}.{ext}")
        if os.path.exists(filepath):
            os.remove(filepath)
            break
    # Xoá khỏi MongoDB
    collection.delete_one({"name": username})
    return redirect(url_for('index'))

@app.route('/rename_user', methods=['POST'])
def rename_user():
    old_filename = request.form['old_name']
    new_name = request.form['new_name'].strip()
    ext = os.path.splitext(old_filename)[1]

    if not new_name:
        return redirect(url_for('index'))

    old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
    new_filename = secure_filename(new_name) + ext
    new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

    if os.path.exists(new_path):
        return "Tên mới đã tồn tại!", 400

    try:
        os.rename(old_path, new_path)
    except FileNotFoundError:
        return "Không tìm thấy file để đổi tên", 404

    # Cập nhật trong MongoDB
    collection.update_one(
        {"filename": old_filename},
        {"$set": {"name": new_name, "filename": new_filename}}
    )

    return redirect(url_for('index'))

@app.route('/known_faces/<filename>')
def known_faces(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
