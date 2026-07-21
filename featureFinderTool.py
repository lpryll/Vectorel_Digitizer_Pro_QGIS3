# -*- coding: utf-8 -*-


from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QCursor, QPixmap
from qgis.core import QgsWkbTypes, QgsGeometry, QgsProject, QgsCoordinateTransform, QgsPointXY, QgsRectangle, Qgis
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand


# Feature Finder Tool class
class FeatureFinderTool(QgsMapToolEmitPoint):
    Clicked = pyqtSignal("QgsGeometry")

    def __init__(self, canvas):
        self.canvas = canvas
        self.feature_id = None
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False

        QgsMapToolEmitPoint.__init__(self, canvas)

        # our own fancy cursor
        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                         "      c None",
                                         ".     c #FF0000",
                                         "+     c #FFFFFF",
                                         "                ",
                                         "       +.+      ",
                                         "      ++.++     ",
                                         "     +.....+    ",
                                         "    +.     .+   ",
                                         "   +.   .   .+  ",
                                         "  +.    .    .+ ",
                                         " ++.    .    .++",
                                         " ... ...+... ...",
                                         " ++.    .    .++",
                                         "  +.    .    .+ ",
                                         "   +.   .   .+  ",
                                         "   ++.     .+   ",
                                         "    ++.....+    ",
                                         "      ++.++     ",
                                         "       +.+      "]))

        try:
            _poly_geom = Qgis.GeometryType.Polygon
        except AttributeError:
            _poly_geom = QgsWkbTypes.PolygonGeometry
        self.rubberBand = QgsRubberBand(self.canvas, _poly_geom)
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setFillColor(Qt.transparent)
        self.rubberBand.setWidth(1)

    def canvasPressEvent(self, e):
        self.startPoint = self.toMapCoordinates(e.pos())
        self.endPoint = self.startPoint
        self.isEmittingPoint = True
        self.showRect(self.startPoint, self.endPoint)

    def canvasReleaseEvent(self, event):
        self.isEmittingPoint = False
        rect = self.rectangle()
        if rect is not None:
            rect_geom = QgsGeometry.fromRect(rect)

            crs_canvas = self.canvas.mapSettings().destinationCrs()
            layer_crs = self.canvas.currentLayer().crs()
            xformer = QgsCoordinateTransform(crs_canvas, layer_crs, QgsProject.instance())

            rect_geom.transform(xformer, QgsCoordinateTransform.ForwardTransform)
            self.canvas.scene().removeItem(self.rubberBand)

            self.Clicked.emit(rect_geom)

    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return

        self.endPoint = self.toMapCoordinates(e.pos())
        self.showRect(self.startPoint, self.endPoint)

    def showRect(self, startPoint, endPoint):
        try:
            _poly_geom2 = Qgis.GeometryType.Polygon
        except AttributeError:
            _poly_geom2 = QgsWkbTypes.PolygonGeometry
        self.rubberBand.reset(_poly_geom2)
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return

        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())

        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, True)  # true to update canvas
        self.rubberBand.show()

    def rectangle(self):
        if self.startPoint is None or self.endPoint is None:
            return None
        elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
            return None

        return QgsRectangle(self.startPoint, self.endPoint)

    def activate(self):
        self.canvas.setCursor(self.cursor)

    def deactivate(self):
        super(FeatureFinderTool, self).deactivate()
        self.deactivated.emit()
