"""Optional local GeoJSON boundary loading for spatial validation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

MAX_BOUNDARY_BYTES = 10 * 1024 * 1024
MAX_BOUNDARY_FEATURES = 5_000
MAX_BOUNDARY_POSITIONS = 500_000


class BoundaryError(ValueError):
    """The supplied GeoJSON is not a supported WGS84 polygon boundary."""


class BoundaryDependencyError(RuntimeError):
    """The optional GIS dependency is not installed."""


@dataclass(frozen=True, slots=True)
class SpatialBoundary:
    """A validated polygon boundary with WGS84 longitude/latitude semantics."""

    geometry: Any

    def covers(self, longitude: float, latitude: float) -> bool:
        from shapely.geometry import Point

        return bool(self.geometry.covers(Point(longitude, latitude)))


def _geometries(document: object) -> list[dict[str, object]]:
    if not isinstance(document, dict):
        raise BoundaryError("The GeoJSON document must be an object.")
    if "crs" in document:
        raise BoundaryError(
            "The GeoJSON must use RFC 7946 WGS84 longitude/latitude coordinates and omit a legacy CRS member."
        )

    kind = document.get("type")
    if kind == "FeatureCollection":
        features = document.get("features")
        if not isinstance(features, list) or not features:
            raise BoundaryError("The GeoJSON FeatureCollection must contain polygon features.")
        if len(features) > MAX_BOUNDARY_FEATURES:
            raise BoundaryError(f"The GeoJSON contains more than {MAX_BOUNDARY_FEATURES} features.")
        geometries = []
        for feature in features:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise BoundaryError("Every FeatureCollection item must be a GeoJSON Feature.")
            if "crs" in feature:
                raise BoundaryError(
                    "The GeoJSON must use RFC 7946 WGS84 longitude/latitude coordinates and omit a legacy CRS member."
                )
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict):
                raise BoundaryError("Every boundary feature must contain a polygon geometry.")
            geometries.append(geometry)
        return geometries
    if kind == "Feature":
        if "crs" in document:
            raise BoundaryError(
                "The GeoJSON must use RFC 7946 WGS84 longitude/latitude coordinates and omit a legacy CRS member."
            )
        geometry = document.get("geometry")
        if not isinstance(geometry, dict):
            raise BoundaryError("The GeoJSON Feature must contain a polygon geometry.")
        return [geometry]
    if kind in {"Polygon", "MultiPolygon"}:
        return [document]
    raise BoundaryError("Use a GeoJSON Polygon, MultiPolygon, Feature, or FeatureCollection.")


def _positions(coordinates: object):
    if not isinstance(coordinates, list):
        raise BoundaryError("Polygon coordinates must be GeoJSON coordinate arrays.")
    if len(coordinates) >= 2 and all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in coordinates[:2]
    ):
        yield coordinates
        return
    for child in coordinates:
        yield from _positions(child)


def load_geojson_boundary(data: bytes) -> SpatialBoundary:
    """Parse bounded RFC 7946 polygon GeoJSON without writing it to disk."""
    if len(data) > MAX_BOUNDARY_BYTES:
        raise BoundaryError(
            f"The GeoJSON boundary exceeds the {MAX_BOUNDARY_BYTES // (1024 * 1024)} MB safety limit."
        )
    try:
        document = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BoundaryError("The boundary file is not valid UTF-8 GeoJSON.") from None

    geometries = _geometries(document)
    position_count = 0
    for geometry in geometries:
        if "crs" in geometry:
            raise BoundaryError(
                "The GeoJSON must use RFC 7946 WGS84 longitude/latitude coordinates and omit a legacy CRS member."
            )
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise BoundaryError("Boundary features must be Polygon or MultiPolygon geometries.")
        coordinates = geometry.get("coordinates")
        found_position = False
        for position in _positions(coordinates):
            found_position = True
            position_count += 1
            if position_count > MAX_BOUNDARY_POSITIONS:
                raise BoundaryError(
                    f"The GeoJSON contains more than {MAX_BOUNDARY_POSITIONS} coordinate positions."
                )
            longitude, latitude = position[:2]
            if not math.isfinite(longitude) or not math.isfinite(latitude):
                raise BoundaryError("Boundary coordinates must be finite WGS84 longitude/latitude values.")
            if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                raise BoundaryError("Boundary coordinates must be within WGS84 longitude and latitude ranges.")
        if not found_position:
            raise BoundaryError("Polygon geometries must contain at least one coordinate position.")

    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union
    except ImportError as exc:
        raise BoundaryDependencyError from exc

    try:
        polygons = [shape(geometry) for geometry in geometries]
        if any(polygon.is_empty or not polygon.is_valid for polygon in polygons):
            raise BoundaryError("Every boundary polygon must be non-empty and geometrically valid.")
        merged = unary_union(polygons)
        if merged.is_empty or not merged.is_valid or merged.geom_type not in {"Polygon", "MultiPolygon"}:
            raise BoundaryError("The boundary polygons could not be combined into a valid polygon area.")
    except BoundaryError:
        raise
    except (TypeError, ValueError, IndexError) as exc:
        raise BoundaryError("The GeoJSON polygon coordinates are malformed.") from exc
    return SpatialBoundary(merged)

