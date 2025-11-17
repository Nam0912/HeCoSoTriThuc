import requests
import tkinter as tk
from tkinter import ttk, messagebox
from googletrans import Translator
from collections import defaultdict

translator = Translator()

useful_relations = {"UsedFor", "MadeOf", "PartOf", "IsA"}
ban_words = {"thing", "object", "something", "someone", "money", "news", "page",
             "marker", "note", "card", "booklet", "item"}


def tra_cuu_conceptnet(concept_en, limit=50):
    """Truy vấn ConceptNet và sinh các quan hệ hợp lệ"""
    url = f"https://api.conceptnet.io/c/en/{concept_en}?offset=0&limit={limit}"
    try:
        data = requests.get(url).json()
    except Exception as e:
        messagebox.showerror("Lỗi", f"Lỗi khi truy cập ConceptNet: {e}")
        return []

    edges = []
    for edge in data.get("edges", []):
        rel = edge["rel"]["label"]
        if rel not in useful_relations:
            continue

        start = edge["start"]["label"].lower()
        end = edge["end"]["label"].lower()

        if not (edge["start"]["@id"].startswith("/c/en/") and edge["end"]["@id"].startswith("/c/en/")):
            continue

        if any(bad in start for bad in ban_words) or any(bad in end for bad in ban_words):
            continue

        edges.append((start, rel, end))
    return edges


def sinh_luat_tu_conceptnet(ds_tu_viet):
    """Sinh luật tri thức từ ConceptNet"""
    en_list = [translator.translate(t.strip(), src="vi", dest="en").text.lower() for t in ds_tu_viet]
    feature_map = defaultdict(set)

    for concept in en_list:
        edges = tra_cuu_conceptnet(concept)
        for s, rel, e in edges:
            # Định hướng luật
            if rel in ("MadeOf", "UsedFor"):
                feature_map[s].add(e)
            elif rel in ("PartOf", "IsA"):
                feature_map[e].add(s)

    return feature_map


def tai_luat(filename="knowledge_base.txt"):
    """Tải dữ liệu cũ từ file"""
    data = defaultdict(set)
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                obj, feats = line.split(":", 1)
                feats = [x.strip() for x in feats.split(",") if x.strip()]
                data[obj.strip()].update(feats)
    except FileNotFoundError:
        pass
    return data


def luu_luat(feature_map, filename="knowledge_base.txt"):
    """Gộp (merge) với dữ liệu cũ và lưu lại"""
    old_data = tai_luat(filename)
    for obj, feats in feature_map.items():
        old_data[obj].update(feats)

    with open(filename, "w", encoding="utf-8") as f:
        for obj, feats in sorted(old_data.items()):
            f.write(f"{obj}: {', '.join(sorted(feats))}\n")


class AdminGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧩 Quản lý Tri thức (Admin)")
        self.geometry("850x650")
        self.configure(bg="#f7f7f7")

        ttk.Label(self, text="Nhập các khái niệm cần sinh luật (cách nhau dấu phẩy):",
                  font=("Arial", 12)).pack(pady=10)
        self.entry = ttk.Entry(self, width=80)
        self.entry.pack(pady=5)

        ttk.Button(self, text="Sinh luật từ ConceptNet", command=self.on_generate).pack(pady=10)
        ttk.Button(self, text="Lưu vào knowledge_base.txt", command=self.on_save).pack(pady=5)

        ttk.Label(self, text="Danh sách tri thức (vật -> đặc trưng):", font=("Arial", 12)).pack(pady=10)
        self.text = tk.Text(self, width=100, height=25)
        self.text.pack(pady=5)

        self.feature_map = {}

    def on_generate(self):
        tu_nhap = self.entry.get().strip()
        if not tu_nhap:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập ít nhất một khái niệm.")
            return

        ds = [x.strip() for x in tu_nhap.split(",") if x.strip()]
        self.feature_map = sinh_luat_tu_conceptnet(ds)

        self.text.delete(1.0, tk.END)
        for obj, feats in self.feature_map.items():
            self.text.insert(tk.END, f"{obj}: {', '.join(feats)}\n")

        messagebox.showinfo("Thành công", f"Đã sinh tri thức cho {len(self.feature_map)} vật.")

    def on_save(self):
        if not self.feature_map:
            messagebox.showwarning("Chưa có dữ liệu", "Bạn cần sinh tri thức trước khi lưu.")
            return
        luu_luat(self.feature_map)
        messagebox.showinfo("Lưu thành công", "Đã hợp nhất và lưu vào file knowledge_base.txt")


if __name__ == "__main__":
    app = AdminGUI()
    app.mainloop()
