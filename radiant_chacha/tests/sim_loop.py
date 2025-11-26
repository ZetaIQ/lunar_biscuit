import asyncio

import numpy as np
from radiant_chacha.core.factory import NeighborFactory
from radiant_chacha.interfaces.block import Block
from radiant_chacha.interfaces.point import Point
from radiant_chacha.interfaces.sphere import Sphere
from radiant_chacha.methods.movement import add_neighbor

# def run_simulation(nodes: list[NeighborBase], ticks: int = 10, dt: float = 1.0):
#     for tick_num in range(ticks):
#         print(f"Tick {tick_num + 1}")
#
#         for node in nodes:
#             node.tick(dt)
#
#         # Optionally print positions and gravity
#         for i, node in enumerate(iterable=nodes, start=1):
#             print(
#                 f"Node {i} ({type(node).__name__}): Pos={node.pos} Gravity={node.gravity:.3f}\n"
#                 f"{'-' * 40}\n"
#                 f"Node {i} ({type(node).__name__}): History={pprint(object=node.history, width=80, indent=2, compact=False, depth=2)}\n"
#                 f"{'-' * 40}\n"
#             )
#
#         time.sleep(1)  # Slow down so you can watch output (optional)
#
#
# if __name__ == "__main__":
#     factory = NeighborFactory()
#
#     # Create a few nodes
#     block = factory.create(Block, pos=np.random.rand(3) * 10, data="block data")
#     point = factory.create(Point, pos=np.random.rand(3) * 10, data="point data")
#     sphere = factory.create(Sphere, pos=np.random.rand(3) * 10, data="sphere data")
#
#     # For demo, manually link neighbors
#     block.add_neighbor(point)
#     block.add_neighbor(sphere)
#     point.add_neighbor(block)
#
#     nodes: list[NeighborBase] = [block, point, sphere]
#
#     run_simulation(nodes, ticks=3, dt=1.0)


async def simulation():
    factory = NeighborFactory()

    block = factory.create(cls=Block, pos=np.random.rand(3) * 10, data="block data")
    point = factory.create(cls=Point, pos=np.random.rand(3) * 10, data="point data")
    sphere = factory.create(cls=Sphere, pos=np.random.rand(3) * 10, data="sphere data")

    nodes = [block, point, sphere]

    # For demo, manually link neighbors
    add_neighbor(obj=block, other=point)
    add_neighbor(obj=block, other=sphere)
    add_neighbor(obj=point, other=block)

    tasks = [asyncio.create_task(node.run(print_stats=True)) for node in nodes]

    # Run for 20 seconds then cancel
    await asyncio.sleep(20)
    for task in tasks:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(simulation())
