# -*- coding: utf-8 -*-


from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import (QgsWkbTypes, QgsGeometry, QgsFeature, QgsMapLayer,
                       QgsPoint, Qgis, QgsMultiPoint, QgsMultiLineString,
                       QgsLineString, QgsMultiPolygon, QgsPolygon, QgsPointXY,
                       QgsApplication, QgsFeatureRequest, QgsVectorLayerUtils)

from .resources import qInitResources, qCleanupResources  # noqa: F401
from .addFeatureGUI import AddFeatureGUI
from .chooseFeatureGUI import ChooseFeatureGUI
from .featureFinderTool import FeatureFinderTool
from .reprojectCoordinates import ReprojectCoordinates
from .drawingDigitizerGUI import DrawingDigitizerGUI
from .drawingTool import DrawingTool
from qgis.gui import QgsMapToolPan
import logging
import os.path
import webbrowser

# ---------------------------------------------------------------------------
# QGIS 3 / Qt5 geometry type constants (with QGIS 4 / Qt6 forward-compat)
# ---------------------------------------------------------------------------
try:
    _PointGeometry   = Qgis.GeometryType.Point
    _LineGeometry    = Qgis.GeometryType.Line
    _PolygonGeometry = Qgis.GeometryType.Polygon
except AttributeError:
    _PointGeometry   = QgsWkbTypes.PointGeometry
    _LineGeometry    = QgsWkbTypes.LineGeometry
    _PolygonGeometry = QgsWkbTypes.PolygonGeometry


