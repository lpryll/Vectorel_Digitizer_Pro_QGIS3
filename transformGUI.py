# -*- coding: utf-8 -*-
"""Dialog of the "Transform Features" tool (move / rotate / scale).

The dialog is a thin view on the state held by TransformTool: typed values are
written to the tool (which redraws the live preview), values changed with the
mouse come back through TransformTool.stateChanged.
"""

import html

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.core import QgsPointXY, QgsUnitTypes

from .transformTool import (
    ANGLE_DECIMALS,
    MODE_MOVE,
    MODE_ROTATE,
    MODE_SCALE,
    PIVOT_CENTER,
    PIVOT_CUSTOM,
    PIVOT_EACH,
    SCALE_DECIMALS,
    MIN_SCALE,
)


def _tr(text):
    return QCoreApplication.translate("TransformGUI", text)


_MODES = [MODE_MOVE, MODE_ROTATE, MODE_SCALE]
_PIVOT_MODES = [PIVOT_CENTER, PIVOT_EACH, PIVOT_CUSTOM]
_BIG = 1.0e12

_STYLE = """
QDialog {
    background-color: #f5f6fa;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 9pt;
}
#headerFrame {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1a5276, stop:1 #2980b9);
    border-radius: 6px;
}
#headerTitle { color: white; font-size: 12pt; font-weight: bold; }
#headerSub { color: #aed6f1; font-size: 8pt; }
#infoLabel {
    background-color: #eaf2fb;
    border: 1px solid #aed6f1;
    border-radius: 4px;
    padding: 4px 6px;
    color: #1a5276;
}
#warnLabel {
    background-color: #fef5e7;
    border: 1px solid #f5cba7;
    border-radius: 4px;
    padding: 4px 6px;
    color: #935116;
}
#hint { color: #5d6d7e; font-style: italic; }
QGroupBox {
    font-weight: bold;
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
QTabWidget::pane {
    border: 1px solid #c8d6e5;
    border-radius: 6px;
    background-color: #ffffff;
}
QTabBar::tab {
    padding: 5px 16px;
    background-color: #e8eef5;
    border: 1px solid #c8d6e5;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    color: #2c3e50;
}
QTabBar::tab:selected { background-color: #ffffff; color: #2980b9; font-weight: bold; }
QDoubleSpinBox, QComboBox {
    border: 1px solid #c8d6e5;
    border-radius: 4px;
    padding: 2px 4px;
    background-color: #ffffff;
    min-height: 22px;
}
QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid #2980b9; }
QPushButton {
    border: 1px solid #aab7c4;
    border-radius: 4px;
    padding: 5px 14px;
    background-color: #ffffff;
    color: #2c3e50;
}
QPushButton:hover { background-color: #eaf2fb; }
QPushButton:checked { background-color: #aed6f1; border: 1px solid #2980b9; }
#applyBtn { background-color: #27ae60; border: 1px solid #1e8449; color: white; font-weight: bold; }
#applyBtn:hover { background-color: #2ecc71; }
"""


