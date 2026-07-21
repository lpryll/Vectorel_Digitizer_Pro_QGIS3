# -*- coding: utf-8 -*-



def classFactory(iface):
    """Load VectorelDigitizerPro class from file vectorelDigitizerPro.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .vectorelDigitizerPro import VectorelDigitizerPro
    return VectorelDigitizerPro(iface)
