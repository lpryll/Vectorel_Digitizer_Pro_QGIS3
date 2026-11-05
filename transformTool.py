# -*- coding: utf-8 -*-
"""Map tool behind "Transform Features": move / rotate / scale the selected
features, either with typed values (see transformGUI.py) or interactively
with the mouse.

All geometry maths is done in the *layer* CRS.  Mouse positions (canvas CRS)
are converted to the layer CRS, and the live preview is drawn with rubber
bands that are re-projected to the canvas CRS by QGIS.
"""

import math

from qgis.PyQt.QtCore import Qt, QTimer, QCoreApplication, pyqtSignal
from qgis.PyQt.QtGui import QColor, QCursor, QTransform
from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsCsException,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand

MODE_MOVE = "move"
MODE_ROTATE = "rotate"
MODE_SCALE = "scale"

PIVOT_CENTER = "center"  # centre of the selection's bounding box
PIVOT_EACH = "each"  # every feature around its own bounding-box centre
PIVOT_CUSTOM = "custom"  # typed / picked point

ANGLE_STEP = 15.0  # Shift while rotating with the mouse
ANGLE_DECIMALS = 6
SCALE_DECIMALS = 8
MIN_SCALE = 1e-6
_EPS = 1e-12


def _tr(text):
    return QCoreApplication.translate("TransformTool", text)


def _icon(name):
    """QgsRubberBand icon type: scoped enum (QGIS >= 3.x with sip 6 / QGIS 4)
    with a fallback to the legacy attribute of older QGIS 3 versions."""
    try:
        return getattr(QgsRubberBand.IconType, name)
    except AttributeError:
        return getattr(QgsRubberBand, name)


def _geomEnum(name):
    """Qgis.GeometryType.<name> with a QgsWkbTypes fallback (same idea as in
    the rest of the plugin)."""
    try:
        return getattr(Qgis.GeometryType, name)
    except AttributeError:
        return getattr(QgsWkbTypes, name + "Geometry")


