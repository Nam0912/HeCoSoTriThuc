import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from deep_translator import GoogleTranslator
import nltk
from nltk.corpus import wordnet as wn

# ==========================================
# CẤU HÌNH NLTK (Tải dữ liệu lần đầu)
# ==========================================
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    print("Đang tải dữ liệu WordNet...")
    nltk.download('wordnet')


# ==========================================
# LOGIC XỬ LÝ WORDNET (CORE ENGINE)
# ==========================================

def clean_term(term):
    """Chuẩn hóa từ: chữ thường, thay dấu _ bằng khoảng trắng"""
    return term.lemmas()[0].name().lower().replace('_', ' ')


def sinh_luat_tu_wordnet(ds_tu_viet):
    """
    Hàm chính:
    1. Dịch từ Việt -> Anh
    2. Tra cứu WordNet
    3. Sinh luật AND (Cấu tạo) và OR (Phân loại)
    """
    translator = GoogleTranslator(source='vi', target='en')

    # Bước 1: Dịch danh sách đầu vào
    try:
        # Dịch từng từ một để đảm bảo chính xác
        ds_tieng_anh = [translator.translate(t.strip()).lower() for t in ds_tu_viet if t.strip()]
    except Exception as e:
        messagebox.showerror("Lỗi Dịch", f"Không thể kết nối Google Translate: {e}")
        return []

    rules = set()  # Dùng set để loại bỏ trùng lặp
    processed_synsets = set()

    # Bước 2: Duyệt qua từng chủ đề
    for topic in ds_tieng_anh:
        synsets = wn.synsets(topic)
        if not synsets:
            continue

        # Dùng hàng đợi BFS để duyệt cây
        queue = [synsets[0]]

        # Giới hạn số lượng node duyệt để không bị treo máy nếu chủ đề quá rộng
        max_nodes = 50
        count = 0

        while queue and count < max_nodes:
            current_syn = queue.pop(0)

            if current_syn.name() in processed_synsets:
                continue
            processed_synsets.add(current_syn.name())
            count += 1

            current_name = clean_term(current_syn)

            # --- LOẠI 1: LUẬT AND (&) - CẤU TẠO (Parts -> Whole) ---
            # Logic: part1 & part2 -> whole
            parts = current_syn.part_meronyms()
            part_names = [clean_term(p) for p in parts if clean_term(p) != current_name]

            # Chỉ tạo luật AND nếu có >= 2 bộ phận
            if len(part_names) >= 2:
                selected_parts = part_names[:3]  # Lấy tối đa 3 bộ phận
                premises = " & ".join(selected_parts)
                # Format: Giả thiết -> Kết luận | Nhãn
                rule_str = f"{premises} -> {current_name} | Rule_CauTao_{current_name.replace(' ', '_')}"
                rules.add(rule_str)

            # --- LOẠI 2: LUẬT OR (v) - PHÂN LOẠI (Children -> Parent) ---
            # Logic: child1 v child2 -> parent
            hyponyms = current_syn.hyponyms()
            child_names = [clean_term(c) for c in hyponyms if clean_term(c) != current_name]

            # Chia nhỏ danh sách con thành các nhóm (chunk) để tạo luật OR
            chunk_size = 4
            for i in range(0, len(child_names), chunk_size):
                chunk = child_names[i:i + chunk_size]
                if len(chunk) > 0:
                    if len(chunk) > 1:
                        premises = " v ".join(chunk)
                        label = f"Rule_PhanLoai_OR_{current_name.replace(' ', '_')}_{i}"
                    else:
                        premises = chunk[0]
                        label = f"Rule_IsA_{current_name.replace(' ', '_')}_{i}"

                    rule_str = f"{premises} -> {current_name} | {label}"
                    rules.add(rule_str)

            # Mở rộng duyệt xuống con
            for child in hyponyms:
                if child.name() not in processed_synsets:
                    queue.append(child)

    return sorted(list(rules))


# ==========================================
# GIAO DIỆN QUẢN TRỊ (ADMIN GUI)
# ==========================================

class AdminGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧩 Admin: Sinh Luật Suy Diễn (WordNet Integration)")
        self.geometry("900x700")
        self.configure(bg="#f0f2f5")

        # Header
        top_frame = ttk.Frame(self, padding=20)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="CÔNG CỤ SINH LUẬT TỰ ĐỘNG", font=("Segoe UI", 16, "bold")).pack()
        ttk.Label(top_frame, text="Nhập chủ đề tiếng Việt (VD: xe hơi, máy tính, động vật)",
                  font=("Segoe UI", 10)).pack(pady=(5, 0))

        # Input Area
        input_frame = ttk.Frame(self, padding=20)
        input_frame.pack(fill="x")

        self.entry = ttk.Entry(input_frame, font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry.bind("<Return>", lambda event: self.on_generate())  # Enter để chạy

        ttk.Button(input_frame, text="🚀 Sinh Luật Ngay", command=self.on_generate).pack(side="right")

        # Action Buttons
        btn_frame = ttk.Frame(self, padding=(20, 0, 20, 10))
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="💾 Lưu file .txt (cho ToanHoc.py)", command=self.on_save).pack(side="right")
        ttk.Button(btn_frame, text="🗑 Xóa màn hình", command=lambda: self.text_area.delete(1.0, tk.END)).pack(
            side="right", padx=5)

        # Result Area
        list_frame = ttk.LabelFrame(self, text="Kết quả Luật sinh ra:", padding=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.text_area = tk.Text(list_frame, font=("Consolas", 10), height=20)
        self.text_area.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, command=self.text_area.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_area.config(yscrollcommand=scrollbar.set)

        # Status bar
        self.status_var = tk.StringVar(value="Sẵn sàng.")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x")

        self.generated_rules = []

    def on_generate(self):
        user_input = self.entry.get().strip()
        if not user_input:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập ít nhất một chủ đề (tiếng Việt).")
            return

        self.status_var.set("Đang xử lý... Vui lòng đợi (Dịch & Tra cứu WordNet)...")
        self.update_idletasks()  # Cập nhật UI ngay lập tức

        ds_chu_de = [x.strip() for x in user_input.split(",") if x.strip()]

        # Gọi hàm xử lý WordNet
        self.generated_rules = sinh_luat_tu_wordnet(ds_chu_de)

        if not self.generated_rules:
            self.status_var.set("Không tìm thấy luật nào phù hợp.")
            messagebox.showinfo("Kết quả", "Không tìm thấy tri thức phù hợp trong WordNet hoặc lỗi dịch.")
            return

        # Hiển thị kết quả
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, f"# Generated Rules for Topics: {user_input}\n")
        for rule in self.generated_rules:
            self.text_area.insert(tk.END, rule + "\n")

        self.status_var.set(f"Hoàn tất! Đã sinh {len(self.generated_rules)} luật.")

    def on_save(self):
        content = self.text_area.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Trống", "Không có nội dung để lưu.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Lưu tập luật"
        )

        if file_path:
            try:
                # Chế độ 'a' (append) để nối thêm vào file cũ, hoặc 'w' để ghi mới
                # Ở đây dùng 'a' để người dùng có thể tích lũy tri thức
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write("\n" + content + "\n")
                messagebox.showinfo("Thành công", f"Đã lưu luật vào: {file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi lưu file", str(e))


if __name__ == "__main__":
    app = AdminGUI()
    app.mainloop()