import requests
from googletrans import Translator
from collections import Counter

translator = Translator()

relation_vi = {
    "UsedFor": "dùng để",
    "MadeOf": "làm từ",
    "IsA": "là một loại",
    "PartOf": "là một phần của",
    "CapableOf": "có khả năng",
    "AtLocation": "có ở",
    "Synonym": "đồng nghĩa với",
    "Antonym": "trái nghĩa với"
}

def tra_cuu_conceptnet(tu_en):
    url = f"https://api.conceptnet.io/c/en/{tu_en}?offset=0&limit=50"
    try:
        res = requests.get(url).json()
    except:
        return []
    edges = []
    for edge in res.get('edges', []):
        rel = edge['rel']['label']
        if rel not in relation_vi:
            continue
        start = edge['start']['label']
        end = edge['end']['label']
        edges.append((start, rel, end))
    return edges


def tra_cuu_nhieu_khai_niem(tu_viet_list):
    en_list = [translator.translate(t.strip(), src='vi', dest='en').text.lower() for t in tu_viet_list]
    print(f"🔍 Tìm tri thức cho: {en_list}\n")

    all_edges = []
    for tu in en_list:
        edges = tra_cuu_conceptnet(tu)
        all_edges.extend(edges)

    # Gom nhóm theo "end" (kết quả)
    ket_qua = Counter([e[2] for e in all_edges])

    # Lọc ra các kết quả có liên hệ với nhiều khái niệm nhập vào
    ket_qua_pho_bien = ket_qua.most_common(10)

    print("\n📘 Các khái niệm liên quan nhiều nhất:")
    goi_y = []
    for end, count in ket_qua_pho_bien:
        vi = translator.translate(end, src='en', dest='vi').text
        print(f"- {vi} ({end}) xuất hiện {count} lần")
        goi_y.append(vi)

    return goi_y


# =========================
# Chạy thử
# =========================
tukhoa = input("Nhập các khái niệm (cách nhau bởi dấu phẩy): ")
ds = [x.strip() for x in tukhoa.split(",")]

goi_y = tra_cuu_nhieu_khai_niem(ds)

print("\n🧠 Gợi ý vật dụng/phương tiện phù hợp:")
for g in goi_y:
    print("-", g)
