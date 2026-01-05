class DemoApp:
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self) -> None:
        print(f"running {self.name}")


def create_app() -> DemoApp:
    return DemoApp("demo")