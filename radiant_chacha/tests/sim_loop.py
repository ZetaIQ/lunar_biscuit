import argparse
import asyncio
from pprint import pformat

import numpy as np

from radiant_chacha.core.factory import NeighborFactory
from radiant_chacha.interfaces.block import Block
from radiant_chacha.interfaces.point import Point
from radiant_chacha.interfaces.sphere import Sphere
from radiant_chacha.utils.log_handler import get_logger

logger = get_logger(__name__, source_file=__file__)


async def simulation(t: int) -> None:
    logger.info("Starting simulation...")
    nodes = []
    try:
        factory = NeighborFactory()

        str_block = factory.create(
            cls=Block, pos=np.random.rand(3) * 10, data="block data"
        )
        str_point = factory.create(
            cls=Point, pos=np.random.rand(3) * 10, data="point data"
        )
        str_sphere = factory.create(
            cls=Sphere, pos=np.random.rand(3) * 10, data="sphere data"
        )
        array_block = factory.create(
            cls=Block, pos=np.random.rand(3) * 10, data=np.random.rand(5)
        )
        array_point = factory.create(
            cls=Point, pos=np.random.rand(3) * 10, data=np.random.rand(5)
        )
        array_sphere = factory.create(
            cls=Sphere, pos=np.random.rand(3) * 10, data=np.random.rand(5)
        )
        matrix_block = factory.create(
            cls=Block,
            pos=np.random.rand(3) * 10,
            data=np.array([[1.0, 2.0], [3.0, 4.0]]),
        )
        matrix_point = factory.create(
            cls=Point, pos=np.random.rand(3) * 10, data=np.array([[7, 3], [3, 50]])
        )
        matrix_sphere = factory.create(
            cls=Sphere, pos=np.random.rand(3) * 10, data=np.array([[0, -1], [1, 0]])
        )
        bytes_block = factory.create(
            cls=Block, pos=np.random.rand(3) * 10, data=b"block data as bytes"
        )
        bytes_point = factory.create(
            cls=Point, pos=np.random.rand(3) * 10, data=b"point data as bytes"
        )
        bytes_sphere = factory.create(
            cls=Sphere, pos=np.random.rand(3) * 10, data=b"sphere data as bytes"
        )
        dict_block = factory.create(
            cls=Block,
            pos=np.random.rand(3) * 10,
            data={"block data": 123, "some_key": [1, 2, 3]},
        )
        dict_point = factory.create(
            cls=Point,
            pos=np.random.rand(3) * 10,
            data={"point data": 456, "other_key": {"a": 1, "b": 2}},
        )
        dict_sphere = factory.create(
            cls=Sphere,
            pos=np.random.rand(3) * 10,
            data={"sphere data": 789, "some_key": {"x": 10, "y": 20}},
        )

        nodes = [
            str_block,
            str_point,
            str_sphere,
            array_block,
            array_point,
            array_sphere,
            matrix_block,
            matrix_point,
            matrix_sphere,
            bytes_block,
            bytes_point,
            bytes_sphere,
            dict_block,
            dict_point,
            dict_sphere,
        ]

        # For demo, manually link neighbors
        # add_neighbor(obj=block, other=point)
        # add_neighbor(obj=block, other=sphere)
        # add_neighbor(obj=point, other=block)

        tasks = [asyncio.create_task(node.run(print_stats=True)) for node in nodes]

        await asyncio.sleep(t)
        for task in tasks:
            task.cancel()
    finally:
        logger.info("\n" * 3)
        logger.info("Simulation ended.")
        logger.info("Final States:")
        for i, node in enumerate(iterable=nodes, start=1):
            logger.info(
                f"Node {i} ({type(node)}): {node.addr} Pos={node.pos} Gravity={float(node.gravity):.3f}"
            )
            logger.info("-" * 40)
            logger.info("Set logging to debug to see full history details.")
            logger.debug(
                f"History of Node {i} ({type(node)}):\n{pformat(node.history, width=80, indent=2)}"
            )
            logger.info("-" * 40)
            logger.info(
                f"Total attempts to connect beyond degree limit for Node {i} ({type(node)}): {node.attempts}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple simulation loop.")
    parser.add_argument(
        "-t", "--time", type=int, default=10, help="Simulation time in seconds"
    )
    args = parser.parse_args()
    asyncio.run(simulation(t=args.time))
