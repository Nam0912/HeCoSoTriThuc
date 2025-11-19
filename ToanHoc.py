# =============================
# GUI Inference Engine - Đáp ứng yêu cầu Bài tập 1
# =============================
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from typing import Tuple, List, Set, Dict, Deque
import matplotlib.pyplot as plt
import networkx as nx
import itertools
from collections import deque
import textwrap


# ---------- Core Engine: Data Structures ----------
@dataclass(frozen=True)
class Rule:
    premises: Tuple[str, ...]
    conclusion: str
    label: str
    id: int  # Thêm ID để theo dõi chỉ số
    op: str  # MỚI: 'AND' hoặc 'OR'

def load_and_parse_rules(filepath: str) -> List[Rule]:
    """
    Đọc luật từ file, xác thực, loại bỏ trùng lặp và trả về danh sách luật hợp lệ.
    Hỗ trợ AND (&) hoặc OR (v) cho tiền đề, nhưng không hỗ trợ trộn lẫn.
    """
    rules: List[Rule] = []
    seen_rules_canonical = set()

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, ln in enumerate(f, 1):
                raw = ln.strip()
                if not raw or raw.startswith("#"):
                    continue

                if "->" not in raw:
                    print(f"Bỏ qua dòng {line_num}: Thiếu '->'. Nội dung: '{raw}'")
                    continue

                left, right = raw.split("->", 1)
                left = left.replace("^", "&").strip()

                op = 'AND'  # Mặc định
                premises_list = []

                has_and = "&" in left
                has_or = "v" in left

                if has_and and has_or:
                    print(f"Bỏ qua dòng {line_num}: Luật chứa cả '&' và 'v' không được hỗ trợ. Nội dung: '{raw}'")
                    continue
                elif has_or:
                    op = 'OR'
                    premises_list = [p.strip() for p in left.split("v") if p.strip()]
                else:  # Mặc định là AND (dù có & hay không)
                    op = 'AND'
                    premises_list = [p.strip() for p in left.split("&") if p.strip()]

                if not premises_list:
                    print(f"Bỏ qua dòng {line_num}: Luật không có tiền đề. Nội dung: '{raw}'")
                    continue

                # Sắp xếp tiền đề để kiểm tra trùng lặp
                premises_sorted = tuple(sorted(premises_list))

                if "|" in right:
                    concl, label = right.split("|", 1)
                else:
                    concl, label = right, f"R{len(rules) + 1}"

                conclusion = concl.strip()
                label = label.strip()

                # 2. KIỂM TRA TRÙNG LẶP
                # Thêm 'op' vào key để phân biệt A&B->C và A v B->C
                canonical_key = (premises_sorted, conclusion, op)
                if canonical_key in seen_rules_canonical:
                    print(f"Bỏ qua dòng {line_num}: Luật trùng lặp. Nội dung: '{raw}'")
                    continue

                seen_rules_canonical.add(canonical_key)

                # Giữ nguyên thứ tự tiền đề gốc
                original_premises = tuple(premises_list)
                new_rule = Rule(premises=original_premises, conclusion=conclusion, label=label, id=len(rules), op=op)
                rules.append(new_rule)

    except FileNotFoundError:
        messagebox.showerror("Lỗi File", f"Không tìm thấy file tại đường dẫn: {filepath}")
        return []
    except Exception as e:
        messagebox.showerror("Lỗi đọc file", f"Đã xảy ra lỗi: {e}")
        return []

    return rules


# ---------- Core Engine: Forward Chaining Algorithms ----------

