import nltk
from nltk.corpus import wordnet as wn

# Tải dữ liệu WordNet nếu chưa có
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')


def clean_term(term):
    """Chuẩn hóa từ: chữ thường, thay dấu _ bằng khoảng trắng"""
    return term.lemmas()[0].name().lower().replace('_', ' ')


def generate_combined_knowledge_base(root_topics, filename="full_knowledge_base.txt"):
    """
    Sinh tập luật tổng hợp cho ToanHoc.py:
    1. Luật AND (&): Dựa trên Cấu tạo (Meronyms) - Nếu có đủ bộ phận -> Suy ra vật.
    2. Luật OR (v): Dựa trên Phân loại (Hyponyms) - Nếu là loại con A hoặc B -> Suy ra cha.
    """
    rules = set()  # Dùng set để tự động loại bỏ luật trùng lặp hoàn toàn
    seen_logic = set()  # Kiểm soát logic để tránh chồng chéo

    print(f"🚀 Đang khởi tạo tri thức cho các chủ đề: {root_topics}...")

    # Duyệt qua từng chủ đề gốc và mở rộng xuống các lớp con
    for topic in root_topics:
        synsets = wn.synsets(topic)
        if not synsets: continue

        # Sử dụng hàng đợi để duyệt cây (BFS)
        queue = [synsets[0]]
        processed_synsets = set()

        while queue:
            current_syn = queue.pop(0)

            # Tránh vòng lặp vô tận
            if current_syn.name() in processed_synsets:
                continue
            processed_synsets.add(current_syn.name())

            current_name = clean_term(current_syn)

            # ==========================================
            # 1. SINH LUẬT AND (&) - CẤU TẠO (Parts -> Whole)
            # Logic: part1 & part2 -> whole
            # ==========================================
            parts = current_syn.part_meronyms()
            part_names = [clean_term(p) for p in parts if clean_term(p) != current_name]

            # Chỉ tạo luật AND nếu có ít nhất 2 bộ phận (để logic chặt chẽ)
            if len(part_names) >= 2:
                # Lấy tối đa 3 bộ phận đặc trưng nhất để luật không quá dài
                selected_parts = part_names[:3]
                premises = " & ".join(selected_parts)

                rule_str = f"{premises} -> {current_name} | Rule_CauTao_{current_name.replace(' ', '_')}"

                # Kiểm tra trùng lặp logic
                if rule_str not in rules:
                    rules.add(rule_str)

            # ==========================================
            # 2. SINH LUẬT OR (v) - PHÂN LOẠI (Children -> Parent)
            # Logic: child1 v child2 -> parent
            # ==========================================
            hyponyms = current_syn.hyponyms()
            child_names = [clean_term(c) for c in hyponyms if clean_term(c) != current_name]

            # Gom nhóm con: chia thành các nhóm nhỏ (chunk) để tạo luật OR
            # Ví dụ: xe sedan v xe tải -> xe hơi
            chunk_size = 4
            for i in range(0, len(child_names), chunk_size):
                chunk = child_names[i:i + chunk_size]
                if len(chunk) > 0:
                    if len(chunk) > 1:
                        # Tạo luật OR
                        premises = " v ".join(chunk)
                        label = f"Rule_PhanLoai_OR_{current_name.replace(' ', '_')}_{i}"
                    else:
                        # Nếu chỉ có 1 con lẻ loi, tạo luật đơn (Simple Rule)
                        premises = chunk[0]
                        label = f"Rule_PhanLoai_IsA_{current_name.replace(' ', '_')}_{i}"

                    rule_str = f"{premises} -> {current_name} | {label}"
                    rules.add(rule_str)

            # Tiếp tục duyệt sâu xuống các con để mở rộng tri thức
            # Giới hạn độ sâu bằng cách chỉ thêm vào queue nếu chưa duyệt
            # (Ở đây duyệt sâu tự nhiên theo dữ liệu WordNet)
            for child in hyponyms:
                if child.name() not in processed_synsets:
                    queue.append(child)

            # Giới hạn số lượng synset xử lý để tránh file quá lớn (Optional)
            if len(processed_synsets) > 200:  # Xử lý khoảng 200 khái niệm mỗi chủ đề
                break

    # ==========================================
    # GHI RA FILE
    # ==========================================
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Knowledge Base Generated from WordNet\n")
        f.write("# Format: Premises -> Conclusion | Label\n")
        f.write("# Contains both AND (&) and OR (v) rules.\n\n")

        # Sắp xếp để dễ nhìn
        for r in sorted(list(rules)):
            f.write(r + "\n")

    print(f"✅ Đã hoàn tất! File '{filename}' đã được tạo với {len(rules)} luật.")
    print("👉 Hãy nạp file này vào ToanHoc.py và thử nghiệm.")


# --- CẤU HÌNH CHẠY ---
# Nhập các chủ đề bạn muốn tạo tri thức
my_topics = ["car", "table"]
generate_combined_knowledge_base(my_topics)