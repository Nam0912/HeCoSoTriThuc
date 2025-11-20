import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import nltk
from nltk.corpus import wordnet as wn
import requests
import threading
import os

# ==========================================
# 1. SETUP
# ==========================================
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')


# ==========================================
# 2. ENGINES
# ==========================================

def fetch_wikidata_composition_only(keyword):
    """WIKIDATA: Chỉ lấy luật AND (Parts/Material)"""
    parts = []
    url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT DISTINCT ?compLabel WHERE {{
      ?item rdfs:label "{keyword.lower()}"@en.
      {{ ?item wdt:P527 ?comp. }} UNION {{ ?item wdt:P186 ?comp. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 10
    """
    try:
        headers = {'User-Agent': 'ExpertSystemBot/DedupMode'}
        r = requests.get(url, params={'format': 'json', 'query': query}, headers=headers, timeout=3)
        data = r.json()
        for item in data['results']['bindings']:
            val = item['compLabel']['value'].lower()
            if not val.startswith("q") and "http" not in val and val != keyword:
                parts.append(val)
        return list(set(parts))
    except:
        return []


def fetch_wordnet_structure_only(keyword):
    """WORDNET: Chỉ lấy luật OR (Hyponyms)"""
    children = []
    synsets = wn.synsets(keyword)
    if not synsets: return []
    syn = synsets[0]
    for h in syn.hyponyms():
        name = h.lemmas()[0].name().lower().replace('_', ' ')
        if name != keyword:
            children.append(name)
    return children


# ==========================================
# 3. LOGIC TẠO LUẬT
# ==========================================

def generate_optimized_rules(input_list, status_callback):
    rules = set()
    processed = set()
    queue = [(w.strip().lower(), 0) for w in input_list if w.strip()]
    MAX_NODES = 100
    count = 0

    while queue and count < MAX_NODES:
        current_word, depth = queue.pop(0)
        if current_word in processed: continue
        processed.add(current_word)
        count += 1

        if status_callback:
            status_callback(f"Processing ({count}): {current_word}...")

        # --- 1. AND Rules (Wikidata) ---
        if depth <= 1:
            parts = fetch_wikidata_composition_only(current_word)
            if len(parts) < 2:
                syns = wn.synsets(current_word)
                if syns:
                    wn_parts = syns[0].part_meronyms() + syns[0].substance_meronyms()
                    parts.extend([p.lemmas()[0].name().lower().replace('_', ' ') for p in wn_parts])

            # Khử trùng và SẮP XẾP
            parts = sorted(list(set(parts)))

            if len(parts) >= 2:
                # Lấy 4 phần tử đầu tiên, nhưng cũng phải đảm bảo 4 phần tử này được sắp xếp
                selected_parts = sorted(parts[:4])
                premises = " & ".join(selected_parts)

                rule = f"{premises} -> {current_word} | Rule_AND_{current_word.replace(' ', '_')}"
                rules.add(rule)

        # --- 2. OR Rules (WordNet) ---
        children = fetch_wordnet_structure_only(current_word)
        chunk_size = 5
        for i in range(0, len(children), chunk_size):
            chunk = children[i:i + chunk_size]

            if len(chunk) > 1:
                # SẮP XẾP trước khi tạo luật OR
                chunk = sorted(chunk)
                premises = " v ".join(chunk)
                rules.add(f"{premises} -> {current_word} | Rule_OR_{current_word}_{i}")
            elif len(chunk) == 1:
                rules.add(f"{chunk[0]} -> {current_word} | Rule_IsA_{current_word}_{i}")

        if depth < 1:
            for child in children:
                if child not in processed:
                    queue.append((child, depth + 1))

    return sorted(list(rules))

# ==========================================
# 4. GUI (ĐÃ SỬA LỖI SAVE)
# ==========================================
class AdminGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Admin: Rule Generator (No Duplicates)")
        self.geometry("900x700")

        tk.Label(self, text="KNOWLEDGE BASE MANAGER", font=("Arial", 16, "bold")).pack(pady=10)

        frm = tk.Frame(self)
        frm.pack(pady=10)
        tk.Label(frm, text="Topics (English):").pack(side="left")
        self.ent = tk.Entry(frm, width=40)
        self.ent.pack(side="left", padx=5)
        self.ent.bind("<Return>", lambda e: self.start())
        tk.Button(frm, text="Generate", command=self.start, bg="blue", fg="white").pack(side="left")

        self.lbl_status = tk.Label(self, text="Ready", fg="blue")
        self.lbl_status.pack()

        tk.Button(self, text="💾 Save Rules (No Duplicates)", command=self.save_smart, bg="green", fg="white").pack(
            pady=5)

        self.txt = tk.Text(self, height=20)
        self.txt.pack(fill="both", expand=True, padx=20, pady=10)
        self.new_rules = []

    def start(self):
        inp = self.ent.get()
        if not inp: return
        self.lbl_status.config(text="Starting...")
        self.txt.delete(1.0, tk.END)
        threading.Thread(target=self.run_logic, args=(inp,)).start()

    def run_logic(self, inp):
        topics = [x.strip() for x in inp.split(",") if x.strip()]
        # Gọi hàm logic bên ngoài class
        self.new_rules = generate_optimized_rules(topics, lambda msg: self.lbl_status.config(text=msg))

        self.txt.insert(tk.END, f"# New Rules Generated:\n")
        for r in self.new_rules:
            self.txt.insert(tk.END, r + "\n")
        self.lbl_status.config(text=f"Done. Generated {len(self.new_rules)} new rules.")

    # =================================================
    # PHẦN SỬA LỖI Ở ĐÂY (Thêm @staticmethod)
    # =================================================
    @staticmethod
    def normalize_rule_string(rule_str):
        """
        Sắp xếp lại vế trái để chuẩn hóa.
        VD: "b & a -> c" biến thành "a & b -> c"
        """
        if "->" not in rule_str: return rule_str

        try:
            left, right = rule_str.split("->", 1)
            premises_str = left.strip()
            conclusion_part = right.strip()

            # Chuẩn hóa AND
            if "&" in premises_str:
                parts = [p.strip() for p in premises_str.split("&")]
                parts.sort()
                new_left = " & ".join(parts)

            # Chuẩn hóa OR
            elif " v " in premises_str:
                parts = [p.strip() for p in premises_str.split(" v ")]
                parts.sort()
                new_left = " v ".join(parts)

            else:
                new_left = premises_str

            return f"{new_left} -> {conclusion_part}"
        except:
            return rule_str

    def save_smart(self):
        if not self.new_rules:
            messagebox.showwarning("Empty", "No new rules to save!")
            return

        path = filedialog.asksaveasfilename(defaultextension=".txt", title="Select Knowledge Base File")
        if not path: return

        existing_rules = set()

        # 1. Đọc và CHUẨN HÓA dữ liệu cũ
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "->" in line and not line.startswith("#"):
                            # Gọi hàm tĩnh bằng self.
                            normalized_line = self.normalize_rule_string(line)
                            existing_rules.add(normalized_line)
            except Exception as e:
                messagebox.showerror("Error", f"Read error: {e}")
                return

        # 2. Chuẩn hóa dữ liệu mới và gộp vào
        for r in self.new_rules:
            existing_rules.add(self.normalize_rule_string(r))

        # 3. Ghi lại
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("# Knowledge Base (Normalized & Deduped)\n")
                f.write("# Format: Premises -> Conclusion | Label\n\n")
                for rule in sorted(list(existing_rules)):
                    f.write(rule + "\n")

            messagebox.showinfo("Success", f"Cleaned and Saved!\nTotal Unique Rules: {len(existing_rules)}")
        except Exception as e:
            messagebox.showerror("Error", f"Write error: {e}")


if __name__ == "__main__":
    app = AdminGUI()
    app.mainloop()