from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap, QImageReader
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLabel
import hashlib
from krita import Krita, DockWidget, DockWidgetFactory, DockWidgetFactoryBase

KI = Krita.instance()

class ImageProcessingThread(QThread):
    imageProcessed = pyqtSignal(QImage)

    def run(self, image):
        resultImage = self.convertToRGB565(image)
        self.imageProcessed.emit(resultImage)

    def convertToRGB565(self, image):
        width, height = image.width(), image.height()
        buffer = bytearray(width * height * 2)  # 2 bytes for each pixel
        image = image.convertToFormat(QImage.Format_RGB16)
        ptr = image.constBits()
        ptr.setsize(width * height * 2)
        buffer[:] = ptr.asarray()
        return QImage(buffer, width, height, QImage.Format_RGB16)

def get_image_hash(image):
    data = image.bits().asstring(image.byteCount())
    return hashlib.md5(data).hexdigest()

class CustomGraphicsView(QGraphicsView):
    zoomChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def wheelEvent(self, event):
        # Capture the current scale factor before applying zoom
        current_scale = self.transform().m11()

        zoom_factor = 1.1  # Adjusted to slow down the zoom speed
        if event.angleDelta().y() > 0:  # Zoom in
            self.scale(zoom_factor, zoom_factor)
        else:  # Zoom out
            if current_scale > 0.25:  # Ensure we're not zooming out below 25%
                self.scale(1 / zoom_factor, 1 / zoom_factor)
        self.zoomChanged.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

class RGB565Preview(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RGB565 Preview")

        layout = QVBoxLayout()

        self.view = CustomGraphicsView(self)
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.pixmapItem = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmapItem)

        layout.addWidget(self.view)

        # Create a horizontal layout for control buttons and label
        controlLayout = QHBoxLayout()

        restoreBtn = QPushButton("Original Size")
        restoreBtn.clicked.connect(self.restoreOriginalSize)
        controlLayout.addWidget(restoreBtn)

        fitBtn = QPushButton("Fit Image")
        fitBtn.clicked.connect(self.fitImageInView)
        controlLayout.addWidget(fitBtn)

        self.zoomLabel = QLabel("100%")
        controlLayout.addWidget(self.zoomLabel)

        layout.addLayout(controlLayout)

        widget = QWidget(self)
        widget.setLayout(layout)
        self.setWidget(widget)

        self.processingThread = ImageProcessingThread()
        self.processingThread.imageProcessed.connect(self.updatePreview)

        self.prevImageData = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkForUpdate)
        self.timer.start(1000)  # Update every 1 second to reduce frequency

        # For panning
        self.view.setDragMode(QGraphicsView.NoDrag)  # Disable the default drag mode

        # Connect the zoomChanged signal to update the zoom label
        self.view.zoomChanged.connect(self.updateZoomLabel)

    def restoreOriginalSize(self):
        self.view.resetTransform()
        self.updateZoomLabel()

    def fitImageInView(self):
        self.view.fitInView(self.pixmapItem, Qt.KeepAspectRatio)
        self.updateZoomLabel()

    def updateZoomLabel(self):
        # Calculate the zoom percentage
        zoom_percentage = round(self.view.transform().m11() * 100)
        self.zoomLabel.setText(f"{zoom_percentage}%")

    def canvasChanged(self, canvas):
        pass

    def checkForUpdate(self):
        doc = KI.activeDocument()
        if doc:
            image = doc.projection(0, 0, doc.width(), doc.height()).convertToFormat(QImage.Format_RGBA8888)
            currImageHash = get_image_hash(image)
            if self.prevImageData != currImageHash:
                self.processingThread.run(image)
                self.prevImageData = currImageHash

    def updatePreview(self, resultImage):
        pixmap = QPixmap.fromImage(resultImage)
        self.pixmapItem.setPixmap(pixmap)

KI.addDockWidgetFactory(DockWidgetFactory("rgb565preview", DockWidgetFactoryBase.DockRight, RGB565Preview))