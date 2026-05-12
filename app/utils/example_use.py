from face_tool import FaceTool
from plate_tool import PlateTool


# 人脸识别示例
face = FaceTool(
    milvus_uri="https://your-milvus-endpoint",
    milvus_token="your-token",
    device="cpu",
)
# face.init_collection()
# face.register("samples/zhangsan.jpg", person_id="emp_001", name="张三")
# print(face.recognize("samples/live.jpg"))


# 车牌识别示例
plate = PlateTool(model_path="models/plate/best.pt", device="cpu")
# print(plate.recognize("samples/car.jpg"))
