import sys
import time
import threading
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QGroupBox, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from qt_material import apply_stylesheet
from PyQt6.QtGui import QImage, QPixmap
import cv2
from ultralytics import YOLO


class SerialReaderGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gripper Control GUI")
        self.setFixedSize(550, 450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.mode = "Manual"
        self.object_type = "Soft"
        self.yolo_model = YOLO(r"/home/amolk/EESTEC HACKA/gripper/weights/weights4--100ep/best.pt")
        self.init_ui()
        self.ser = None
        self.baud_rate = 115200
        self.port = self.find_xmc1100_port()

        if self.port:
            self.connect_serial()
        else:
            self.z_value_box.setText("No XMC1100 found")
            self.z_value_box.setStyleSheet("color: red")

        self.stop_thread = False
        self.thread = threading.Thread(target=self.read_serial)
        self.thread.daemon = True
        self.thread.start()
        self.run_yolo_inference()
        self.connection_monitor = ConnectionMonitor(self)

    def init_ui(self):
        # Main layout
        main_layout = QHBoxLayout()

        # Left layout for live feed and status
        left_layout = QVBoxLayout()

        self.label = QLabel("Z-Axis Magnetic Field (mT):")
        left_layout.addWidget(self.label)
        self.z_value_box = QLabel("Disconnected")
        self.z_value_box.setStyleSheet("color:red; background-color: white; padding: 10px;")
        left_layout.addWidget(self.z_value_box)

        # Command Entry
        cmd_layout = QHBoxLayout()
        self.cmd_entry = QLineEdit()
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_command)
        cmd_layout.addWidget(QLabel("Send Command:"))
        cmd_layout.addWidget(self.cmd_entry)
        cmd_layout.addWidget(self.send_button)
        left_layout.addLayout(cmd_layout)

        self.status_label = QLabel("")
        left_layout.addWidget(self.status_label)

        # Live YOLO feed
        self.video_label = QLabel("Live YOLO Feed")
        self.video_label.setFixedSize(640, 480)  # Set to 640x480 resolution
        self.video_label.setStyleSheet("background-color: black;")
        left_layout.addWidget(self.video_label)

        # Right layout for gripper controls
        right_layout = QVBoxLayout()

        self.gripper_group = QGroupBox("Gripper Control")
        grip_layout = QGridLayout()

        self.open_button = QPushButton("Open Gripper")
        self.close_button = QPushButton("Close Gripper")
        self.toggle_mode_button = QPushButton("Switch to Automatic Mode")
        self.object_dropdown = QComboBox()
        self.object_dropdown.addItems(["Soft", "Hard"])
        self.manual_grip_button = QPushButton("Grip Object (Manual)")

        self.open_button.clicked.connect(self.dummy_open_gripper)
        self.close_button.clicked.connect(self.dummy_close_gripper)
        self.toggle_mode_button.clicked.connect(self.toggle_mode)
        self.manual_grip_button.clicked.connect(self.dummy_grip_manual)
        self.object_dropdown.currentTextChanged.connect(lambda val: setattr(self, 'object_type', val))

        grip_layout.addWidget(self.open_button, 0, 0)
        grip_layout.addWidget(self.close_button, 0, 1)
        grip_layout.addWidget(self.toggle_mode_button, 1, 0, 1, 2)
        grip_layout.addWidget(QLabel("Object Type:"), 2, 0)
        grip_layout.addWidget(self.object_dropdown, 2, 1)
        grip_layout.addWidget(self.manual_grip_button, 3, 0, 1, 2)

        self.gripper_group.setLayout(grip_layout)
        right_layout.addWidget(self.gripper_group)

        # Add left and right layouts to the main layout
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

    def find_xmc1100_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'J-Link - CDC' in port.description or "USB Serial Device" in port.description:
                return port.device
        return None

    def connect_serial(self):
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2)
            self.z_value_box.setText("Connected")
            self.z_value_box.setStyleSheet("color: green")
        except Exception as e:
            self.z_value_box.setText(f"Error: {str(e)}")
            self.z_value_box.setStyleSheet("color: red")

    def read_serial(self):
        while not self.stop_thread:
            try:
                if self.is_connected() and self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if "Filtered Z:" in line:
                        z_value = line.split("Filtered Z:")[1].strip().split()[0]
                        self.z_value_box.setText(z_value)
                        print(f"Z Value: {z_value}")
                    elif "ECHO:" in line.upper():  # Case-insensitive check
                        echo = line.split("ECHO:")[1].strip()
                        print(f"Received: {echo}")
                        self.status_label.setText(f"Board received: {echo}")
                    elif "CLOSING" in line:
                        self.status_label.setText("GRIPPER CLOSING")
                    elif "STOP" in line:
                        self.status_label.setText("GRIPPER STOPPED")
                elif not self.is_connected():
                    self.z_value_box.setText("Disconnected")
                    self.z_value_box.setStyleSheet("color: orange")
                    self.status_label.setText("Device disconnected")
            except (serial.SerialException, OSError):
                self.z_value_box.setText("Disconnected")
                self.z_value_box.setStyleSheet("color: orange")
                self.status_label.setText("Device disconnected")
                if self.ser:
                    self.ser.close()
                    self.ser = None
            except Exception as e:
                self.z_value_box.setText(f"Read error: {str(e)}")
            time.sleep(0.1)

    def send_command(self):
        if not self.ser or not self.ser.is_open:
            self.status_label.setText("Not connected to serial port!")
            return

        cmd = self.cmd_entry.text().strip()
        if not cmd:
            self.status_label.setText("Please enter a command")
            return

        try:
            self.ser.write((cmd + '\n').encode('utf-8'))
            self.status_label.setText(f"Sent: {cmd}")
            self.cmd_entry.clear()
        except Exception as e:
            self.status_label.setText(f"Send error: {str(e)}")

    def is_connected(self):
        return self.ser and self.ser.is_open

    def closeEvent(self, event):
        self.stop_thread = True
        self.connection_monitor.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
        event.accept()

    def dummy_open_gripper(self):
        self.status_label.setText("Gripper Open Command Sent (Dummy)")

    def dummy_close_gripper(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(("CLOSE\n").encode('utf-8'))
                #self.status_label.setText("Sent CLOSE command to gripper")
            except Exception as e:
                self.status_label.setText(f"Error sending CLOSE: {str(e)}")
                print(str(e))
        else:
            self.status_label.setText("Serial port not open")

    def dummy_grip_manual(self):
        self.status_label.setText(f"Manual grip for {self.object_type} object (Dummy)")

    def toggle_mode(self):
        if self.mode == "Manual":
            self.mode = "Automatic"
            self.toggle_mode_button.setText("Switch to Manual Mode")
            self.object_dropdown.setEnabled(False)
            self.manual_grip_button.setEnabled(False)
            self.status_label.setText("Switched to Automatic Mode (Dummy)")
        else:
            self.mode = "Manual"
            self.toggle_mode_button.setText("Switch to Automatic Mode")
            self.object_dropdown.setEnabled(True)
            self.manual_grip_button.setEnabled(True)
            self.status_label.setText("Switched to Manual Mode")

    def run_yolo_inference(self):
        if hasattr(self, 'yolo_running') and self.yolo_running:
            self.status_label.setText("YOLO live feed already running.")
            return
        self.status_label.setText("Starting YOLO live feed...")
        self.yolo_running = True
        self.yolo_thread = threading.Thread(target=self._yolo_live_worker)
        self.yolo_thread.daemon = True
        self.yolo_thread.start()

    def _yolo_live_worker(self):
        try:
            for results in self.yolo_model.predict(source=0, stream=True):  # Stream frames from the webcam
                try:
                    # Get the annotated frame
                    annotated_frame = results.plot()
                    key = results.probs.top1
                    class_name = results.names[int(key)]
                    # Convert to QImage
                    rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image).scaled(
                        640, 480, Qt.AspectRatioMode.KeepAspectRatio  # Match QLabel size
                    )

                    # Show in QLabel
                    self.video_label.setPixmap(pixmap)

                    # Stop the loop if YOLO is no longer running
                    if not self.yolo_running:
                        break
                except Exception as e:
                    self.status_label.setText(f"YOLO inference error: {str(e)}")
                    break
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
        finally:
            self.yolo_running = False
            self.status_label.setText("YOLO live feed stopped.")