class TransformTool(QgsMapTool):
    stateChanged = pyqtSignal()  # tool changed the parameters -> GUI must re-sync
    pivotPicked = pyqtSignal()
    message = pyqtSignal(str, bool)  # text, isError
    closeRequested = pyqtSignal()

    def __init__(self, canvas):
        super().__init__(canvas)
        self._canvas = canvas

        # --- parameters (shared with the dialog) -----------------------
        self.mode = MODE_MOVE
        self.dx = 0.0
        self.dy = 0.0
        self.angle = 0.0  # degrees, clockwise positive
        self.sx = 1.0
        self.sy = 1.0
        self.uniform = True
        self.pivotMode = PIVOT_CENTER
        self.pivot = QgsPointXY(0.0, 0.0)
        self.center = QgsPointXY(0.0, 0.0)  # centre of the current selection
        self.applyOnRelease = False
        self.pickingPivot = False

        self.layer = None
        self.decimals = 4
        self.layerIsGeographic = False
        self._features = []  # [(fid, QgsGeometry)] snapshot, layer CRS

        # --- CRS helpers -------------------------------------------------
        self._sameCrs = True
        self._toLayer = None
        self._toCanvas = None

        # --- drag state --------------------------------------------------
        self._dragging = False
        self._startMap = None
        self._startLayer = None
        self._refAngle = 0.0
        self._refDist = 0.0
        self._refDx = 0.0
        self._refDy = 0.0
        self._pendingMap = None
        self._pendingMods = Qt.KeyboardModifier.NoModifier

        self._moveTimer = QTimer()
        self._moveTimer.setSingleShot(True)
        self._moveTimer.setInterval(30)
        self._moveTimer.timeout.connect(self._processPendingMove)

        # --- rubber bands (built per layer in activate) ------------------
        self._previewBand = None
        self._guideBand = None
        self._pivotBand = None
        self._bandType = None

        self._pointType = _geomEnum("Point")
        self._lineType = _geomEnum("Line")
        self._polygonType = _geomEnum("Polygon")

        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------
    def activate(self):
        super().activate()
        self.layer = self._canvas.currentLayer()
        if self.layer is None:
            self.closeRequested.emit()
            return

        try:
            self.layerIsGeographic = self.layer.crs().isGeographic()
        except AttributeError:
            self.layerIsGeographic = False
        self.decimals = 8 if self.layerIsGeographic else 4

        self._rebuildCrsTransforms()
        self._buildBands()
        self._connectSignals()

        self.pickingPivot = False
        self.resetParams()
        self.refreshSelection()
        self.updatePreview()
        self.stateChanged.emit()

    def deactivate(self):
        self._dragging = False
        self._moveTimer.stop()
        self.pickingPivot = False
        self._disconnectSignals()
        self._clearBands()
        self.layer = None
        self._features = []
        super().deactivate()

    def cleanup(self):
        """Remove the rubber bands from the canvas (plugin unload)."""
        self._moveTimer.stop()
        self._disconnectSignals()
        for band in (self._previewBand, self._guideBand, self._pivotBand):
            self._removeBand(band)
        self._previewBand = self._guideBand = self._pivotBand = None

    def _connectSignals(self):
        self.layer.selectionChanged.connect(self._onSelectionChanged)
        self.layer.editingStopped.connect(self._onLayerGone)
        self.layer.willBeDeleted.connect(self._onLayerGone)
        self._canvas.currentLayerChanged.connect(self._onLayerGone)
        self._canvas.destinationCrsChanged.connect(self._onCanvasCrsChanged)

    def _disconnectSignals(self):
        layer = self.layer
        if layer is not None:
            for name, slot in (
                ("selectionChanged", self._onSelectionChanged),
                ("editingStopped", self._onLayerGone),
                ("willBeDeleted", self._onLayerGone),
            ):
                try:
                    getattr(layer, name).disconnect(slot)
                except (TypeError, RuntimeError):
                    # not connected, or the layer's C++ object is already gone
                    pass
        for sig, slot in (
            (self._canvas.currentLayerChanged, self._onLayerGone),
            (self._canvas.destinationCrsChanged, self._onCanvasCrsChanged),
        ):
            try:
                sig.disconnect(slot)
            except (TypeError, RuntimeError):
                pass

    def _onLayerGone(self, *args):
        self.closeRequested.emit()

    def _onCanvasCrsChanged(self, *args):
        self._rebuildCrsTransforms()
        self.updatePreview()

    def _onSelectionChanged(self, *args):
        if self._dragging:
            self._dragging = False
            self._moveTimer.stop()
        self.resetParams()
        self.refreshSelection()
        self.updatePreview()
        self.stateChanged.emit()

    # ------------------------------------------------------------------
    # Rubber bands
    # ------------------------------------------------------------------
    def _buildBands(self):
        for band in (self._previewBand, self._guideBand, self._pivotBand):
            self._removeBand(band)

        gt = self.layer.geometryType()
        if gt == self._pointType:
            self._bandType = self._pointType
        elif gt == self._lineType:
            self._bandType = self._lineType
        else:
            self._bandType = self._polygonType

        orange = QColor(230, 126, 34)
        self._previewBand = QgsRubberBand(self._canvas, self._bandType)
        self._previewBand.setColor(orange)
        self._previewBand.setFillColor(QColor(230, 126, 34, 50))
        self._previewBand.setWidth(2)
        if self._bandType == self._pointType:
            self._previewBand.setIcon(_icon("ICON_CIRCLE"))
            self._previewBand.setIconSize(10)

        self._guideBand = QgsRubberBand(self._canvas, self._lineType)
        self._guideBand.setColor(QColor(41, 128, 185))
        self._guideBand.setWidth(1)
        try:
            self._guideBand.setLineStyle(Qt.PenStyle.DashLine)
        except (AttributeError, TypeError):
            pass

        self._pivotBand = QgsRubberBand(self._canvas, self._pointType)
        self._pivotBand.setColor(QColor(204, 76, 47))
        self._pivotBand.setIcon(_icon("ICON_CROSS"))
        self._pivotBand.setIconSize(14)
        self._pivotBand.setWidth(2)

    def _removeBand(self, band):
        if band is None:
            return
        try:
            band.reset()
            self._canvas.scene().removeItem(band)
        except (RuntimeError, AttributeError):
            pass

    def _clearBands(self):
        if self._previewBand is not None:
            self._previewBand.reset(self._bandType)
        if self._guideBand is not None:
            self._guideBand.reset(self._lineType)
        if self._pivotBand is not None:
            self._pivotBand.reset(self._pointType)

    def _clearGuide(self):
        if self._guideBand is not None:
            self._guideBand.reset(self._lineType)

    # ------------------------------------------------------------------
    # CRS helpers
    # ------------------------------------------------------------------
    def _rebuildCrsTransforms(self):
        canvasCrs = self._canvas.mapSettings().destinationCrs()
        layerCrs = self.layer.crs()
        self._sameCrs = canvasCrs == layerCrs
        if self._sameCrs:
            self._toLayer = self._toCanvas = None
        else:
            project = QgsProject.instance()
            self._toLayer = QgsCoordinateTransform(canvasCrs, layerCrs, project)
            self._toCanvas = QgsCoordinateTransform(layerCrs, canvasCrs, project)

    def _mapToLayer(self, pt):
        if self._sameCrs:
            return QgsPointXY(pt)
        try:
            return self._toLayer.transform(pt)
        except QgsCsException:
            return None

    def _layerToCanvas(self, pt):
        if self._sameCrs:
            return QgsPointXY(pt)
        try:
            return self._toCanvas.transform(pt)
        except QgsCsException:
            return None

    def _snap(self, mapPt):
        """Snap to project snapping layers if snapping is enabled."""
        try:
            if QgsProject.instance().snappingConfig().enabled():
                match = self._canvas.snappingUtils().snapToMap(mapPt)
                if match.isValid():
                    return QgsPointXY(match.point())
        except (TypeError, RuntimeError, AttributeError):
            pass
        return QgsPointXY(mapPt)

    # ------------------------------------------------------------------
    # Selection snapshot / parameters
    # ------------------------------------------------------------------
    def featureCount(self):
        return len(self._features)

    def refreshSelection(self):
        self._features = []
        if self.layer is None:
            return
        for feat in self.layer.getSelectedFeatures():
            geom = feat.geometry()
            if geom is None or geom.isNull() or geom.isEmpty():
                continue
            self._features.append((feat.id(), QgsGeometry(geom)))
        self.center = self._computeCenter()

    def _computeCenter(self):
        if not self._features:
            return QgsPointXY(0.0, 0.0)
        xmin = ymin = float("inf")
        xmax = ymax = float("-inf")
        for _fid, geom in self._features:
            bb = geom.boundingBox()
            xmin = min(xmin, bb.xMinimum())
            xmax = max(xmax, bb.xMaximum())
            ymin = min(ymin, bb.yMinimum())
            ymax = max(ymax, bb.yMaximum())
        return QgsPointXY((xmin + xmax) / 2.0, (ymin + ymax) / 2.0)

    def resetParams(self):
        self.dx = self.dy = 0.0
        self.angle = 0.0
        self.sx = self.sy = 1.0

    def hasChange(self):
        if self.mode == MODE_MOVE:
            return abs(self.dx) > _EPS or abs(self.dy) > _EPS
        if self.mode == MODE_ROTATE:
            return abs(self.angle) > _EPS
        return abs(self.sx - 1.0) > _EPS or abs(self.sy - 1.0) > _EPS

    def referencePivot(self):
        """Single pivot used for mouse reference (and for the shared modes)."""
        if self.pivotMode == PIVOT_CUSTOM:
            return QgsPointXY(self.pivot)
        return QgsPointXY(self.center)

    # ------------------------------------------------------------------
    # Geometry maths
    # ------------------------------------------------------------------
    def _transformGeometry(self, geom):
        g = QgsGeometry(geom)
        if self.mode == MODE_MOVE:
            g.translate(self.dx, self.dy)
            return g

        if self.pivotMode == PIVOT_EACH:
            c = geom.boundingBox().center()
        else:
            c = self.referencePivot()
        px, py = c.x(), c.y()

        if self.mode == MODE_ROTATE:
            # UI convention: positive = clockwise. The matrix below is the
            # standard counter-clockwise one (map coordinates, y up), so the
            # angle is negated:
            # x' = px + cos*(x-px) - sin*(y-py) ; y' = py + sin*(x-px) + cos*(y-py)
            rad = math.radians(-self.angle)
            cs, sn = math.cos(rad), math.sin(rad)
            t = QTransform(cs, sn, -sn, cs, px - cs * px + sn * py, py - sn * px - cs * py)
        else:
            t = QTransform(
                self.sx, 0.0, 0.0, self.sy, px * (1.0 - self.sx), py * (1.0 - self.sy)
            )
        self._applyAffine(g, t)
        return g

    @staticmethod
    def _applyAffine(g, t):
        try:
            g.transform(t)
        except (TypeError, AttributeError):
            # very old QGIS 3 without QgsGeometry.transform(QTransform)
            for i, v in enumerate(list(g.vertices())):
                x, y = t.map(v.x(), v.y())
                p = v.clone()
                p.setX(x)
                p.setY(y)
                g.moveVertex(p, i)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def updatePreview(self):
        if self._previewBand is None or self.layer is None:
            return

        self._previewBand.reset(self._bandType)
        if self._features and self.hasChange():
            geoms = []
            for _fid, geom in self._features:
                ng = self._transformGeometry(geom)
                if ng is not None and not ng.isNull():
                    geoms.append(ng)
            if geoms:
                self._previewBand.setToGeometry(
                    QgsGeometry.collectGeometry(geoms), self.layer
                )
        self._updatePivotMarker()

    def _updatePivotMarker(self):
        self._pivotBand.reset(self._pointType)
        if (
            self.mode == MODE_MOVE
            or not self._features
            or self.pivotMode == PIVOT_EACH
        ):
            return
        cp = self._layerToCanvas(self.referencePivot())
        if cp is not None:
            self._pivotBand.addPoint(cp)

    def _updateGuide(self, curMap):
        if self.mode == MODE_MOVE:
            pts = [self._startMap, curMap]
        else:
            pc = self._layerToCanvas(self.referencePivot())
            if pc is None:
                return
            if self.mode == MODE_ROTATE:
                pts = [self._startMap, pc, curMap]
            else:
                pts = [pc, curMap]
        self._guideBand.reset(self._lineType)
        last = len(pts) - 1
        for i, p in enumerate(pts):
            self._guideBand.addPoint(p, i == last)

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------
    def applyTransform(self):
        layer = self.layer
        if layer is None:
            return False
        if not self._features:
            self.message.emit(_tr("No features selected."), True)
            return False
        if not self.hasChange():
            self.message.emit(_tr("Nothing to apply – the values are unchanged."), True)
            return False
        if not layer.isEditable():
            self.message.emit(_tr("Layer is not editable."), True)
            return False

        names = {
            MODE_MOVE: "Move features",
            MODE_ROTATE: "Rotate features",
            MODE_SCALE: "Scale features",
        }
        count = 0
        ok = True
        layer.beginEditCommand(names[self.mode])
        try:
            for fid, geom in self._features:
                ng = self._transformGeometry(geom)
                if ng is None or ng.isNull():
                    continue
                if not layer.changeGeometry(fid, ng):
                    ok = False
                    break
                count += 1
        except Exception:
            ok = False

        if ok:
            layer.endEditCommand()
        else:
            layer.destroyEditCommand()
            self.message.emit(_tr("Transformation failed – no feature was changed."), True)
            return False

        self.resetParams()
        self.refreshSelection()
        self.updatePreview()
        self._canvas.refresh()
        self.stateChanged.emit()
        self.message.emit(
            _tr("Applied to {n} feature(s). Use Undo (Ctrl+Z) to revert.").format(n=count),
            False,
        )
        return True

    # ------------------------------------------------------------------
    # Mouse / keyboard
    # ------------------------------------------------------------------
    def canvasPressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self._cancelInteraction()
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return

        mapPt = self._snap(e.mapPoint())
        layerPt = self._mapToLayer(mapPt)
        if layerPt is None:
            return

        ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if self.mode != MODE_MOVE and (self.pickingPivot or ctrl):
            self.pivot = QgsPointXY(
                round(layerPt.x(), self.decimals), round(layerPt.y(), self.decimals)
            )
            self.pivotMode = PIVOT_CUSTOM
            self.pickingPivot = False
            self.updatePreview()
            self.pivotPicked.emit()
            self.stateChanged.emit()
            return

        if not self._features:
            self.message.emit(
                _tr("No features selected. Select features first, then use this tool."),
                True,
            )
            return

        ref = self.referencePivot()
        self._dragging = True
        self._startMap = mapPt
        self._startLayer = layerPt
        self._refDx = layerPt.x() - ref.x()
        self._refDy = layerPt.y() - ref.y()
        self._refDist = math.hypot(self._refDx, self._refDy)
        self._refAngle = math.atan2(self._refDy, self._refDx)

    def canvasMoveEvent(self, e):
        if not self._dragging:
            return
        self._pendingMap = e.mapPoint()
        self._pendingMods = e.modifiers()
        if not self._moveTimer.isActive():
            self._moveTimer.start()

    def canvasReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return
        self._moveTimer.stop()
        self._updateDrag(e.mapPoint(), e.modifiers())
        self._dragging = False
        self._clearGuide()
        if self.applyOnRelease and self.hasChange():
            self.applyTransform()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.applyTransform()
            e.accept()
        elif e.key() == Qt.Key.Key_Escape:
            self._cancelInteraction()
            e.accept()
        else:
            e.ignore()

    def _cancelInteraction(self):
        self._dragging = False
        self._moveTimer.stop()
        self.pickingPivot = False
        self._clearGuide()
        self.resetParams()
        self.updatePreview()
        self.stateChanged.emit()

    def _processPendingMove(self):
        if self._dragging and self._pendingMap is not None:
            self._updateDrag(self._pendingMap, self._pendingMods)

    def _updateDrag(self, rawMapPt, mods):
        mapPt = self._snap(rawMapPt)
        lp = self._mapToLayer(mapPt)
        if lp is None:
            return
        ref = self.referencePivot()

        if self.mode == MODE_MOVE:
            self.dx = round(lp.x() - self._startLayer.x(), self.decimals)
            self.dy = round(lp.y() - self._startLayer.y(), self.decimals)

        elif self.mode == MODE_ROTATE:
            if self._refDist > _EPS:
                a = math.atan2(lp.y() - ref.y(), lp.x() - ref.x()) - self._refAngle
                deg = -math.degrees(a)  # positive = clockwise
                deg = (deg + 180.0) % 360.0 - 180.0  # [-180, 180)
                if mods & Qt.KeyboardModifier.ShiftModifier:
                    deg = round(deg / ANGLE_STEP) * ANGLE_STEP
                self.angle = round(deg, ANGLE_DECIMALS)

        else:  # scale
            if self.uniform:
                if self._refDist > _EPS:
                    f = math.hypot(lp.x() - ref.x(), lp.y() - ref.y()) / self._refDist
                    f = round(max(f, MIN_SCALE), SCALE_DECIMALS)
                    self.sx = self.sy = f
            else:
                if abs(self._refDx) > _EPS:
                    self.sx = round(
                        max(abs(lp.x() - ref.x()) / abs(self._refDx), MIN_SCALE),
                        SCALE_DECIMALS,
                    )
                if abs(self._refDy) > _EPS:
                    self.sy = round(
                        max(abs(lp.y() - ref.y()) / abs(self._refDy), MIN_SCALE),
                        SCALE_DECIMALS,
                    )

        self._updateGuide(mapPt)
        self.updatePreview()
        self.stateChanged.emit()
