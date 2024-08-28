import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import overpy
import time
import os
import numpy as np
from sqlalchemy import create_engine, text
from geoalchemy2 import Geometry, WKTElement
import geopandas as gpd
import logging

logger = logging.getLogger()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def enrich_graph_with_osm_tags(G, categories, batch_size=1000):
    # Enrich data in G
    api = overpy.Overpass()

    n_edges = len(G.edges)

    edges = [(u, v, key, data) for u, v, key, data in G.edges(keys=True, data=True)]

    counter = 0
    for i in range(0, len(edges), batch_size):
        batch = edges[i : i + batch_size]

        # Construct a query for all edges in the batch
        query = "("
        for u, v, key, data in batch:
            osmid = data["osmid"]
            query += f"way({osmid});"
        query += "); out body;"

        # Query the Overpass API
        result = api.query(query)

        # Process the response
        for way in result.ways:
            for u, v, key, data in batch:
                if str(data["osmid"]) == str(way.id):
                    for tag in way.tags:
                        # Add each tag as a separate data point in the edge data
                        G[u][v][key][tag] = way.tags[tag]

                    # Categorize the type of road, for bicycles
                    data["bike_category"] = categorize_edge(data, categories)
                    # print(data["bike_category"])

        counter += batch_size

        print(counter / n_edges, end="\r")
        time.sleep(2)

    return G


def assign_categories(gdf, categories, category_type):
    def check_criteria(row):
        for category in categories:
            criteria = category["criteria"]
            if criteria is None:
                continue
            if all(row.get(key) == value for key, value in criteria.items()):
                return category[category_type]

        return "Road without bike lane"

    gdf[category_type] = gdf.apply(check_criteria, axis=1)
    return gdf


def set_category_score(gdf, categories, category_type):
    scores = {
        category[category_type]: category[f"{category_type}Score"]
        for category in categories
    }

    gdf[f"{category_type}Score"] = gdf[category_type].map(scores)

    return gdf


def categorize_edge(data, categories):
    # Iterate each category in the dictionary
    for category in categories:
        # Check criteria
        criteria = category["criteria"]
        if all(data.get(key) == value for key, value in criteria.items()):
            bike_category = category["category"]
            return bike_category

    else:
        return "Road with no bike lane"


def make_gdf_directed(edges: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Create a list to hold the modified edges
    new_edges_list = []

    # Starting ID for new edges
    counter = 1

    # Iterate through each edge
    for _, row in edges.iterrows():
        # Add osmid as original ID
        row["osmid"] = row["id"]

        # If the edge is one-way in the reverse order
        if row["oneway"] == "-1":
            row["u"], row["v"] = row["v"], row["u"]  # swap u and v
            row["id"] = str(counter) + "_r"
            counter += 1
            new_edges_list.append(row)

        # If the edge is bi-directional
        elif pd.isna(row["oneway"]) or row["oneway"] != "yes":
            # Append the original edge with new ID
            row["id"] = counter
            new_edges_list.append(row)

            # Create a duplicate edge with reversed u and v and an updated ID
            new_row = row.copy()
            new_row["id"] = str(counter) + "_r"
            new_row["u"], new_row["v"] = row["v"], row["u"]
            new_edges_list.append(new_row)

            counter += 1

        # If the edge is one-way in the forward order
        else:
            row["id"] = counter
            counter += 1
            new_edges_list.append(row)

    # Convert the list of modified edges back to a GeoDataFrame
    new_edges = gpd.GeoDataFrame(new_edges_list)

    return new_edges


def plot_bike_roads_with_category(
    gdf, place, category, category_score, cmap_name="RdYlGn", bg_color="black"
):
    fig, ax = plt.subplots(figsize=(20, 20))
    ax.set_facecolor(bg_color)
    fig.patch.set_facecolor(bg_color)  # Set outer color

    # Create a color map
    cmap = plt.get_cmap(cmap_name)

    # Handle NaN values in category_score
    gdf[category_score] = gdf[category_score].fillna("missing")

    # Create a normalized color map based on the unique scores in your data
    scores = list(gdf[category_score].unique())
    colors = [cmap(i) for i in np.linspace(0, 1, len(scores))]
    color_map = dict(zip(scores, colors))

    # Create a new column in your GeoDataFrame with the corresponding color for each score
    gdf["color"] = gdf[category_score].map(color_map)

    # Plot the GeoDataFrame using the color column
    for color, data in gdf.groupby("color"):
        data.plot(color=color, linewidth=0.8, ax=ax, edgecolor="0.8")

    # Create a custom legend
    patches = [
        mpatches.Patch(color=color_map[score], label=cat)
        for score, cat in zip(gdf[category_score].unique(), gdf[category].unique())
    ][::-1]
    ax.legend(handles=patches, loc="upper left")

    # Remove X and Y axis labels
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.autoscale()

    # Save the figure
    figpath = os.path.join("figures", f"{place}_by_{category}.png")
    plt.savefig(figpath, dpi=200, bbox_inches="tight")

    plt.close()


def write_geodf_to_postgis(gdf, table_name, engine, index: list = None):
    """
    Write a GeoDataFrame to a PostGIS table.
    """

    # Convert geometry column to WKTElement
    gdf["geom"] = gdf["geometry"].apply(lambda x: WKTElement(x.wkt, srid=4326))

    # Drop original geometry column
    gdf = gdf.drop("geometry", axis=1)

    # Write DataFrame to PostGIS table
    gdf.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False,
        dtype={"geom": Geometry("GEOMETRY", srid=4326)},
    )

    if index:
        with engine.connect() as connection:
            for i in index:
                query = f"""
                CREATE INDEX idx_{i} ON "{table_name}"({i});
                """

                logging.info(f"Creating index on column {i}")
                connection.execute(text(query))

        connection.close()
