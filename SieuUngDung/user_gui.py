import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
from io import BytesIO
from googletrans import Translator
from collections import deque
from typing import List, Set, Tuple, Dict, Deque

# Khởi tạo Translator (cần cho việc dịch)
translator = Translator()


# ======================
# ĐỊNH NGHĨA CẤU TRÚC RULE
# ======================
class Rule:
    """Cấu trúc đại diện cho một luật suy diễn: IF (Premises) THEN (Conclusion)"""

    def __init__(self, label: str, premises: Tuple[str, ...], conclusion: str):
        self.label = label
        self.premises = premises
        self.conclusion = conclusion

    def __repr__(self):
        return f"'{self.label}': {', '.join(self.premises)} -> {self.conclusion}"


# ======================
# MOTOR SUY DIỄN TIẾN BFS
# (Hàm được cung cấp bởi người dùng, đã thêm type hints và import cần thiết)
# ======================
def forward_chain_bfs(rules: List[Rule], facts: Set[str], selection_mode: str = 'Min'):
    """
    Thực hiện suy diễn tiến bằng Breadth-First Search (BFS).

    Args:
        rules: Danh sách các Rule (Luật).
        facts: Tập hợp các Fact (Sự kiện) ban đầu được biết.
        selection_mode: Chế độ ưu tiên luật ('Min' - luật đầu tiên, 'Max' - luật cuối cùng).

    Returns:
        known: Tập hợp các fact được biết (bao gồm cả fact ban đầu và fact mới được suy diễn).
        prov: Chứng minh (cây suy diễn) cho mỗi fact mới.
        steps: Các bước kích hoạt luật (quy trình suy diễn).
    """
    known = set(facts)
    prov: Dict[str, Tuple[Rule, Tuple[str, ...]]] = {}
    steps: List[str] = []

    # Queue chứa các fact mới được suy diễn hoặc fact ban đầu chưa được dùng để mở rộng
    queue: Deque[str] = deque(list(facts))
    visited_facts_for_expansion = set()

    # Chọn thứ tự luật dựa trên selection_mode
    rule_source = rules if selection_mode == 'Min' else list(reversed(rules))

    while queue:
        current_fact = queue.popleft()
        if current_fact in visited_facts_for_expansion:
            continue
        visited_facts_for_expansion.add(current_fact)

        for r in rule_source:
            # Kiểm tra xem fact hiện tại có phải là một premise của luật r không
            if r.conclusion not in known and current_fact in r.premises:
                # Kiểm tra xem TẤT CẢ các premise của luật r đã được biết chưa (logic AND)
                if all(p in known for p in r.premises):
                    new_fact = r.conclusion
                    known.add(new_fact)
                    prov[new_fact] = (r, r.premises)
                    # Ghi lại bước suy diễn
                    steps.append(f"({len(steps) + 1}) Kích hoạt '{r.label}': {{{', '.join(r.premises)}}} → {new_fact}")

                    if new_fact not in queue:
                        queue.append(new_fact)

    return known, prov, steps


# ======================
# CHUYỂN DỮ LIỆU THÀNH RULES
# ======================
def load_rules(filename="knowledge_base.txt"):
    """Đọc knowledge_base.txt và chuyển đổi thành danh sách các Rule đơn giản."""
    rules: List[Rule] = []
    possible_objects: Set[str] = set()
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if ":" not in line:
                    continue
                # Ví dụ: a book: a chapter, a ledger, a novel
                obj_raw, feats_raw = line.strip().split(":", 1)
                obj = obj_raw.strip().lower()
                feats = [x.strip().lower() for x in feats_raw.split(",") if x.strip()]
                possible_objects.add(obj)

                for i, feat in enumerate(feats):
                    label = f"IF_{feat.replace(' ', '_').upper()}_THEN_{obj.replace(' ', '_').upper()}"
                    # Tạo Rule đơn giản: IF {feature} THEN {object}
                    rules.append(Rule(
                        label=label,
                        premises=(feat,),  # Premises là một tuple chỉ chứa 1 feature
                        conclusion=obj
                    ))
    except FileNotFoundError:
        messagebox.showerror("Lỗi", "Không tìm thấy file knowledge_base.txt!")
    return rules, possible_objects