class ConnectionMonitor:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.stop_monitor = False
        self.monitor_thread = threading.Thread(target=self.monitor_connection)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def monitor_connection(self):
        while not self.stop_monitor:
            if not self.gui.is_connected():
                self.gui.z_value_box.setText("Attempting to reconnect...")
                self.gui.z_value_box.setStyleSheet("color: orange")
                try:
                    new_port = self.gui.find_xmc1100_port()
                    if new_port:
                        self.gui.port = new_port
                        self.gui.ser = serial.Serial(self.gui.port, self.gui.baud_rate, timeout=1)
                        time.sleep(1)

                        if self.gui.thread.is_alive():
                            self.gui.stop_thread = True
                            self.gui.thread.join()

                        self.gui.stop_thread = False
                        self.gui.thread = threading.Thread(target=self.gui.read_serial)
                        self.gui.thread.daemon = True
                        self.gui.thread.start()

                        self.gui.z_value_box.setText("Reconnected")
                        self.gui.z_value_box.setStyleSheet("color: green")
                    else:
                        self.gui.z_value_box.setText("Device not found")
                        self.gui.z_value_box.setStyleSheet("color: red")
                except Exception as e:
                    self.gui.z_value_box.setText(f"Reconnect failed: {str(e)}")
                    self.gui.z_value_box.setStyleSheet("color: red")
            time.sleep(2)

    def stop(self):
        self.stop_monitor = True
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_teal.xml')  # Try 'dark_teal.xml', 'dark_cyan.xml' etc.
    window = SerialReaderGUI()
    window.show()
    sys.exit(app.exec())