import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
from io import BytesIO
from collections import defaultdict


# ======================
# CẤU HÌNH & LOGIC CỐT LÕI
# ======================
class InferenceEngine:
    def __init__(self, filename="knowledge_base.txt"):
        # Cấu trúc: target_obj -> list of required_feature_sets
        self.knowledge = defaultdict(list)
        self.load_rules(filename)

    def load_rules(self, filename):
        """Đọc file luật format: A & B -> C | Label"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "->" not in line or line.startswith("#"):
                        continue

                    left, right = line.split("->", 1)
                    conclusion = right.split("|")[0].strip().lower()
                    premises_str = left.strip().lower()

                    # AND rule
                    if "&" in premises_str:
                        required_feats = set(p.strip() for p in premises_str.split("&"))
                        self.knowledge[conclusion].append(required_feats)

                    # OR rule
                    elif "v" in premises_str:
                        options = [p.strip() for p in premises_str.split("v")]
                        for opt in options:
                            self.knowledge[conclusion].append({opt})

                    # Single rule
                    else:
                        self.knowledge[conclusion].append({premises_str})

        except FileNotFoundError:
            return False
        return True

    def infer(self, user_input_en):
        """Suy luận dựa trên độ khớp (Matching Score) — ENGLISH ONLY"""
        if not user_input_en:
            return None, 0

        raw = user_input_en.lower().strip()

        # Tách từ khoá
        user_feats = set(x.strip() for x in raw.replace(",", " ").split() if x.strip())
        user_feats.add(raw)            # thêm cụm nguyên văn
        user_feats.update(x.strip() for x in raw.split(","))

        best_obj = None
        best_score = 0

        # 2. Match với tri thức
        for obj, rule_sets in self.knowledge.items():
            obj_max_score = 0

            for required_set in rule_sets:
                if not required_set:
                    continue

                matched = len(required_set.intersection(user_feats))
                score = matched / len(required_set)

                if score > obj_max_score:
                    obj_max_score = score

            # Cập nhật vật tốt nhất
            if obj_max_score > best_score:
                best_score = obj_max_score
                best_obj = obj
            elif obj_max_score == best_score and best_score > 0:
                if best_obj and len(obj) > len(best_obj):
                    best_obj = obj

        return best_obj, best_score


# ======================
# GIAO DIỆN NGƯỜI DÙNG (ENGLISH INPUT ONLY)
# ======================
class UserGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔍 Object Finder (English Only)")
        self.geometry("750x600")
        self.configure(bg="#f0f2f5")

        # Khởi động Engine
        self.engine = InferenceEngine("wordnet.txt")
        if not self.engine.knowledge:
            messagebox.showwarning("Warning",
                                   "Knowledge base empty or missing!\nPlease use Admin GUI to generate rules first.")

        # UI Components
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Describe your object (English):", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text="Example: wheel and engine, or screen and keyboard",
                  font=("Segoe UI", 10, "italic")).pack(pady=(0, 10))

        self.entry = ttk.Entry(main_frame, font=("Segoe UI", 12), width=50)
        self.entry.pack(pady=5, ipady=5)
        self.entry.bind("<Return>", lambda e: self.on_search())

        ttk.Button(main_frame, text="🔍 Analyze & Search", command=self.on_search).pack(pady=15)

        self.result_label = ttk.Label(main_frame, text="...", font=("Segoe UI", 13), wraplength=700, justify="center")
        self.result_label.pack(pady=10)

        self.img_label = ttk.Label(main_frame)
        self.img_label.pack(pady=10, expand=True)

    def on_search(self):
        user_in = self.entry.get().strip()
        if not user_in:
            return

        self.result_label.config(text="⏳ Analyzing...")
        self.img_label.config(image="", text="")
        self.update()

        # Không dịch nữa — xử lý tiếng Anh trực tiếp
        best_obj, score = self.engine.infer(user_in)

        if score >= 0.5:
            confidence = int(score * 100)
            self.result_label.config(
                text=f"✅ Best Match: {best_obj.title()}\n🎯 Confidence: {confidence}%",
                foreground="#007acc"
            )
            self.show_image(best_obj)
        else:
            self.result_label.config(
                text=f"❌ No suitable object found.\nTry describing with more details.",
                foreground="red"
            )

    def show_image(self, keyword):
        """Tải ảnh từ Pixabay"""
        try:
            api_key = "53101775-37777e069e2eb137c3c11588e"
            url = f"https://pixabay.com/api/?key={api_key}&q={keyword}&image_type=photo&per_page=3"

            response = requests.get(url, timeout=5)
            data = response.json()

            if data.get("hits"):
                img_url = data["hits"][0]["webformatURL"]
                raw_data = requests.get(img_url, timeout=5).content

                image = Image.open(BytesIO(raw_data))
                image.thumbnail((350, 350))
                photo = ImageTk.PhotoImage(image)

                self.img_label.config(image=photo)
                self.img_label.image = photo
            else:
                self.img_label.config(image="", text="(No image found)")
        except Exception as e:
            print(f"Image load error: {e}")
            self.img_label.config(image="", text="(Image loading error)")


if __name__ == "__main__":
    app = UserGUI()
    app.mainloop()
