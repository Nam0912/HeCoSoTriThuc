# =============================
# GUI Inference Engine - Đáp ứng yêu cầu Bài tập 1
# =============================
import tkinter as tk
from tkinter import ttk, messagebox
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
    id: int # Thêm ID để theo dõi chỉ số

def parse_rules(text: str) -> List[Rule]:
    rules: List[Rule] = []
    for i, ln in enumerate(text.splitlines()):
        raw = ln.strip()
        if not raw or raw.startswith("#"):
            continue
        if "->" not in raw:
            raise ValueError(f"Thiếu '->' trong luật: {raw}")
        left, right = raw.split("->", 1)
        left = left.replace("^", "&")
        premises = tuple(p.strip() for p in left.split("&") if p.strip())
        if not premises:
            raise ValueError(f"Luật không có tiền đề: {raw}")
        if "|" in right:
            concl, label = right.split("|", 1)
        else:
            concl, label = right, f"R{i+1}"
        conclusion = concl.strip()
        label = label.strip()
        rules.append(Rule(premises, conclusion, label, i))
    return rules

# ---------- Core Engine: Forward Chaining Algorithms ----------

# --- FORWARD CHAINING (BFS / Queue) ---
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
            if r.conclusion not in known and current_fact in r.premises:
                if all(p in known for p in r.premises):
                    new_fact = r.conclusion
                    known.add(new_fact)
                    prov[new_fact] = (r, r.premises)
                    steps.append(f"({len(steps)+1}) Kích hoạt '{r.label}': {{{', '.join(r.premises)}}} → {new_fact}")
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
                if all(p in known for p in r.premises):
                    new_fact = r.conclusion
                    known.add(new_fact)
                    prov[new_fact] = (r, r.premises)
                    steps.append(f"({len(steps)+1}) Kích hoạt '{r.label}': {{{', '.join(r.premises)}}} → {new_fact}")
                    _dfs_visit(new_fact)

    for fact in initial_facts:
        _dfs_visit(fact)
        
    return known, prov, steps

# ---------- Core Engine: Backward Chaining Algorithm ----------
def backward_chain_all(goal: str, rules: List[Rule], facts: Set[str], seen: Set[str], selection_mode: str) -> List[List[Rule]]:
    if goal in facts:
        return [[]]
    if goal in seen:
        return []
    seen.add(goal)

    paths = []
    
    rule_source = rules if selection_mode == 'Min' else list(reversed(rules))
    relevant_rules = [r for r in rule_source if r.conclusion == goal]

    for r in relevant_rules:
        all_subpaths = []
        valid = True
        for p in r.premises:
            sub = backward_chain_all(p, rules, facts, seen.copy(), selection_mode)
            if not sub:
                valid = False
                break
            all_subpaths.append(sub)
        if valid:
            for combo in itertools.product(*all_subpaths):
                chain = list(itertools.chain(*combo)) + [r]
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
        color = "#9ecae1" if node in prov else "#f7f7f7" # Kết luận màu xanh, GT màu xám
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

