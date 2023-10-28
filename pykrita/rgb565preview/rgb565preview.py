from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap, QImageReader
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
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

def get_scaled_image(image, scale_factor):
    scaled_image = image.scaled(int(image.width() * scale_factor), int(image.height() * scale_factor))
    return scaled_image

class RGB565Preview(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RGB565 Preview")

        layout = QVBoxLayout()
        self.previewLabel = QLabel(self)
        self.previewLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.previewLabel)
        widget = QWidget(self)
        widget.setLayout(layout)
        self.setWidget(widget)

        self.processingThread = ImageProcessingThread()
        self.processingThread.imageProcessed.connect(self.updatePreview)

        self.prevImageData = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkForUpdate)
        self.timer.start(1000)  # Update every 1 second to reduce frequency

    def canvasChanged(self, canvas):
        pass

    def checkForUpdate(self):
        doc = KI.activeDocument()
        if doc:
            image = doc.projection(0, 0, doc.width(), doc.height()).convertToFormat(QImage.Format_RGBA8888)
            scaled_image = get_scaled_image(image, 0.5)  # Scale down by 50%
            currImageData = scaled_image.bits().asstring(scaled_image.byteCount())
            if self.prevImageData != currImageData:
                self.processingThread.run(scaled_image)
                self.prevImageData = currImageData

    def updatePreview(self, resultImage):
        pixmap = QPixmap.fromImage(resultImage)
        self.previewLabel.setPixmap(pixmap.scaled(self.previewLabel.width(), self.previewLabel.height(), Qt.KeepAspectRatio))

KI.addDockWidgetFactory(DockWidgetFactory("rgb565preview", DockWidgetFactoryBase.DockRight, RGB565Preview))