# ======================
# GIAO DIỆN NGƯỜI DÙNG
# ======================
class UserGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("🧠 Hệ Chuyên Gia Suy Diễn Tiến (BFS)")
        self.master.geometry("850x650")

        # Tải rules và danh sách tất cả các đối tượng có thể có
        self.rules, self.possible_objects = load_rules()

        # --- UI Setup ---
        ttk.Label(master, text="Nhập các đặc trưng (Facts) cách nhau dấu phẩy:",
                  font=("Segoe UI", 12, "bold")).pack(pady=10)

        self.entry = ttk.Entry(master, width=80)
        self.entry.pack(pady=5, padx=20)

        ttk.Button(master, text="🔥 Bắt đầu Suy Diễn Tiến", command=self.on_infer).pack(pady=10)

        # Khung chứa kết quả chính và bước suy diễn
        self.results_frame = ttk.Frame(master)
        self.results_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Kết quả chính (Inferred Objects)
        ttk.Label(self.results_frame, text="✅ Vật Phù Hợp (Inferred Objects):",
                  font=("Segoe UI", 11, "bold")).pack(anchor='w', pady=(0, 5))
        self.result_text = tk.Text(self.results_frame, height=5, wrap="word", font=("Segoe UI", 10))
        self.result_text.pack(fill='x', padx=5, pady=5)

        # Bước suy diễn (Steps)
        ttk.Label(self.results_frame, text="📚 Quá Trình Suy Diễn (Reasoning Steps):",
                  font=("Segoe UI", 11, "bold")).pack(anchor='w', pady=(10, 5))
        self.steps_text = tk.Text(self.results_frame, height=10, wrap="word", font=("Consolas", 9),
                                  background="#f0f0f0")
        self.steps_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Label hiển thị ảnh
        self.img_label = ttk.Label(master)
        self.img_label.pack(pady=10)

    # ======================
    # KÍCH HOẠT SUY DIỄN TIẾN
    # ======================
    def on_infer(self):
        user_input = self.entry.get().strip()
        self.result_text.delete('1.0', tk.END)
        self.steps_text.delete('1.0', tk.END)
        self.img_label.config(image="", text="")

        if not user_input:
            messagebox.showwarning("Lỗi", "Bạn phải nhập ít nhất 1 đặc trưng (Fact) để bắt đầu suy diễn!")
            return

        # 1. Dịch sang tiếng Anh để chuẩn hóa với knowledge base
        try:
            # Chỉ dịch khi input không phải chỉ chứa các ký tự Latin
            if any(ord(c) > 127 for c in user_input):
                translated = translator.translate(user_input, src="vi", dest="en").text
            else:
                translated = user_input
        except Exception as e:
            print(f"Lỗi dịch thuật: {e}")
            translated = user_input  # Sử dụng nguyên bản nếu dịch lỗi

        # 2. Chuẩn bị các Fact ban đầu (Premises)
        initial_facts = set(x.strip().lower() for x in translated.split(",") if x.strip())

        if not initial_facts:
            messagebox.showwarning("Lỗi", "Input không chứa Fact hợp lệ.")
            return

        # 3. Chạy Motor Suy Diễn Tiến BFS
        known, _, steps = forward_chain_bfs(self.rules, initial_facts)

        # 4. Lọc ra các Object được suy diễn (Kết quả chính)
        inferred_objects = sorted(list(known.intersection(self.possible_objects)))

        # 5. Hiển thị Kết Quả
        if inferred_objects:
            # Hiển thị tất cả các objects được suy diễn
            result_str = "Các vật đã được suy diễn thành công:\n"
            for obj in inferred_objects:
                # Dịch ngược lại sang tiếng Việt để hiển thị thân thiện
                try:
                    vi_name = translator.translate(obj, src="en", dest="vi").text
                except:
                    vi_name = obj
                result_str += f"- {vi_name.capitalize()} ({obj})\n"

            self.result_text.insert(tk.END, result_str)

            # Chỉ hiển thị ảnh của vật đầu tiên được suy diễn (hoặc vật đầu tiên trong danh sách)
            self.show_image(inferred_objects[0])
        else:
            self.result_text.insert(tk.END, "❌ Không có vật nào được suy diễn từ các Facts đã nhập.")

        # 6. Hiển thị Quá Trình Suy Diễn
        if steps:
            self.steps_text.insert(tk.END, "\n".join(steps))
        else:
            self.steps_text.insert(tk.END,
                                   "Không có luật nào được kích hoạt. Các Facts đã nhập không dẫn đến kết luận mới.")

    def show_image(self, keyword):
        """Tải và hiển thị ảnh minh họa cho keyword"""
        try:
            # Sử dụng key mẫu của bạn
            api_key = "53101775-37777e069e2eb137c3c11588e"
            url = f"https://pixabay.com/api/?key={api_key}&q={keyword}&image_type=photo&per_page=3"

            response = requests.get(url, headers=headers, timeout=6)
            response.raise_for_status()  # Raise exception cho lỗi HTTP
            data = response.json()

            if data.get("hits"):
                img_url = data["hits"][0]["webformatURL"]
                img_data = requests.get(img_url, headers=headers, timeout=6).content
                img = Image.open(BytesIO(img_data)).resize((260, 260), Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=self.photo, text="")
            else:
                self.img_label.config(image="", text="(Không tìm thấy ảnh minh họa)")
        except requests.exceptions.RequestException as e:
            # Xử lý lỗi kết nối, timeout, hoặc HTTP
            print(f"⚠️ Lỗi tải ảnh (Kết nối/HTTP): {e}")
            self.img_label.config(image="", text="(Lỗi kết nối hoặc không tìm thấy ảnh)")
        except Exception as e:
            # Xử lý lỗi PIL hoặc lỗi chung khác
            print(f"⚠️ Lỗi tải ảnh: {e}")
            self.img_label.config(image="", text="(Lỗi xử lý ảnh)")


if __name__ == "__main__":
    root = tk.Tk()
    app = UserGUI(root)
    root.mainloop()