# --- FORWARD CHAINING (BFS / Queue) ---
# SỬA ĐỔI: forward_chain_bfs
def forward_chain_bfs(rules: List[Rule], facts: Set[str], selection_mode: str):
    known = set(facts)
    prov: Dict[str, Tuple[Rule, Tuple[str, ...]]] = {}
    steps: List[str] = []

    queue: Deque[str] = deque(list(facts))
    visited_facts_for_expansion = set()

    rule_source = rules if selection_mode == 'Min' else list(reversed(rules))

    while queue:
        current_fact = queue.popleft()
        if current_fact in visited_facts_for_expansion:
            continue
        visited_facts_for_expansion.add(current_fact)

        for r in rule_source:
            # Bỏ qua nếu đã biết kết luận
            if r.conclusion in known:
                continue

            # Chỉ kích hoạt nếu fact hiện tại nằm trong tiền đề của luật
            if current_fact in r.premises:

                # BẮT ĐẦU SỬA ĐỔI: Kiểm tra tiền đề dựa trên toán tử
                premises_met = False
                if r.op == 'AND':
                    premises_met = all(p in known for p in r.premises)
                elif r.op == 'OR':
                    # Chỉ cần 1 tiền đề (là current_fact) nằm trong 'known' là đủ
                    premises_met = True
                # KẾT THÚC SỬA ĐỔI

                if premises_met:
                    new_fact = r.conclusion
                    known.add(new_fact)
                    # Lưu tất cả tiền đề (dù là AND hay OR) để hiển thị log
                    prov[new_fact] = (r, r.premises)
                    steps.append(f"({len(steps) + 1}) Kích hoạt '{r.label}': {{{', '.join(r.premises)}}} → {new_fact}")
                    if new_fact not in queue:
                        queue.append(new_fact)
    return known, prov, steps


# --- FORWARD CHAINING (DFS / Stack) ---
def forward_chain_dfs(rules: List[Rule], facts: Set[str], selection_mode: str):
    known = set(facts)
    prov: Dict[str, Tuple[Rule, Tuple[str, ...]]] = {}
    steps: List[str] = []

    rule_source = rules if selection_mode == 'Min' else list(reversed(rules))

    initial_facts = list(facts)

    def _dfs_visit(fact_to_process: str):
        for r in rule_source:
            if r.conclusion not in known and fact_to_process in r.premises:

                # BẮT ĐẦU SỬA ĐỔI: Kiểm tra tiền đề dựa trên toán tử
                premises_met = False
                if r.op == 'AND':
                    premises_met = all(p in known for p in r.premises)
                elif r.op == 'OR':
                    premises_met = True  # fact_to_process đang được xử lý, nên OR thỏa mãn
                # KẾT THÚC SỬA ĐỔI

                if premises_met:
                    new_fact = r.conclusion
                    known.add(new_fact)
                    prov[new_fact] = (r, r.premises)
                    steps.append(f"({len(steps) + 1}) Kích hoạt '{r.label}': {{{', '.join(r.premises)}}} → {new_fact}")
                    _dfs_visit(new_fact)

    for fact in initial_facts:
        _dfs_visit(fact)

    return known, prov, steps


# ---------- Core Engine: Backward Chaining Algorithm ----------
# VIẾT LẠI: backward_chain_all
def backward_chain_all(goal: str, rules: List[Rule], facts: Set[str], seen: Set[str], selection_mode: str) -> List[
    List[Rule]]:
    if goal in facts:
        return [[]]
    if goal in seen:
        return []
    seen.add(goal)

    paths = []

    rule_source = rules if selection_mode == 'Min' else list(reversed(rules))
    relevant_rules = [r for r in rule_source if r.conclusion == goal]

    for r in relevant_rules:

        if r.op == 'AND':
            # Logic AND (giữ nguyên): Cần chứng minh *tất cả* tiền đề
            all_subpaths = []
            valid = True
            for p in r.premises:
                sub = backward_chain_all(p, rules, facts, seen.copy(), selection_mode)
                if not sub:
                    valid = False
                    break
                all_subpaths.append(sub)
            if valid:
                # Tổ hợp tất cả các đường con
                for combo in itertools.product(*all_subpaths):
                    chain = list(itertools.chain(*combo)) + [r]
                    paths.append(chain)

        elif r.op == 'OR':
            # Logic OR (MỚI): Chỉ cần chứng minh *bất kỳ* một tiền đề nào
            for p in r.premises:
                # Tìm tất cả các đường chứng minh cho tiền đề 'p'
                subpaths_for_p = backward_chain_all(p, rules, facts, seen.copy(), selection_mode)

                # Với mỗi đường chứng minh thành công cho 'p',
                # nó tạo thành một đường chứng minh hoàn chỉnh
                for sub_path in subpaths_for_p:
                    chain = sub_path + [r]
                    paths.append(chain)

    return paths


