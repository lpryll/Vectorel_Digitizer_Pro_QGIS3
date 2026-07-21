# -*- coding: utf-8 -*-


from qgis.PyQt.QtCore import (QSettings, QPersistentModelIndex, pyqtSignal,
                               QCoreApplication, QModelIndex, Qt, QSize)
from qgis.PyQt.QtGui import QColor, QBrush
from qgis.PyQt.QtWidgets import (QMessageBox, QDialogButtonBox, QHeaderView,
                                   QTableWidgetItem, QDialog, QApplication,
                                   QFrame, QVBoxLayout, QHBoxLayout,
                                   QLabel, QComboBox)
from qgis.core import (QgsCoordinateReferenceSystem, QgsWkbTypes, Qgis,
                       QgsDistanceArea, QgsProject, QgsPoint, QgsPointXY,
                       QgsPolygon, QgsLineString, QgsGeometry, QgsSettings,
                       QgsApplication)
from qgis.gui import QgsProjectionSelectionDialog

from .resources import qInitResources, qCleanupResources  # noqa: F401
from .highlightFeature import HighlightFeature
from .reprojectCoordinates import ReprojectCoordinates
from .valueChecker import ValueChecker, CellValue
from .ui_addFeatureGUI import Ui_numericalDigitize_MainDialog

import os
currentPath = os.path.dirname(__file__)


def _fmtNum(val, decimals=6):
    s = '{:,.{d}f}'.format(val, d=decimals)
    return s.replace('.', '\x00').replace(',', '.').replace('\x00', ',')

# ---------------------------------------------------------------------------
# QGIS 3 / Qt5 geometry type constants
# ---------------------------------------------------------------------------
try:
    _PointGeometry   = Qgis.GeometryType.Point
    _LineGeometry    = Qgis.GeometryType.Line
    _PolygonGeometry = Qgis.GeometryType.Polygon
except AttributeError:
    _PointGeometry   = QgsWkbTypes.PointGeometry
    _LineGeometry    = QgsWkbTypes.LineGeometry
    _PolygonGeometry = QgsWkbTypes.PolygonGeometry