class VectorelDigitizerPro:
    """Main plugin class for Vectorel Digitizer Pro."""

    def __init__(self, iface):
        """Constructor.

        :param iface: QGIS interface instance.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Locale / translation
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir, 'i18n',
            'numericalDigitize_{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Instance attributes
        self.actions = []
        self.menu = self.tr('&Vectorel Digitizer Pro')
        self.first_start      = None
        self.first_start_edit = None
        self.CRS = None

        self.canvas = self.iface.mapCanvas()
        self.EditFeatureMapTool  = None
        self.prevMapTool         = None

        self.__dlg         = None
        self.__dlgEdit     = None
        self.__dlgChooser  = None
        self.__dlgDraw     = None
        self.__drawTool    = None

        self.__layer             = None
        self.__layergeometryType = None
        self.__layerwkbType      = None
        self.__hasZ              = False
        self.__hasM              = False
        self.__isMultiType       = False
        self.__isEditMode        = False

    # ------------------------------------------------------------------
    # Translation helper
    # ------------------------------------------------------------------
    @staticmethod
    def tr(message):
        return QCoreApplication.translate('VectorelDigitizerPro', message)

    # ------------------------------------------------------------------
    # GUI setup / teardown
    # ------------------------------------------------------------------
    def initGui(self):
        """Create menu entries and toolbar icons."""
        icon = QIcon(self.plugin_dir + '/images/icon.svg')
        action = QAction(icon, self.tr('Add By Coordinates'), self.iface.mainWindow())
        action.triggered.connect(self.run)
        action.setEnabled(False)
        action.setWhatsThis(self.tr('Add By Coordinates – enter vertex coordinates from keyboard'))
        self.iface.digitizeToolBar().addAction(action)
        self.iface.addPluginToVectorMenu(self.menu, action)
        self.actions.append(action)

        icon = QIcon(self.plugin_dir + '/images/icon-edit.svg')
        action = QAction(icon, self.tr('Coordinate Editor'), self.iface.mainWindow())
        action.triggered.connect(self.runEdit)
        action.setEnabled(False)
        action.setWhatsThis(self.tr('Coordinate Editor – edit existing feature coordinates'))
        self.iface.digitizeToolBar().addAction(action)
        self.iface.addPluginToVectorMenu(self.menu, action)
        self.actions.append(action)

        icon = QIcon(self.plugin_dir + '/images/icon-draw.svg')
        action = QAction(icon, self.tr('Drawing Digitizer'), self.iface.mainWindow())
        action.triggered.connect(self.runDrawing)
        action.setEnabled(False)
        action.setCheckable(True)
        action.setWhatsThis(self.tr('Drawing Digitizer – draw point, line or polygon on the map canvas'))
        self.iface.digitizeToolBar().addAction(action)
        self.iface.addPluginToVectorMenu(self.menu, action)
        self.actions.append(action)

        icon = QIcon(self.plugin_dir + '/images/mActionHelpContents.svg')
        action = QAction(icon, self.tr('Help'), self.iface.mainWindow())
        action.triggered.connect(self.help)
        self.iface.addPluginToVectorMenu(self.menu, action)
        self.actions.append(action)

        self.first_start      = True
        self.first_start_edit = True

        self.canvas.currentLayerChanged.connect(self.toggle)
        self.canvas.mapToolSet.connect(self.deactivate)
        self.toggle()

    def unload(self):
        """Remove plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(self.tr('&Vectorel Digitizer Pro'), action)
            self.iface.digitizeToolBar().removeAction(action)
        try:
            self.canvas.currentLayerChanged.disconnect(self.toggle)
        except Exception:
            logging.debug('Disconnect layerChanged failed: %s', Exception)
        try:
            self.canvas.mapToolSet.disconnect(self.deactivate)
        except Exception:
            logging.debug('Disconnect mapToolSet failed: %s', Exception)

    # ------------------------------------------------------------------
    # Layer helpers
    # ------------------------------------------------------------------
    def __setlayerproperties(self):
        self.__layergeometryType = self.__layer.geometryType()
        self.__layerwkbType      = self.__layer.wkbType()
        self.__hasZ              = QgsWkbTypes.hasZ(self.__layerwkbType)
        self.__hasM              = QgsWkbTypes.hasM(self.__layerwkbType)
        self.__isMultiType       = QgsWkbTypes.isMultiType(self.__layerwkbType)

    # ------------------------------------------------------------------
    # Tool entry points
    # ------------------------------------------------------------------
    def run(self):
        """Open Add By Coordinates dialog (add new feature)."""
        if self.first_start:
            self.first_start = False
            try:
                self.__dlg = AddFeatureGUI(self.iface.mainWindow())
                self.__dlg.returnCoordList.connect(self.createGeom)
                self.__dlg.selectedCRS.connect(self.doTransformFromCrs)
                self.__dlg.configureSignals()
                self.__dlg.setWindowTitle(self.tr('Vectorel Digitizer Pro – Add Feature'))
            except Exception:
                import traceback
                self.__dlg       = None
                self.first_start = True
                self.iface.messageBar().pushCritical(
                    'VectorelDigitizerPro',
                    'Dialog init error: ' + traceback.format_exc())
                return

        if self.__dlg is None:
            return

        self.__setlayerproperties()
        self.__isEditMode = False
        self.__dlg.clearControls()
        self.__dlg.configureDialog(
            self.__layergeometryType, self.__layerwkbType,
            self.__isMultiType, self.__hasZ, self.__hasM,
            self.__isEditMode, self.canvas)
        self.__dlg.show()

    def runEdit(self):
        """Activate the feature-selector map tool to pick a feature for editing."""
        self.__isEditMode = True
        self.prevMapTool  = self.canvas.mapTool()
        self.EditFeatureMapTool = FeatureFinderTool(self.canvas)
        self.EditFeatureMapTool.Clicked.connect(self.EditFeature)
        self.canvas.setMapTool(self.EditFeatureMapTool)

    def runDrawing(self):
        """Start Drawing Digitizer – point, line or polygon drawing on the map canvas."""
        self.__isEditMode = False
        self.__layer = self.canvas.currentLayer()
        if self.__layer is None:
            return

        self.__setlayerproperties()

        if self.__layergeometryType == _PointGeometry:
            geomType = 'point'
        elif self.__layergeometryType == _LineGeometry:
            geomType = 'line'
        else:
            geomType = 'polygon'

        if self.__dlgDraw is None:
            self.__dlgDraw = DrawingDigitizerGUI(self.iface.mainWindow())
            self.__dlgDraw.finishedDrawing.connect(self._onDialogFinish)
            self.__dlgDraw.restartRequested.connect(self._onRestartDrawing)
            self.__dlgDraw.undoRequested.connect(self._onUndoPoint)
            self.__dlgDraw.pointEdited.connect(self._onPointEdited)
            self.__dlgDraw.drawingEnded.connect(self._onDialogEndDrawing)
            self.__dlgDraw.vertexSelected.connect(self._onVertexSelected)

        self.__dlgDraw.setGeometryType(geomType)
        self.__dlgDraw.clearPoints()
        self.__dlgDraw.setCanvas(self.canvas)
        self.__dlgDraw.show()

        if self.__drawTool is not None:
            try:
                self.__drawTool.pointAdded.disconnect(self._drawPointAdded)
            except Exception:
                logging.debug('Disconnect pointAdded failed: %s', Exception)
            try:
                self.__drawTool.mouseMoved.disconnect(self._onMouseMoved)
            except Exception:
                logging.debug('Disconnect mouseMoved failed: %s', Exception)
            try:
                self.__drawTool.drawingFinished.disconnect(self._onDrawingFinished)
            except Exception:
                logging.debug('Disconnect drawingFinished failed: %s', Exception)
            try:
                self.__drawTool.drawingEnded.disconnect(self._onToolEndDrawing)
            except Exception:
                logging.debug('Disconnect drawingEnded failed: %s', Exception)
            try:
                self.__drawTool.canceled.disconnect(self._onDrawingCanceled)
            except Exception:
                logging.debug('Disconnect canceled failed: %s', Exception)

        self.__drawTool = DrawingTool(self.canvas, geomType=geomType)
        self.__drawTool.pointAdded.connect(self._drawPointAdded)
        self.__drawTool.mouseMoved.connect(self._onMouseMoved)
        self.__drawTool.drawingFinished.connect(self._onDrawingFinished)
        self.__drawTool.drawingEnded.connect(self._onToolEndDrawing)
        self.__drawTool.canceled.connect(self._onDrawingCanceled)

        try:
            self.__dlgDraw.rejected.disconnect(self._onDrawingCanceled)
        except Exception:
            logging.debug('Disconnect rejected failed: %s', Exception)
        self.__dlgDraw.rejected.connect(self._onDrawingCanceled)

        self.canvas.setMapTool(self.__drawTool)

    # ------------------------------------------------------------------
    # Drawing Digitizer callbacks
    # ------------------------------------------------------------------
    def _drawPointAdded(self, point):
        if self.__dlgDraw is not None:
            self.__dlgDraw.addPoint(point)
            self.__dlgDraw.clearPreviewPoint()

    def _onMouseMoved(self, point):
        if self.__dlgDraw is not None:
            self.__dlgDraw.setPreviewPoint(point)

    def _onDialogFinish(self, points):
        if self.__dlgDraw is None:
            return
        geomType = self.__dlgDraw.geomType
        min_pts = self.__dlgDraw._minPoints()
        if len(points) < min_pts:
            return
        self.__dlgDraw.clearPoints()
        if self.__drawTool is not None:
            self.__drawTool.clear()
        if geomType == 'point':
            self._createPointFromClick(points[0])
        elif geomType == 'line':
            self._createLineFromPoints(points)
        else:
            self._createPolygonFromPoints(points)
        if geomType != 'point':
            self._setPanTool()
        else:
            self.canvas.setMapTool(self.__drawTool)

    def _onVertexSelected(self, row):
        if self.__drawTool is not None:
            self.__drawTool.setHighlightedVertex(row)

    def _onToolEndDrawing(self):
        if self.__dlgDraw is not None:
            self.__dlgDraw._onEndDrawing()

    def _onDialogEndDrawing(self):
        if self.__drawTool is not None and self.__dlgDraw is not None:
            self.__drawTool.setPoints(self.__dlgDraw.points)
            self.__drawTool.updateRubberBand()
        if self.__drawTool is not None and self.__drawTool.isDrawing:
            self.__drawTool.endDrawing()

    def _onDrawingFinished(self, points):
        if self.__dlgDraw is None:
            return
        geomType = self.__dlgDraw.geomType
        min_pts = self.__dlgDraw._minPoints()
        if len(points) < min_pts:
            return
        self.__dlgDraw.clearPoints()
        self.__drawTool.clear()
        if geomType == 'point':
            self._createPointFromClick(points[0])
        elif geomType == 'line':
            self._createLineFromPoints(points)
        else:
            self._createPolygonFromPoints(points)
        self._setPanTool()

    def _onDrawingCanceled(self):
        if self.__dlgDraw is not None:
            self.__dlgDraw.clearPoints()
        self._setPanTool()

    def _onPointEdited(self, index, point):
        if self.__drawTool is not None:
            self.__drawTool.updatePoint(index, point)

    def _onUndoPoint(self):
        if self.__drawTool is not None:
            self.__drawTool.undoLastPoint()

    def _onRestartDrawing(self):
        if self.__drawTool is not None:
            self.__drawTool.clear()
        if self.__dlgDraw is not None:
            self.__dlgDraw.clearPoints()
        if self.__drawTool is not None:
            self.canvas.setMapTool(self.__drawTool)

    def _createPolygonFromPoints(self, points):
        layer = self.canvas.currentLayer()
        if layer is None or not layer.isEditable():
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr('Error'),
                self.tr('Layer is not editable'),
                QMessageBox.Ok)
            return
        if len(points) < 3:
            return

        geom = QgsGeometry.fromPolygonXY([points])
        if geom is None or geom.isEmpty():
            return

        self.__layer = layer
        self.__setlayerproperties()
        self.__isEditMode = False

        coord_list = [['1', []]]
        for p in points:
            row = [p.x(), p.y()]
            if self.__hasZ:
                row.append(0.0)
            if self.__hasM:
                row.append(0.0)
            coord_list[0][1].append(row)

        self.CRS = self.canvas.mapSettings().destinationCrs()
        self.createGeom(coord_list)

    def _createPointFromClick(self, point):
        layer = self.canvas.currentLayer()
        if layer is None or not layer.isEditable():
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr('Error'),
                self.tr('Layer is not editable'),
                QMessageBox.Ok)
            return

        self.__layer = layer
        self.__setlayerproperties()
        self.__isEditMode = False

        coord_list = [['1', []]]
        row = [point.x(), point.y()]
        if self.__hasZ:
            row.append(0.0)
        if self.__hasM:
            row.append(0.0)
        coord_list[0][1].append(row)

        self.CRS = self.canvas.mapSettings().destinationCrs()
        self.createGeom(coord_list)

    def _createLineFromPoints(self, points):
        layer = self.canvas.currentLayer()
        if layer is None or not layer.isEditable():
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr('Error'),
                self.tr('Layer is not editable'),
                QMessageBox.Ok)
            return
        if len(points) < 2:
            return

        self.__layer = layer
        self.__setlayerproperties()
        self.__isEditMode = False

        coord_list = [['1', []]]
        for p in points:
            row = [p.x(), p.y()]
            if self.__hasZ:
                row.append(0.0)
            if self.__hasM:
                row.append(0.0)
            coord_list[0][1].append(row)

        self.CRS = self.canvas.mapSettings().destinationCrs()
        self.createGeom(coord_list)

    def _setPanTool(self):
        self.canvas.setMapTool(QgsMapToolPan(self.canvas))

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------
    def help(self):
        url = QUrl.fromLocalFile(
            self.plugin_dir + '/help' + self.tr('/index_en.html')).toString()
        webbrowser.open(url, new=2)

    # ------------------------------------------------------------------
    # Feature editing
    # ------------------------------------------------------------------
    def EditFeature(self, Rectangle):
        self.EditFeatureMapTool.Clicked.disconnect(self.EditFeature)
        QgsApplication.restoreOverrideCursor()
        self.iface.mapCanvas().setMapTool(self.prevMapTool)

        layer        = self.canvas.currentLayer()
        feature_list = []

        if layer is not None and Rectangle is not None:
            request = QgsFeatureRequest()
            request.setFilterRect(Rectangle.boundingBox())
            request.setFlags(QgsFeatureRequest.ExactIntersect)
            feature_list = list(layer.getFeatures(request))

            if len(feature_list) == 0:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    self.tr('Coordinate Editor – Error'),
                    self.tr('No feature selected'),
                    QMessageBox.Ok)
                self.feature_id = None
            elif len(feature_list) > 1:
                if self.__dlgChooser is None:
                    self.__dlgChooser = ChooseFeatureGUI(self.iface.mainWindow())
                    self.__dlgChooser.configureSignals()
                self.__dlgChooser.clearControls()
                self.__dlgChooser.configureDialog(feature_list, self.__layer)
                if self.__dlgChooser.exec() == 1:
                    self.feature_id = feature_list[self.__dlgChooser.selectedFeature].id()
                else:
                    self.feature_id = None
            else:
                self.feature_id = feature_list[0].id()

        if self.feature_id is not None:
            Feature = layer.getFeature(self.feature_id)
            coords  = []
            self.__setlayerproperties()
            self.createCoords(coords, Feature)

            if self.first_start_edit:
                self.first_start_edit = False
                self.__dlgEdit = AddFeatureGUI(self.iface.mainWindow())
                self.__dlgEdit.returnCoordList.connect(self.createGeom)
                self.__dlgEdit.selectedCRS.connect(self.doTransformFromCrs)
                self.__dlgEdit.configureSignals()
                self.__dlgEdit.setWindowTitle(self.tr('Vectorel Digitizer Pro – Edit Feature'))

            self.__dlgEdit.clearControls()
            self.__dlgEdit.configureDialog(
                self.__layergeometryType, self.__layerwkbType,
                self.__isMultiType, self.__hasZ, self.__hasM,
                self.__isEditMode, self.canvas)
            self.__dlgEdit.setValues(coords)
            self.__dlgEdit.show()

    # ------------------------------------------------------------------
    # Coordinate extraction from existing feature
    # ------------------------------------------------------------------
    def createCoords(self, coords, feature):
        geom = feature.geometry()

        if self.__layergeometryType == _PointGeometry:
            coords.append(['1', []])
            iterable = (geom.constParts() if self.__isMultiType else [None])
            if self.__isMultiType:
                for part in iterable:
                    for vertex in part.vertices():
                        row = [vertex.x(), vertex.y()]
                        if self.__hasZ: row.append(vertex.z())
                        if self.__hasM: row.append(vertex.m())
                        coords[0][1].append(row)
            else:
                for vertex in geom.vertices():
                    row = [vertex.x(), vertex.y()]
                    if self.__hasZ: row.append(vertex.z())
                    if self.__hasM: row.append(vertex.m())
                    coords[0][1].append(row)

        elif self.__layergeometryType == _LineGeometry:
            for part_num, part in enumerate(geom.constParts()):
                coords.append([str(part_num + 1), []])
                for vertex in part.vertices():
                    row = [vertex.x(), vertex.y()]
                    if self.__hasZ: row.append(vertex.z())
                    if self.__hasM: row.append(vertex.m())
                    coords[part_num][1].append(row)

        elif self.__layergeometryType == _PolygonGeometry:
            part_num = 0
            ring_num = 0
            for part in geom.constParts():
                ring = part.exteriorRing()
                coords.append([str(part_num + 1), []])
                for vertex in ring.vertices():
                    row = [vertex.x(), vertex.y()]
                    if self.__hasZ: row.append(vertex.z())
                    if self.__hasM: row.append(vertex.m())
                    coords[part_num + ring_num][1].append(row)

                # Remove duplicate closing vertex
                pl = coords[part_num + ring_num][1]
                if len(pl) > 1 and pl[0][0] == pl[-1][0] and pl[0][1] == pl[-1][1]:
                    del pl[-1]

                part_num += 1

                for i in range(part.numInteriorRings()):
                    ring = part.interiorRing(i)
                    coords.append([str(-(ring_num + 1)), []])
                    for vertex in ring.vertices():
                        row = [vertex.x(), vertex.y()]
                        if self.__hasZ: row.append(vertex.z())
                        if self.__hasM: row.append(vertex.m())
                        coords[part_num + ring_num][1].append(row)

                    pl = coords[part_num + ring_num][1]
                    if len(pl) > 1 and pl[0][0] == pl[-1][0] and pl[0][1] == pl[-1][1]:
                        del pl[-1]
                    ring_num += 1

    # ------------------------------------------------------------------
    # Layer state toggle
    # ------------------------------------------------------------------
    def toggle(self):
        """Enable / disable plugin actions depending on current layer state."""
        self.__layer = self.canvas.currentLayer()
        if self.__layer is None:
            for action in self.actions:
                if action.text() != self.tr('Help'):
                    action.setEnabled(False)
            return

        try:
            _vector_type = Qgis.LayerType.Vector
        except AttributeError:
            _vector_type = QgsMapLayer.VectorLayer

        if self.__layer.type() == _vector_type:
            self.__setlayerproperties()
            editing = self.__layer.isEditable()
            supported_geom = self.__layergeometryType in (
                _PointGeometry, _LineGeometry, _PolygonGeometry)

            if editing and supported_geom:
                for action in self.actions:
                    action.setEnabled(True)
                self.__layer.editingStopped.connect(self.toggle)
                try:
                    self.__layer.editingStarted.disconnect(self.toggle)
                except Exception:
                    logging.debug('Disconnect editingStarted failed: %s', Exception)
            else:
                for action in self.actions:
                    if action.text() != self.tr('Help'):
                        action.setEnabled(False)
                self.__layer.editingStarted.connect(self.toggle)
                try:
                    self.__layer.editingStopped.disconnect(self.toggle)
                except Exception:
                    logging.debug('Disconnect editingStopped failed: %s', Exception)
        else:
            for action in self.actions:
                if action.text() != self.tr('Help'):
                    action.setEnabled(False)

    def deactivate(self):
        """Uncheck toolbar buttons when a different map tool is selected."""
        for action in self.actions:
            action.setChecked(False)

    # ------------------------------------------------------------------
    # CRS / geometry creation
    # ------------------------------------------------------------------
    def doTransformFromCrs(self, p_CRS):
        self.CRS = p_CRS

    def createGeom(self, coords):
        crsDest = self.__layer.crs()
        rc = ReprojectCoordinates(self.CRS, crsDest, self.__hasZ, self.__hasM)
        if self.CRS != crsDest:
            coordsPoint = list(rc.reproject(coords, True))
        else:
            coordsPoint = list(rc.copyCoordstoPoints(coords))

        if self.__layergeometryType == _PointGeometry:
            if self.__isMultiType:
                mp = QgsMultiPoint()
                for item in coordsPoint[0][1]:
                    mp.addGeometry(item)
                self.createFeature(QgsGeometry(mp))
            else:
                self.createFeature(QgsGeometry(coordsPoint[0][1][0]))

        elif self.__layergeometryType == _LineGeometry:
            if self.__isMultiType:
                ml = QgsMultiLineString()
                for j in range(len(coordsPoint)):
                    ml.addGeometry(QgsLineString(coordsPoint[j][1]))
                self.createFeature(QgsGeometry(ml))
            else:
                self.createFeature(QgsGeometry(QgsLineString(coordsPoint[0][1])))

        elif self.__layergeometryType == _PolygonGeometry:
            if self.__isMultiType:
                mpoly = QgsMultiPolygon()
                for i in range(len(coordsPoint)):
                    if int(coordsPoint[i][0]) > 0:
                        ext_curve = QgsLineString(coordsPoint[i][1])
                        poly = QgsPolygon()
                        poly.setExteriorRing(ext_curve)
                        poly_geom = QgsGeometry(QgsPolygon(poly))
                        for j in range(len(coordsPoint)):
                            if int(coordsPoint[j][0]) < 0:
                                all_inside = all(
                                    poly_geom.contains(
                                        QgsPointXY(coordsPoint[j][1][k].x(),
                                                   coordsPoint[j][1][k].y()))
                                    for k in range(len(coordsPoint[j][1])))
                                if all_inside:
                                    poly.addInteriorRing(
                                        QgsLineString(coordsPoint[j][1]))
                        mpoly.addGeometry(poly)
                self.createFeature(QgsGeometry(mpoly))
            else:
                ext_ring = next(
                    (i for i in range(len(coordsPoint))
                     if int(coordsPoint[i][0]) > 0), 0)
                poly = QgsPolygon()
                poly.setExteriorRing(QgsLineString(coordsPoint[ext_ring][1]))
                poly_geom = QgsGeometry(QgsPolygon(poly))

                for i in range(len(coordsPoint)):
                    if int(coordsPoint[i][0]) < 0:
                        all_inside = all(
                            poly_geom.contains(
                                QgsPointXY(coordsPoint[i][1][j].x(),
                                           coordsPoint[i][1][j].y()))
                            for j in range(len(coordsPoint[i][1])))
                        if all_inside:
                            poly.addInteriorRing(QgsLineString(coordsPoint[i][1]))
                        else:
                            QMessageBox.question(
                                self.iface.mainWindow(),
                                self.tr('Ring not in exterior contour'),
                                self.tr('The new geometry is not valid. '
                                        'Do you want to use it anyway?'),
                                QMessageBox.Yes, QMessageBox.No)
                self.createFeature(QgsGeometry(poly))

    def createFeature(self, geom):
        provider = self.__layer.dataProvider()  # noqa – kept for symmetry

        if not self.__isEditMode:
            feature = QgsVectorLayerUtils.createFeature(self.__layer)
        else:
            feature = self.__layer.getFeature(self.feature_id)

        if not geom.validateGeometry():
            feature.setGeometry(geom)
        else:
            reply = QMessageBox.question(
                self.iface.mainWindow(),
                self.tr('Feature not valid'),
                self.tr("The new geometry is not valid. "
                        "Do you want to use it anyway?"),
                QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                feature.setGeometry(geom)
            else:
                return False

        if not self.__isEditMode:
            self.__layer.beginEditCommand('Feature added')
            self.__layer.addFeature(feature)
            if self.iface.openFeatureForm(self.__layer, feature):
                self.__layer.endEditCommand()
            else:
                self.__layer.destroyEditCommand()
        else:
            self.__layer.beginEditCommand('Feature updated')
            self.__layer.updateFeature(feature)
            self.__layer.endEditCommand()

        self.canvas.refresh()