# ---------- GUI Application ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inference Engine")
        self.geometry("1100x800")

        # Main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Left side: Rules, Facts, Goals
        left_pane = ttk.Frame(main_frame)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 10))
        # Sửa lại dòng này
        DEFAULT_RULES = textwrap.dedent("""\
            a & b & C -> c | Định lý cos: c^2 = a^2 + b^2 - 2ab·cos(C)
            a & b & ma -> c | Quan hệ trung tuyến ma^2 = (2b^2+2c^2-a^2)/4
            a & b & mb -> c | Quan hệ trung tuyến mb^2 = (2a^2+2c^2-b^2)/4
            A & B -> C | Tổng góc: C = pi - A - B
            a & hc -> B | sin(B) = hc / a
            b & hc -> A | sin(A) = hc / b
            a & R -> A | sin(A) = a / (2R)
            b & R -> B | sin(B) = b / (2R)
            a & b & c -> P | Chu vi: P = a + b + c
            a & b & c -> p | Nửa chu vi: p = (a+b+c)/2
            a & b & c -> mc | mc = 0.5·sqrt(2a^2 + 2b^2 - c^2)
            a & ha -> S | S = a·ha/2
            a & b & C -> S | S = ab·sin(C)/2
            a & b & c & p -> S | Heron: S = sqrt(p(p-a)(p-b)(p-c))
            b & S -> hb | hb = 2S / b
            S & p -> r | r = S / p
            """)
        ttk.Label(left_pane, text="Luật (Rules):").pack(anchor="w")
        self.txt_rules = tk.Text(left_pane, height=15, wrap="word", font=("Courier New", 10))
        self.txt_rules.pack(fill="both", expand=True)
        self.txt_rules.insert("1.0", DEFAULT_RULES)
        
        input_grid = ttk.Frame(left_pane, padding=(0, 10))
        input_grid.pack(fill="x")
        ttk.Label(input_grid, text="Sự kiện (Facts):").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_gt = ttk.Entry(input_grid, width=40)
        self.ent_gt.grid(row=0, column=1, sticky="ew", padx=5)
        self.ent_gt.insert(0, "a,f,g")
        ttk.Label(input_grid, text="Mục tiêu (Goals):").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_goal = ttk.Entry(input_grid, width=40)
        self.ent_goal.grid(row=1, column=1, sticky="ew", padx=5)
        self.ent_goal.insert(0, "e")
        input_grid.columnconfigure(1, weight=1)

        # Right side: Options
        right_pane = ttk.Frame(main_frame)
        right_pane.pack(side="left", fill="y", padx=(10, 0))

        # --- Forward Chaining Options ---
        fc_frame = ttk.LabelFrame(right_pane, text="Tùy chọn Suy diễn Tiến", padding=10)
        fc_frame.pack(fill="x", pady=5)
        self.fc_conflict_mode = tk.StringVar(value="Queue")
        ttk.Radiobutton(fc_frame, text="Tập THOA: Queue (FIFO)", variable=self.fc_conflict_mode, value="Queue").pack(anchor="w")
        ttk.Radiobutton(fc_frame, text="Tập THOA: Stack (LIFO)", variable=self.fc_conflict_mode, value="Stack").pack(anchor="w")
        
        ttk.Separator(fc_frame, orient="horizontal").pack(fill="x", pady=5)
        
        self.fc_selection_mode = tk.StringVar(value="Min")
        ttk.Radiobutton(fc_frame, text="Chọn luật: Chỉ số Min", variable=self.fc_selection_mode, value="Min").pack(anchor="w")
        ttk.Radiobutton(fc_frame, text="Chọn luật: Chỉ số Max", variable=self.fc_selection_mode, value="Max").pack(anchor="w")

        # --- Backward Chaining Options ---
        bc_frame = ttk.LabelFrame(right_pane, text="Tùy chọn Suy diễn Lùi", padding=10)
        bc_frame.pack(fill="x", pady=5)
        self.bc_selection_mode = tk.StringVar(value="Min")
        ttk.Radiobutton(bc_frame, text="Chọn luật: Chỉ số Min", variable=self.bc_selection_mode, value="Min").pack(anchor="w")
        ttk.Radiobutton(bc_frame, text="Chọn luật: Chỉ số Max", variable=self.bc_selection_mode, value="Max").pack(anchor="w")

        # Control Buttons
        btn_frame = ttk.Frame(right_pane, padding=(0, 10))
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Suy diễn Tiến", command=lambda: self.on_prove("Forward")).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Suy diễn Lùi", command=lambda: self.on_prove("Backward")).pack(fill="x", pady=2)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Vẽ FPG", command=self.on_draw_fpg).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Vẽ RPG", command=self.on_draw_rpg).pack(fill="x", pady=2)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Xóa kết quả", command=lambda: self.txt_out.delete("1.0", "end")).pack(fill="x", pady=2)

        # Output text area
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(side="bottom", fill="both", expand=True, pady=(10, 0))
        ttk.Label(output_frame, text="Kết quả suy diễn:").pack(anchor="w")
        self.txt_out = tk.Text(output_frame, height=10, wrap="word", font=("Courier New", 10))
        self.txt_out.pack(fill="both", expand=True)

        self.last_prov = {}
        self.last_facts = set()
        self.last_rules = []

    def on_prove(self, mode):
        try:
            self.last_rules = parse_rules(self.txt_rules.get("1.0", "end"))
        except Exception as e:
            messagebox.showerror("Lỗi phân tích luật", str(e))
            return

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
            else: # Stack
                known, prov, steps = forward_chain_dfs(self.last_rules, self.last_facts, selection_mode)
            
            self.last_prov = prov
            lines.append(f"GT = {{{', '.join(sorted(self.last_facts))}}}")
            lines.append("Các bước suy diễn:")
            lines.extend(steps)
            ok_all = all(g in known for g in goals)
            lines.append(f"\nKết quả: {'CHỨNG MINH ĐƯỢC' if ok_all else 'KHÔNG CHỨNG MINH ĐƯỢC'} KL = {{{', '.join(goals)}}}")

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
                    sorted_paths = sorted([(len(chain), chain) for chain in paths])
                    lines.append(f"\nTìm thấy {len(paths)} đường chứng minh cho '{g}', sắp xếp theo độ ưu tiên (ngắn nhất):")
                    best_cost = sorted_paths[0][0]
                    for i, (cost, chain) in enumerate(sorted_paths, 1):
                        highlight = " (Tốt nhất)" if cost == best_cost else ""
                        lines.append(f"  Đường chứng minh #{i} (Số bước: {cost}){highlight}:")
                        for r in chain:
                            lines.append(f"    - Áp dụng '{r.label}': {{{', '.join(r.premises)}}} → {r.conclusion}")
                    best_path_rules = sorted_paths[0][1]
                    for r in best_path_rules:
                        prov_for_fpg[r.conclusion] = (r, r.premises)
            
            self.last_prov = prov_for_fpg
            lines.append(f"\nKết quả: {'CHỨNG MINH ĐƯỢC' if all_goals_proved else 'KHÔNG CHỨNG MINH ĐƯỢC'} KL = {{{', '.join(goals)}}}")

        self.txt_out.delete("1.0", "end")
        self.txt_out.insert("1.0", "\n".join(lines))

    def on_draw_fpg(self):
        draw_fpg(self.last_prov, self.last_facts)

    def on_draw_rpg(self):
        try:
            rules = parse_rules(self.txt_rules.get("1.0", "end"))
            draw_rpg(rules)
        except Exception as e:
            messagebox.showerror("Lỗi phân tích luật", str(e))

if __name__ == "__main__":
    app = App()
    app.mainloop()