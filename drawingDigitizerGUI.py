# -*- coding: utf-8 -*-


from qgis.PyQt.QtCore import Qt, pyqtSignal, QCoreApplication, QSize, QTimer
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSizePolicy, QWidget,
    QComboBox, QToolButton, QApplication)
from qgis.PyQt.QtGui import QColor, QFont, QIcon
from qgis.core import (QgsCoordinateReferenceSystem, QgsDistanceArea,
                       QgsProject, QgsPointXY, QgsPoint, QgsLineString,
                       QgsPolygon, QgsGeometry, QgsCoordinateTransform,
                       QgsSettings, QgsApplication)
from qgis.gui import QgsProjectionSelectionDialog
from qgis.PyQt.QtCore import QSettings

import logging
import os

_PLUGIN_DIR = os.path.dirname(__file__)


def _fmtNum(val, decimals=6):
    s = '{:,.{d}f}'.format(val, d=decimals)
    return s.replace('.', '\x00').replace(',', '.').replace('\x00', ',')


def _parseNum(text):
    return float(text.replace('.', '').replace(',', '.'))

# ---------------------------------------------------------------------------
# Full stylesheet for DrawingDigitizerGUI
# ---------------------------------------------------------------------------
_DRAW_STYLE = """
QDialog {
    background-color: #f5f6fa;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 9pt;
}

/* Header banner */
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

/* Group boxes */
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

/* Instruction label */
#instrLabel {
    color: #5d6d7e;
    font-style: italic;
    padding: 4px 6px;
    background: #eaf2fb;
    border-radius: 4px;
    border-left: 3px solid #2980b9;
}

/* Status bar */
#statusFrame {
    background-color: #eaf2fb;
    border: 1px solid #aed6f1;
    border-radius: 4px;
    padding: 2px 6px;
}
#pointCountLabel {
    font-weight: bold;
    color: #1a5276;
    font-size: 9pt;
}

/* Coordinate table */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #eaf2fb;
    gridline-color: #d5d8dc;
    border: 1px solid #c8d6e5;
    border-radius: 4px;
    selection-background-color: #2980b9;
    selection-color: white;
    font-size: 9pt;
}
QTableWidget::item { padding: 2px 5px; }
QTableWidget::item:selected { background-color: #2980b9; color: white; }
QHeaderView::section {
    background-color: #2c3e50;
    color: #ecf0f1;
    font-weight: bold;
    font-size: 9pt;
    padding: 4px 5px;
    border: none;
    border-right: 1px solid #3d5166;
}

/* Area frame */
#areaFrame {
    background: #eafaf1;
    border: 1px solid #a9dfbf;
    border-radius: 5px;
    padding: 4px;
}
#areaHaLabel {
    font-weight: bold;
    font-size: 11pt;
    color: #27ae60;
}

/* Length frame */
#lengthFrame {
    background: #eaf2fb;
    border: 1px solid #aed6f1;
    border-radius: 5px;
    padding: 4px;
}
#lengthLabel {
    font-weight: bold;
    font-size: 11pt;
    color: #1a5276;
}

/* Action buttons row */
QPushButton#btnUndo {
    background-color: #e67e22;
    color: white; border: none;
    border-radius: 5px; padding: 5px 10px;
    font-weight: bold; font-size: 9pt; min-height: 22px;
}
QPushButton#btnUndo:hover   { background-color: #f39c12; }
QPushButton#btnUndo:pressed { background-color: #ca6f1e; }
QPushButton#btnUndo:disabled { background-color: #bdc3c7; color: #7f8c8d; }

QPushButton#btnEnd {
    background-color: #2980b9;
    color: white; border: none;
    border-radius: 5px; padding: 5px 10px;
    font-weight: bold; font-size: 9pt; min-height: 22px;
}
QPushButton#btnEnd:hover   { background-color: #3498db; }
QPushButton#btnEnd:pressed { background-color: #1a6fa3; }
QPushButton#btnEnd:disabled { background-color: #bdc3c7; color: #7f8c8d; }

QPushButton#btnFinish {
    background-color: #27ae60;
    color: white; border: none;
    border-radius: 5px; padding: 5px 14px;
    font-weight: bold; font-size: 10pt; min-height: 26px;
}
QPushButton#btnFinish:hover   { background-color: #2ecc71; }
QPushButton#btnFinish:pressed { background-color: #1e8449; }
QPushButton#btnFinish:disabled { background-color: #bdc3c7; color: #7f8c8d; }

QPushButton#btnRestart {
    background-color: #ffffff;
    color: #c0392b;
    border: 1px solid #c0392b;
    border-radius: 5px; padding: 4px 10px;
    font-weight: bold; font-size: 9pt;
}
QPushButton#btnRestart:hover {
    background-color: #c0392b; color: white;
}

QPushButton#btnClose {
    background-color: #7f8c8d;
    color: white; border: none;
    border-radius: 5px; padding: 4px 10px;
    font-weight: bold; font-size: 9pt;
}
QPushButton#btnClose:hover { background-color: #95a5a6; }

/* CRS select button */
QPushButton#btnSelectCrs {
    background-color: #2c3e50;
    color: white; border: none;
    border-radius: 4px; padding: 3px 8px; font-size: 9pt;
}
QPushButton#btnSelectCrs:hover { background-color: #3d5166; }

QLabel#crsNameLabel {
    color: #2980b9;
    font-style: italic;
    font-size: 9pt;
}

/* Scroll bars */
QScrollBar:vertical {
    background: #f0f3f4; width: 10px; border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #aab7b8; border-radius: 5px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #7f8c8d; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
"""


