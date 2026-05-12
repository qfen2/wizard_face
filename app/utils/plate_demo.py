import warnings

from plate_tool import PlateTool

warnings.filterwarnings(
    "ignore",
    message="No ccache found.*"
)
plate_tool = PlateTool(
    # model_path="yolo26n.pt",
    model_path="models/plate/best.pt",
    device="cpu",
    conf=0.25
)

result = plate_tool.recognize_best("medias/cars/car6.jpeg")

print(result)