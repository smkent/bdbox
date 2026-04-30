from typing import Any

from tests.models.utils import build123d

assert build123d

from build123d import Box  # noqa: E402

from bdbox import Float, Int, Model  # noqa: E402
from tests.models.mono_model.misc.constants import Defaults  # noqa: E402


class FirstModel(Model):
    a: float = Defaults.A
    b: int = Defaults.B
    c = Int(Defaults.C, min=1, max=10)
    d = Float(Defaults.D, min=1.0, max=10.0)

    def build(self) -> Any:
        return Box(self.a, self.b, self.c)


class SecondModel(Model):
    a: float = Defaults.A
    b: int = Defaults.B
    c = Int(Defaults.C, min=1, max=10)
    d = Float(Defaults.D, min=1.0, max=10.0)

    def build(self) -> Any:
        return Box(self.b, self.c, self.d)
