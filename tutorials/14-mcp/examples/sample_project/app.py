from parser import parse_items


def main() -> None:
    data = "apple, banana, cherry"
    items = parse_items(data)
    print(items)


if __name__ == "__main__":
    # TODO: add CLI argument parsing
    main()
