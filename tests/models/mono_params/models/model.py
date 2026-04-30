from tests.models.mono_params.misc.constants import Defaults
from tests.models.utils import build123d

assert build123d

from build123d import Box  # noqa: E402

from bdbox import Float, Int, Params, show  # noqa: E402


class P(Params):
    a: float = Defaults.A
    b: int = Defaults.B
    c = Int(Defaults.C, min=1, max=10)
    d = Float(Defaults.D, min=1.0, max=10.0)


b1 = Box(P.a, P.b, P.c)
b2 = Box(P.b, P.c, P.d)
print("b1", b1)  # noqa: T201
print("b2", b2)  # noqa: T201
show(b1, b2)
