from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from flask_cors import CORS
import os
import base64
from bson.objectid import ObjectId

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(app.root_path, "known_faces")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# MongoDB URI
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://cuong123:cuong123@cluster0.htvcj.mongodb.net/")
client = MongoClient(MONGO_URI)
db = client["face_database"]
collection = db["face_data"]

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --------------------- HTML WEB ROUTES ---------------------

@app.route("/", methods=["GET"])
def home():
    users = list(collection.find())
    return render_template("index.html", users=users)

@app.route("/known_faces/<filename>")
def known_faces(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/upload_image", methods=["POST"])
def upload_image():
    name = request.form.get("name")
    if 'image' not in request.files or not name:
        return "Thiếu ảnh hoặc tên!", 400

    file = request.files['image']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        collection.insert_one({"name": name, "filename": filename})
        return redirect(url_for('home'))
    return "File không hợp lệ", 400

@app.route("/upload_webcam", methods=["POST"])
def upload_webcam():
    data = request.get_json()
    name = data.get("name")
    image_base64 = data.get("image")

    if not name or not image_base64:
        return jsonify({"error": "Thiếu dữ liệu!"}), 400

    image_data = base64.b64decode(image_base64.split(",")[1])
    filename = f"{secure_filename(name)}.jpg"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(path, "wb") as f:
        f.write(image_data)

    collection.insert_one({"name": name, "filename": filename})
    return jsonify({"message": "Tải ảnh thành công!"})

@app.route("/delete/<username>")
def delete_user(username):
    user = collection.find_one({"name": username})
    if user:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], user['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        collection.delete_one({"_id": user["_id"]})
    return redirect(url_for('home'))

@app.route("/rename", methods=["POST"])
def rename_user():
    user_id = request.form.get("user_id")
    new_name = request.form.get("new_name")
    if not user_id or not new_name:
        return "Thiếu dữ liệu!", 400
    collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"name": new_name}})
    return redirect(url_for('home'))

# --------------------- API ROUTES (cho Flutter hoặc JS) ---------------------

@app.route("/api/users", methods=["GET"])
def api_get_users():
    users = list(collection.find())
    result = [{"_id": str(user["_id"]), "name": user["name"], "image_url": url_for('known_faces', filename=user["filename"], _external=True)} for user in users]
    return jsonify(result)

@app.route("/api/upload", methods=["POST"])
def api_upload_image():
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({"error": "Thiếu dữ liệu!"}), 400

    file = request.files['image']
    name = request.form['name']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        collection.insert_one({"name": name, "filename": filename})
        return jsonify({"message": "Upload thành công!"})
    return jsonify({"error": "File không hợp lệ!"}), 400

@app.route("/api/delete_user/<user_id>", methods=["DELETE"])
def api_delete_user(user_id):
    user = collection.find_one({"_id": ObjectId(user_id)})
    if user:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], user['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        collection.delete_one({"_id": ObjectId(user_id)})
        return jsonify({"message": "Xóa thành công!"})
    return jsonify({"error": "Không tìm thấy user!"}), 404

@app.route("/api/rename_user", methods=["POST"])
def api_rename_user():
    data = request.get_json()
    user_id = data.get("user_id")
    new_name = data.get("new_name")
    if not user_id or not new_name:
        return jsonify({"error": "Thiếu dữ liệu!"}), 400
    collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"name": new_name}})
    return jsonify({"message": "Đổi tên thành công!"})

# --------------------- RUN APP ---------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
