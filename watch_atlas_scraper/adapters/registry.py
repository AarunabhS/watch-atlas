from .breitling import ADAPTER as breitling
from .patek import ADAPTER as patek
from .jaeger_lecoultre import ADAPTER as jaeger_lecoultre
from .omega import ADAPTER as omega
from .tudor import ADAPTER as tudor
from .iwc import ADAPTER as iwc

ADAPTERS = {a.key: a for a in (breitling, patek, jaeger_lecoultre, omega, tudor, iwc)}
