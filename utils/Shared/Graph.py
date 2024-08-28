from typing import List
from shapely.geometry import LineString, Point
from sqlalchemy import create_engine, func, select, Table, MetaData
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import functions as geofunc
import logging

logger = logging.getLogger()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Node:
    def __init__(self, id, osmid, lon, lat, geometry):
        self.id = str(id)
        self.osmid = str(osmid)
        self.lon = str(lon)
        self.lat = str(lat)
        self.geometry = Point(
            self.lon,
            self.lat,
        )
        self.neighbors: List[Edge] = []


class Edge:
    def __init__(
        self,
        id,
        osmid,
        u,
        v,
        distance,
        geometry,
        oneway,
        onewaybicycle,
        category,
        parentCategory,
    ):
        self.id = str(id)
        self.osmid = str(osmid)
        self.u = str(u)
        self.v = str(v)
        self.distance = distance
        self.geometry = LineString(geometry)
        self.oneway = oneway
        self.onewaybicycle = onewaybicycle
        self.category = category
        self.parentCategory = parentCategory


class Graph:
    def __init__(self, db_url: str, tablename_nodes: str, tablename_edges: str):
        logging.info("Graph instantiated")
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.metadata = MetaData()
        self.nodes = Table(tablename_nodes, self.metadata, autoload_with=self.engine)
        self.edges = Table(tablename_edges, self.metadata, autoload_with=self.engine)
        self.adjacency_list = self.load_graph()

    def load_graph(self) -> None:
        """Loads edges into a adjacency list for faster pathfinding into the class

        Returns:
            None: None
        """
        all_nodes = set(
            row[0] for row in self.session.query(self.nodes.columns.id).all()
        )

        # Query edges
        results = self.session.query(
            self.edges.columns.u,
            self.edges.columns.v,
            self.edges.columns.length,
        ).all()

        # Construct the adjacency list
        adjacency_list = {
            node: [] for node in all_nodes
        }  # Initialize all nodes, even if they don't act as a start node
        for start_node, end_node, weight in results:
            adjacency_list[start_node].append((end_node, weight))

        return adjacency_list

    # This one is redundant. Bit leep
    def get_bounding_box_query(
        self, table_name: str, lon1: float, lat1: float, lon2: float, lat2: float
    ):
        bbox_query = f"""SELECT *
        FROM "{table_name}"
        WHERE geom && ST_MakeEnvelope({lon1 + 0.1}, {lat1 + 0.1}, {lon2 + 0.1}, {lat2 + 0.1} 4326);"""

        return bbox_query

    def closest_node(self, lat: float, lon: float) -> int:
        session = self.Session()

        # Construct a point representation of the input lat and lon
        point = f"POINT({lon} {lat})"

        query = (
            select(self.nodes.c.id)
            .order_by(
                func.ST_Distance(
                    geofunc.ST_GeomFromText(point, 4326),
                    self.nodes.c.geom,
                )
            )
            .limit(1)
        )

        result = session.execute(query).mappings().all()

        # session.close()

        if result:
            node_id = result[0]["id"]
            logging.info(f"Closest node to point {(lat, lon)} is {node_id}")
            return node_id
        else:
            logging.info("Result is None")
            return None

    def close_session(self):
        self.session.close()
        logging.info("Session closed.")
