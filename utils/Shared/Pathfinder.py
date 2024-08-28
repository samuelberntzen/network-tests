from typing import Union, List
from utils.Shared.Graph import Graph

from matplotlib.collections import LineCollection
import heapq
import matplotlib.pyplot as plt
from sqlalchemy import text, or_
from sqlalchemy.sql.functions import func

from utils.Shared import Graph
import logging
from shapely import wkb

logger = logging.getLogger()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Pathfinder:
    def __init__(self, graph: Graph, priority: Union[dict, None] = None):
        self.graph = graph
        self.priority = priority
        self.__quote = "Who's ready to fly on a zipline? ..I am!"

    def shortest_path_dijkstra(self, start_node_id, end_node_id):
        # Initialize shortest paths to a high value (infinity) and set start_node's distance to 0
        shortest_paths = {node: float("infinity") for node in self.graph.adjacency_list}
        shortest_paths[start_node_id] = 0

        # This dictionary will store the previous node for each node, useful for retracing our path
        previous_nodes = {node: None for node in self.graph.adjacency_list}

        # Priority queue to keep track of nodes to be evaluated
        priority_queue = [(0, start_node_id)]

        # Set to keep track of visited nodes
        visited = set()

        while priority_queue:
            # Get node with lowest distance from priority_queue
            current_distance, current_node = heapq.heappop(priority_queue)

            # If the current_node is the end_node_id, we've found our path
            if current_node == end_node_id:
                path = []
                while current_node:
                    path.append(current_node)
                    current_node = previous_nodes[current_node]
                return path[::-1], shortest_paths[end_node_id]  # Return reversed path

            # If we've already visited this node, skip
            if current_node in visited:
                continue

            visited.add(current_node)

            for neighbor, edge_weight in self.graph.adjacency_list[current_node]:
                distance = current_distance + edge_weight

                # If new path to neighbor is shorter, update the shortest distance and previous node for the neighbor
                if distance < shortest_paths[neighbor]:
                    shortest_paths[neighbor] = distance
                    previous_nodes[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))

        return None  # If no path found, return None

    def shortest_path_dijkstra_sql(
        self, start_node_id: str, end_node_id: str
    ) -> List[int]:
        query = f"""
            WITH RECURSIVE dijkstra AS (
                SELECT 
                    u AS start_node, 
                    v AS end_node, 
                    ARRAY[u] as path, 
                    length AS weight 
                FROM 
                    "{self.graph.edges.name}"
                WHERE 
                    u = {start_node_id}

                UNION ALL

                SELECT 
                    e.u AS start_node,
                    e.v AS end_node,
                    d.path || e.v,
                    d.weight + e.length
                FROM 
                    "{self.graph.edges.name}" e
                INNER JOIN dijkstra d ON e.u = d.end_node 
                WHERE 
                    NOT e.v = ANY(d.path)
            )
            SELECT 
                start_node, 
                end_node, 
                path, 
                weight 
            FROM 
                dijkstra
            WHERE 
                end_node = {end_node_id}
            ORDER BY 
                weight LIMIT 1;

        """

        result = self.graph.session.execute(text(query)).mappings().all()

        return result

    def get_route_geometries(self, route):
        route_set = set(route)

        # Query for edge geometries where either 'u' or 'v' is in the route
        geoms_query = self.graph.session.query(
            func.ST_AsGeoJSON(self.graph.edges.c.geom)
        ).filter(
            or_(
                self.graph.edges.c.u.in_(route_set), self.graph.edges.c.v.in_(route_set)
            )
        )

        geoms = [row[0] for row in geoms_query.all()]
        return geoms

    # def plot_route(
    #     self,
    #     route,
    #     edge_color="gray",
    #     overlay_color="red",
    #     bg_color="black",
    #     filepath=None,
    #     show=False,
    # ):
    #     fig, ax = self.graph.plot_graph(edge_color=edge_color, bg_color=bg_color)

    #     overlay_segments = [list(line.geometry.coords) for line in route]
    #     overlay_collection = LineCollection(
    #         overlay_segments, linewidths=0.4, colors=overlay_color, linestyle="solid"
    #     )
    #     ax.add_collection(overlay_collection)
    #     ax.autoscale()

    #     # Save the figure if filepath is provided
    #     if filepath:
    #         fig.savefig(filepath, dpi=300)  # You can adjust the dpi if needed

    #     # Display the figure if show is True
    #     if show:
    #         plt.show()
