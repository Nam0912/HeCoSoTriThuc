import requests
from googletrans import Translator
from collections import defaultdict

translator = Translator()

# Các quan hệ hữu ích
useful_relations = {"UsedFor", "MadeOf", "PartOf", "IsA"}

# Từ rác nên loại bỏ
ban_words = {"thing", "object", "something", "someone", "money", "news", "page",
             "marker", "note", "card", "booklet", "item"}


def tra_cuu_conceptnet(concept_en, limit=100):
    """
    Truy vấn ConceptNet đúng định dạng /c/en/{từ}
    và trả về danh sách (start, rel, end)
    """
    url = f"https://api.conceptnet.io/c/en/{concept_en}?offset=0&limit={limit}"
    try:
        data = requests.get(url).json()
    except Exception as e:
        print("⚠️ Lỗi truy cập API:", e)
        return []

    edges = []
    for edge in data.get("edges", []):
        rel = edge["rel"]["label"]
        if rel not in useful_relations:
            continue

        start = edge["start"]["label"].lower()
        end = edge["end"]["label"].lower()

        # Chỉ lấy khái niệm tiếng Anh
        if not (edge["start"]["@id"].startswith("/c/en/") and edge["end"]["@id"].startswith("/c/en/")):
            continue

        # Loại bỏ từ rác
        if any(bad in start for bad in ban_words) or any(bad in end for bad in ban_words):
            continue

        edges.append((start, rel, end))
    return edges


def sinh_luat_tu_conceptnet(ds_tu_viet, limit_per_word=100):
    """Sinh luật tri thức vật–hành động hoặc vật–chất liệu."""
    en_list = [translator.translate(t.strip(), src="vi", dest="en").text.lower() for t in ds_tu_viet]
    print(f"🔍 Đang sinh tri thức cho: {en_list}")

    rules = []

    for concept in en_list:
        edges = tra_cuu_conceptnet(concept, limit_per_word)
        for s, rel, e in edges:
            # nếu đồ vật được làm từ chất liệu
            if rel == "MadeOf":
                rules.append(f"{e} -> {s}")
            # nếu dùng để làm gì
            elif rel == "UsedFor":
                rules.append(f"{e} -> {s}")
            # nếu là một phần của
            elif rel == "PartOf":
                rules.append(f"{s} -> {e}")
            # nếu là phân cấp
            elif rel == "IsA":
                rules.append(f"{s} -> {e}")

    # loại trùng
    rules = sorted(set(rules))

    # lưu file
    with open("knowledge_base.txt", "w", encoding="utf-8") as f:
        for r in rules:
            f.write(r + "\n")

    print(f"\n💾 Đã sinh {len(rules)} luật vào 'knowledge_base.txt'")

    # hiển thị bản dịch mẫu
    if rules:
        print("\n📘 Một số luật mẫu (dịch sang tiếng Việt):")
        for rule in rules[:8]:
            left, right = rule.split(" -> ")
            vi_left = translator.translate(left, src="en", dest="vi").text
            vi_right = translator.translate(right, src="en", dest="vi").text
            print(f"- {vi_left} -> {vi_right}")

    return rules


# =========================
# CHẠY THỬ
# =========================
if __name__ == "__main__":
    tu_nhap = input("Nhập các khái niệm (cách nhau bởi dấu phẩy): ")
    ds = [x.strip() for x in tu_nhap.split(",") if x.strip()]
    sinh_luat_tu_conceptnet(ds)
