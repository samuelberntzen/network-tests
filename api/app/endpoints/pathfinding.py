from fastapi import APIRouter
from typing import Optional
from app.models import schemas
from app.Shared.Pathfinder import Pathfinder
from app.Shared.Graph import Graph
import logging

# Instantiate Graph and Pathfinder
logging.info("Instantiating graph...")
graph = Graph.from_json_file("app/data/Graph/graph.json")
logging.info("Graph instantiated.")

pathfinder = Pathfinder(graph)
logging.info("Pathfinder instantiated.")

router = APIRouter(
    prefix="/pathfinding",
    tags=["route", "routing", "pathfinder"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def read_root() -> dict:
    """Test endpoint for checking connection

    Returns:
        dict: connection successfull
    """
    return {"connection": "successfull"}


@router.get("/route/dijkstra", response_model=schemas.DijkstraResponse)
async def shortest_path_dijkstra(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
):
    """_placeholder_

    Args:
        response_payload (schemas.DijkstraResponse): _description_
    """

    start_node = graph.find_closest_node(start_lat, start_lon)
    end_node = graph.find_closest_node(end_lat, end_lon)

    route = pathfinder.shortest_path_dijkstra(start_node, end_node)

    # Structure data
    nodes = [edge.u for edge in route] + [route[-1].v]
    edges = [edge.id for edge in route]
    meters = sum([edge.distance for edge in route])
    road_type = None

    data = {
        "nodes": nodes,
        "edges": edges,
        "routeData": {"meters": meters, "roadType": road_type},
    }

    return data
