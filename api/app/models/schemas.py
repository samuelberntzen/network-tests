from pydantic import BaseModel
from typing import List, Literal


class Node(BaseModel):
    nodeId: str


class Edge(BaseModel):
    edgeId: str


class RouteData(BaseModel):
    meters: int
    roadType: str


class DijkstraResponse(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    routeData: RouteData