class DrawingDigitizerGUI(QDialog):

    finishedDrawing  = pyqtSignal(list)
    coordCrsChanged  = pyqtSignal(object)
    restartRequested = pyqtSignal()
    undoRequested    = pyqtSignal()
    pointEdited      = pyqtSignal(int, object)
    drawingEnded     = pyqtSignal()
    vertexSelected   = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Vectorel Digitizer Pro – Drawing Digitizer')
        self.setModal(False)
        self.resize(370, 540)
        self.setMinimumWidth(340)

        self.featureCrs  = None
        self.otherCrs    = None
        self.projectCrs  = None
        self.points      = []
        self._previewPt  = None
        self._drawingEnded = False
        self.mapCanvas   = None
        self.geomType    = 'polygon'

        self._cachedTransformForward = None
        self._cachedTransformReverse = None
        self._cachedTransformProjectCrs = None
        self._cachedTransformFeatureCrs = None

        self._areaTimer = QTimer()
        self._areaTimer.setSingleShot(True)
        self._areaTimer.setInterval(50)
        self._areaTimer.timeout.connect(self._doDeferredAreaUpdate)
        self._pendingAreaPreview = False

        self._setupUi()
        self._connectSignals()
        self.setStyleSheet(_DRAW_STYLE)

    # ------------------------------------------------------------------
    def _setupUi(self):
        root = QVBoxLayout(self)
        root.setSpacing(7)
        root.setContentsMargins(8, 8, 8, 8)

        # ── Header banner ──────────────────────────────────────────────
        hdrFrame = QFrame()
        hdrFrame.setObjectName('headerFrame')
        hdrLayout = QVBoxLayout(hdrFrame)
        hdrLayout.setContentsMargins(10, 6, 10, 6)
        hdrLayout.setSpacing(1)

        titleLbl = QLabel('Drawing Digitizer')
        titleLbl.setObjectName('headerTitle')
        subLbl   = QLabel('Click the map to add polygon vertices')
        subLbl.setObjectName('headerSub')
        hdrLayout.addWidget(titleLbl)
        hdrLayout.addWidget(subLbl)
        root.addWidget(hdrFrame)

        # ── CRS group ──────────────────────────────────────────────────
        crsGroup  = QGroupBox('CRS Selection')
        crsLayout = QVBoxLayout(crsGroup)
        crsLayout.setContentsMargins(8, 8, 8, 8)
        crsLayout.setSpacing(4)

        crsRow = QHBoxLayout()
        self.lblCrsInfo = QLabel('CRS not selected')
        self.lblCrsInfo.setMinimumHeight(24)
        crsRow.addWidget(self.lblCrsInfo, 1)
        self.tbSelectCrs = QToolButton()
        self.tbSelectCrs.setMinimumSize(28, 28)
        self.tbSelectCrs.setMaximumSize(28, 28)
        self.tbSelectCrs.setIcon(
            QgsApplication.getThemeIcon('mIconProjectionEnabled.svg'))
        self.tbSelectCrs.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.tbSelectCrs.setIconSize(QSize(20, 20))
        self.tbSelectCrs.setToolTip('Select CRS')
        crsRow.addWidget(self.tbSelectCrs)
        crsLayout.addLayout(crsRow)
        root.addWidget(crsGroup)

        # ── Instruction ────────────────────────────────────────────────
        self._instrLbl = QLabel(
            'Left-click to add vertices  ·  '
            'Double-click or press Enter to finish  ·  '
            'Esc to cancel\n'
            'Hold Shift to temporarily disable snap')
        self._instrLbl.setObjectName('instrLabel')
        self._instrLbl.setWordWrap(True)
        root.addWidget(self._instrLbl)

        # ── Status bar ─────────────────────────────────────────────────
        statusFrame = QFrame()
        statusFrame.setObjectName('statusFrame')
        statusRow = QHBoxLayout(statusFrame)
        statusRow.setContentsMargins(4, 2, 4, 2)
        self.lblPointCount = QLabel('Vertices: 0')
        self.lblPointCount.setObjectName('pointCountLabel')
        statusRow.addWidget(self.lblPointCount)
        statusRow.addStretch()
        root.addWidget(statusFrame)

        # ── Table toolbar (Copy/Paste/AddRow/DelRow) ───────────────────
        tblToolbar = QFrame()
        tblToolbar.setObjectName('tblToolbar')
        tblToolbar.setStyleSheet(
            'QFrame#tblToolbar { background: transparent; }')
        tbLayout = QHBoxLayout(tblToolbar)
        tbLayout.setContentsMargins(0, 0, 0, 0)
        tbLayout.setSpacing(2)

        _img_dir = os.path.join(_PLUGIN_DIR, 'images')

        def _iconFile(name):
            p = os.path.join(_img_dir, name)
            if os.path.isfile(p):
                return QIcon(p)
            return QIcon()

        self.toolButtonCopy = QToolButton()
        self.toolButtonCopy.setMinimumSize(QSize(32, 32))
        self.toolButtonCopy.setMaximumSize(QSize(32, 32))
        self.toolButtonCopy.setIcon(_iconFile('mActionEditCopy.svg'))
        self.toolButtonCopy.setIconSize(QSize(24, 24))
        self.toolButtonCopy.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolButtonCopy.setToolTip('Copy coordinates to clipboard')

        self.toolButtonPaste = QToolButton()
        self.toolButtonPaste.setMinimumSize(QSize(32, 32))
        self.toolButtonPaste.setMaximumSize(QSize(32, 32))
        self.toolButtonPaste.setIcon(_iconFile('mActionEditPaste.svg'))
        self.toolButtonPaste.setIconSize(QSize(24, 24))
        self.toolButtonPaste.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolButtonPaste.setToolTip('Paste coordinates from clipboard')

        self.toolButtonSwap = QToolButton()
        self.toolButtonSwap.setMinimumSize(QSize(32, 32))
        self.toolButtonSwap.setMaximumSize(QSize(32, 32))
        self.toolButtonSwap.setIcon(_iconFile('swap.svg'))
        self.toolButtonSwap.setIconSize(QSize(24, 24))
        self.toolButtonSwap.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolButtonSwap.setToolTip('Swap X and Y columns')

        self.toolButtonAddRows = QToolButton()
        self.toolButtonAddRows.setMinimumSize(QSize(32, 32))
        self.toolButtonAddRows.setMaximumSize(QSize(32, 32))
        self.toolButtonAddRows.setIcon(_iconFile('mActionNewTableRow.svg'))
        self.toolButtonAddRows.setIconSize(QSize(24, 24))
        self.toolButtonAddRows.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolButtonAddRows.setToolTip('Add row')

        self.toolButtonRemoveRows = QToolButton()
        self.toolButtonRemoveRows.setMinimumSize(QSize(32, 32))
        self.toolButtonRemoveRows.setMaximumSize(QSize(32, 32))
        self.toolButtonRemoveRows.setIcon(_iconFile('mActionDeleteTableRow.svg'))
        self.toolButtonRemoveRows.setIconSize(QSize(24, 24))
        self.toolButtonRemoveRows.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolButtonRemoveRows.setToolTip('Delete selected rows')

        tbLayout.addWidget(self.toolButtonCopy)
        tbLayout.addWidget(self.toolButtonPaste)
        tbLayout.addWidget(self.toolButtonSwap)
        tbLayout.addWidget(self.toolButtonAddRows)
        tbLayout.addWidget(self.toolButtonRemoveRows)
        tbLayout.addStretch()
        root.addWidget(tblToolbar)

        # ── Coordinate table ───────────────────────────────────────────
        self.tblCoords = QTableWidget(0, 3)
        self.tblCoords.setHorizontalHeaderLabels(['#', 'X', 'Y'])
        self.tblCoords.setMaximumHeight(160)
        self.tblCoords.setMinimumHeight(90)
        self.tblCoords.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents)
        self.tblCoords.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        self.tblCoords.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch)
        self.tblCoords.verticalHeader().hide()
        self.tblCoords.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblCoords.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.tblCoords.setAlternatingRowColors(True)
        f = self.tblCoords.font()
        f.setPointSize(9)
        self.tblCoords.setFont(f)
        root.addWidget(self.tblCoords)

        # ── Area display ───────────────────────────────────────────────
        self._area_sqm = 0.0

        self.areaFrame = QFrame()
        self.areaFrame.setObjectName('areaFrame')
        areaLayout = QVBoxLayout(self.areaFrame)
        areaLayout.setContentsMargins(8, 6, 8, 6)
        areaLayout.setSpacing(1)

        lblTitle = QLabel('Calculated Area')
        lblTitle.setStyleSheet(
            'font-weight: bold; font-size: 11pt; color: #1a5c32;')
        areaLayout.addWidget(lblTitle)

        unitRow = QHBoxLayout()
        unitRow.setSpacing(4)
        lblUnit = QLabel('Unit:')
        lblUnit.setStyleSheet('font-size: 9pt; color: #27ae60;')
        self.cbAreaUnit = QComboBox()
        self.cbAreaUnit.addItems([
            'Hectares', 'Acres', 'Square Feet',
            'Square Meters', 'Square Kilometers', 'Square Miles'])
        self.cbAreaUnit.setStyleSheet('font-size: 9pt; color: #27ae60;')
        self.cbAreaUnit.currentIndexChanged.connect(self._onAreaUnitChanged)
        unitRow.addWidget(lblUnit)
        unitRow.addWidget(self.cbAreaUnit, 1)
        areaLayout.addLayout(unitRow)

        self.lblArea = QLabel('Area: —')
        self.lblArea.setObjectName('areaHaLabel')
        areaLayout.addWidget(self.lblArea)
        self.areaFrame.hide()
        root.addWidget(self.areaFrame)

        # ── Length display ─────────────────────────────────────────────
        self._length_m = 0.0

        self.lengthFrame = QFrame()
        self.lengthFrame.setObjectName('lengthFrame')
        lengthLayout = QVBoxLayout(self.lengthFrame)
        lengthLayout.setContentsMargins(8, 6, 8, 6)
        lengthLayout.setSpacing(1)

        lblLenTitle = QLabel('Calculated Length')
        lblLenTitle.setStyleSheet(
            'font-weight: bold; font-size: 11pt; color: #1a5276;')
        lengthLayout.addWidget(lblLenTitle)

        lenUnitRow = QHBoxLayout()
        lenUnitRow.setSpacing(4)
        lblLenUnit = QLabel('Unit:')
        lblLenUnit.setStyleSheet('font-size: 9pt; color: #2980b9;')
        self.cbLengthUnit = QComboBox()
        self.cbLengthUnit.addItems([
            'Meters', 'Kilometers', 'Feet', 'Miles', 'Yards'])
        self.cbLengthUnit.setStyleSheet('font-size: 9pt; color: #2980b9;')
        self.cbLengthUnit.currentIndexChanged.connect(self._onLengthUnitChanged)
        lenUnitRow.addWidget(lblLenUnit)
        lenUnitRow.addWidget(self.cbLengthUnit, 1)
        lengthLayout.addLayout(lenUnitRow)

        self.lblLength = QLabel('Length: —')
        self.lblLength.setObjectName('lengthLabel')
        lengthLayout.addWidget(self.lblLength)
        self.lengthFrame.hide()
        root.addWidget(self.lengthFrame)

        root.addStretch()

        # ── Action buttons ─────────────────────────────────────────────
        actionRow = QHBoxLayout()
        actionRow.setSpacing(6)

        self.btnUndo = QPushButton('↩  Undo')
        self.btnUndo.setObjectName('btnUndo')
        self.btnUndo.setToolTip('Remove last vertex (Backspace)')

        self.btnEnd = QPushButton('⏹  End Drawing')
        self.btnEnd.setObjectName('btnEnd')
        self.btnEnd.setToolTip('Close polygon without finishing the dialog')

        self.btnFinish = QPushButton('✔  Save Feature')
        self.btnFinish.setObjectName('btnFinish')
        self.btnFinish.setToolTip('Save as a new layer feature (Enter)')

        actionRow.addWidget(self.btnUndo)
        actionRow.addWidget(self.btnEnd)
        actionRow.addWidget(self.btnFinish, 1)
        root.addLayout(actionRow)

        # ── Bottom buttons ─────────────────────────────────────────────
        bottomRow = QHBoxLayout()
        bottomRow.setSpacing(6)

        self.btnRestart = QPushButton('🔄  Restart')
        self.btnRestart.setObjectName('btnRestart')
        self.btnRestart.setToolTip('Clear all points and start over')

        self.btnClose = QPushButton('✕  Close')
        self.btnClose.setObjectName('btnClose')
        self.btnClose.setToolTip('Close dialog and discard current drawing')

        bottomRow.addWidget(self.btnRestart)
        bottomRow.addStretch()
        bottomRow.addWidget(self.btnClose)
        root.addLayout(bottomRow)

    # ------------------------------------------------------------------
    def _connectSignals(self):
        self.tbSelectCrs.clicked.connect(self._selectCustomCrs)

        self.tblCoords.cellChanged.connect(self._onCellEdited)
        self.tblCoords.cellClicked.connect(self._onCellClicked)

        self.toolButtonCopy.clicked.connect(self._copyCoords)
        self.toolButtonPaste.clicked.connect(self._pasteCoords)
        self.toolButtonSwap.clicked.connect(self._swapXY)
        self.toolButtonAddRows.clicked.connect(self._addRow)
        self.toolButtonRemoveRows.clicked.connect(self._deleteRow)

        self.btnUndo.clicked.connect(self.undoPoint)
        self.btnEnd.clicked.connect(self._onEndDrawing)
        self.btnFinish.clicked.connect(self.finishDrawing)
        self.btnRestart.clicked.connect(self.restartDrawing)
        self.btnClose.clicked.connect(self.reject)

    # ------------------------------------------------------------------
    def setCanvas(self, canvas):
        self.mapCanvas   = canvas
        self.projectCrs  = canvas.mapSettings().destinationCrs()

        dlg = QgsProjectionSelectionDialog()
        layer_crs = canvas.currentLayer().crs()
        if layer_crs.isValid():
            dlg.setCrs(layer_crs)
        saved_wkt = QSettings().value(
            '/Plugin-VectorelDigitizerPro/LastCrsWkt', '', type=str)
        if saved_wkt:
            crs = QgsCoordinateReferenceSystem.fromWkt(saved_wkt)
            if crs.isValid():
                dlg.setCrs(crs)
        if dlg.exec():
            self.featureCrs = dlg.crs()
        elif layer_crs.isValid():
            self.featureCrs = layer_crs
        self._invalidateTransformCache()
        self.lblCrsInfo.setText(self._crsDisplayText(self.featureCrs))
        self.coordCrsChanged.emit(self.featureCrs)

    def setGeometryType(self, geomType):
        self.geomType = geomType
        if geomType == 'point':
            self._instrLbl.setText(
                'Left-click on the map to place a point  ·  '
                'Click again to reposition  ·  '
                'Save Feature to confirm\n'
                'Hold Shift to temporarily disable snap')
            self.areaFrame.hide()
            self.lengthFrame.hide()
            self.btnEnd.setEnabled(False)
            self.btnEnd.setToolTip('Not available for point geometry')
            self.btnUndo.setEnabled(True)
        elif geomType == 'line':
            self._instrLbl.setText(
                'Left-click to add vertices  ·  '
                'Double-click or press Enter to finish  ·  '
                'Esc to cancel\n'
                'Hold Shift to temporarily disable snap')
            self.areaFrame.hide()
            self.lengthFrame.show()
            self.btnEnd.setEnabled(True)
            self.btnEnd.setToolTip('Finish line without closing')
            self.btnUndo.setEnabled(True)
        else:
            self._instrLbl.setText(
                'Left-click to add vertices  ·  '
                'Double-click or press Enter to finish  ·  '
                'Esc to cancel\n'
                'Hold Shift to temporarily disable snap')
            self.areaFrame.show()
            self.lengthFrame.hide()
            self.btnEnd.setEnabled(True)
            self.btnEnd.setToolTip('Close polygon without finishing the dialog')
            self.btnUndo.setEnabled(True)

    def _minPoints(self):
        if self.geomType == 'point':
            return 1
        elif self.geomType == 'line':
            return 2
        return 3

    # ------------------------------------------------------------------
    # CRS selection
    # ------------------------------------------------------------------
    def _crsDisplayText(self, crs):
        desc = crs.description()
        auth = crs.authid()
        if desc:
            return f'{desc} ({auth})'
        return auth

    def _selectCustomCrs(self):
        dlg = QgsProjectionSelectionDialog()
        dlg.setCrs(self.featureCrs if (self.featureCrs and self.featureCrs.isValid())
                   else QgsCoordinateReferenceSystem('EPSG:4326'))
        if dlg.exec():
            new_crs = dlg.crs()
            if not new_crs.isValid():
                return
            old = self.featureCrs
            self.featureCrs = new_crs
            self._invalidateTransformCache()
            self.lblCrsInfo.setText(self._crsDisplayText(new_crs))
            self.coordCrsChanged.emit(new_crs)
            if old is not None and old.isValid() and old != new_crs:
                self._updateCoordList()
                self._updateArea()
                self._updateLength()

    # ------------------------------------------------------------------
    # Point management
    # ------------------------------------------------------------------
    def addPoint(self, point):
        if self.geomType == 'point':
            self.points = [point]
            self.lblPointCount.setText('Point set')
            self._updateCoordList()
            self._updateArea()
            self._updateLength()
            self.vertexSelected.emit(0)
        else:
            self.points.append(point)
            self.lblPointCount.setText('Vertices: %d' % len(self.points))
            self._updateCoordList(incremental=True)
            self._updateArea()
            self._updateLength()
            self.vertexSelected.emit(len(self.points) - 1)

    def undoPoint(self):
        if self.geomType == 'point':
            self.points.clear()
            self.lblPointCount.setText('No point selected')
            self._updateCoordList()
            self._updateArea()
            self.undoRequested.emit()
            return
        if self.points:
            self.points.pop()
            self.lblPointCount.setText('Vertices: %d' % len(self.points))
            self._updateCoordList()
            self._updateArea()
            self._updateLength()
            self.undoRequested.emit()
            if self.points:
                self.vertexSelected.emit(len(self.points) - 1)
            if self._drawingEnded:
                self._drawingEnded = False
                if self.points:
                    self.setPreviewPoint(self.points[-1])

    def sortCoordinatesClockwise(self):
        if len(self.points) < 3:
            return

        pts_fmt = []
        for pt in self.points:
            x, y = self._formatCoords(pt)
            pts_fmt.append((x, y))

        xs = [p[0] for p in pts_fmt]
        ys = [p[1] for p in pts_fmt]
        min_x = min(xs)
        max_y = max(ys)

        nw_idx = 0
        nw_dist = float('inf')
        for i, (x, y) in enumerate(pts_fmt):
            d = (x - min_x) ** 2 + (max_y - y) ** 2
            if d < nw_dist:
                nw_dist = d
                nw_idx = i

        area = 0.0
        n = len(pts_fmt)
        for i in range(n):
            j = (i + 1) % n
            area += pts_fmt[i][0] * pts_fmt[j][1]
            area -= pts_fmt[j][0] * pts_fmt[i][1]

        reordered = []
        for i in range(n):
            idx = (nw_idx + i) % n
            reordered.append(self.points[idx])

        if area > 0:
            reordered = [reordered[0]] + reordered[1:][::-1]

        self.points = reordered
        self._updateCoordList()
        self._updateArea()
        self.vertexSelected.emit(0)
        self.lblPointCount.setText('Vertices: %d (sorted CW from NW)' % len(self.points))

    # ------------------------------------------------------------------
    # Copy / Paste / Swap / Add Row / Delete Row
    # ------------------------------------------------------------------
    def _copyCoords(self):
        selected = self.tblCoords.selectionModel().selectedRows()
        rows = sorted(set(idx.row() for idx in selected)) if selected else []

        if not rows:
            rows = list(range(self.tblCoords.rowCount()))

        lines = []
        for r in rows:
            x_item = self.tblCoords.item(r, 1)
            y_item = self.tblCoords.item(r, 2)
            x = x_item.data(Qt.UserRole) if x_item else ''
            y = y_item.data(Qt.UserRole) if y_item else ''
            lines.append(f'{x}\t{y}')

        QApplication.clipboard().setText('\n'.join(lines))

    def _pasteCoords(self):
        text = QApplication.clipboard().text()
        if not text.strip():
            return

        lines = [ln for ln in text.strip().split('\n') if ln.strip()]
        selected = self.tblCoords.selectionModel().selectedRows()
        start_row = selected[0].row() if selected else self.tblCoords.rowCount()

        for i, line in enumerate(lines):
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            try:
                x = float(parts[0].replace(',', '.'))
                y = float(parts[1].replace(',', '.'))
            except ValueError:
                continue

            row = start_row + i
            if row < self.tblCoords.rowCount():
                self.tblCoords.item(row, 1).setText('%.2f' % x)
                self.tblCoords.item(row, 1).setData(Qt.UserRole, x)
                self.tblCoords.item(row, 2).setText('%.2f' % y)
                self.tblCoords.item(row, 2).setData(Qt.UserRole, y)
                newPt = self._toProjectCrs(x, y)
                if row < len(self.points):
                    self.points[row] = newPt
                    self.pointEdited.emit(row, newPt)
            else:
                pt = self._toProjectCrs(x, y)
                self.points.append(pt)
                self.lblPointCount.setText('Vertices: %d' % len(self.points))

        self._updateCoordList()
        self._updateArea()
        self._updateLength()

    def _swapXY(self):
        self.tblCoords.blockSignals(True)
        for r in range(self.tblCoords.rowCount()):
            x_item = self.tblCoords.item(r, 1)
            y_item = self.tblCoords.item(r, 2)
            if x_item and y_item:
                tmp = x_item.text()
                x_item.setText(y_item.text())
                y_item.setText(tmp)
        self.tblCoords.blockSignals(False)

        for pt in self.points:
            pt_new = QgsPointXY(pt.y(), pt.x())
            idx = self.points.index(pt)
            self.points[idx] = pt_new

        self._updateArea()
        self.vertexSelected.emit(0)

    def _addRow(self):
        selected = self.tblCoords.selectionModel().selectedRows()
        if selected:
            row = selected[0].row() + 1
        else:
            row = self.tblCoords.rowCount()

        self.tblCoords.insertRow(row)
        idx = self.tblCoords.item(row - 1, 0) if row > 0 else None
        num = int(idx.text()) + 1 if idx else row + 1

        item0 = QTableWidgetItem(str(num))
        item0.setFlags(item0.flags() & ~Qt.ItemIsEditable)
        item0.setTextAlignment(Qt.AlignCenter)
        self.tblCoords.setItem(row, 0, item0)
        self.tblCoords.setItem(row, 1, QTableWidgetItem('0.00'))
        self.tblCoords.setItem(row, 2, QTableWidgetItem('0.00'))

        pt = self.points[row - 1] if row <= len(self.points) else self.points[-1]
        self.points.insert(row, pt)
        self.lblPointCount.setText('Vertices: %d' % len(self.points))

    def _deleteRow(self):
        selected = self.tblCoords.selectionModel().selectedRows()
        if not selected:
            return

        rows = sorted([idx.row() for idx in selected], reverse=True)
        for r in rows:
            if r < len(self.points):
                self.points.pop(r)
            self.tblCoords.removeRow(r)

        self._updateCoordList()
        self._updateArea()
        self._updateLength()
        self.lblPointCount.setText('Vertices: %d' % len(self.points))

    def _formatCoords(self, point):
        if not self.featureCrs or not self.mapCanvas:
            return (point.x(), point.y())
        projectCrs = self.mapCanvas.mapSettings().destinationCrs()
        if projectCrs != self.featureCrs:
            try:
                if (self._cachedTransformForward is None or
                        self._cachedTransformProjectCrs != projectCrs or
                        self._cachedTransformFeatureCrs != self.featureCrs):
                    self._cachedTransformForward = QgsCoordinateTransform(
                        projectCrs, self.featureCrs, QgsProject.instance())
                    self._cachedTransformProjectCrs = projectCrs
                    self._cachedTransformFeatureCrs = self.featureCrs
                t = self._cachedTransformForward.transform(point)
                return (t.x(), t.y())
            except Exception:
                logging.debug('CRS transform failed: %s', Exception)
        return (point.x(), point.y())

    def _toProjectCrs(self, x, y):
        if not self.featureCrs or not self.mapCanvas:
            return QgsPointXY(x, y)
        projectCrs = self.mapCanvas.mapSettings().destinationCrs()
        if projectCrs != self.featureCrs:
            try:
                if (self._cachedTransformReverse is None or
                        self._cachedTransformProjectCrs != projectCrs or
                        self._cachedTransformFeatureCrs != self.featureCrs):
                    self._cachedTransformReverse = QgsCoordinateTransform(
                        self.featureCrs, projectCrs, QgsProject.instance())
                    self._cachedTransformProjectCrs = projectCrs
                    self._cachedTransformFeatureCrs = self.featureCrs
                return self._cachedTransformReverse.transform(QgsPointXY(x, y))
            except Exception:
                logging.debug('Reverse CRS transform failed: %s', Exception)
        return QgsPointXY(x, y)

    def _invalidateTransformCache(self):
        self._cachedTransformForward = None
        self._cachedTransformReverse = None
        self._cachedTransformProjectCrs = None
        self._cachedTransformFeatureCrs = None

    def _updateCoordList(self, incremental=False):
        self.tblCoords.blockSignals(True)
        if incremental and self.tblCoords.rowCount() == len(self.points) - 1:
            i = len(self.points) - 1
            pt = self.points[i]
            x, y = self._formatCoords(pt)
            self.tblCoords.insertRow(i)
            item0 = QTableWidgetItem(str(i + 1))
            item0.setFlags(item0.flags() & ~Qt.ItemIsEditable)
            item0.setTextAlignment(Qt.AlignCenter)
            self.tblCoords.setItem(i, 0, item0)
            itemX = QTableWidgetItem('%.2f' % x)
            itemX.setData(Qt.UserRole, x)
            itemX.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            itemY = QTableWidgetItem('%.2f' % y)
            itemY.setData(Qt.UserRole, y)
            itemY.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tblCoords.setItem(i, 1, itemX)
            self.tblCoords.setItem(i, 2, itemY)
        else:
            self.tblCoords.setRowCount(len(self.points))
            for i, pt in enumerate(self.points):
                x, y = self._formatCoords(pt)
                item0 = QTableWidgetItem(str(i + 1))
                item0.setFlags(item0.flags() & ~Qt.ItemIsEditable)
                item0.setTextAlignment(Qt.AlignCenter)
                self.tblCoords.setItem(i, 0, item0)
                itemX = QTableWidgetItem('%.2f' % x)
                itemX.setData(Qt.UserRole, x)
                itemX.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                itemY = QTableWidgetItem('%.2f' % y)
                itemY.setData(Qt.UserRole, y)
                itemY.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tblCoords.setItem(i, 1, itemX)
                self.tblCoords.setItem(i, 2, itemY)
        self.tblCoords.blockSignals(False)

    def _onCellClicked(self, row, col):
        if 0 <= row < len(self.points):
            self.vertexSelected.emit(row)

    def _onCellEdited(self, row, col):
        if col < 1 or row >= len(self.points):
            return
        try:
            x = float(self.tblCoords.item(row, 1).text())
            y = float(self.tblCoords.item(row, 2).text())
            self.tblCoords.item(row, 1).setData(Qt.UserRole, x)
            self.tblCoords.item(row, 2).setData(Qt.UserRole, y)
            newPt = self._toProjectCrs(x, y)
            self.points[row] = newPt
            self._updateArea()
            self._updateLength()
            self.pointEdited.emit(row, newPt)
        except Exception:
            logging.debug('Point edit failed: %s', Exception)

    def clearPoints(self):
        self.points.clear()
        self._previewPt = None
        self._drawingEnded = False
        self.lblPointCount.setText('Vertices: 0')
        self.tblCoords.setRowCount(0)
        self.lblArea.setText('Area: —')
        self.areaFrame.hide()
        self.lblLength.setText('Length: —')
        self.lengthFrame.hide()

    # ------------------------------------------------------------------
    # Drawing actions
    # ------------------------------------------------------------------
    def restartDrawing(self):
        self.restartRequested.emit()

    def _onEndDrawing(self):
        min_pts = self._minPoints()
        if len(self.points) >= min_pts:
            if self.geomType == 'polygon':
                self.sortCoordinatesClockwise()
            self.clearPreviewPoint()
            self._drawingEnded = True
            self.drawingEnded.emit()

    def finishDrawing(self):
        min_pts = self._minPoints()
        if len(self.points) >= min_pts:
            self.finishedDrawing.emit(list(self.points))

    def setPreviewPoint(self, point):
        self._previewPt = point
        self._pendingAreaPreview = True
        if not self._areaTimer.isActive():
            self._areaTimer.start()

    def clearPreviewPoint(self):
        self._previewPt = None
        self._pendingAreaPreview = False
        self._updateArea(use_preview=False)
        self._updateLength(use_preview=False)

    def _doDeferredAreaUpdate(self):
        if self._pendingAreaPreview:
            self._pendingAreaPreview = False
            self._updateArea(use_preview=True)
            self._updateLength(use_preview=True)

    # ------------------------------------------------------------------
    # Area calculation
    # ------------------------------------------------------------------
    _AREA_UNITS = {
        'Hectares':         (10000,       'ha'),
        'Acres':            (4046.8564224, 'ac'),
        'Square Feet':      (0.09290304,  'ft²'),
        'Square Meters':    (1.0,         'm²'),
        'Square Kilometers': (1e6,        'km²'),
        'Square Miles':     (2589988.110336, 'mi²'),
    }

    def _convertArea(self, area_sqm):
        unit = self.cbAreaUnit.currentText()
        divisor, symbol = self._AREA_UNITS[unit]
        return f'{_fmtNum(area_sqm / divisor, 2)} {symbol}'

    def _onAreaUnitChanged(self, _index):
        if self._area_sqm > 0:
            self.lblArea.setText(f'Area: {self._convertArea(self._area_sqm)}')

    def _updateArea(self, use_preview=False):
        if self.geomType != 'polygon':
            self.areaFrame.hide()
            self._area_sqm = 0.0
            return
        self.areaFrame.hide()
        self._area_sqm = 0.0
        pts = list(self.points)
        if use_preview and self._previewPt and pts:
            pts.append(self._previewPt)
        if not self.mapCanvas or len(pts) < 3:
            return
        if not self.featureCrs:
            return
        try:
            feature_pts = []
            for pt in pts:
                x, y = self._formatCoords(pt)
                feature_pts.append(QgsPointXY(x, y))
            ring = QgsLineString(feature_pts)
            ring.close()
            poly = QgsPolygon()
            poly.setExteriorRing(ring)
            geom = QgsGeometry(poly)
            da = QgsDistanceArea()
            da.setSourceCrs(self.featureCrs,
                            QgsProject.instance().transformContext())
            if self.featureCrs.isGeographic():
                da.setEllipsoid(QgsProject.instance().ellipsoid())
            self._area_sqm = abs(da.measureArea(geom))
            self.lblArea.setText(f'Area: {self._convertArea(self._area_sqm)}')
            self.areaFrame.show()
        except Exception:
            self.lblArea.setText('N/A')

    # ------------------------------------------------------------------
    # Length calculation
    # ------------------------------------------------------------------
    _LENGTH_UNITS = {
        'Meters':      (1.0,      'm'),
        'Kilometers':  (1000.0,   'km'),
        'Feet':        (0.3048,   'ft'),
        'Miles':       (1609.344, 'mi'),
        'Yards':       (0.9144,    'yd'),
    }

    def _convertLength(self, length_m):
        unit = self.cbLengthUnit.currentText()
        divisor, symbol = self._LENGTH_UNITS[unit]
        return f'{_fmtNum(length_m / divisor, 2)} {symbol}'

    def _onLengthUnitChanged(self, _index):
        if self._length_m > 0:
            self.lblLength.setText(f'Length: {self._convertLength(self._length_m)}')

    def _updateLength(self, use_preview=False):
        if self.geomType != 'line':
            self.lengthFrame.hide()
            self._length_m = 0.0
            return
        self.lengthFrame.hide()
        self._length_m = 0.0
        pts = list(self.points)
        if use_preview and self._previewPt and pts:
            pts.append(self._previewPt)
        if not self.mapCanvas or len(pts) < 2:
            return
        if not self.featureCrs:
            return
        try:
            feature_pts = []
            for pt in pts:
                x, y = self._formatCoords(pt)
                feature_pts.append(QgsPointXY(x, y))
            line = QgsLineString(feature_pts)
            geom = QgsGeometry(line)
            da = QgsDistanceArea()
            da.setSourceCrs(self.featureCrs,
                            QgsProject.instance().transformContext())
            if self.featureCrs.isGeographic():
                da.setEllipsoid(QgsProject.instance().ellipsoid())
            self._length_m = da.measureLength(geom)
            self.lblLength.setText(f'Length: {self._convertLength(self._length_m)}')
            self.lengthFrame.show()
        except Exception:
            self.lblLength.setText('N/A')

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        super().closeEvent(event)
