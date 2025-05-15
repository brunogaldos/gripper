from ultralytics import YOLO


if __name__ == "__main__":
    # model = YOLO(r"weights\weights--50ep\best.pt")  # load an official model
    # model = YOLO(r"weights\weights3--100ep\best.pt")  # load an official model
    model = YOLO(r"D:\TempOutsideOneDrive\weights\weights4--100ep\best.pt")  # load an official model
    path_testimages = r"D:\TempOutsideOneDrive\Camera2\test"
    # Predict with the model
    # Predict with live webcam
    results = model.predict(source=0, show=True)  # predict with the model
    # results = model.predict(source=path_testimages,
    #                         save_conf = True)  # predict with the model