import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
from io import BytesIO
from googletrans import Translator
from collections import defaultdict, Counter

translator = Translator()

# ======================
# ĐỌC TRI THỨC DẠNG object: feat1, feat2
# ======================
def load_feature_map(filename="knowledge_base.txt"):
    feature_map = defaultdict(set)
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if ":" not in line:
                    continue
                obj, feats = line.strip().split(":", 1)
                feats = [x.strip().lower() for x in feats.split(",") if x.strip()]
                feature_map[obj.strip().lower()].update(feats)
    except FileNotFoundError:
        messagebox.showerror("Lỗi", "Không tìm thấy file knowledge_base.txt!")
    return feature_map


# ======================
# GIAO DIỆN NGƯỜI DÙNG
# ======================
class UserGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("🔍 Tìm vật theo đặc trưng")
        self.master.geometry("750x550")

        # Tải tri thức mới dạng object -> features
        self.feature_map = load_feature_map()

        ttk.Label(master, text="Nhập các đặc trưng (cách nhau dấu phẩy):",
                  font=("Segoe UI", 11)).pack(pady=10)

        self.entry = ttk.Entry(master, width=70)
        self.entry.pack(pady=5)

        ttk.Button(master, text="🧠 Tìm vật", command=self.on_infer).pack(pady=10)

        self.result_text = ttk.Label(master, text="", font=("Segoe UI", 12))
        self.result_text.pack(pady=10)

        self.img_label = ttk.Label(master)
        self.img_label.pack(pady=10)

    # ======================
    # Tìm vật theo rate đặc trưng
    # ======================
    def on_infer(self):
        user_input = self.entry.get().strip()
        if not user_input:
            messagebox.showwarning("Lỗi", "Bạn phải nhập ít nhất 1 đặc trưng!")
            return

        # Dịch sang tiếng Anh
        try:
            translated = translator.translate(user_input, src="vi", dest="en").text
        except:
            translated = user_input

        input_feats = [x.strip().lower() for x in translated.split(",") if x.strip()]
        scores = Counter()

        # So khớp đặc trưng
        for obj, feats in self.feature_map.items():
            matched = len(set(input_feats) & feats)
            if matched > 0:
                scores[obj] = matched / len(feats)

        if not scores:
            self.result_text.config(text="❌ Không tìm thấy vật phù hợp.")
            self.img_label.config(image="", text="")
            return

        # Sắp xếp vật theo mức độ phù hợp
        best_obj, best_score = scores.most_common(1)[0]

        # Dịch vật sang tiếng Việt
        try:
            vi_name = translator.translate(best_obj, src="en", dest="vi").text
        except:
            vi_name = best_obj

        self.result_text.config(
            text=f"✅ Vật phù hợp nhất: {vi_name} ({best_obj})\nĐộ khớp: {best_score:.2f}"
        )

        # Tải ảnh minh họa
        self.show_image(best_obj)

    # ======================
    # Ảnh minh họa bằng Pixabay
    # ======================
    def show_image(self, keyword):
        try:
            api_key = "53101775-37777e069e2eb137c3c11588e"  # key bạn đã dùng
            url = f"https://pixabay.com/api/?key={api_key}&q={keyword}&image_type=photo&per_page=3"
            headers = {"User-Agent": "Mozilla/5.0"}

            response = requests.get(url, headers=headers, timeout=6)
            data = response.json()

            if "hits" in data and data["hits"]:
                img_url = data["hits"][0]["webformatURL"]
                img_data = requests.get(img_url, headers=headers, timeout=6).content
                img = Image.open(BytesIO(img_data)).resize((260, 260))
                self.photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=self.photo)
            else:
                self.img_label.config(text="(Không tìm thấy ảnh minh họa)")
        except Exception as e:
            print("⚠️ Ảnh lỗi:", e)
            self.img_label.config(text="(Không tải được ảnh minh họa)")


# ======================
# CHẠY GIAO DIỆN
# ======================
if __name__ == "__main__":
    root = tk.Tk()
    app = UserGUI(root)
    root.mainloop()
