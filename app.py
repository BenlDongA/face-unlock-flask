from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from pymongo import MongoClient
import base64
from bson.objectid import ObjectId

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

# MongoDB
MONGO_URI = "mongodb+srv://cuong123:cuong123@cluster0.htvcj.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client["face_database"]
collection = db["face_data"]

# --------------------- HTML WEB ROUTES ---------------------

@app.route("/", methods=["GET"])
def home():
    users = list(collection.find())
    return render_template("index.html", users=users)

@app.route("/upload_image", methods=["POST"])
def upload_image():
    name = request.form.get("name")
    file = request.files.get("image")

    if not name or not file:
        return "Thiếu tên hoặc ảnh!", 400

    image_data = base64.b64encode(file.read()).decode('utf-8')
    collection.insert_one({"name": name, "image_base64": image_data})
    return redirect(url_for("home"))

@app.route("/upload_webcam", methods=["POST", "OPTIONS"])
def upload_webcam():
    if request.method == "OPTIONS":
        return jsonify({"message": "CORS Preflight"}), 200

    data = request.get_json()
    name = data.get("name")
    image_base64 = data.get("image")

    if not name or not image_base64:
        return jsonify({"error": "Thiếu dữ liệu!"}), 400

    # Loại bỏ header data:image/jpeg;base64,...
    encoded = image_base64.split(",")[1]
    collection.insert_one({"name": name, "image_base64": encoded})
    return jsonify({"message": "Tải ảnh thành công!"})

@app.route("/delete/<username>")
def delete_user(username):
    user = collection.find_one({"name": username})
    if user:
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

# --------------------- API ROUTES ---------------------

@app.route("/api/users", methods=["GET"])
def api_get_users():
    users = list(collection.find())
    result = []
    for user in users:
        result.append({
            "_id": str(user["_id"]),
            "name": user["name"],
            "image_base64": f"data:image/jpeg;base64,{user['image_base64']}"
        })
    return jsonify(result)

@app.route("/api/upload", methods=["POST"])
def api_upload_image():
    file = request.files.get("image")
    name = request.form.get("name")

    if not file or not name:
        return jsonify({"error": "Thiếu dữ liệu!"}), 400

    encoded = base64.b64encode(file.read()).decode('utf-8')
    collection.insert_one({"name": name, "image_base64": encoded})
    return jsonify({"message": "Upload thành công!"})

@app.route("/api/delete_user/<user_id>", methods=["DELETE"])
def api_delete_user(user_id):
    result = collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Không tìm thấy user!"}), 404
    return jsonify({"message": "Xóa thành công!"})

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
