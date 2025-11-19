import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
from io import BytesIO
from deep_translator import GoogleTranslator
from collections import defaultdict


# ======================
# CẤU HÌNH & LOGIC CỐT LÕI
# ======================
class InferenceEngine:
    def __init__(self, filename="knowledge_base.txt"):
        # Cấu trúc: target_obj -> list of required_feature_sets
        # Ví dụ: "computer" -> [{'screen', 'keyboard'}, {'laptop'}, {'desktop'}]
        self.knowledge = defaultdict(list)
        self.load_rules(filename)
        self.en_translator = GoogleTranslator(source='auto', target='en')
        self.vi_translator = GoogleTranslator(source='en', target='vi')

    def load_rules(self, filename):
        """Đọc file luật format mới: A & B -> C | Label"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "->" not in line or line.startswith("#"):
                        continue

                    # Tách phần Giả thiết và Kết luận
                    left, right = line.split("->", 1)
                    conclusion = right.split("|")[0].strip().lower()
                    premises_str = left.strip().lower()

                    # Xử lý logic AND (&) và OR (v)
                    if "&" in premises_str:
                        # Luật cấu tạo: Cần tất cả các phần tử
                        required_feats = set(p.strip() for p in premises_str.split("&"))
                        self.knowledge[conclusion].append(required_feats)
                    elif "v" in premises_str:
                        # Luật phân loại: Cần bất kỳ phần tử nào (tách thành nhiều tập luật đơn)
                        options = [p.strip() for p in premises_str.split("v")]
                        for opt in options:
                            self.knowledge[conclusion].append({opt})
                    else:
                        # Luật đơn: A -> B
                        self.knowledge[conclusion].append({premises_str})

        except FileNotFoundError:
            return False
        return True

    def infer(self, user_input_vi):
        """Suy luận dựa trên độ khớp (Matching Score)"""
        if not user_input_vi:
            return None, 0

        # 1. Dịch input sang tiếng Anh
        try:
            input_en = self.en_translator.translate(user_input_vi).lower()
            # Tách các từ khóa (ví dụ: "bánh xe, động cơ")
            user_feats = set(x.strip() for x in input_en.replace(",", " ").split() if x.strip())
            # Thêm cả cụm từ nguyên vẹn phòng trường hợp tách từ sai
            user_feats.add(input_en)
            # Xử lý trường hợp nhập dấu phẩy
            user_feats.update(x.strip() for x in input_en.split(","))
        except Exception as e:
            print(f"Lỗi dịch: {e}")
            return None, 0

        best_obj = None
        best_score = 0

        # 2. Quét qua toàn bộ tri thức
        for obj, rule_sets in self.knowledge.items():
            # Một vật có thể có nhiều cách định nghĩa (nhiều rule_sets)
            # Lấy điểm cao nhất trong các cách đó
            obj_max_score = 0

            for required_set in rule_sets:
                # Tính độ phủ: Bao nhiêu phần tử trong required_set xuất hiện trong user_feats
                if not required_set: continue

                matched = len(required_set.intersection(user_feats))
                score = matched / len(required_set)

                if score > obj_max_score:
                    obj_max_score = score

            # Cập nhật vật tốt nhất toàn cục
            if obj_max_score > best_score:
                best_score = obj_max_score
                best_obj = obj
            # Nếu điểm bằng nhau, ưu tiên vật có tên dài hơn (thường cụ thể hơn)
            elif obj_max_score == best_score and best_score > 0:
                if best_obj and len(obj) > len(best_obj):
                    best_obj = obj

        return best_obj, best_score


# ======================
# GIAO DIỆN NGƯỜI DÙNG
# ======================
class UserGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔍 Tìm vật theo đặc trưng (Deep Search)")
        self.geometry("750x600")
        self.configure(bg="#f0f2f5")

        # Khởi động Engine
        self.engine = InferenceEngine("wordnet.txt")  # Hoặc rules.txt tùy file bạn lưu
        if not self.engine.knowledge:
            messagebox.showwarning("Cảnh báo",
                                   "Chưa tìm thấy file dữ liệu hoặc file rỗng!\nVui lòng dùng Admin GUI để tạo file trước.")

        # UI Components
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Mô tả vật bạn muốn tìm:", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text="(Ví dụ: bánh xe và động cơ, hoặc màn hình và bàn phím)",
                  font=("Segoe UI", 10, "italic")).pack(pady=(0, 10))

        self.entry = ttk.Entry(main_frame, font=("Segoe UI", 12), width=50)
        self.entry.pack(pady=5, ipady=5)
        self.entry.bind("<Return>", lambda e: self.on_search())

        ttk.Button(main_frame, text="🔍 Phân tích & Tìm kiếm", command=self.on_search).pack(pady=15)

        self.result_label = ttk.Label(main_frame, text="...", font=("Segoe UI", 13), wraplength=700, justify="center")
        self.result_label.pack(pady=10)

        self.img_label = ttk.Label(main_frame)
        self.img_label.pack(pady=10, expand=True)

    def on_search(self):
        user_in = self.entry.get().strip()
        if not user_in:
            return

        self.result_label.config(text="⏳ Đang suy luận...")
        self.img_label.config(image="")
        self.update()

        # Gọi Engine suy luận
        best_obj, score = self.engine.infer(user_in)

        if score >= 0.5:  # Ngưỡng tin cậy tối thiểu
            try:
                vi_name = self.engine.vi_translator.translate(best_obj).title()
            except:
                vi_name = best_obj.title()

            # Hiển thị kết quả
            confidence = int(score * 100)
            self.result_label.config(
                text=f"✅ Kết quả: {vi_name} ({best_obj})\n🎯 Độ tin cậy: {confidence}%",
                foreground="#007acc"
            )
            self.show_image(best_obj)
        else:
            self.result_label.config(
                text=f"❌ Không tìm thấy vật phù hợp trong cơ sở tri thức.\nHãy thử mô tả chi tiết hơn.",
                foreground="red"
            )

    def show_image(self, keyword):
        """Tải ảnh từ Pixabay"""
        try:
            # API Key Pixabay (Miễn phí)
            api_key = "53101775-37777e069e2eb137c3c11588e"
            url = f"https://pixabay.com/api/?key={api_key}&q={keyword}&image_type=photo&per_page=3"

            response = requests.get(url, timeout=5)
            data = response.json()

            if data.get("hits"):
                img_url = data["hits"][0]["webformatURL"]
                raw_data = requests.get(img_url, timeout=5).content

                image = Image.open(BytesIO(raw_data))
                # Resize giữ tỉ lệ
                image.thumbnail((350, 350))
                photo = ImageTk.PhotoImage(image)

                self.img_label.config(image=photo)
                self.img_label.image = photo  # Giữ tham chiếu để không bị GC thu hồi
            else:
                self.img_label.config(image="", text="(Không tìm thấy ảnh minh họa)")
        except Exception as e:
            print(f"Lỗi tải ảnh: {e}")
            self.img_label.config(image="", text="(Lỗi kết nối ảnh)")


if __name__ == "__main__":
    app = UserGUI()
    app.mainloop()