# ---------------------------------------------------------------------------
# Modern stylesheet – applied once in __init__
# ---------------------------------------------------------------------------
_DIALOG_STYLE = """
/* ── Dialog background ─────────────────────────────────────── */
QDialog {
    background-color: #f5f6fa;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 9pt;
}

/* ── Header banner ─────────────────────────────────────────── */
#headerFrame {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1a5276, stop:1 #2980b9);
    border-radius: 6px;
    padding: 2px;
}
#headerTitle {
    color: white;
    font-size: 12pt;
    font-weight: bold;
}
#headerSub {
    color: #aed6f1;
    font-size: 8pt;
}

/* ── Group boxes ────────────────────────────────────────────── */
QGroupBox {
    font-weight: bold;
    font-size: 9pt;
    color: #2c3e50;
    border: 1px solid #c8d6e5;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 6px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    background-color: #f5f6fa;
    color: #2980b9;
}

/* ── Radio buttons ──────────────────────────────────────────── */
QRadioButton {
    color: #2c3e50;
    spacing: 6px;
}
QRadioButton::indicator {
    width: 14px; height: 14px;
    border-radius: 7px;
    border: 2px solid #95a5a6;
    background: white;
}
QRadioButton::indicator:checked {
    background: #2980b9;
    border-color: #2980b9;
}
QRadioButton::indicator:hover {
    border-color: #3498db;
}

/* ── Labels ─────────────────────────────────────────────────── */
QLabel {
    color: #2c3e50;
}

/* ── Table widget ───────────────────────────────────────────── */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #eaf2fb;
    gridline-color: #d5d8dc;
    border: 1px solid #c8d6e5;
    border-radius: 4px;
    selection-background-color: #2980b9;
    selection-color: #ffffff;
    font-size: 9pt;
}
QTableWidget::item {
    padding: 3px 6px;
}
QTableWidget::item:selected {
    background-color: #2980b9;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #2c3e50;
    color: #ecf0f1;
    font-weight: bold;
    font-size: 9pt;
    padding: 5px 6px;
    border: none;
    border-right: 1px solid #3d5166;
}
QHeaderView::section:first {
    border-top-left-radius: 4px;
}
QHeaderView::section:last {
    border-right: none;
}

/* ── Parts list ─────────────────────────────────────────────── */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #c8d6e5;
    border-radius: 4px;
    color: #2c3e50;
    font-size: 9pt;
}
QListWidget::item:selected {
    background-color: #2980b9;
    color: white;
    border-radius: 3px;
}
QListWidget::item:hover {
    background-color: #d6eaf8;
}

/* ── Tool buttons (icon-only) ───────────────────────────────── */
QToolButton {
    background-color: #ffffff;
    border: 1px solid #c8d6e5;
    border-radius: 4px;
    padding: 3px;
    color: #2c3e50;
}
QToolButton:hover {
    background-color: #d6eaf8;
    border-color: #2980b9;
}
QToolButton:pressed {
    background-color: #2980b9;
    border-color: #1a6fa3;
}
QToolButton:disabled {
    background-color: #ecf0f1;
    border-color: #d5d8dc;
    color: #aab7b8;
}

/* ── Push buttons ───────────────────────────────────────────── */
QPushButton {
    background-color: #2980b9;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 5px 14px;
    font-weight: bold;
    font-size: 9pt;
    min-height: 22px;
}
QPushButton:hover   { background-color: #3498db; }
QPushButton:pressed { background-color: #1a6fa3; }
QPushButton:disabled {
    background-color: #bdc3c7;
    color: #7f8c8d;
}

/* ── Dialog button box ──────────────────────────────────────── */
QDialogButtonBox QPushButton[text="OK"] {
    background-color: #27ae60;
}
QDialogButtonBox QPushButton[text="OK"]:hover   { background-color: #2ecc71; }
QDialogButtonBox QPushButton[text="OK"]:pressed { background-color: #1e8449; }
QDialogButtonBox QPushButton[text="Cancel"] {
    background-color: #c0392b;
}
QDialogButtonBox QPushButton[text="Cancel"]:hover   { background-color: #e74c3c; }
QDialogButtonBox QPushButton[text="Cancel"]:pressed { background-color: #922b21; }

/* ── Frame divider ──────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #c8d6e5;
}

/* ── Scroll bars ────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #f0f3f4; width: 10px; border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #aab7b8; border-radius: 5px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #7f8c8d; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class AddFeatureGUI(QDialog, Ui_numericalDigitize_MainDialog):

    returnCoordList = pyqtSignal(list)
    selectedCRS     = pyqtSignal(object)

    coords_matrix = []
    prev_row      = 0
    layertype     = None
    wkbtype       = None
    has_Z         = False
    has_M         = False
    isMultiType   = False
    isEditMode    = False
    mapCanvas     = None
    highLighter   = None
    valueChecker  = None

    __ignore_changeCellEvent = False
    __part_changing          = False
    __contursCount           = 1
    __ringsCount             = 0
    __deletedPart            = None

    def __init__(self, parent=None):
        super(AddFeatureGUI, self).__init__(parent)
        self.setupUi(self)

        # Apply modern stylesheet
        self.setStyleSheet(_DIALOG_STYLE)

        self.featureCrs  = None
        self.otherCrs    = None
        self.projectCrs  = None

        # ── Header banner (insert at top of grid) ────────────────
        hdrFrame = QFrame()
        hdrFrame.setObjectName('headerFrame')
        hdrLayout = QVBoxLayout(hdrFrame)
        hdrLayout.setContentsMargins(10, 6, 10, 6)
        hdrLayout.setSpacing(1)
        self.hdrTitle = QLabel('Add By Coordinates')
        self.hdrTitle.setObjectName('headerTitle')
        self.hdrSub = QLabel('Enter vertex coordinates from keyboard')
        self.hdrSub.setObjectName('headerSub')
        hdrLayout.addWidget(self.hdrTitle)
        hdrLayout.addWidget(self.hdrSub)

        # Shift existing grid items down to make room for header
        items = []
        for i in range(self.gridLayout.count()):
            item = self.gridLayout.itemAt(i)
            if item is not None:
                pos = self.gridLayout.getItemPosition(i)
                items.append((pos[0], pos[1], pos[2], pos[3], item))
        for row, col, rowSpan, colSpan, item in items:
            self.gridLayout.removeItem(item)
            if item.widget():
                self.gridLayout.addWidget(item.widget(), row + 1, col, rowSpan, colSpan)
            elif item.layout():
                self.gridLayout.addLayout(item.layout(), row + 1, col, rowSpan, colSpan)
        self.gridLayout.addWidget(hdrFrame, 0, 1, 1, 1)

        # ── CRS select button icon ────────────────────────────────
        self.tbSelectCrs.setIcon(
            QgsApplication.getThemeIcon('mIconProjectionEnabled.svg'))
        self.tbSelectCrs.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.tbSelectCrs.setIconSize(QSize(20, 20))

        # Replace combo with a read-only label showing the selected CRS
        self.lblCrsInfo = QLabel('CRS not selected')
        self.lblCrsInfo.setMinimumHeight(24)
        idx = self.crsLayout.indexOf(self.cbCrsSelection)
        if idx >= 0:
            self.crsLayout.removeWidget(self.cbCrsSelection)
        self.cbCrsSelection.hide()
        self.crsLayout.insertWidget(idx, self.lblCrsInfo, 1)
        self.tbSelectCrs.clicked.connect(self._selectCustomCrs)

        self.toolButtonUndoPart.setIcon(
            QgsApplication.getThemeIcon('mActionUndo.svg'))
        self.toolButtonUndoPart.setEnabled(False)

        # Area / Length display widgets (added programmatically below groupBox)
        self._area_sqm = 0.0
        self._area_total_sqm = 0.0
        self._line_length_m = 0.0
        self._line_total_length_m = 0.0
        self._is_line_mode = False

        self.areaFrame  = QFrame()
        self.areaLayout = QVBoxLayout(self.areaFrame)
        self.areaLayout.setContentsMargins(6, 6, 6, 6)
        self.areaLayout.setSpacing(2)

        self.lblAreaTitle = QLabel('Calculated Area')
        self.lblAreaTitle.setStyleSheet(
            'font-weight: bold; font-size: 11pt; color: #1a5c32;')
        self.areaLayout.addWidget(self.lblAreaTitle)

        unitRow = QHBoxLayout()
        unitRow.setSpacing(4)
        self.lblAreaUnit = QLabel('Unit:')
        self.lblAreaUnit.setStyleSheet(
            'font-size: 9pt; color: #27ae60;')
        self.cbAreaUnit = QComboBox()
        self.cbAreaUnit.setStyleSheet(
            'font-size: 9pt; color: #27ae60;')
        self.cbAreaUnit.currentIndexChanged.connect(self._onAreaUnitChanged)
        unitRow.addWidget(self.lblAreaUnit)
        unitRow.addWidget(self.cbAreaUnit, 1)
        self.areaLayout.addLayout(unitRow)

        self.lblArea  = QLabel()
        self.lblArea.setStyleSheet(
            'font-weight: bold; font-size: 11pt; color: #27ae60;')
        self.areaLayout.addWidget(self.lblArea)

        self.areaSeparator = QFrame()
        self.areaSeparator.setFrameShape(QFrame.Shape.HLine)
        self.areaSeparator.setFrameShadow(QFrame.Shadow.Sunken)
        self.areaLayout.addWidget(self.areaSeparator)

        self.lblTotalArea = QLabel()
        self.lblTotalArea.setStyleSheet(
            'font-weight: bold; font-size: 10pt; color: #1a5c32;')
        self.areaLayout.addWidget(self.lblTotalArea)

        self.areaFrame.setStyleSheet(
            'QFrame { background: #eafaf1; border: 1px solid #a9dfbf; '
            'border-radius: 5px; }')

        self.areaSeparator.hide()
        self.lblTotalArea.hide()

        self.areaFrameRow = 4
        self.gridLayout.addWidget(self.areaFrame, self.areaFrameRow, 1, 1, 1)
        self.areaFrame.hide()

    # ------------------------------------------------------------------
    def configureSignals(self):
        self.twPoints.currentCellChanged.connect(self.onCellChanged)
        self.twPoints.cellChanged.connect(self.onCellValueChanged)
        self.twPoints.cellClicked.connect(self.onCellClicked)

        self.buttonBox.accepted.connect(self.onOK)
        self.finished.connect(self.onFinished)

        self.toolButtonCopy.clicked.connect(self.copyButtonClicked)
        self.toolButtonPaste.clicked.connect(self.pasteButtonClicked)
        self.toolButtonSwap.clicked.connect(self.swapButtonClicked)
        self.toolButtonAddRows.clicked.connect(self.addRowsButtonClicked)
        self.toolButtonRemoveRows.clicked.connect(self.removeRowsButtonClicked)

        self.toolButtonAddPart.clicked.connect(self.addPartButtonClicked)
        self.toolButtonAddRing.clicked.connect(self.addRingButtonClicked)
        self.toolButtonRemovePart.clicked.connect(self.removePartButtonClicked)
        self.toolButtonUndoPart.clicked.connect(self.undoPartButtonClicked)
        self.listParts.currentRowChanged.connect(self.partChanged)

    def clearControls(self):
        self.coords_matrix.clear()
        self.coords_matrix.append([1, []])
        self.prev_row       = 0
        self.__contursCount = 0
        self.__ringsCount   = 0
        self.__deletedPart  = None
        self.highLighter    = None

        model = self.twPoints.model()
        self.__ignore_changeCellEvent = True
        model.removeRows(0, model.rowCount())
        model.insertRows(0, 1)
        self.__ignore_changeCellEvent = False

        self.listParts.model().removeRows(0, self.listParts.model().rowCount())
        self.valueChecker = None
        self.areaFrame.hide()

    def configureDialog(self, p_layertype, p_wkbtype, p_Multitype=False,
                        p_Z=False, p_M=False, p_EditMode=False, p_Canvas=None):
        self.layertype   = p_layertype
        self.wkbtype     = p_wkbtype
        self.has_Z       = p_Z
        self.has_M       = p_M
        self.isMultiType = p_Multitype
        self.isEditMode  = p_EditMode
        self.hdrTitle.setText(
            'Coordinate Editor' if p_EditMode
            else 'Add By Coordinates')
        self.hdrSub.setText(
            'Edit existing feature coordinates' if p_EditMode
            else 'Enter vertex coordinates from keyboard')
        self.mapCanvas   = p_Canvas
        self.projectCrs  = self.mapCanvas.mapSettings().destinationCrs()
        self.highLighter = HighlightFeature(
            self.mapCanvas,
            self.layertype == _PointGeometry,
            self.layertype == _PolygonGeometry,
            self.projectCrs)
        self.valueChecker = ValueChecker(self.twPoints, self.layertype)

        if (self.layertype == _PointGeometry or
                (self.layertype == _LineGeometry and not self.isMultiType)):
            self.partButtonsFrame.hide()
            self.partsFrame.hide()
            self.gridMainLayout.setHorizontalSpacing(0)
        else:
            self.partButtonsFrame.show()
            self.partsFrame.show()
            self.gridMainLayout.setHorizontalSpacing(3)
            self.toolButtonAddRing.setEnabled(self.layertype == _PolygonGeometry)
            self.toolButtonAddPart.setEnabled(self.isMultiType)

            model = self.listParts.model()
            model.blockSignals(True)
            model.insertRows(0, 1)
            # BUG FIX: use Qt.EditRole (not QtCore.Qt.EditRole)
            model.setData(model.index(0), '1', Qt.ItemDataRole.EditRole)
            model.blockSignals(False)
            self.__contursCount = 1
            self.prev_row       = 0

        if self.has_Z and self.has_M:
            tableColumns  = 4
            headerLabels  = ['X', 'Y', 'Z', 'M']
        elif self.has_Z != self.has_M:
            tableColumns  = 3
            headerLabels  = ['X', 'Y', 'Z'] if self.has_Z else ['X', 'Y', 'M']
        else:
            tableColumns  = 2
            headerLabels  = ['X', 'Y']

        modelColumns = self.twPoints.model().columnCount()
        if tableColumns > modelColumns:
            self.twPoints.model().insertColumns(2, tableColumns - modelColumns)
        elif tableColumns < modelColumns:
            self.twPoints.model().removeColumns(2, modelColumns - tableColumns)

        for i, label in enumerate(headerLabels):
            item = self.twPoints.horizontalHeaderItem(i)
            if item is not None:
                item.setText(label)
            else:
                item = QTableWidgetItem()
                item.setText(label)
                self.twPoints.setHorizontalHeaderItem(i, item)

        for i in range(self.twPoints.columnCount()):
            self.twPoints.setColumnWidth(
                i, int(self.twPoints.width() / self.twPoints.columnCount()))
            self.twPoints.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.Stretch)

        self.twPoints.setAlternatingRowColors(True)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        self._is_line_mode = (self.layertype == _LineGeometry)
        self._configureUnits()

        # Always prompt for CRS at dialog open
        dlg = QgsProjectionSelectionDialog()
        layer_crs = self.mapCanvas.currentLayer().crs()
        if layer_crs.isValid():
            dlg.setCrs(layer_crs)
        saved_wkt = QSettings().value(
            '/Plugin-VectorelDigitizerPro/LastCrsWkt', '', type=str)
        if saved_wkt:
            crs = QgsCoordinateReferenceSystem.fromWkt(saved_wkt)
            if crs.isValid():
                dlg.setCrs(crs)
        if dlg.exec():
            self.otherCrs = dlg.crs()
            self.featureCrs = dlg.crs()
        elif layer_crs.isValid():
            self.otherCrs = layer_crs
            self.featureCrs = layer_crs
        self.lblCrsInfo.setText(self._crsDisplayText(self.featureCrs))
        self.selectedCRS.emit(self.featureCrs)

    @staticmethod
    def translate_str(message):
        return QCoreApplication.translate('AddFeatureGUI', message)

    @staticmethod
    def _crsDisplayText(crs):
        desc = crs.description()
        auth = crs.authid()
        if desc:
            return f'{desc} ({auth})'
        return auth

    # ------------------------------------------------------------------
    # Highlight helpers
    # ------------------------------------------------------------------
    def highLightFeature(self, partNum, vertexNum=-1):
        if self.highLighter is not None:
            self.highLighter.removeHighlight()
            if -1 < partNum < len(self.coords_matrix):
                self.highLighter.createHighlight(
                    self.coords_matrix, partNum, self.featureCrs)
                if -1 < vertexNum < len(self.coords_matrix[partNum][1]):
                    self.highLighter.changeCurrentVertex(vertexNum)

    # ------------------------------------------------------------------
    # Load existing coords
    # ------------------------------------------------------------------
    def setValues(self, coord_list):
        self.coords_matrix = list(coord_list)

        model = self.listParts.model()
        model.removeRows(0, model.rowCount())
        model.insertRows(0, len(self.coords_matrix))

        self.__contursCount = len(
            [p for p in self.coords_matrix if int(p[0]) > 0])
        self.__ringsCount   = len(self.coords_matrix) - self.__contursCount

        model.blockSignals(True)
        for i in range(len(self.coords_matrix)):
            model.setData(model.index(i, 0, QModelIndex()),
                          self.coords_matrix[i][0])
        model.blockSignals(False)
        model.dataChanged.emit(
            model.index(0, 0, QModelIndex()),
            model.index(model.rowCount() - 1, 0, QModelIndex()))

        tw_model = self.twPoints.model()
        tw_model.removeRows(0, tw_model.rowCount())
        row_count = (len(self.coords_matrix[0][1])
                     if (self.layertype == _PointGeometry and
                         not self.isMultiType)
                     else len(self.coords_matrix[0][1]) + 1)
        tw_model.insertRows(0, row_count)

        coordslist = self.coords_matrix[0][1]
        tw_model.blockSignals(True)
        for i, row in enumerate(coordslist):
            for j in range(self.twPoints.columnCount()):
                val = row[j]
                if isinstance(val, float):
                    tw_model.setData(
                        tw_model.index(i, j, QModelIndex()), '%.2f' % val)
                    tw_model.setData(
                        tw_model.index(i, j, QModelIndex()), val,
                        Qt.ItemDataRole.UserRole)
                else:
                    tw_model.setData(
                        tw_model.index(i, j, QModelIndex()), str(val))
        tw_model.blockSignals(False)

        self.__part_changing = True
        tw_model.dataChanged.emit(
            tw_model.index(0, 0, QModelIndex()),
            tw_model.index(tw_model.rowCount() - 1,
                           tw_model.columnCount() - 1, QModelIndex()))
        self.__part_changing = False

        layerCrs = self.mapCanvas.currentLayer().crs()
        if (layerCrs.isValid() and self.featureCrs.isValid() and
                layerCrs != self.featureCrs):
            rc = ReprojectCoordinates(layerCrs, self.featureCrs,
                                      self.has_Z, self.has_M)
            self.coords_matrix = list(rc.reproject(self.coords_matrix, False))
            self.__part_changing = True
            self.refreshTable(0)
            self.__part_changing = False

        self.highLightFeature(0, 0)
        self.updateAreaDisplay()
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(
            self.valueChecker.setOkButtonState())

    # ------------------------------------------------------------------
    # Area / Length display
    # ------------------------------------------------------------------
    _AREA_UNITS = {
        'Hectares':         (10000,       'ha'),
        'Acres':            (4046.8564224, 'ac'),
        'Square Feet':      (0.09290304,  'ft²'),
        'Square Meters':    (1.0,         'm²'),
        'Square Kilometers': (1e6,        'km²'),
        'Square Miles':     (2589988.110336, 'mi²'),
    }

    _LENGTH_UNITS = {
        'Meters':      (1.0,    'm'),
        'Kilometers':  (1000.0, 'km'),
        'Feet':        (0.3048, 'ft'),
        'Miles':       (1609.344, 'mi'),
        'Yards':       (0.9144, 'yd'),
    }

    def _configureUnits(self):
        self.cbAreaUnit.blockSignals(True)
        self.cbAreaUnit.clear()
        if self._is_line_mode:
            self.lblAreaTitle.setText('Calculated Length')
            self.cbAreaUnit.addItems(self._LENGTH_UNITS.keys())
        else:
            self.lblAreaTitle.setText('Calculated Area')
            self.cbAreaUnit.addItems(self._AREA_UNITS.keys())
        self.cbAreaUnit.blockSignals(False)

    def _convertArea(self, area_sqm):
        unit = self.cbAreaUnit.currentText()
        divisor, symbol = self._AREA_UNITS[unit]
        return f'{_fmtNum(area_sqm / divisor, 2)} {symbol}'

    def _convertLength(self, length_m):
        unit = self.cbAreaUnit.currentText()
        divisor, symbol = self._LENGTH_UNITS[unit]
        return f'{_fmtNum(length_m / divisor, 2)} {symbol}'

    def _onAreaUnitChanged(self, _index):
        if self._is_line_mode:
            self.lblArea.setText(self._convertLength(self._line_length_m))
            if self._line_total_length_m > 0:
                self.lblTotalArea.setText(
                    f'Total: {self._convertLength(self._line_total_length_m)}')
        else:
            self.lblArea.setText(self._convertArea(self._area_sqm))
            if self._area_total_sqm > 0:
                self.lblTotalArea.setText(
                    f'Total: {self._convertArea(self._area_total_sqm)}')

    def updateAreaDisplay(self):
        self.areaFrame.hide()
        self.areaSeparator.hide()
        self.lblTotalArea.hide()
        self._area_sqm = 0.0
        self._area_total_sqm = 0.0
        self._line_length_m = 0.0
        self._line_total_length_m = 0.0
        if self.featureCrs is None:
            return
        if not self.coords_matrix:
            return
        try:
            da = QgsDistanceArea()
            da.setSourceCrs(self.featureCrs,
                            QgsProject.instance().transformContext())
            if self.featureCrs.isGeographic():
                da.setEllipsoid(QgsProject.instance().ellipsoid())

            ext_indices = [i for i, p in enumerate(self.coords_matrix)
                           if int(p[0]) > 0]

            if self._is_line_mode:
                self._updateLengthDisplay(da, ext_indices)
            else:
                self._updateAreaCalc(da, ext_indices)

            self.areaFrame.show()
        except Exception:
            self.lblArea.setText('N/A')
            self.areaFrame.show()

    def _updateLengthDisplay(self, da, ext_indices):
        def build_line_geom(ext_idx):
            pts = self.coords_matrix[ext_idx][1]
            if len(pts) < 2:
                return None
            line_pts = [QgsPoint(float(c[0]), float(c[1])) for c in pts]
            return QgsGeometry(QgsLineString(line_pts))

        current_row = self.prev_row
        seg_length = 0.0
        seg_label = ''
        if current_row >= 0 and current_row < len(self.coords_matrix):
            row_num = int(self.coords_matrix[current_row][0])
            pts = self.coords_matrix[current_row][1]
            if row_num > 0 and len(pts) >= 2:
                geom = build_line_geom(current_row)
                if geom and not geom.isEmpty():
                    seg_length = abs(da.measureLength(geom))
                    if len(ext_indices) > 1:
                        seg_label = f"Part {row_num}: "
            elif row_num < 0 and len(pts) >= 2:
                ring_pts = [QgsPoint(float(c[0]), float(c[1]))
                           for c in pts]
                line = QgsLineString(ring_pts)
                geom = QgsGeometry(line)
                if not geom.isEmpty():
                    seg_length = abs(da.measureLength(geom))
                    if len(ext_indices) > 1:
                        seg_label = f"Segment {abs(row_num)}: "

        if seg_length > 0:
            self._line_length_m = seg_length
            self.lblArea.setText(
                f'{seg_label}{self._convertLength(seg_length)}')
        else:
            self.lblArea.setText('N/A')

        total_length = 0.0
        for ei in ext_indices:
            geom = build_line_geom(ei)
            if geom and not geom.isEmpty():
                total_length += abs(da.measureLength(geom))

        if total_length > 0 and len(ext_indices) > 1:
            self._line_total_length_m = total_length
            self.areaSeparator.show()
            self.lblTotalArea.setText(
                f'Total: {self._convertLength(total_length)}')
            self.lblTotalArea.show()

    def _updateAreaCalc(self, da, ext_indices):
        def build_part_geom(ext_idx):
            ext = self.coords_matrix[ext_idx]
            if len(ext[1]) < 3:
                return None
            ext_pts = [QgsPoint(float(c[0]), float(c[1]))
                      for c in ext[1]]
            ring = QgsLineString(ext_pts)
            ring.close()
            poly = QgsPolygon()
            poly.setExteriorRing(ring)
            ext_geom = QgsGeometry(QgsPolygon(poly))

            next_ext = min(
                (i for i in ext_indices if i > ext_idx),
                default=len(self.coords_matrix))
            ring_candidates = []
            for i in range(ext_idx + 1, next_ext):
                if (int(self.coords_matrix[i][0]) < 0 and
                        len(self.coords_matrix[i][1]) >= 3):
                    ring_candidates.append(i)

            for ri in ring_candidates:
                ring_pts = [QgsPoint(float(c[0]), float(c[1]))
                           for c in self.coords_matrix[ri][1]]
                centroid = QgsPointXY(
                    sum(float(c[0])
                        for c in self.coords_matrix[ri][1])
                    / len(self.coords_matrix[ri][1]),
                    sum(float(c[1])
                        for c in self.coords_matrix[ri][1])
                    / len(self.coords_matrix[ri][1]))
                if ext_geom.contains(centroid):
                    interior = QgsLineString(ring_pts)
                    interior.close()
                    poly.addInteriorRing(interior)

            for i, entry in enumerate(self.coords_matrix):
                if (i in ring_candidates or
                        int(entry[0]) >= 0 or
                        len(entry[1]) < 3):
                    continue
                centroid = QgsPointXY(
                    sum(float(c[0]) for c in entry[1])
                    / len(entry[1]),
                    sum(float(c[1]) for c in entry[1])
                    / len(entry[1]))
                if ext_geom.contains(centroid):
                    ring_pts = [QgsPoint(float(c[0]), float(c[1]))
                               for c in entry[1]]
                    interior = QgsLineString(ring_pts)
                    interior.close()
                    poly.addInteriorRing(interior)

            return QgsGeometry(poly)

        def calc_area(geom):
            if geom is None or geom.isEmpty():
                return 0.0
            a = da.measureArea(geom)
            return a if a >= 0 else -a

        current_row = self.prev_row
        part_area   = 0.0
        part_label  = ''
        if current_row >= 0 and current_row < len(self.coords_matrix):
            if (int(self.coords_matrix[current_row][0]) > 0 and
                    len(self.coords_matrix[current_row][1]) >= 3):
                geom = build_part_geom(current_row)
                part_area = calc_area(geom)
                if len(ext_indices) > 1:
                    part_label = (
                        f"Part {int(self.coords_matrix[current_row][0])}: ")
            elif int(self.coords_matrix[current_row][0]) < 0:
                for i in range(current_row - 1, -1, -1):
                    if int(self.coords_matrix[i][0]) > 0:
                        geom = build_part_geom(i)
                        part_area = calc_area(geom)
                        if len(ext_indices) > 1:
                            part_label = (
                                f"Part "
                                f"{int(self.coords_matrix[i][0])}: ")
                        break

        if part_area > 0:
            self._area_sqm = part_area
            self.lblArea.setText(
                f'{part_label}{self._convertArea(part_area)}')
        else:
            self.lblArea.setText('N/A')

        total_area = 0.0
        for ei in ext_indices:
            if len(self.coords_matrix[ei][1]) >= 3:
                geom = build_part_geom(ei)
                total_area += calc_area(geom)

        if total_area > 0 and len(ext_indices) > 1:
            self._area_total_sqm = total_area
            self.areaSeparator.show()
            self.lblTotalArea.setText(
                f'Total: {self._convertArea(total_area)}')
            self.lblTotalArea.show()

    # ------------------------------------------------------------------
    # CRS change helpers
    # ------------------------------------------------------------------
    def _reprojectDisplayCoords(self, fromCrs, toCrs):
        if (not fromCrs or not toCrs or not fromCrs.isValid() or
                not toCrs.isValid() or fromCrs == toCrs):
            return
        if self.prev_row < 0 or not self.coords_matrix:
            return
        self.refreshCoordsMatrix(self.prev_row)
        rc = ReprojectCoordinates(fromCrs, toCrs, self.has_Z, self.has_M)
        self.coords_matrix = list(rc.reproject(self.coords_matrix, False))
        self.__part_changing = True
        self.refreshTable(self.prev_row)
        self.__part_changing = False

    def _selectCustomCrs(self):
        dlg = QgsProjectionSelectionDialog()
        dlg.setCrs(self.featureCrs if (self.featureCrs and self.featureCrs.isValid())
                    else QgsCoordinateReferenceSystem('EPSG:4326'))
        if dlg.exec():
            new_crs = dlg.crs()
            if not new_crs.isValid():
                return
            old = self.featureCrs
            self.otherCrs = new_crs
            self.featureCrs = new_crs
            self.lblCrsInfo.setText(self._crsDisplayText(new_crs))
            self.selectedCRS.emit(new_crs)
            self._reprojectDisplayCoords(old, self.featureCrs)
            self.updateAreaDisplay()

    # ------------------------------------------------------------------
    # Cell event handlers
    # ------------------------------------------------------------------
    def onCellClicked(self, newRow, newColumn):
        if self.highLighter is not None and newRow != -1:
            self.highLighter.changeCurrentVertex(newRow)

    def onCellValueChanged(self, newRow, newColumn):
        if newRow == -1 or self.__part_changing:
            return
        model = self.twPoints.model()
        for j in range(model.columnCount()):
            idx = model.index(newRow, j, QModelIndex())
            edit_val = model.data(idx, Qt.ItemDataRole.EditRole)
            if edit_val is not None:
                try:
                    model.setData(idx, float(edit_val),
                                   Qt.ItemDataRole.UserRole)
                except (ValueError, TypeError):
                    model.setData(idx, edit_val,
                                   Qt.ItemDataRole.UserRole)
        self.refreshCoordsMatrix(self.prev_row)
        self.highLightFeature(self.prev_row, newRow)
        self.updateAreaDisplay()

    def onCellChanged(self, newRow, newColumn, currentRow, currentColumn):
        if self.__ignore_changeCellEvent:
            self.__ignore_changeCellEvent = False
            return
        if (currentRow == -1 or currentColumn == -1 or
                self.__part_changing or self.valueChecker is None):
            return
        if self.highLighter and newRow != -1 and not self.__part_changing:
            self.highLighter.changeCurrentVertex(newRow)

        theCell  = self.twPoints.item(currentRow, currentColumn)
        theValue = self.valueChecker.checkCellValue(theCell)

        if theValue == CellValue.ValueFloat:
            if theCell.foreground() == QBrush(QColor(255, 0, 0)):
                theCell.setForeground(QBrush(QColor(0, 0, 0)))
            if self.twPoints.rowCount() == currentRow + 1:
                if (self.valueChecker.isRowValid(currentRow) and
                        (self.isMultiType or
                         self.layertype != _PointGeometry)):
                    self.twPoints.setRowCount(self.twPoints.rowCount())
                    self.twPoints.insertRow(self.twPoints.rowCount())
                    self.__ignore_changeCellEvent = True
                    self.twPoints.setCurrentCell(
                        self.twPoints.rowCount() - 1, 0)
                    self.twPoints.edit(self.twPoints.currentIndex())

        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(
            self.valueChecker.setOkButtonState())
        self.updateAreaDisplay()

        if theValue in (CellValue.ValueNotFloat, CellValue.ValueNone):
            if theValue == CellValue.ValueNotFloat:
                theCell.setForeground(QBrush(QColor(231, 76, 60)))

    # ------------------------------------------------------------------
    # Copy / paste / swap
    # ------------------------------------------------------------------
    def copyButtonClicked(self):
        model = self.twPoints.model()
        droprow = 1 if self.valueChecker.isLastRowEmpty() else 0
        selectedCells = sorted(
            self.twPoints.selectionModel().selectedIndexes())
        textstring = ''

        if len(selectedCells) > 1:
            for i in range(model.rowCount() - droprow):
                current = ''
                for j in range(model.columnCount()):
                    idx = model.index(i, j, QModelIndex())
                    if idx in selectedCells:
                        user_val = model.data(idx, Qt.ItemDataRole.UserRole)
                        if user_val is not None:
                            current += str(user_val) + '\t'
                        else:
                            current += str(model.data(idx, Qt.ItemDataRole.EditRole)) + '\t'
                if current:
                    textstring += current[:-1] + '\n'
        else:
            for i in range(model.rowCount() - droprow):
                for j in range(model.columnCount()):
                    idx = model.index(i, j, QModelIndex())
                    user_val = model.data(idx, Qt.ItemDataRole.UserRole)
                    if user_val is not None:
                        textstring += str(user_val) + '\t'
                    else:
                        textstring += str(model.data(idx, Qt.ItemDataRole.EditRole)) + '\t'
                textstring = textstring[:-1] + '\n'

        QApplication.clipboard().setText(textstring)

    def pasteButtonClicked(self):
        model      = self.twPoints.model()
        pasteStr   = QApplication.clipboard().text()
        rows       = [r for r in pasteStr.split('\n')
                      if r.replace('\t', '') != '']
        numRows    = len(rows)
        if numRows <= 0:
            return

        numCols        = rows[0].count('\t') + 1
        decimalDivider = self.locale().decimalPoint()
        values         = []

        for row in rows:
            if decimalDivider == '.' and ',' in row:
                row = row.replace(',', '.')
            elif decimalDivider == ',' and '.' in row:
                row = row.replace('.', ',')
            cols = row.split('\t')
            if model.columnCount() > numCols:
                cols.extend('0' for _ in range(
                    model.columnCount() - numCols))
            values.append(cols)

        selectedRows  = sorted(
            self.twPoints.selectionModel().selectedRows())
        selectedCells = sorted(
            self.twPoints.selectionModel().selectedIndexes())

        if len(selectedCells) < 2 or len(selectedRows) == 1:
            if len(selectedRows) == 1:
                upperRow = selectedRows[0].row()
                model.insertRows(selectedRows[0].row(), numRows)
            else:
                upperRow = model.rowCount() - 1
                model.insertRows(model.rowCount(), numRows)

            model.blockSignals(True)
            for i, l_tuple in enumerate(values):
                colRange = min(len(l_tuple), model.columnCount())
                for j in range(colRange):
                    idx = model.index(upperRow + i, j, QModelIndex())
                    model.setData(idx, l_tuple[j])
                    try:
                        model.setData(idx, float(l_tuple[j]),
                                       Qt.ItemDataRole.UserRole)
                    except (ValueError, TypeError):
                        pass
            model.blockSignals(False)
        else:
            model.blockSignals(True)
            i_values = 0
            for i in range(model.rowCount()):
                j_values = 0
                for j in range(model.columnCount()):
                    idx = model.index(i, j, QModelIndex())
                    if idx in selectedCells:
                        model.setData(idx, values[i_values][j_values])
                        try:
                            model.setData(idx, float(values[i_values][j_values]),
                                           Qt.ItemDataRole.UserRole)
                        except (ValueError, TypeError):
                            pass
                        j_values += 1
                if j_values > 0:
                    i_values += 1
                if i_values > len(values) - 1:
                    break
            model.blockSignals(False)

        self.refreshCoordsMatrix(self.prev_row)
        model.dataChanged.emit(
            model.index(0, 0, QModelIndex()),
            model.index(model.rowCount() - 1,
                        model.columnCount() - 1, QModelIndex()))
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(
            self.valueChecker.setOkButtonState())
        self.updateAreaDisplay()

    def swapButtonClicked(self):
        model = self.twPoints.model()
        self.__part_changing = True
        for i in range(model.rowCount()):
            idx1 = model.index(i, 0, QModelIndex())
            idx2 = model.index(i, 1, QModelIndex())
            tmp  = model.data(idx1, Qt.ItemDataRole.EditRole)
            model.setData(idx1, model.data(idx2, Qt.ItemDataRole.EditRole), Qt.ItemDataRole.EditRole)
            model.setData(idx2, tmp, Qt.ItemDataRole.EditRole)
            tmp_user = model.data(idx1, Qt.ItemDataRole.UserRole)
            model.setData(idx1, model.data(idx2, Qt.ItemDataRole.UserRole), Qt.ItemDataRole.UserRole)
            model.setData(idx2, tmp_user, Qt.ItemDataRole.UserRole)
        self.__part_changing = False

        for part in self.coords_matrix:
            for coord in part[1]:
                coord[0], coord[1] = coord[1], coord[0]

        self.highLightFeature(self.prev_row, 0)
        self.updateAreaDisplay()

    # ------------------------------------------------------------------
    # Row add / remove
    # ------------------------------------------------------------------
    def addRowsButtonClicked(self):
        model        = self.twPoints.model()
        selectedRows = sorted(
            self.twPoints.selectionModel().selectedRows())
        if len(selectedRows) == 0:
            if not self.valueChecker.isLastRowEmpty():
                model.insertRows(model.rowCount(), 1)
            currentRow = model.rowCount() - 1
        else:
            model.insertRows(selectedRows[0].row(), 1)
            currentRow = selectedRows[0].row()
        self.__ignore_changeCellEvent = True
        self.twPoints.setCurrentCell(currentRow, 0)
        self.twPoints.edit(self.twPoints.currentIndex())

    def removeRowsButtonClicked(self):
        model        = self.twPoints.model()
        selectedRows = self.twPoints.selectionModel().selectedRows()
        if len(selectedRows) == 0:
            reply = QMessageBox.warning(
                self.window(),
                self.translate_str('Warning'),
                self.translate_str('Remove all rows?'),
                QMessageBox.Ok | QMessageBox.Cancel)
            if reply == QMessageBox.Ok:
                model.removeRows(0, model.rowCount())
                model.insertRows(0, 1)
        else:
            indexes = [QPersistentModelIndex(i) for i in selectedRows]
            for idx in indexes:
                model.removeRow(idx.row())
            if model.rowCount() == 0:
                model.insertRows(0, 1)
            elif not self.valueChecker.isLastRowEmpty():
                model.insertRows(model.rowCount(), 1)

        self.refreshCoordsMatrix(self.prev_row)
        self.highLightFeature(self.prev_row, 0)
        self.updateAreaDisplay()

    # ------------------------------------------------------------------
    # Part / ring add / remove
    # ------------------------------------------------------------------
    def addPartButtonClicked(self):
        self.__contursCount += 1
        self.listParts.addItem(str(self.__contursCount))
        self.coords_matrix.append([self.__contursCount, []])
        self.updateAreaDisplay()

    def addRingButtonClicked(self):
        self.__ringsCount += 1
        insert_pos = self.listParts.currentRow() + 1
        self.listParts.insertItem(insert_pos, str(-self.__ringsCount))
        self.coords_matrix.insert(insert_pos, [-self.__ringsCount, []])
        self.updateAreaDisplay()

    def removePartButtonClicked(self):
        l_currentRow = self.listParts.currentRow()
        if l_currentRow == -1:
            QMessageBox.warning(
                self.window(),
                self.translate_str('Warning'),
                self.translate_str('Select part before delete'))
            return

        reply = QMessageBox.question(
            self.window(),
            self.translate_str('Confirm delete'),
            self.translate_str('Are you sure to delete this part?'),
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        deletedPartNumber = int(self.listParts.item(l_currentRow).text())
        self.__deletedPart = {
            'row': l_currentRow,
            'number': deletedPartNumber,
            'coords': list(self.coords_matrix[l_currentRow])
        }
        self.toolButtonUndoPart.setEnabled(True)

        self.prev_row     = -1

        if deletedPartNumber > 0:
            self.__contursCount -= 1
        else:
            self.__ringsCount -= 1

        self.coords_matrix.remove(self.coords_matrix[l_currentRow])
        self.listParts.removeItemWidget(
            self.listParts.takeItem(l_currentRow))

        for i in range(self.listParts.count()):
            cur = int(self.listParts.item(i).text())
            if deletedPartNumber > 0:
                if deletedPartNumber < cur:
                    self.listParts.item(i).setData(0, str(cur - 1))
                    self.coords_matrix[i][0] = cur - 1
            else:
                if deletedPartNumber > cur:
                    self.listParts.item(i).setData(0, str(cur + 1))
                    self.coords_matrix[i][0] = cur + 1

        if self.__contursCount == 0:
            self.addPartButtonClicked()
            self.listParts.setCurrentRow(0)
            self.prev_row = 0
        else:
            self.prev_row = -1
        self.updateAreaDisplay()

    def undoPartButtonClicked(self):
        if self.__deletedPart is None:
            return
        data = self.__deletedPart
        self.__deletedPart = None
        self.toolButtonUndoPart.setEnabled(False)

        self.coords_matrix.insert(data['row'], list(data['coords']))

        contour_num = 1
        ring_num = 1
        for i in range(len(self.coords_matrix)):
            if int(self.coords_matrix[i][0]) > 0:
                self.coords_matrix[i][0] = contour_num
                contour_num += 1
            else:
                self.coords_matrix[i][0] = -ring_num
                ring_num += 1

        self.__contursCount = contour_num - 1
        self.__ringsCount = ring_num - 1

        model = self.listParts.model()
        model.removeRows(0, model.rowCount())
        model.insertRows(0, len(self.coords_matrix))
        model.blockSignals(True)
        for i in range(len(self.coords_matrix)):
            model.setData(model.index(i, 0), self.coords_matrix[i][0])
        model.blockSignals(False)

        self.listParts.setCurrentRow(data['row'])
        self.prev_row = data['row']
        self.updateAreaDisplay()

    # ------------------------------------------------------------------
    # Internal model refresh
    # ------------------------------------------------------------------
    def refreshCoordsMatrix(self, part_num):
        self.coords_matrix[part_num][1].clear()
        model     = self.twPoints.model()
        skipLast  = 1 if (self.valueChecker.isLastRowEmpty() or not
                          self.valueChecker.isRowValid(
                              model.rowCount() - 1)) else 0
        for i in range(model.rowCount() - skipLast):
            row = []
            for j in range(model.columnCount()):
                cv = self.valueChecker.checkModelValue(i, j)
                if cv == CellValue.ValueFloat:
                    user_val = model.data(
                        model.index(i, j, QModelIndex()),
                        Qt.ItemDataRole.UserRole)
                    if user_val is not None:
                        row.append(user_val)
                    else:
                        row.append(model.data(
                            model.index(i, j, QModelIndex()),
                            Qt.ItemDataRole.EditRole))
                else:
                    row.append('NaN')
            self.coords_matrix[part_num][1].append(list(row))

    def refreshTable(self, part_num):
        if -1 < part_num < len(self.coords_matrix):
            model      = self.twPoints.model()
            coordslist = self.coords_matrix[part_num][1]
            model.removeRows(0, model.rowCount())
            model.insertRows(0, len(coordslist) + 1)
            model.blockSignals(True)
            for i, row in enumerate(coordslist):
                for j in range(model.columnCount()):
                    val = row[j]
                    if isinstance(val, float):
                        model.setData(
                            model.index(i, j, QModelIndex()), '%.2f' % val)
                        model.setData(
                            model.index(i, j, QModelIndex()), val,
                            Qt.ItemDataRole.UserRole)
                    else:
                        model.setData(
                            model.index(i, j, QModelIndex()), str(val))
            model.blockSignals(False)
            model.dataChanged.emit(
                model.index(0, 0, QModelIndex()),
                model.index(model.rowCount() - 1,
                            model.columnCount() - 1, QModelIndex()))

    def partChanged(self, currentRow):
        self.__part_changing = True
        if self.prev_row != -1:
            self.refreshCoordsMatrix(self.prev_row)
        self.refreshTable(currentRow)
        self.prev_row = currentRow
        self.highLightFeature(currentRow, 0)
        self.__part_changing = False
        self.updateAreaDisplay()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def saveDialogSettings(self):
        if self.featureCrs and self.featureCrs.isValid():
            recent = QSettings().value(
                '/Plugin-VectorelDigitizerPro/RecentCrsList', [], type=list)
            wkt = self.featureCrs.toWkt()
            if wkt in recent:
                recent.remove(wkt)
            recent.insert(0, wkt)
            QSettings().setValue(
                '/Plugin-VectorelDigitizerPro/RecentCrsList', recent[:10])

            QSettings().setValue(
                '/Plugin-VectorelDigitizerPro/LastCrsWkt',
                self.featureCrs.toWkt())

    # ------------------------------------------------------------------
    # OK / Finish
    # ------------------------------------------------------------------
    def onOK(self):
        if self.prev_row != -1:
            self.refreshCoordsMatrix(self.prev_row)
        if not self.valueChecker.checkCoordsMatrix(self.coords_matrix):
            return
        if not self.valueChecker.isCurrentPartValid(True):
            QMessageBox.critical(
                self.window(),
                self.translate_str('Values error'),
                self.translate_str('Current part contains incorrect values'))
            return
        self.accept()
        self.saveDialogSettings()
        self.returnCoordList.emit(self.coords_matrix)

    def onFinished(self, result):
        if self.highLighter is not None:
            self.highLighter.removeHighlight()
            self.highLighter = None
