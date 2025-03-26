QUANTITY_MAP = {
    'nhất': 1, 'đầu': 1, 'một': 1, 'số 1': 1, 'top đầu': 1,
    'hai': 2, 'nhì': 2, 'số 2': 2, 'hạng hai': 2,
    'ba': 3, 'số 3': 3, 'hạng ba': 3,
    'bốn': 4, 'số 4': 4,
    'năm': 5, 'số 5': 5,
    'vài': 3, 'một vài': 3
}


def process_quantity(text: str, entity_value: str = None) -> int:
    """
    Xử lý số lượng từ text hoặc entity value
    Args:
        text: Câu input từ người dùng
        entity_value: Giá trị entity quantity (nếu có)
    Returns:
        Số lượng đã chuẩn hóa (mặc định 3)
    """
    # Ưu tiên xử lý entity
    if entity_value:
        if entity_value.isdigit():
            return int(entity_value)
        return QUANTITY_MAP.get(entity_value.lower(), 3)

    # Fallback: Tìm trong text
    text_lower = text.lower()
    for word, num in QUANTITY_MAP.items():
        if word in text_lower:
            return num

    return 3  # Mặc định