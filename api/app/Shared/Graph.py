import json
from math import atan2, cos, radians, sin, sqrt
from typing import List, Tuple
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from shapely.geometry import LineString, Point


class Node:
    def __init__(self, data):
        self.id = str(data["properties"]["id"])
        self.osmid = str(data["properties"]["id"])
        self.lon = data["properties"]["lon"]
        self.lat = data["properties"]["lat"]
        self.geometry = Point(
            self.lon,
            self.lat,
        )
        self.neighbors: List[Edge] = []

    def __repr__(self):
        return f"Node(id={self.id}, lon={self.lon}, lat={self.lat})"

    def __str__(self):
        return f"Node {self.id}"

    def __eq__(self, other):
        return isinstance(other, Node) and self.id == other.id

    def __lt__(self, other):
        if isinstance(other, Node):
            return self.id < other.id
        raise ValueError("Comparison with non-Node object")

    def __hash__(self):
        return hash(self.id)


class Edge:
    def __init__(self, id, data):
        self.id = str(id)
        self.osmid = str(data["properties"]["id"])
        self.u = str(data["properties"]["u"])
        self.v = str(data["properties"]["v"])
        self.distance = data["properties"]["length"]
        self.geometry = LineString(data["geometry"]["coordinates"])
        self.oneway = data["properties"]["oneway"]
        self.onewaybicycle = data["properties"]["oneway:bicycle"]
        self.category = data["properties"]["category"]
        self.parentCategory = data["properties"]["parent"]

    def __repr__(self):
        return f"Edge(id={self.id}, osmid={self.osmid}, u={self.u}, v={self.v}, distance={self.distance})"

    def __str__(self):
        return f"Edge[id: {self.id}, osmid: {self.osmid}, from: {self.u} to: {self.v}, distance: {self.distance}m]"

    def __eq__(self, other):
        if isinstance(other, Edge):
            return self.id == other.id
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, Edge):
            return self.id < other.id
        raise ValueError("Comparison with non-Edge object")

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other):
        if isinstance(other, Edge):
            return self.id > other.id
        raise ValueError("Comparison with non-Edge object")

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

    def __hash__(self):
        return hash(self.id)


class Graph:
    def __init__(self, nodes_data=None, edges_data=None):
        self.nodes = {}
        self.edges = {}

        # Populate on instantiation if data is provided
        if nodes_data and edges_data:
            self.populate(nodes_data, edges_data)

    @classmethod
    def from_json_file(cls, filename: str):
        """Instantiate a Graph object from a JSON file."""
        with open(filename, "r") as f:
            data = json.load(f)

        nodes_data = data.get("nodes", [])
        edges_data = data.get("edges", [])

        return cls(nodes_data, edges_data)

    def add_node(self, data):
        node = Node(data)
        self.nodes[node.id] = node

    def add_edge(self, id, data):
        edge = Edge(id, data)
        self.edges[str(edge.id)] = edge
        self.nodes[edge.u].neighbors.append(edge)

        # Check if we should create a reverse edge. Conditions for creating a reverse edge:
        # 1. The oneway attribute is not set or is set to "-1"
        # 2. The onewaybicycle attribute is set to "no"
        create_reverse = False
        if edge.oneway == None or edge.oneway == "-1":
            create_reverse = True
        elif edge.oneway == "yes" and edge.onewaybicycle == "no":
            create_reverse = True

        if create_reverse:
            id = f"{id}_r"
            reverse_data = data.copy()
            reverse_data["properties"]["u"], reverse_data["properties"]["v"] = (
                edge.v,
                edge.u,
            )
            reverse_edge = Edge(id, reverse_data)
            self.edges[reverse_edge.id] = reverse_edge
            # Add the reverse edge to the start node's neighbors
            self.nodes[reverse_edge.u].neighbors.append(reverse_edge)

    def __repr__(self):
        return f"Graph(nodes={len(self.nodes)}, edges={len(self.edges)})"

    def populate(self, nodes_data, edges_data):
        # First, populate nodes
        for node_data in nodes_data:
            self.add_node(node_data)

        # Then, populate edges
        id_counter = 0
        for edge_data in edges_data:
            self.add_edge(id_counter, edge_data)
            id_counter += 1

    def dfs(self, start_node_id, visited=None):
        if visited is None:
            visited = set()

        visited.add(start_node_id)
        for edge in self.nodes[start_node_id].neighbors:
            if edge.v not in visited:
                self.dfs(edge.v, visited)
        return visited

    def is_connected(self):
        # Start DFS from the first node
        visited = self.dfs(list(self.nodes.keys())[0])

        # If the number of visited nodes is equal to the total nodes in the graph,
        # then the graph is connected.
        print(len(visited))
        return len(visited) == len(self.nodes)

    @staticmethod
    def haversine_distance(
        coord1: Tuple[float, float], coord2: Tuple[float, float]
    ) -> float:
        R = 6371  # Radius of the earth in km
        lat1, lon1 = radians(coord1[0]), radians(coord1[1])
        lat2, lon2 = radians(coord2[0]), radians(coord2[1])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def find_closest_node(self, lat: float, lon: float) -> Node:
        return min(
            self.nodes.values(),
            key=lambda node: self.haversine_distance((node.lat, node.lon), (lat, lon)),
        )

    def plot_graph(
        self, edge_color="gray", bg_color="black", filepath=None, show=False
    ):
        edge_linestrings = [edge.geometry for key, edge in self.edges.items()]

        # Extract segments from the LineStrings
        segments = [list(line.coords) for line in edge_linestrings]
        line_collection = LineCollection(
            segments, linewidths=0.2, colors=edge_color, linestyle="solid"
        )

        fig, ax = plt.subplots(figsize=(20, 20))

        ax.set_facecolor(bg_color)  # Set background color
        fig.patch.set_facecolor(bg_color)  # Set outer color

        ax.add_collection(line_collection)
        ax.autoscale()

        if filepath:
            plt.savefig(filepath, dpi=300)

        if show:
            plt.show()

        else:
            plt.close()

        return fig, ax  # Return the figure and axes objects

    def graph_to_dict(self) -> dict:
        """Convert the Graph object to a dictionary representation."""

        nodes_data = []
        for node_id, node in self.nodes.items():
            nodes_data.append(
                {"properties": {"id": node.id, "lon": node.lon, "lat": node.lat}}
            )

        edges_data = []
        for edge_id, edge in self.edges.items():
            edges_data.append(
                {
                    "properties": {
                        "id": edge.osmid,
                        "u": edge.u,
                        "v": edge.v,
                        "length": edge.distance,
                        "oneway": edge.oneway,
                        "oneway:bicycle": edge.onewaybicycle,
                        "category": edge.category,
                        "parent": edge.parentCategory,
                    },
                    "geometry": {"coordinates": list(edge.geometry.coords)},
                }
            )

        return {"nodes": nodes_data, "edges": edges_data}

    def export_graph_to_json(self, filename: str):
        """Export the Graph object to a JSON file."""

        graph_data = self.graph_to_dict()
        with open(filename, "w") as f:
            json.dump(graph_data, f, indent=4)
