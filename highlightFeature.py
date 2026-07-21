# -*- coding: utf-8 -*-


from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import (QgsCoordinateReferenceSystem, QgsWkbTypes, QgsCoordinateTransform,
                       QgsProject, QgsPointXY, Qgis, QgsPoint, QgsRectangle)
from qgis.gui import QgsRubberBand
from math import isnan

# QGIS 4 / Qt6 geometry type compatibility
try:
    _LineGeometry = Qgis.GeometryType.Line
    _PointGeometry = Qgis.GeometryType.Point
except AttributeError:
    _LineGeometry = QgsWkbTypes.LineGeometry
    _PointGeometry = QgsWkbTypes.PointGeometry

# QgsRubberBand icon type compatibility
try:
    _ICON_FULL_BOX     = QgsRubberBand.IconType.ICON_FULL_BOX
    _ICON_FULL_DIAMOND = QgsRubberBand.IconType.ICON_FULL_DIAMOND
except AttributeError:
    _ICON_FULL_BOX     = QgsRubberBand.ICON_FULL_BOX
    _ICON_FULL_DIAMOND = QgsRubberBand.ICON_FULL_DIAMOND


class HighlightFeature:

    def __init__(self, canvas, p_pointsonly, p_closecontour, p_projectcrs):
        self.canvas = canvas

        self.lineHighlight  = list()
        self.nodesHighlight = list()
        self.projectCrs     = p_projectcrs
        self.featureCrs     = -1
        self.pointsOnly     = p_pointsonly
        self.closeContour   = p_closecontour

    def createHighlight(self, coords, currentPart, p_featurecrs, currentVertex=0):
        """
        coords - list of tuples with coordinates coords matrix type from addFeatureGUI
        """
        needTransformation = False
        self.featureCrs = p_featurecrs
        if self.featureCrs != self.projectCrs:
            needTransformation = True
            transformation = QgsCoordinateTransform(self.featureCrs, self.projectCrs,
                                                    QgsProject.instance())

        if not self.pointsOnly:
            for partNum in range(len(coords)):
                self.lineHighlight.append(QgsRubberBand(self.canvas, _LineGeometry))
                coordsPart = coords[partNum][1]
                for i in range(len(coordsPart)):
                    if self.isFloat(coordsPart[i][0]) and self.isFloat(coordsPart[i][1]):
                        if needTransformation:
                            src_point = QgsPoint(float(coordsPart[i][0]), float(coordsPart[i][1]))
                            src_point.transform(transformation)
                            point = QgsPointXY(src_point)
                        else:
                            point = QgsPointXY(float(coordsPart[i][0]), float(coordsPart[i][1]))
                        self.lineHighlight[partNum].addPoint(point, True, 0)

                if self.closeContour and self.lineHighlight[partNum].numberOfVertices() > 2:
                    self.lineHighlight[partNum].closePoints(True)

                self.lineHighlight[partNum].setColor(Qt.red)
                self.lineHighlight[partNum].setWidth(2)

        j = 0
        coordsPart = coords[currentPart][1]
        for i in range(len(coordsPart)):
            if self.isFloat(coordsPart[i][0]) and self.isFloat(coordsPart[i][1]):
                self.nodesHighlight.append(QgsRubberBand(self.canvas, _PointGeometry))
                if needTransformation:
                    src_point = QgsPoint(float(coordsPart[i][0]), float(coordsPart[i][1]))
                    src_point.transform(transformation)
                    point = QgsPointXY(src_point)
                else:
                    point = QgsPointXY(float(coordsPart[i][0]), float(coordsPart[i][1]))
                self.nodesHighlight[j].addPoint(point, True, 0)

                if i == currentVertex:
                    self.nodesHighlight[j].setIcon(_ICON_FULL_BOX)
                    self.nodesHighlight[j].setColor(Qt.darkRed)
                else:
                    self.nodesHighlight[j].setIcon(_ICON_FULL_DIAMOND)
                    self.nodesHighlight[j].setColor(Qt.darkBlue)
                self.nodesHighlight[j].setIconSize(10)
                j += 1

        if len(self.nodesHighlight) > 0:
            x_list = [self.nodesHighlight[i].getPoint(0).x() for i in range(len(self.nodesHighlight))]
            y_list = [self.nodesHighlight[i].getPoint(0).y() for i in range(len(self.nodesHighlight))]

            featureRect = QgsRectangle(min(x_list), min(y_list), max(x_list), max(y_list))
            mapRect = self.canvas.extent()
            if not mapRect.contains(featureRect):
                centerPoint = QgsPointXY(float((min(x_list) + max(x_list)) / 2),
                                         float((min(y_list) + max(y_list)) / 2))
                self.canvas.setCenter(centerPoint)

                mapRect = self.canvas.extent()
                if not mapRect.contains(featureRect):
                    self.canvas.setExtent(featureRect)

        self.canvas.refresh()

    def changeCurrentVertex(self, currentVertex=0):
        if self.nodesHighlight is not None:
            for i in range(len(self.nodesHighlight)):
                if i == currentVertex:
                    self.nodesHighlight[i].setIcon(_ICON_FULL_BOX)
                    self.nodesHighlight[i].setColor(Qt.darkRed)
                else:
                    self.nodesHighlight[i].setIcon(_ICON_FULL_DIAMOND)
                    self.nodesHighlight[i].setColor(Qt.darkBlue)

            self.canvas.refresh()

    def removeHighlight(self):
        if len(self.lineHighlight) > 0:
            for partNum in range(len(self.lineHighlight)):
                self.canvas.scene().removeItem(self.lineHighlight[partNum])
                self.lineHighlight[partNum].reset(_LineGeometry)
            self.lineHighlight.clear()

        for i in range(len(self.nodesHighlight)):
            self.canvas.scene().removeItem(self.nodesHighlight[i])
            self.nodesHighlight[i].reset(_PointGeometry)
        self.nodesHighlight.clear()

        self.canvas.refresh()

    @staticmethod
    def isFloat(value):
        """Qt6 uyumlu: QVariant kullanmadan Python native float kontrolü."""
        if value is None:
            return False
        s = str(value).strip()
        if s == '' or s == 'None':
            return False
        try:
            f = float(s)
            return not isnan(f)
        except (ValueError, TypeError):
            return False
