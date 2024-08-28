import os

os.environ["USE_PYGEOS"] = "0"
os.environ["LD_LIBRARY_PATH"] = "/usr/lib/x86_64-linux-gnu/libstdc++.so.6"

import json
import logging
import os

import shapely
from pyrosm import OSM, get_data

from utils.functions import *
from utils.Shared import *


logger = logging.getLogger()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

logging.info("Starting populate_db.py")

# TODO: Remove when extending covered areas
place = "Oslo"
logging.info(f"Place is {place}")


sub_areas = [
    "Alna",
    "Bjerke",
    "Frogner",
    "Gamle Oslo",
    "Grorud",
    "Grünerløkka",
    "Nordre Aker",
    "Nordstrand",
    "Sagene",
    "St. Hanshaugen",
    "Stovner",
    "Søndre Nordstrand",
    "Ullern",
    "Vestre Aker",
    "Østensjø",
]

logging.info(f"Sub areas are {sub_areas}")


# Load self-defined lane types and criterias
with open("categories.json", "r") as f:
    categories = json.load(f)

# Attributes
attributes = list(
    set(
        [
            colname
            for category in categories
            for colname, value in category["criteria"].items()
        ]
    )
)

# Define the roads and their order for bicyclists
# TODO: Check if this can be added by user?
category_score = {
    "Designated cycleway, segregated": 1,
    "Bicycle and footpath": 2,
    "Road with bike lane": 3,
    "Road with one-directional cycleway": 4,
    "Footpath": 5,
    "Sidewalk": 6,
    "Pedestrian way": 7,
    "Road without bike lane": 8,
}

parent_category_score = {
    "Designated cyclepath": 1,
    "Footway": 2,
    "Road without bike lane": 3,
}


# Add road score to categories
for category, score in category_score.items():
    for road in categories:
        if road["category"] == category:
            road["categoryScore"] = score

# Add road score to parent categories
for parent, score in parent_category_score.items():
    for road in categories:
        if road["parent"] == parent:
            road["parentScore"] = score

# TODO: Reference cloud stored osm.pbf file here?

# Initialize the OSM object
logging.info("Instantiating OSM data and object...")
fp = os.path.join("data", "OpenStreetMap", f"{place}.osm.pbf")
osm = OSM(fp)
logging.info("OSM data and object instantiated.")


# Set bounding boxes from specified sub-areas
bounding_boxes = []
if sub_areas:
    for a in sub_areas:
        bounding_box = osm.get_boundaries(name=a)
        bounding_boxes.append(bounding_box["geometry"].values[0])

    # Merge bounding boxes into one
    bb = shapely.ops.unary_union(bounding_boxes)
else:
    bb = None

logging.info("Boundig box created.")


# Initiliaze with bounding box
osm = OSM(fp, bounding_box=bb)

nodes, edges = osm.get_network(
    network_type="all", nodes=True, extra_attributes=attributes
)

logging.info("Nodes, edges retrieved.")


roads_to_keep = [
    "cycleway",
    "footway",
    "secondary",
    "tertiary",
    "unclassified",
    "sidewalk",
    "pedestrian",
    "service",
    "residential",
]

# Filter out un-bikeable roads
edges = edges[edges["highway"].isin(roads_to_keep)]
edges = edges[edges["access"].isnull()]

logging.info(f"Number of edges before nodes filtering: {len(edges)}")
logging.info(f"Number of nodes before nodes filtering: {len(nodes)}\n")


# Filter out nodes that are not in edges
nodes_in_edges = [u for u in edges["u"]] + [v for v in edges["v"]]
nodes = nodes[nodes["id"].isin(nodes_in_edges)]

logging.info(f"Number of edges after edge filtering: {len(edges)}")
logging.info(f"Number of nodes after edge filtering: {len(nodes)}\n")

# Filter out edges not are not in nodes
nodes_in_nodes = [u for u in nodes["id"]]
edges = edges[edges["u"].isin(nodes_in_nodes)]
edges = edges[edges["v"].isin(nodes_in_nodes)]

logging.info(f"Number of edges after node filtering: {len(edges)}")
logging.info(f"Number of nodes after node filtering: {len(nodes)}\n")

edges = assign_categories(edges, categories, "category")
edges = assign_categories(edges, categories, "parent")

edges = set_category_score(edges, categories, "category")
edges = set_category_score(edges, categories, "parent")

# Trim GDFs
edge_cols_to_keep = [
    "id",
    "u",
    "v",
    "highway",
    "category",
    "categoryScore",
    "parent",
    "parentScore",
    "lit",
    "oneway",
    "oneway:bicycle",
    "segregated",
    "surface",
    "length",
    "geometry",
]

node_cols_to_keep = [
    "timestamp",
    "changeset",
    "version",
    "visible",
    "lon",
    "lat",
    "id",
    "geometry",
]

edges = edges[edge_cols_to_keep]
nodes = nodes[node_cols_to_keep]

# Save GeoDataFrames as GeoJSON
with open(f"data/processed/{place}_nodes.geojson", "w") as f:
    f.write(nodes.to_json(indent=4))

with open(f"data/processed/{place}_edges.geojson", "w") as f:
    f.write(edges.to_json(indent=4))

n_edges = len(edges)
n_nodes = len(nodes)

logging.info(f"Number of edges: {n_edges}")
logging.info(f"Number of nodes: {n_nodes}")


plot_bike_roads_with_category(
    edges,
    place,
    "parent",
    "parentScore",
    cmap_name="Oranges_r",
    bg_color="black",
)

m = edges[["id", "parent", "geometry"]].explore(column="parent")

outfp = f"figures/{place}_bike_roads_interactive.html"
m.save(outfp)
del m

# For computational purposes, convert the graph to directed by altering the edges geodataframe according to OpenStreetMap Oneway logic
logging.info(f"Number of edges before making directed: {len(edges)}")
edges = make_gdf_directed(edges)
logging.info(f"Number of edges after making directed: {len(edges)}\n")


# Create a connection to the PostgreSQL database
database_url = "postgresql://admin:admin@localhost:5432/bikenetwork"
engine = create_engine(database_url, echo=False)

# Create tables
logging.info("Loading nodes to PostGis...")
write_geodf_to_postgis(gdf=nodes, table_name="bikeableNodes", engine=engine)
logging.info("Nodes loaded to PostGis.")

logging.info("Loading edges to PostGis.")
write_geodf_to_postgis(
    gdf=edges, table_name="bikeableEdges", index=["u", "v"], engine=engine
)
logging.info("Edges loaded to PostGis.")

logging.info("Database populated.")
