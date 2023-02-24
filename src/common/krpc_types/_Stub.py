from typing import Type


class Stub:
    """Dummy class to allow cleanly importing kRPC type helper files at runtime."""

    def __getattr__(self, _):
        return Type[None]