class TransformGUI(QDialog):
    """Non-modal dialog bound to a TransformTool instance."""

    def __init__(self, parent, tool):
        super().__init__(parent)
        self._tool = tool
        self._syncing = False
        self._shownLayerId = None

        self.setWindowTitle(_tr("Vectorel Digitizer Pro – Transform Features"))
        self.setStyleSheet(_STYLE)
        self.setMinimumWidth(360)
        self._build()

        tool.activated.connect(self._onToolActivated)
        tool.deactivated.connect(self.hide)
        tool.stateChanged.connect(self.syncFromTool)
        tool.pivotPicked.connect(self._onPivotPicked)
        tool.message.connect(self.showMessage)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _spin(self, lo, hi, decimals, step):
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(decimals)
        s.setSingleStep(step)
        s.setAlignment(Qt.AlignmentFlag.AlignRight)
        return s

    def _hint(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("hint")
        lbl.setWordWrap(True)
        return lbl

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # Header
        header = QFrame()
        header.setObjectName("headerFrame")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(10, 6, 10, 6)
        hl.setSpacing(0)
        title = QLabel(_tr("Transform Features"))
        title.setObjectName("headerTitle")
        sub = QLabel(_tr("Move · Rotate · Scale the selected features"))
        sub.setObjectName("headerSub")
        hl.addWidget(title)
        hl.addWidget(sub)
        root.addWidget(header)

        self.infoLabel = QLabel()
        self.infoLabel.setObjectName("infoLabel")
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(self.infoLabel)

        self.warnLabel = QLabel(
            _tr(
                "Geographic CRS: values are in degrees and rotation/scale are applied "
                "to degree coordinates, so shapes may distort. A projected CRS is "
                "recommended."
            )
        )
        self.warnLabel.setObjectName("warnLabel")
        self.warnLabel.setWordWrap(True)
        self.warnLabel.hide()
        root.addWidget(self.warnLabel)

        # Tabs --------------------------------------------------------------
        self.tabs = QTabWidget()

        # Move
        tabMove = QWidget()
        fl = QFormLayout(tabMove)
        self.dxSpin = self._spin(-_BIG, _BIG, 4, 1.0)
        self.dySpin = self._spin(-_BIG, _BIG, 4, 1.0)
        self.dxLabel = QLabel(_tr("ΔX:"))
        self.dyLabel = QLabel(_tr("ΔY:"))
        fl.addRow(self.dxLabel, self.dxSpin)
        fl.addRow(self.dyLabel, self.dySpin)
        fl.addRow(
            self._hint(
                _tr(
                    "Drag on the map from a base point to a destination. "
                    "Snapping is used when enabled in the project."
                )
            )
        )
        self.tabs.addTab(tabMove, _tr("Move"))

        # Rotate
        tabRot = QWidget()
        fl = QFormLayout(tabRot)
        self.angleSpin = self._spin(-360.0, 360.0, ANGLE_DECIMALS, 1.0)
        self.angleSpin.setSuffix(" °")
        fl.addRow(_tr("Angle:"), self.angleSpin)
        fl.addRow(
            self._hint(
                _tr(
                    "Positive = clockwise, negative = counter-clockwise. Drag around the pivot; "
                    "hold Shift for 15° steps."
                )
            )
        )
        self.tabs.addTab(tabRot, _tr("Rotate"))

        # Scale
        tabScale = QWidget()
        fl = QFormLayout(tabScale)
        self.sxSpin = self._spin(MIN_SCALE, 1.0e6, SCALE_DECIMALS, 0.1)
        self.sySpin = self._spin(MIN_SCALE, 1.0e6, SCALE_DECIMALS, 0.1)
        self.uniformChk = QCheckBox(_tr("Uniform (keep X = Y)"))
        fl.addRow(_tr("Factor X:"), self.sxSpin)
        fl.addRow(_tr("Factor Y:"), self.sySpin)
        fl.addRow(self.uniformChk)
        fl.addRow(
            self._hint(
                _tr(
                    "1.0 = no change. Drag away from / towards the pivot to "
                    "enlarge / shrink."
                )
            )
        )
        self.tabs.addTab(tabScale, _tr("Scale"))
        root.addWidget(self.tabs)

        # Pivot (Rotate / Scale) -------------------------------------------
        self.pivotGroup = QGroupBox(_tr("Pivot"))
        pl = QFormLayout(self.pivotGroup)
        self.pivotCombo = QComboBox()
        self.pivotCombo.addItem(_tr("Centre of selection"))
        self.pivotCombo.addItem(_tr("Each feature's own centre"))
        self.pivotCombo.addItem(_tr("Custom point"))
        pl.addRow(self.pivotCombo)
        self.pivotX = self._spin(-_BIG, _BIG, 4, 1.0)
        self.pivotY = self._spin(-_BIG, _BIG, 4, 1.0)
        pl.addRow(_tr("X:"), self.pivotX)
        pl.addRow(_tr("Y:"), self.pivotY)
        self.pickBtn = QPushButton(_tr("Pick pivot on map"))
        self.pickBtn.setCheckable(True)
        pl.addRow(self.pickBtn)
        pl.addRow(self._hint(_tr("Tip: Ctrl+click on the map also sets the pivot.")))
        root.addWidget(self.pivotGroup)

        # Options ------------------------------------------------------------
        self.releaseChk = QCheckBox(_tr("Apply when the mouse button is released"))
        root.addWidget(self.releaseChk)

        self.statusLabel = QLabel("")
        self.statusLabel.setWordWrap(True)
        self.statusLabel.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(self.statusLabel)

        root.addWidget(
            self._hint(_tr("Enter: apply · Esc / right-click: reset values"))
        )

        # Buttons --------------------------------------------------------------
        bl = QHBoxLayout()
        self.applyBtn = QPushButton(_tr("Apply"))
        self.applyBtn.setObjectName("applyBtn")
        self.applyBtn.setDefault(True)
        self.resetBtn = QPushButton(_tr("Reset"))
        self.closeBtn = QPushButton(_tr("Close"))
        self.resetBtn.setAutoDefault(False)
        self.closeBtn.setAutoDefault(False)
        bl.addWidget(self.applyBtn)
        bl.addWidget(self.resetBtn)
        bl.addStretch(1)
        bl.addWidget(self.closeBtn)
        root.addLayout(bl)

        # Signals -------------------------------------------------------------
        self.tabs.currentChanged.connect(self._onTabChanged)
        self.dxSpin.valueChanged.connect(self._onMoveEdited)
        self.dySpin.valueChanged.connect(self._onMoveEdited)
        self.angleSpin.valueChanged.connect(self._onAngleEdited)
        self.sxSpin.valueChanged.connect(self._onScaleXEdited)
        self.sySpin.valueChanged.connect(self._onScaleYEdited)
        self.uniformChk.toggled.connect(self._onUniformToggled)
        self.pivotCombo.currentIndexChanged.connect(self._onPivotModeChanged)
        self.pivotX.valueChanged.connect(self._onPivotEdited)
        self.pivotY.valueChanged.connect(self._onPivotEdited)
        self.pickBtn.clicked.connect(self._onPickClicked)
        self.releaseChk.toggled.connect(self._onReleaseToggled)
        self.applyBtn.clicked.connect(self._onApply)
        self.resetBtn.clicked.connect(self._onReset)
        self.closeBtn.clicked.connect(self.reject)

        self.pivotGroup.setVisible(False)

    # ------------------------------------------------------------------
    # Tool -> dialog
    # ------------------------------------------------------------------
    def _onToolActivated(self):
        self.statusLabel.setText("")
        self.show()
        self.raise_()

    def showMessage(self, text, isError=False):
        color = "#c0392b" if isError else "#1e8449"
        self.statusLabel.setText(
            '<span style="color:%s;">%s</span>' % (color, html.escape(text))
        )

    def _onPivotPicked(self):
        self.pickBtn.setChecked(False)
        self.showMessage(_tr("Pivot set."), False)

    @staticmethod
    def _setSpin(spin, value):
        # Do not touch the widget that is being typed into.
        if spin.value() != round(value, spin.decimals()):
            spin.setValue(value)

    def _applyLayerInfo(self):
        layer = self._tool.layer
        lid = layer.id() if layer is not None else None
        if lid == self._shownLayerId:
            return
        self._shownLayerId = lid
        if layer is None:
            return

        dec = self._tool.decimals
        step = 0.0001 if self._tool.layerIsGeographic else 1.0
        for spin in (self.dxSpin, self.dySpin, self.pivotX, self.pivotY):
            spin.setDecimals(dec)
            spin.setSingleStep(step)

        try:
            unit = QgsUnitTypes.toString(layer.crs().mapUnits())
        except (AttributeError, TypeError):
            unit = ""
        for spin in (self.dxSpin, self.dySpin, self.pivotX, self.pivotY):
            spin.setSuffix(" " + unit if unit else "")
        self.warnLabel.setVisible(bool(self._tool.layerIsGeographic))

    def _updateInfo(self):
        t = self._tool
        name = html.escape(t.layer.name()) if t.layer is not None else "-"
        n = t.featureCount()
        if n == 0:
            self.infoLabel.setText(
                _tr("Layer: <b>%s</b><br><span style='color:#c0392b;'>No features "
                    "selected – select features first, then use this tool.</span>")
                % name
            )
        else:
            self.infoLabel.setText(
                _tr("Layer: <b>%s</b> · <b>%d</b> feature(s) selected (values are in "
                    "layer CRS units)") % (name, n)
            )

    def syncFromTool(self):
        t = self._tool
        if t.layer is None:
            return
        self._syncing = True
        try:
            self._applyLayerInfo()

            self._setSpin(self.dxSpin, t.dx)
            self._setSpin(self.dySpin, t.dy)
            self._setSpin(self.angleSpin, t.angle)
            self._setSpin(self.sxSpin, t.sx)
            self._setSpin(self.sySpin, t.sy)
            self.uniformChk.setChecked(t.uniform)

            idx = _PIVOT_MODES.index(t.pivotMode)
            if self.pivotCombo.currentIndex() != idx:
                self.pivotCombo.setCurrentIndex(idx)
            shown = t.pivot if t.pivotMode == PIVOT_CUSTOM else t.center
            self._setSpin(self.pivotX, shown.x())
            self._setSpin(self.pivotY, shown.y())
            custom = t.pivotMode == PIVOT_CUSTOM
            self.pivotX.setEnabled(custom)
            self.pivotY.setEnabled(custom)
            self.pickBtn.setEnabled(t.pivotMode != PIVOT_EACH)
            self.pickBtn.setChecked(t.pickingPivot)

            tab = _MODES.index(t.mode)
            if self.tabs.currentIndex() != tab:
                self.tabs.setCurrentIndex(tab)
            self.pivotGroup.setVisible(tab != 0)
            self.releaseChk.setChecked(t.applyOnRelease)
        finally:
            self._syncing = False
        self._updateInfo()

    # ------------------------------------------------------------------
    # Dialog -> tool
    # ------------------------------------------------------------------
    def _onTabChanged(self, index):
        if self._syncing:
            return
        t = self._tool
        t.mode = _MODES[index]
        t.pickingPivot = False
        self.pickBtn.setChecked(False)
        self.pivotGroup.setVisible(index != 0)
        t.updatePreview()
        self.adjustSize()

    def _onMoveEdited(self, _value):
        if self._syncing:
            return
        t = self._tool
        t.dx = self.dxSpin.value()
        t.dy = self.dySpin.value()
        t.updatePreview()

    def _onAngleEdited(self, value):
        if self._syncing:
            return
        self._tool.angle = value
        self._tool.updatePreview()

    def _onScaleXEdited(self, value):
        if self._syncing:
            return
        t = self._tool
        t.sx = value
        if t.uniform:
            t.sy = value
        t.updatePreview()
        self.syncFromTool()

    def _onScaleYEdited(self, value):
        if self._syncing:
            return
        t = self._tool
        t.sy = value
        if t.uniform:
            t.sx = value
        t.updatePreview()
        self.syncFromTool()

    def _onUniformToggled(self, on):
        if self._syncing:
            return
        t = self._tool
        t.uniform = on
        if on:
            t.sy = t.sx
            t.updatePreview()
            self.syncFromTool()

    def _onPivotModeChanged(self, index):
        if self._syncing:
            return
        t = self._tool
        mode = _PIVOT_MODES[index]
        if mode == PIVOT_CUSTOM and t.pivotMode != PIVOT_CUSTOM:
            # start from where the pivot currently is
            t.pivot = QgsPointXY(t.center)
        t.pivotMode = mode
        t.pickingPivot = False
        t.updatePreview()
        self.syncFromTool()

    def _onPivotEdited(self, _value):
        if self._syncing:
            return
        t = self._tool
        t.pivot = QgsPointXY(self.pivotX.value(), self.pivotY.value())
        t.pivotMode = PIVOT_CUSTOM
        t.updatePreview()
        self.syncFromTool()

    def _onPickClicked(self, checked):
        if self._syncing:
            return
        self._tool.pickingPivot = checked
        if checked:
            self.showMessage(_tr("Click on the map to set the pivot."), False)

    def _onReleaseToggled(self, on):
        if self._syncing:
            return
        self._tool.applyOnRelease = on

    def _onApply(self):
        self._tool.applyTransform()

    def _onReset(self):
        t = self._tool
        t.resetParams()
        t.updatePreview()
        self.syncFromTool()
        self.statusLabel.setText("")
