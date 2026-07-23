def hello_world(name: str = "World") -> str:
    """Hàm Hello World đơn giản."""
    message = f"Hello, {name}!"
    print(message)
    return message


if __name__ == "__main__":
    hello_world()
