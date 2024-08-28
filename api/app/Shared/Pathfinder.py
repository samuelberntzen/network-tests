from typing import Union, List
from app.Shared.Graph import Graph, Edge, Node
from typing import Union

from matplotlib.collections import LineCollection

import matplotlib.pyplot as plt
import heapq


class Pathfinder:
    def __init__(self, graph: Graph, priority: Union[dict, None] = None):
        self.graph = graph
        self.priority = priority
        self.__quote = "Who's ready to fly on a zipline? ..I am!"

    def shortest_path_dijkstra(self, start_node: Node, end_node: Node):
        # Initialize shortest distances dict with infinite distances for all nodes
        shortest_distances = {
            node: float("infinity") for node in self.graph.nodes.values()
        }
        shortest_distances[start_node] = 0

        # Keep track of the previous node (as Node object) for path reconstruction
        previous_nodes = {node: None for node in self.graph.nodes.values()}

        # Using a priority queue to determine the next node to explore
        priority_queue = [(0, start_node)]

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            # If the popped node's distance is not updated in the priority queue, skip
            if current_distance > shortest_distances[current_node]:
                continue

            for edge in current_node.neighbors:
                neighbor_node = self.graph.nodes[edge.v]
                # Calculate the distance via current_node
                distance = current_distance + edge.distance

                # If this path is shorter than previously known path to the neighbor, update
                if distance < shortest_distances[neighbor_node]:
                    shortest_distances[neighbor_node] = distance
                    previous_nodes[neighbor_node] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor_node))

        # Reconstruct the shortest path
        path = []
        while end_node:
            if previous_nodes[end_node]:
                # Find edge from previous_node to end_node
                previous = previous_nodes[end_node]
                # Use list comprehension to get the edge connecting previous_node and end_node
                edge = next((e for e in previous.neighbors if e.v == end_node.id), None)
                if edge:
                    path.insert(0, edge)
            end_node = previous_nodes[end_node]

        return path

    def plot_route(
        self,
        route,
        edge_color="gray",
        overlay_color="red",
        bg_color="black",
        filepath=None,
        show=False,
    ):
        fig, ax = self.graph.plot_graph(edge_color=edge_color, bg_color=bg_color)

        overlay_segments = [list(line.geometry.coords) for line in route]
        overlay_collection = LineCollection(
            overlay_segments, linewidths=0.4, colors=overlay_color, linestyle="solid"
        )
        ax.add_collection(overlay_collection)
        ax.autoscale()

        # Save the figure if filepath is provided
        if filepath:
            fig.savefig(filepath, dpi=300)  # You can adjust the dpi if needed

        # Display the figure if show is True
        if show:
            plt.show()
