import numpy as np

from radiant_chacha.core.factory import NeighborFactory
from radiant_chacha.interfaces.block import Block
from radiant_chacha.interfaces.point import Point
from radiant_chacha.interfaces.sphere import Sphere
from radiant_chacha.utils.log_handler import get_logger

logger = get_logger(__name__, source_file=__file__)


def test_factory():
    factory = NeighborFactory()

    block = factory.create(Block, data="Block payload")
    point = factory.create(Point, data={"some": "data"})
    sphere = factory.create(Sphere, pos=np.array([10.0, 0.0, -5.0]))

    # Basic assertions
    assert block.id == 1
    assert point.id == 2
    assert sphere.id == 3

    assert isinstance(block.pos, np.ndarray)
    assert block.pos.shape == (3,)

    logger.info("Block: %s", block)
    logger.info("Point: %s", point)
    logger.info("Sphere: %s", sphere)

    # Check that addr is set and looks like a SHA256 hex string (64 chars)
    for obj in (block, point, sphere):
        assert obj.addr is not None
        assert len(obj.addr) == 64

    logger.info("All tests passed.")


if __name__ == "__main__":
    test_factory()