# ---------- Graph Drawing ----------
# --- FPG (Flow Process Graph) ---
def draw_fpg(prov: Dict[str, Tuple[Rule, Tuple[str, ...]]], facts: Set[str]):
    if not prov and not facts:
        messagebox.showwarning("Lỗi", "Không có dữ liệu để vẽ đồ thị.")
        return

    G = nx.DiGraph()
    all_nodes = set(facts)
    for concl, (_, premises) in prov.items():
        all_nodes.add(concl)
        for p in premises:
            all_nodes.add(p)

    for node in all_nodes:
        color = "#9ecae1" if node in prov else "#f7f7f7"  # Kết luận màu xanh, GT màu xám
        G.add_node(node, color=color)

    for concl, (r, used) in prov.items():
        for p in used:
            G.add_edge(p, concl, label=r.label)

    plt.figure(figsize=(10, 8))
    colors = [G.nodes[n].get("color", "#ffffff") for n in G.nodes]
    pos = nx.spring_layout(G, seed=42, k=0.9)
    nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=2000, edgecolors="black")
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")
    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle="-|>", arrowsize=20, connectionstyle="arc3,rad=0.1")
    edge_labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9, label_pos=0.5)
    plt.title("Flow Process Graph (FPG)", fontsize=16)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


# --- RPG (Rule Process Graph) ---
def draw_rpg(rules: List[Rule]):
    if not rules:
        messagebox.showwarning("Lỗi", "Không có luật nào để vẽ đồ thị.")
        return

    G = nx.DiGraph()
    for r in rules:
        G.add_node(r.label)

    for r1 in rules:
        for r2 in rules:
            if r1.id != r2.id:
                if r1.conclusion in r2.premises:
                    G.add_edge(r1.label, r2.label)

    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, seed=42, k=0.9)
    nx.draw_networkx_nodes(G, pos, node_color="#ffb3ba", node_size=2000, edgecolors="black")
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")
    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle="-|>", arrowsize=20, connectionstyle="arc3,rad=0.1")
    plt.title("Rule Process Graph (RPG)", fontsize=16)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


