from qgis.PyQt.QtCore import pyqtSignal, Qt, QTimer
from qgis.PyQt.QtGui import QCursor, QPixmap, QColor
from qgis.core import (QgsWkbTypes, QgsPointXY, Qgis,
                        QgsSnappingConfig, QgsPointLocator,
                        QgsProject, QgsTolerance, QgsRectangle,
                        QgsVectorLayer, QgsFeatureRequest)
import logging
from qgis.gui import QgsMapTool, QgsMapToolPan, QgsRubberBand


class DrawingTool(QgsMapTool):
    pointAdded = pyqtSignal(object)
    drawingFinished = pyqtSignal(object)
    canceled = pyqtSignal()
    mouseMoved = pyqtSignal(object)
    drawingEnded = pyqtSignal()

    def __init__(self, canvas, geomType='polygon'):
        super().__init__(canvas)
        self.canvas = canvas
        self.points = []
        self.isDrawing = False
        self._drawingEnded = False
        self._origSnapConfig = None
        self._panTool = None
        self.geomType = geomType

        try:
            _point_geom = Qgis.GeometryType.Point
            _line_geom = Qgis.GeometryType.Line
            _poly_geom = Qgis.GeometryType.Polygon
        except AttributeError:
            _point_geom = QgsWkbTypes.PointGeometry
            _line_geom = QgsWkbTypes.LineGeometry
            _poly_geom = QgsWkbTypes.PolygonGeometry

        self._point_geom = _point_geom
        self._line_geom = _line_geom
        self._poly_geom = _poly_geom

        if self.geomType == 'point':
            rb_geom = _point_geom
        elif self.geomType == 'line':
            rb_geom = _line_geom
        else:
            rb_geom = _poly_geom

        self.rubberBand = QgsRubberBand(self.canvas, rb_geom)
        if self.geomType == 'point':
            try:
                icon = QgsRubberBand.ICON_CIRCLE
            except AttributeError:
                icon = 2
            self.rubberBand.setIcon(icon)
            self.rubberBand.setIconSize(14)
            self.rubberBand.setColor(Qt.darkGreen)
        else:
            self.rubberBand.setColor(Qt.darkGreen)
            self.rubberBand.setFillColor(QColor(0, 180, 0, 40))
            self.rubberBand.setWidth(2)

        icon_type = (QgsRubberBand.ICON_FULL_DIAMOND
                     if hasattr(QgsRubberBand, 'ICON_FULL_DIAMOND')
                     else QgsRubberBand.ICON_FULL_DIAMOND)
        self.vertexBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.vertexBand.setIcon(icon_type)
        self.vertexBand.setColor(Qt.darkGreen)
        self.vertexBand.setIconSize(10)

        box_icon = (QgsRubberBand.ICON_FULL_BOX
                    if hasattr(QgsRubberBand, 'ICON_FULL_BOX')
                    else QgsRubberBand.ICON_FULL_BOX)
        self.highlightBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.highlightBand.setIcon(box_icon)
        self.highlightBand.setColor(Qt.red)
        self.highlightBand.setIconSize(12)
        self.highlightBand.hide()
        self._highlightedIndex = -1

        self._moveTimer = QTimer()
        self._moveTimer.setSingleShot(True)
        self._moveTimer.setInterval(30)
        self._moveTimer.timeout.connect(self._processDeferredMove)
        self._pendingMovePos = None

        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                         "      c None",
                                         ".     c #CC4C2F",
                                         "+     c #FFFFFF",
                                         "                ",
                                         "  ..           ",
                                         " .+..          ",
                                         " .++..         ",
                                         " .+++..        ",
                                         "  .++++..      ",
                                         "  .+++++..     ",
                                         "   .++++++..   ",
                                         "   .+++++++..  ",
                                         "    .++++++++. ",
                                         "    .+++..     ",
                                         "     .++.      ",
                                         "     .+.       ",
                                         "      ..       ",
                                         "                ",
                                         "                "]))

    def _snapPoint(self, mapPoint, skipSnap=False):
        if skipSnap:
            return mapPoint
        try:
            snapUtils = self.canvas.snappingUtils()
            result = snapUtils.snapToMap(
                mapPoint, None,
                QgsPointLocator.Vertex | QgsPointLocator.Edge)
            if result.isValid():
                return result.point()
        except Exception:
            logging.debug('Snap to map failed: %s', Exception)
        try:
            return self._manualSnap(mapPoint)
        except Exception:
            logging.debug('Manual snap failed: %s', Exception)
        return mapPoint

    def _manualSnap(self, mapPoint):
        pixelTolerance = 8
        mapTolerance = pixelTolerance * self.canvas.mapUnitsPerPixel()
        bestDist = mapTolerance
        bestPoint = None
        rect = QgsRectangle(
            mapPoint.x() - mapTolerance,
            mapPoint.y() - mapTolerance,
            mapPoint.x() + mapTolerance,
            mapPoint.y() + mapTolerance)
        for layer in self.canvas.layers():
            if not isinstance(layer, QgsVectorLayer):
                continue
            if not layer.isSpatial():
                continue
            request = QgsFeatureRequest()
            request.setFilterRect(rect)
            for feat in layer.getFeatures(request):
                geom = feat.geometry()
                for v in geom.vertices():
                    pt = QgsPointXY(v.x(), v.y())
                    dist = mapPoint.distance(pt)
                    if dist < bestDist:
                        bestDist = dist
                        bestPoint = pt
        return bestPoint if bestPoint else mapPoint

    def canvasPressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._startPan()
            return
        if e.button() == Qt.LeftButton:
            if not self.isDrawing and len(self.points) > 0:
                return
            point = self.toMapCoordinates(e.pos())
            skipSnap = bool(e.modifiers() & Qt.ShiftModifier)
            snapped = self._snapPoint(point, skipSnap)
            self.points.append(snapped)
            self.isDrawing = True
            self.updateRubberBand()
            self.pointAdded.emit(snapped)

    def canvasReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._endPan()
            return

    def _startPan(self):
        self._panTool = QgsMapToolPan(self.canvas)
        self._panTool.panningFinished.connect(self._endPan)
        self.canvas.setMapTool(self._panTool)

    def _endPan(self):
        if self._panTool is not None:
            try:
                self._panTool.panningFinished.disconnect(self._endPan)
            except Exception:
                logging.debug('Disconnect pan signal failed: %s', Exception)
            self._panTool = None
        self.canvas.setMapTool(self)

    def canvasDoubleClickEvent(self, e):
        min_pts = self._minPoints()
        if len(self.points) >= min_pts:
            self.endDrawing()

    def canvasMoveEvent(self, e):
        if self.isDrawing and len(self.points) > 0 and self.geomType != 'point':
            pos = self.toMapCoordinates(e.pos())
            skipSnap = bool(e.modifiers() & Qt.ShiftModifier)
            snapped = self._snapPoint(pos, skipSnap)
            self.rubberBand.movePoint(snapped)
            self._pendingMovePos = snapped
            if not self._moveTimer.isActive():
                self._moveTimer.start()

    def _processDeferredMove(self):
        if self._pendingMovePos is not None:
            self.mouseMoved.emit(self._pendingMovePos)
            self._pendingMovePos = None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancelDrawing()
        elif e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
            min_pts = self._minPoints()
            if len(self.points) >= min_pts:
                self.endDrawing()
        elif e.key() == Qt.Key_Backspace or e.key() == Qt.Key_Delete:
            self.undoLastPoint()

    def _minPoints(self):
        if self.geomType == 'point':
            return 1
        elif self.geomType == 'line':
            return 2
        return 3

    def setHighlightedVertex(self, index):
        if self.geomType == 'point':
            self.highlightBand.hide()
            return
        self._highlightedIndex = index
        if 0 <= index < len(self.points):
            self.highlightBand.reset(QgsWkbTypes.PointGeometry)
            self.highlightBand.addPoint(self.points[index])
            self.highlightBand.show()
        else:
            self.highlightBand.hide()
        self.canvas.refresh()

    def clearHighlightedVertex(self):
        self._highlightedIndex = -1
        self.highlightBand.hide()
        self.canvas.refresh()

    def updateRubberBand(self):
        if self.geomType == 'point':
            self.rubberBand.reset(self._point_geom)
            self.highlightBand.reset(QgsWkbTypes.PointGeometry)
            self.highlightBand.hide()
            self._highlightedIndex = -1
            if self.points:
                self.rubberBand.addPoint(self.points[-1])
                self.rubberBand.show()
            return

        if self.geomType == 'line':
            self.rubberBand.reset(self._line_geom)
        else:
            self.rubberBand.reset(self._poly_geom)
        self.vertexBand.reset(QgsWkbTypes.PointGeometry)

        for pt in self.points:
            self.rubberBand.addPoint(pt, False)
            self.vertexBand.addPoint(pt, False)
        self.rubberBand.addPoint(self.points[-1], False)
        self.rubberBand.movePoint(self.points[-1])

        if self.geomType == 'polygon' and len(self.points) > 2:
            self.rubberBand.closePoints(True)

        self.rubberBand.show()
        self.vertexBand.show()

        if 0 <= self._highlightedIndex < len(self.points):
            self.highlightBand.reset(QgsWkbTypes.PointGeometry)
            self.highlightBand.addPoint(self.points[self._highlightedIndex])
            self.highlightBand.show()
        else:
            self.highlightBand.hide()

        self.canvas.refresh()

    def finishDrawing(self):
        min_pts = self._minPoints()
        if len(self.points) >= min_pts:
            self.isDrawing = False
            self.drawingFinished.emit(list(self.points))

    def endDrawing(self):
        min_pts = self._minPoints()
        if len(self.points) >= min_pts:
            self.isDrawing = False
            self._drawingEnded = True
            self.updateRubberBand()
            self.drawingEnded.emit()

    def updatePoint(self, index, point):
        if 0 <= index < len(self.points):
            self.points[index] = point
            self.updateRubberBand()

    def undoLastPoint(self):
        if len(self.points) > 0:
            self.points.pop()
            if len(self.points) == 0:
                self.resetRubberBand()
            else:
                self.updateRubberBand()
            if self._drawingEnded:
                self._drawingEnded = False
                self.isDrawing = True

    def cancelDrawing(self):
        self.isDrawing = False
        self.points.clear()
        self.resetRubberBand()
        self.canceled.emit()

    def resetRubberBand(self):
        if self.geomType == 'point':
            self.rubberBand.reset(self._point_geom)
        elif self.geomType == 'line':
            self.rubberBand.reset(self._line_geom)
        else:
            self.rubberBand.reset(self._poly_geom)
        self.vertexBand.reset(QgsWkbTypes.PointGeometry)
        self.highlightBand.reset(QgsWkbTypes.PointGeometry)
        self.rubberBand.hide()
        self.vertexBand.hide()
        self.highlightBand.hide()
        self._highlightedIndex = -1
        self.canvas.refresh()

    def clear(self):
        self.points.clear()
        self.isDrawing = False
        self._drawingEnded = False
        self._highlightedIndex = -1
        self.resetRubberBand()

    def activate(self):
        self.canvas.setCursor(self.cursor)
        self._enableSnapping()
        super().activate()

    def deactivate(self):
        self.clear()
        self._restoreSnapping()
        super().deactivate()

    def _enableSnapping(self):
        proj = QgsProject.instance()
        self._origSnapConfig = proj.snappingConfig()
        cfg = QgsSnappingConfig(self._origSnapConfig)
        cfg.setMode(QgsSnappingConfig.AllLayers)
        cfg.setTolerance(8)
        cfg.setUnits(QgsTolerance.Pixels)
        for attr in ('setSnapType', 'setType'):
            if hasattr(cfg, attr):
                for val in (QgsSnappingConfig.VertexAndSegment, 3):
                    try:
                        getattr(cfg, attr)(val)
                        break
                    except Exception:
                        logging.debug('Set snap config failed: %s', Exception)
                break
        proj.setSnappingConfig(cfg)
        try:
            snapUtils = self.canvas.snappingUtils()
            for attr in ('setConfig', 'setConfigMode', 'readConfigFromProject',
                         'readFromProject'):
                if hasattr(snapUtils, attr):
                    try:
                        fn = getattr(snapUtils, attr)
                        fn(cfg) if attr in ('setConfig',) else fn()
                        break
                    except Exception:
                        logging.debug('Snap utils config failed: %s', Exception)
        except Exception:
            logging.debug('Snapping utils setup failed: %s', Exception)

    def _restoreSnapping(self):
        if self._origSnapConfig is not None:
            QgsProject.instance().setSnappingConfig(self._origSnapConfig)
            self._origSnapConfig = None

    def setPoints(self, points):
        self.points = list(points)
        self.updateRubberBand()

    def getPoints(self):
        return list(self.points)
