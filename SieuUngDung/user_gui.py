import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
from io import BytesIO
from ToanHoc import forward_chain_bfs


# ======================
# RULE STRUCTURE
# ======================
class Rule:
    def __init__(self, label, premises, conclusion, op):
        self.label = label
        self.premises = premises
        self.conclusion = conclusion
        self.op = op


# ======================
# LOAD RULES FROM FILE
# ======================
def load_rules(filename="wordnet.txt"):
    rules = []
    possible_objects = set()

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "->" not in line:
                continue

            left, right = line.split("->", 1)
            left = left.strip()
            right = right.strip()

            if "|" in right:
                conclusion, label = right.split("|", 1)
                conclusion = conclusion.strip().lower()
                label = label.strip()
            else:
                conclusion = right.strip().lower()
                label = f"RULE_{len(rules)}"

            possible_objects.add(conclusion)

            if "&" in left:
                prem = [p.strip().lower() for p in left.split("&")]
                op = "AND"
            elif "v" in left:
                prem = [p.strip().lower() for p in left.split("v")]
                op = "OR"
            else:
                prem = [left.strip().lower()]
                op = "AND"

            rules.append(Rule(label, tuple(prem), conclusion, op))

    return rules, possible_objects


# ======================
# GUI
# ======================
class UserGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("🧠 Expert System – Forward Chaining")
        self.master.geometry("1000x650")
        style = ttk.Style()
        style.configure(
            "TButton",
            font=("Segoe UI", 10, "bold"),
            padding=6
        )

        self.rules, self.possible_objects = load_rules("wordnet.txt")

        # MAIN FRAME: 2 COLUMNS FIXED 50/50
        main_frame = ttk.Frame(master, padding=10)
        main_frame.pack(fill="both", expand=True)

        total_width = 1000
        main_frame.grid_columnconfigure(0, weight=1, minsize=total_width // 2)
        main_frame.grid_columnconfigure(1, weight=1, minsize=total_width // 2)

        # ================================================
        # LEFT COLUMN
        # ================================================
        left_frame = ttk.LabelFrame(main_frame, text="Input Facts", padding=15)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_frame.grid_columnconfigure(0, weight=1)

        left_frame.grid_rowconfigure(10, weight=1)

        ttk.Label(left_frame, text="Enter features separated by commas:",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.entry = ttk.Entry(left_frame, width=40, font=("Segoe UI", 11))
        self.entry.pack(fill="x", pady=10)

        button_width = 28  # mọi nút đều dùng chung kích thước

        btn_run = ttk.Button(left_frame, text="🔥 Run Forward Chaining",
                             command=self.on_infer, width=button_width)
        btn_run.pack(pady=6)

        btn_show = ttk.Button(left_frame, text="📜 Show Steps",
                              command=self.toggle_steps, width=button_width)
        btn_show.pack(pady=6)

        btn_clear = ttk.Button(left_frame, text="🧹 Clear All",
                               command=self.clear_all, width=button_width)
        btn_clear.pack(pady=12)

        # Steps (hidden by default)
        self.steps_frame = ttk.Frame(left_frame)
        self.steps_visible = False

        self.steps_text = tk.Text(self.steps_frame, height=15, wrap="word",
                                  font=("Consolas", 9), background="#f0f0f0")
        self.steps_text.pack(fill="both", expand=True)

        # ================================================
        # RIGHT COLUMN
        # ================================================
        right_frame = ttk.LabelFrame(main_frame, text="Inference Results", padding=15)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        ttk.Label(right_frame, text="Inferred Objects:",
                  font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")

        # CHIP TAG AREA (THAY CHO TEXT)
        self.tags_frame = tk.Frame(right_frame, bg="#ffffff")
        self.tags_frame.grid(row=1, column=0, sticky="nw", pady=5)

        # IMAGE
        self.img_label = ttk.Label(right_frame)
        self.img_label.grid(row=2, column=0, pady=10)

    # ======================
    # CLEAR TAGS
    # ======================
    def clear_tags(self):
        for widget in self.tags_frame.winfo_children():
            widget.destroy()

    # ======================
    # RUN FORWARD CHAINING
    # ======================
    def on_infer(self):
        user_input = self.entry.get().strip()
        self.clear_tags()
        self.steps_text.delete("1.0", "end")
        self.img_label.config(image="", text="")

        if not user_input:
            messagebox.showwarning("Error", "Please enter at least one fact.")
            return

        initial_facts = {x.strip().lower() for x in user_input.split(",") if x.strip()}
        known, _, steps = forward_chain_bfs(self.rules, initial_facts, "Min")

        inferred = sorted(list(known.intersection(self.possible_objects)))

        # ---- CHIP TAG RENDER ----
        if inferred:
            for obj in inferred:
                tag = tk.Label(
                    self.tags_frame,
                    text=obj,
                    bg="#d1e7ff",
                    fg="#084298",
                    padx=12,
                    pady=6,
                    font=("Segoe UI", 10, "bold"),
                    borderwidth=1,
                    relief="solid"
                )
                tag.pack(side="left", padx=5, pady=5)

            self.show_image(inferred[0])
        else:
            tag = tk.Label(self.tags_frame, text="❌ No objects inferred",
                           bg="#ffd6d6", fg="#7a0000", padx=12, pady=6,
                           font=("Segoe UI", 10, "bold"), borderwidth=1, relief="solid")
            tag.pack(side="left", padx=5, pady=5)

        # ---- reasoning steps ----
        if steps:
            self.steps_text.insert("end", "\n".join(steps))
        else:
            self.steps_text.insert("end", "No rules fired.")

    # ======================
    # IMAGE DISPLAY
    # ======================
    def show_image(self, keyword):
        try:
            url = f"https://pixabay.com/api/?key=53101775-37777e069e2eb137c3c11588e&q={keyword}&image_type=photo"
            data = requests.get(url, timeout=6).json()

            if data.get("hits"):
                img_url = data["hits"][0]["webformatURL"]
                img_data = requests.get(img_url, timeout=6).content
                img = Image.open(BytesIO(img_data)).resize((260, 260))
                self.photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=self.photo)
            else:
                self.img_label.config(text="(No image found)")
        except:
            self.img_label.config(text="(Image load error)")

    # ======================
    # SHOW / HIDE STEPS
    # ======================
    def toggle_steps(self):
        if self.steps_visible:
            self.steps_frame.pack_forget()
        else:
            self.steps_frame.pack(fill="both", expand=True, pady=10)

        self.steps_visible = not self.steps_visible

    # ======================
    # CLEAR ALL
    # ======================
    def clear_all(self):
        self.entry.delete(0, "end")
        self.clear_tags()
        self.steps_text.delete("1.0", "end")
        self.img_label.config(image="", text="")
        self.steps_frame.pack_forget()
        self.steps_visible = False


if __name__ == "__main__":
    root = tk.Tk()
    app = UserGUI(root)
    root.mainloop()
