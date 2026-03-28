def parse_items(raw: str) -> list[str]:
    # FIXME: handle quoted values with commas correctly
    return [item.strip() for item in raw.split(",") if item.strip()]