class RuleEditor(tk.Toplevel):
    """Cửa sổ dialog để thêm hoặc sửa một luật, hỗ trợ nhiều giả thiết và kết luận."""

    def __init__(self, parent, title, rule=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.parent = parent
        self.result = None

        self.premise_entries = []
        self.premise_ops = []
        self.premise_rows = []  # lưu các widget để dễ xóa

        self.conclusion_entries = []
        self.conclusion_ops = []
        self.conclusion_rows = []

        # Frame tổng
        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)

        # --- Giả thiết ---
        ttk.Label(body, text="Giả thiết (Tiền đề):", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.premise_frame = ttk.Frame(body)
        self.premise_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        self.premise_frame.columnconfigure(1, weight=1)
        ttk.Button(body, text="+ Thêm Giả thiết", command=self.add_premise_field).grid(row=2, column=0, sticky="w", pady=(5, 0))
        ttk.Label(body, text="& = AND, v = OR", foreground="gray").grid(row=2, column=1, sticky="e")

        # --- Kết luận ---
        ttk.Label(body, text="Kết luận:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.conclusion_frame = ttk.Frame(body)
        self.conclusion_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        self.conclusion_frame.columnconfigure(1, weight=1)
        ttk.Button(body, text="+ Thêm Kết luận", command=self.add_conclusion_field).grid(row=5, column=0, sticky="w", pady=(5, 0))
        ttk.Label(body, text="& = AND, v = OR", foreground="gray").grid(row=5, column=1, sticky="e")

        # --- Nhãn luật ---
        ttk.Label(body, text="Nhãn Luật:").grid(row=6, column=0, sticky="w", pady=(10, 0))
        self.label_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.label_var, width=40).grid(row=6, column=1, sticky="ew")

        # --- Nút Lưu/Hủy ---
        button_frame = ttk.Frame(body, padding=(0, 10))
        button_frame.grid(row=7, column=0, columnspan=2, sticky="e")
        ttk.Button(button_frame, text="Lưu", command=self.on_ok).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Hủy", command=self.destroy).pack(side="right")

        # Nếu là sửa
        if rule:
            for p in rule.premises:
                self.add_premise_field(p)
            self.add_conclusion_field(rule.conclusion)
            self.label_var.set(rule.label)
        else:
            self.add_premise_field()
            self.add_conclusion_field()

        self.grab_set()
        self.wait_window(self)

    # ==============================
    # HÀM THÊM VÀ XÓA GIẢ THIẾT / KẾT LUẬN
    # ==============================

    def add_premise_field(self, value=""):
        row = len(self.premise_entries)
        widgets = {}

        # Toán tử (nếu không phải phần tử đầu)
        if row > 0:
            op_var = tk.StringVar(value="&")
            op_menu = ttk.Combobox(self.premise_frame, textvariable=op_var, values=["&", "v"], width=5)
            op_menu.grid(row=row, column=0, padx=(0, 5), pady=2)
            self.premise_ops.append(op_var)
            widgets["op_menu"] = op_menu
        else:
            widgets["op_menu"] = None

        # Ô nhập
        entry = ttk.Entry(self.premise_frame, width=40)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        entry.insert(0, value)
        self.premise_entries.append(entry)
        widgets["entry"] = entry

        # Nút xóa
        btn = ttk.Button(self.premise_frame, text="🗑", width=3, command=lambda: self.remove_premise_field(row))
        btn.grid(row=row, column=2, padx=(5, 0))
        widgets["delete"] = btn

        self.premise_rows.append(widgets)

    def remove_premise_field(self, index):
        """Xóa 1 dòng giả thiết theo index."""
        # Hủy widget
        row_widgets = self.premise_rows[index]
        for w in row_widgets.values():
            if w:
                w.destroy()

        # Xóa phần tử khỏi list
        del self.premise_entries[index]
        if index > 0 and index - 1 < len(self.premise_ops):
            del self.premise_ops[index - 1]
        del self.premise_rows[index]

        # Cập nhật lại layout
        for widget in self.premise_frame.winfo_children():
            widget.grid_forget()
        for i, w in enumerate(self.premise_rows):
            if w["op_menu"]:
                w["op_menu"].grid(row=i, column=0, padx=(0, 5), pady=2)
            w["entry"].grid(row=i, column=1, sticky="ew", pady=2)
            w["delete"].grid(row=i, column=2, padx=(5, 0))

    def add_conclusion_field(self, value=""):
        row = len(self.conclusion_entries)
        widgets = {}

        if row > 0:
            op_var = tk.StringVar(value="&")
            op_menu = ttk.Combobox(self.conclusion_frame, textvariable=op_var, values=["&", "v"], width=5)
            op_menu.grid(row=row, column=0, padx=(0, 5), pady=2)
            self.conclusion_ops.append(op_var)
            widgets["op_menu"] = op_menu
        else:
            widgets["op_menu"] = None

        entry = ttk.Entry(self.conclusion_frame, width=40)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        entry.insert(0, value)
        self.conclusion_entries.append(entry)
        widgets["entry"] = entry

        btn = ttk.Button(self.conclusion_frame, text="🗑", width=3, command=lambda: self.remove_conclusion_field(row))
        btn.grid(row=row, column=2, padx=(5, 0))
        widgets["delete"] = btn

        self.conclusion_rows.append(widgets)

    def remove_conclusion_field(self, index):
        """Xóa 1 dòng kết luận theo index."""
        row_widgets = self.conclusion_rows[index]
        for w in row_widgets.values():
            if w:
                w.destroy()

        del self.conclusion_entries[index]
        if index > 0 and index - 1 < len(self.conclusion_ops):
            del self.conclusion_ops[index - 1]
        del self.conclusion_rows[index]

        for widget in self.conclusion_frame.winfo_children():
            widget.grid_forget()
        for i, w in enumerate(self.conclusion_rows):
            if w["op_menu"]:
                w["op_menu"].grid(row=i, column=0, padx=(0, 5), pady=2)
            w["entry"].grid(row=i, column=1, sticky="ew", pady=2)
            w["delete"].grid(row=i, column=2, padx=(5, 0))

    # ==============================
    # XỬ LÝ LƯU DỮ LIỆU
    # ==============================

    def on_ok(self):
        premises = [e.get().strip() for e in self.premise_entries if e.get().strip()]
        conclusions = [e.get().strip() for e in self.conclusion_entries if e.get().strip()]

        if not premises or not conclusions:
            messagebox.showerror("Lỗi", "Phần Giả thiết và Kết luận không được rỗng.", parent=self)
            return

        # 1. Kiểm tra toán tử tiền đề
        premise_ops = {op.get() for op in self.premise_ops}
        if len(premise_ops) > 1:
            messagebox.showerror("Lỗi", "Không hỗ trợ trộn lẫn '&' và 'v' trong cùng một luật.", parent=self)
            return

        op = 'AND'  # Mặc định
        if premise_ops:
            op_str = premise_ops.pop()
            if op_str == 'v':
                op = 'OR'

        # 2. Kiểm tra toán tử kết luận (Engine này chỉ hỗ trợ 1 kết luận)
        conclusion_ops = {op.get() for op in self.conclusion_ops}
        if len(conclusions) > 1 or conclusion_ops:
            messagebox.showwarning("Lưu ý",
                                   "Engine chỉ hỗ trợ 1 kết luận duy nhất (không có toán tử).\nChỉ kết luận đầu tiên sẽ được lưu.",
                                   parent=self)

        conclusion = conclusions[0]
        label = self.label_var.get().strip() or "R?"

        # 3. Tạo kết quả với 'op' và tuple tiền đề
        self.result = Rule(premises=tuple(premises), conclusion=conclusion, label=label, id=-1, op=op)
        self.destroy()



# ---------- GUI Application ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inference Engine")
        self.geometry("1100x800")
        self.last_prov = {}
        self.last_facts = set()
        self.last_rules = []

        # Main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Left side: Rules, Facts, Goals
        left_pane = ttk.Frame(main_frame)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 10))
        # Biến để lưu đường dẫn file đang mở
        self.rules_filepath = None

        # --- Khung hiển thị và quản lý luật ---
        rules_header_frame = ttk.Frame(left_pane)
        rules_header_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(rules_header_frame, text="Luật (Rules):").pack(side="left", anchor="w")

        self.btn_load_rules = ttk.Button(rules_header_frame, text="Tải Luật từ File...", command=self.load_rules_action)
        self.btn_load_rules.pack(side="right")

        # Khung chứa Listbox và thanh cuộn
        rules_list_frame = ttk.Frame(left_pane)
        rules_list_frame.pack(fill="both", expand=True)

        # Listbox để hiển thị danh sách luật
        self.rules_listbox = tk.Listbox(rules_list_frame, font=("Courier New", 10), height=15)
        self.rules_listbox.pack(side="left", fill="both", expand=True)

        # Thanh cuộn cho Listbox
        scrollbar = ttk.Scrollbar(rules_list_frame, orient="vertical", command=self.rules_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.rules_listbox.config(yscrollcommand=scrollbar.set)

        # Right side: Options
        right_pane = ttk.Frame(main_frame)
        right_pane.pack(side="left", fill="y", padx=(10, 0))

        # --- Forward Chaining Options ---
        fc_frame = ttk.LabelFrame(right_pane, text="Tùy chọn Suy diễn Tiến", padding=10)
        fc_frame.pack(fill="x", pady=5)
        self.fc_conflict_mode = tk.StringVar(value="Queue")
        ttk.Radiobutton(fc_frame, text="Tập THOA: Queue (FIFO)", variable=self.fc_conflict_mode, value="Queue").pack(
            anchor="w")
        ttk.Radiobutton(fc_frame, text="Tập THOA: Stack (LIFO)", variable=self.fc_conflict_mode, value="Stack").pack(
            anchor="w")

        ttk.Separator(fc_frame, orient="horizontal").pack(fill="x", pady=5)

        self.fc_selection_mode = tk.StringVar(value="Min")
        ttk.Radiobutton(fc_frame, text="Chọn luật: Chỉ số Min", variable=self.fc_selection_mode, value="Min").pack(
            anchor="w")
        ttk.Radiobutton(fc_frame, text="Chọn luật: Chỉ số Max", variable=self.fc_selection_mode, value="Max").pack(
            anchor="w")

        # --- Backward Chaining Options ---
        bc_frame = ttk.LabelFrame(right_pane, text="Tùy chọn Suy diễn Lùi", padding=10)
        bc_frame.pack(fill="x", pady=5)
        self.bc_selection_mode = tk.StringVar(value="Min")
        ttk.Radiobutton(bc_frame, text="Chọn luật: Chỉ số Min", variable=self.bc_selection_mode, value="Min").pack(
            anchor="w")
        ttk.Radiobutton(bc_frame, text="Chọn luật: Chỉ số Max", variable=self.bc_selection_mode, value="Max").pack(
            anchor="w")

        # Control Buttons
        btn_frame = ttk.Frame(right_pane, padding=(0, 10))
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Suy diễn Tiến", command=lambda: self.on_prove("Forward")).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Suy diễn Lùi", command=lambda: self.on_prove("Backward")).pack(fill="x", pady=2)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Vẽ FPG", command=self.on_draw_fpg).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Vẽ RPG", command=self.on_draw_rpg).pack(fill="x", pady=2)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Xóa kết quả", command=lambda: self.txt_out.delete("1.0", "end")).pack(fill="x",
                                                                                                          pady=2)

        rule_actions_frame = ttk.LabelFrame(right_pane, text="Quản lý Luật", padding=10)
        rule_actions_frame.pack(fill="x", pady=5)

        # Tạo một frame con để các nút có thể co giãn đều
        inner_actions_frame = ttk.Frame(rule_actions_frame)
        inner_actions_frame.pack(fill="x", expand=True)

        ttk.Button(inner_actions_frame, text="Thêm Luật", command=self.add_rule_action).pack(side="left", expand=True,
                                                                                             fill="x", padx=2)
        ttk.Button(inner_actions_frame, text="Sửa Luật", command=self.edit_rule_action).pack(side="left", expand=True,
                                                                                             fill="x", padx=2)
        ttk.Button(inner_actions_frame, text="Xóa Luật", command=self.delete_rule_action).pack(side="left", expand=True,
                                                                                               fill="x", padx=2)

        input_grid = ttk.LabelFrame(right_pane, text="Dữ liệu vào", padding=10)
        input_grid.pack(fill="x", pady=5)
        ttk.Label(input_grid, text="Sự kiện (Facts):").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_gt = ttk.Entry(input_grid, width=40)
        self.ent_gt.grid(row=0, column=1, sticky="ew", padx=5)
        self.ent_gt.insert(0, "a,b,c")
        ttk.Label(input_grid, text="Mục tiêu (Goals):").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_goal = ttk.Entry(input_grid, width=40)
        self.ent_goal.grid(row=1, column=1, sticky="ew", padx=5)
        self.ent_goal.insert(0, "r")
        input_grid.columnconfigure(1, weight=1)

        # Output text area
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(side="bottom", fill="both", expand=True, pady=(10, 0))
        ttk.Label(output_frame, text="Kết quả suy diễn:").pack(anchor="w")
        self.txt_out = tk.Text(output_frame, height=10, wrap="word", font=("Courier New", 10))
        self.txt_out.pack(fill="both", expand=True)

        self.last_prov = {}
        self.last_facts = set()
        self.last_rules = []

    # THÊM CÁC PHƯƠNG THỨC NÀY VÀO BÊN TRONG LỚP App

    def _update_rules_display(self):
        """Cập nhật Listbox hiển thị từ self.last_rules."""
        self.rules_listbox.delete(0, "end")
        for i, r in enumerate(self.last_rules):
            # Cập nhật lại ID
            self.last_rules[i] = Rule(premises=r.premises, conclusion=r.conclusion, label=r.label, id=i, op=r.op)

            # SỬA: Dùng đúng toán tử
            op_str = ' & ' if r.op == 'AND' else ' v '
            rule_str = f"({i + 1}) {op_str.join(r.premises)} -> {r.conclusion} | {r.label}"
            self.rules_listbox.insert("end", rule_str)

    # SỬA ĐỔI: App._save_rules_to_file
    def _save_rules_to_file(self):
        """Lưu danh sách self.last_rules hiện tại vào file."""
        if not self.rules_filepath:
            messagebox.showerror("Lỗi", "Không có file nào được mở để lưu.")
            return False

        try:
            with open(self.rules_filepath, 'w', encoding='utf-8') as f:
                for r in self.last_rules:
                    # SỬA: Dùng đúng toán tử
                    op_str = ' & ' if r.op == 'AND' else ' v '
                    premises_str = op_str.join(r.premises)
                    f.write(f"{premises_str} -> {r.conclusion} | {r.label}\n")
            return True
        except Exception as e:
            messagebox.showerror("Lỗi Lưu File", f"Không thể lưu file: {e}")
            return False

    # SỬA ĐỔI: App.add_rule_action (để kiểm tra trùng lặp)
    def add_rule_action(self):
        """Mở cửa sổ để thêm một luật mới."""
        # ... (code mở editor y như cũ) ...

        editor = RuleEditor(self, title="Thêm Luật Mới")
        if editor.result:
            new_rule = editor.result

            # SỬA: Kiểm tra trùng lặp phải bao gồm cả 'op'
            canonical_key = (tuple(sorted(new_rule.premises)), new_rule.conclusion, new_rule.op)
            is_duplicate = any(
                (tuple(sorted(r.premises)), r.conclusion, r.op) == canonical_key
                for r in self.last_rules
            )

            if is_duplicate:
                messagebox.showwarning("Trùng lặp", "Luật này đã tồn tại.")
                return

            self.last_rules.append(new_rule)
            if self._save_rules_to_file():
                self._update_rules_display()
                messagebox.showinfo("Thành công", "Đã thêm và lưu luật mới.")

    def edit_rule_action(self):
        """Mở cửa sổ để sửa luật đã chọn."""
        try:
            selected_index = self.rules_listbox.curselection()[0]
        except IndexError:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một luật để sửa.")
            return

        original_rule = self.last_rules[selected_index]

        editor = RuleEditor(self, title="Sửa Luật", rule=original_rule)
        if editor.result:
            self.last_rules[selected_index] = editor.result
            if self._save_rules_to_file():
                self._update_rules_display()
                messagebox.showinfo("Thành công", "Đã cập nhật và lưu luật.")

    def delete_rule_action(self):
        """Xóa luật đã chọn."""
        try:
            selected_index = self.rules_listbox.curselection()[0]
        except IndexError:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một luật để xóa.")
            return

        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa luật này?"):
            self.last_rules.pop(selected_index)
            if self._save_rules_to_file():
                self._update_rules_display()
                messagebox.showinfo("Thành công", "Đã xóa luật.")

    def load_rules_action(self):
        """Mở hộp thoại để chọn file .txt và tải các luật."""
        filepath = filedialog.askopenfilename(
            title="Chọn file luật",
            filetypes=(("Text Files", "*.txt"), ("All files", "*.*"))
        )
        if not filepath:
            return  # Người dùng không chọn file

        self.rules_filepath = filepath  # Lưu đường dẫn file
        self.last_rules = load_and_parse_rules(filepath)
        self._update_rules_display()

        if self.last_rules:
            messagebox.showinfo("Hoàn tất", f"Đã tải và xử lý xong {len(self.last_rules)} luật hợp lệ.")
        else:
            messagebox.showwarning("Lưu ý", "Không có luật nào hợp lệ được tìm thấy trong file.")

    def on_prove(self, mode):
        if not self.last_rules:
            messagebox.showerror("Lỗi", "Vui lòng tải tập luật từ file trước khi suy diễn.")
            return

        self.last_facts = {x.strip() for x in self.ent_gt.get().split(",") if x.strip()}

        self.last_facts = {x.strip() for x in self.ent_gt.get().split(",") if x.strip()}
        goals = {x.strip() for x in self.ent_goal.get().split(",") if x.strip()}
        if not self.last_facts:
            messagebox.showerror("Lỗi đầu vào", "Sự kiện (GT) không được rỗng.")
            return

        lines = []
        self.last_prov = {}

        if mode == "Forward":
            if not goals:
                messagebox.showerror("Lỗi đầu vào", "Mục tiêu (KL) không được rỗng cho Suy diễn tiến.")
                return

            conflict_mode = self.fc_conflict_mode.get()
            selection_mode = self.fc_selection_mode.get()
            lines.append(f"[Suy diễn Tiến - {conflict_mode} - Chỉ số {selection_mode}]")

            if conflict_mode == "Queue":
                known, prov, steps = forward_chain_bfs(self.last_rules, self.last_facts, selection_mode)
            else:  # Stack
                known, prov, steps = forward_chain_dfs(self.last_rules, self.last_facts, selection_mode)

            self.last_prov = prov
            lines.append(f"GT = {{{', '.join(sorted(self.last_facts))}}}")
            lines.append("Các bước suy diễn:")
            lines.extend(steps)
            ok_all = all(g in known for g in goals)
            lines.append(
                f"\nKết quả: {'CHỨNG MINH ĐƯỢC' if ok_all else 'KHÔNG CHỨNG MINH ĐƯỢC'} KL = {{{', '.join(goals)}}}")

        elif mode == "Backward":
            if not goals:
                messagebox.showerror("Lỗi đầu vào", "Mục tiêu (KL) không được rỗng cho Suy diễn lùi.")
                return

            selection_mode = self.bc_selection_mode.get()
            lines.append(f"[Suy diễn Lùi - Chỉ số {selection_mode}]")
            prov_for_fpg = {}
            all_goals_proved = True

            for g in goals:
                paths = backward_chain_all(g, self.last_rules, self.last_facts, set(), selection_mode)
                if not paths:
                    lines.append(f"\nKhông chứng minh được '{g}'.")
                    all_goals_proved = False
                else:
                    if selection_mode == 'Min':
                        min_len = min(len(p) for p in paths)
                        filtered_paths = [p for p in paths if len(p) == min_len]
                        lines.append(
                            f"\nTìm thấy {len(filtered_paths)} đường chứng minh NGẮN NHẤT cho '{g}' (Số bước: {min_len}):")
                    else:  # 'Max'
                        max_len = max(len(p) for p in paths)
                        filtered_paths = [p for p in paths if len(p) == max_len]
                        lines.append(
                            f"\nTìm thấy {len(filtered_paths)} đường chứng minh DÀI NHẤT cho '{g}' (Số bước: {max_len}):")

                    for i, chain in enumerate(filtered_paths, 1):
                        lines.append(f"  Đường chứng minh #{i}:")
                        for r in chain:
                            lines.append(f"    - Áp dụng '{r.label}': {{{', '.join(r.premises)}}} → {r.conclusion}")

                    best_path_rules = filtered_paths[0]
                    for r in best_path_rules:
                        prov_for_fpg[r.conclusion] = (r, r.premises)

            self.last_prov = prov_for_fpg
            lines.append(
                f"\nKết quả: {'CHỨNG MINH ĐƯỢC' if all_goals_proved else 'KHÔNG CHỨNG MINH ĐƯỢC'} KL = {{{', '.join(goals)}}}")

        self.txt_out.delete("1.0", "end")
        self.txt_out.insert("1.0", "\n".join(lines))

    def on_draw_fpg(self):
        draw_fpg(self.last_prov, self.last_facts)

    def on_draw_rpg(self):
        if not self.last_rules:
            messagebox.showerror("Lỗi", "Vui lòng tải tập luật từ file để vẽ đồ thị.")
            return
        draw_rpg(self.last_rules)


if __name__ == "__main__":
    app = App()
    app.mainloop()
