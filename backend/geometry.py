from flask import abort
from sqlalchemy.sql import select, func, and_, cast
import sys
import pdb

from geonature.utils.env import DB

from sqlalchemy import func, cast

from geoalchemy2.shape import to_shape
from geoalchemy2.types import Geography, Geometry


from .model.zh_schema import TZH, CorZhArea
from .api_error import ZHApiError


def set_geom(geometry, id_zh=None):
    try:
        if not id_zh:
            id_zh = 0
        polygon = DB.session.query(
            func.ST_GeomFromGeoJSON(str(geometry))).one()[0]
        q_zh = DB.session.query(TZH).all()
        is_intersected = False
        for zh in q_zh:
            if zh.id_zh != id_zh:
                zh_geom = DB.session.query(func.ST_GeogFromWKB(
                    func.ST_AsEWKB(zh.geom))).scalar()
                polygon_geom = DB.session.query(
                    func.ST_GeogFromWKB(func.ST_AsEWKB(polygon))).scalar()
                if DB.session.query(func.ST_Intersects(polygon_geom, zh_geom)).scalar():
                    is_intersected = True
                if DB.session.query(func.ST_Contains(zh.geom, polygon)).scalar():
                    raise ZHApiError(
                        message="polygon_contained_in_zh",
                        details="the new zh contour is fully contained in an existing one",
                        status_code=400)
                intersect = DB.session.query(
                    func.ST_Difference(polygon_geom, zh_geom))
                polygon = DB.session.query(func.ST_GeomFromText(
                    to_shape(intersect.scalar()).to_wkt())).one()[0]
        return {
            'polygon': polygon,
            'is_intersected': is_intersected
        }
    except ZHApiError:
        raise
    except Exception as e:
        exc_type, value, tb = sys.exc_info()
        raise ZHApiError(
            message="set_geom_error", details=str(exc_type) + ': ' + str(e.with_traceback(tb)))


def set_area(geom):
    try:
        # unit : ha
        return round((DB.session.query(func.ST_Area(func.ST_GeomFromText(
            func.ST_AsText(geom['polygon'])), False)).scalar()) / 10000, 2)
    except ZHApiError:
        raise
    except Exception as e:
        exc_type, value, tb = sys.exc_info()
        raise ZHApiError(
            message="set_area_error", details=str(exc_type) + ': ' + str(e.with_traceback(tb)))
