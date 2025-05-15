import tkinter as tk
import serial
import serial.tools.list_ports
import threading
import time

class SerialReaderGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("XMC1100 Z-Value Monitor & Controller")
        self.master.geometry("500x300")

        # GUI Elements - Monitoring
        self.label = tk.Label(master, text="Z-Axis Magnetic Field (mT):", font=('Arial', 12))
        self.label.pack(pady=5)

        self.z_value_box = tk.Label(master, text="Disconnected", font=('Arial', 14), 
                                  bg='white', relief='sunken', width=50, height=2)
        self.z_value_box.pack(pady=5)

        # GUI Elements - Commanding
        self.cmd_frame = tk.Frame(master)
        self.cmd_frame.pack(pady=10)

        self.cmd_label = tk.Label(self.cmd_frame, text="Send Command:", font=('Arial', 10))
        self.cmd_label.grid(row=0, column=0, padx=5)

        self.cmd_entry = tk.Entry(self.cmd_frame, width=20, font=('Arial', 12))
        self.cmd_entry.grid(row=0, column=1, padx=5)

        self.send_button = tk.Button(self.cmd_frame, text="Send", 
                                   command=self.send_command, width=10)
        self.send_button.grid(row=0, column=2, padx=5)

        self.status_label = tk.Label(master, text="", fg='blue')
        self.status_label.pack()

        # Serial setup
        self.ser = None
        self.baud_rate = 115200
        self.port = self.find_xmc1100_port()
        
        if self.port:
            self.connect_serial()
        else:
            self.z_value_box.config(text="No XMC1100 found", fg='red')

        # Start thread
        self.stop_thread = False
        self.thread = threading.Thread(target=self.read_serial)
        self.thread.daemon = True
        self.thread.start()

        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Initialize connection monitor with proper thread handling
        self.connection_monitor = ConnectionMonitor(self)

    def find_xmc1100_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            print(port.description)
            if "J-Link - CDC" in port.description or "USB Serial Device" in port.description:
                return port.device
        return None

    def connect_serial(self):
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2)  # Wait for connection to stabilize
            self.z_value_box.config(text="Connected", fg='green')
        except Exception as e:
            self.z_value_box.config(text=f"Error: {str(e)}", fg='red')


    def read_serial(self):
        while not self.stop_thread:
            try:
                if self.is_connected() and self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if "Value Z is:" in line:
                        z_value = line.replace("Value Z is:", "").strip()
                        self.update_gui(z_value)
                    elif "ECHO:" in line:
                        echo = line.replace("ECHO:", "").strip()
                        self.status_label.config(text=f"Board received: {echo}", fg='blue')
            except (serial.SerialException, OSError) as e:
                self.z_value_box.config(text="Disconnected", fg='orange')
                self.ser.close()
                self.ser = None
            except Exception as e:
                self.update_gui(f"Read error: {str(e)}")
            time.sleep(0.1)


    def send_command(self):
        if not self.ser or not self.ser.is_open:
            self.status_label.config(text="Not connected to serial port!", fg='red')
            return

        cmd = self.cmd_entry.get().strip()
        if not cmd:
            self.status_label.config(text="Please enter a command", fg='red')
            return

        try:
            self.ser.write((cmd + '\n').encode('utf-8'))
            self.status_label.config(text=f"Sent: {cmd}", fg='green')
            self.cmd_entry.delete(0, tk.END)  # Clear the entry field
        except Exception as e:
            self.status_label.config(text=f"Send error: {str(e)}", fg='red')

    def update_gui(self, message):
        self.z_value_box.config(text=message)

    def is_connected(self):
        return self.ser and self.ser.is_open    

    def on_close(self):
        self.stop_thread = True
        self.connection_monitor.stop()  # Add this line
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.master.destroy()

class ConnectionMonitor:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.stop_monitor = False
        self.monitor_thread = threading.Thread(target=self.monitor_connection)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

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
                self.gui.z_value_box.config(text="Attempting to reconnect...", fg='orange')
                try:
                    new_port = self.gui.find_xmc1100_port()
                    if new_port:
                        self.gui.port = new_port
                        self.gui.ser = serial.Serial(self.gui.port, self.gui.baud_rate, timeout=1)
                        time.sleep(1)

                        # Restart reading thread safely
                        if self.gui.thread.is_alive():
                            self.gui.stop_thread = True
                            self.gui.thread.join()

                        self.gui.stop_thread = False
                        self.gui.thread = threading.Thread(target=self.gui.read_serial)
                        self.gui.thread.daemon = True
                        self.gui.thread.start()

                        self.gui.z_value_box.config(text="Reconnected", fg='green')
                    else:
                        self.gui.z_value_box.config(text="Device not found", fg='red')
                except Exception as e:
                    self.gui.z_value_box.config(text=f"Reconnect failed: {str(e)}", fg='red')
            time.sleep(2)

    def stop(self):
        self.stop_monitor = True
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()






if __name__ == '__main__':
    root = tk.Tk()
    app = SerialReaderGUI(root)
    root.mainloop()