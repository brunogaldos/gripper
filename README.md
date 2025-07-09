# Adaptive Vision-Guided Robotic Gripper

This project demonstrates an adaptive, torque-controlled robotic gripper capable of handling a wide spectrum of objects—from fragile balloons to heavy metal rods—without manual reconfiguration. By combining precision magnetic sensing, adaptive PID torque control, lightweight deep learning, and an intuitive GUI, the system achieves both hands-on versatility and vision-guided autonomy.

---

## Features

- **Torque-Controlled Gripping**  
  – Zero-bias correction and 5-sample median filtering of Z-axis magnetic readings  
  – PID controller (kp = 2.5, ki = 0.5, kd = 0.1) for smooth, stable closing  
  – Safety clamp enforces –3 V minimum (closing) and 0 V maximum (idle)  
  – Automatic “STOP” on contact detection to hold grip without damage  

- **Vision-Based Classification**  
  – YOLO-style CNN trained on ~100 images (metal, wood, balloon, background)  
  – High accuracy via transfer learning and aggressive augmentation  
  – Designed for online fine-tuning to recognize new object classes  

- **Two-Tab GUI**  
  – **Manual Mode** – Direct “Hard” or “Soft” presets, Open/Close buttons, real-time status bar  
  – **Automatic Mode** – Live camera feed with object bounding boxes, auto-actuation routines, action log, “Pause” control  

---

## Task 1: Sensor Filtering and Torque Control

1. **Calibration** – Collect 20 samples to compute x/y/z offsets.  
2. **Median Filter** – Buffer the last five Z-axis readings, sort them, and select the median to reject spikes.  
3. **PID Control** – Compute error = setpoint – ΔZ, then apply P/I/D gains to generate a negative drive voltage.  
4. **Safety Clamp** – Ensure a minimum of –3 V for movement; cap at 0 V to prevent over-exertion.  
5. **Contact Detection** – When the filtered deviation enters the preset window (0.20–0.245 T), print `"STOP"` and zero the voltage to maintain grip.

---

## Task 2: Vision-Based Object Classification

- A compact CNN processes each camera frame, identifies object class (metal, wood, balloon, background), and outputs bounding boxes and labels in real time.  
- Hard objects trigger the high-torque closing routine; soft objects invoke a low-force, PID-filtered sequence.  
- The model can be incrementally retrained online for future generalization to arbitrary objects.

---

## User Interface

### Manual Mode
- **Radio Buttons**: Toggle between “Hard Object” and “Soft Object.”  
- **Action Buttons**: “Open Gripper” / “Close Gripper” send immediate commands.  
- **Status Bar**: Displays target voltage and sensor feedback; tooltips indicate active force profile.

### Automatic Mode
- **Live Feed**: YOLO overlays show bounding boxes and labels.  
- **Auto-Actuation**: Executes appropriate grip routine upon classification.  
- **Action Log**: Timestamps each detection and action (e.g., “Detected: Balloon → executing soft grip”).  
- **Pause Control**: Halts video feed and actuation for inspection or safety.

---

By uniting robust magnetic sensing, refined PID control, AI-driven vision, and a user-centric GUI, this gripper delivers reliable, adaptive performance across diverse pick-and-place tasks.  


https://github.com/user-attachments/assets/20fb79ab-a6c5-40cd-9c8c-7b2fdb01e51a



