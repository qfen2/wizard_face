# Simple AI Tools

只保留两个可直接调用的工具：

- `face_tool.py`：人脸识别，InsightFace + 云端 Milvus / Zilliz Cloud
- `plate_tool.py`：车牌识别，YOLO + PaddleOCR

没有 FastAPI、没有 CLI、没有 `main.py`。

## 安装依赖

```bash
pip install -r requirements.txt
```

GPU 环境建议：

```bash
pip uninstall -y onnxruntime
pip install onnxruntime-gpu
```

## 1. 人脸工具

```python
from face_tool import FaceTool

face = FaceTool(
    milvus_uri="https://你的云端-milvus-endpoint",
    milvus_token="你的-token",
    collection_name="face_vectors",
    device="cpu",  # 有 GPU 可改为 cuda
)

# 第一次使用时初始化 collection
face.init_collection()

# 注册人脸
ret = face.register(
    "samples/zhangsan.jpg",
    person_id="emp_001",
    name="张三",
)
print(ret)

# 识别人脸
ret = face.recognize(
    "samples/live.jpg",
    threshold=0.45,
    top_k=5,
)
print(ret)

# 删除某个人的所有人脸向量
face.delete_person("emp_001")
```

也可以通过环境变量配置：

```bash
export MILVUS_URI="https://你的云端-milvus-endpoint"
export MILVUS_TOKEN="你的-token"
export FACE_COLLECTION="face_vectors"
export FACE_DEVICE="cpu"
```

然后：

```python
from face_tool import FaceTool
face = FaceTool()
```

## 2. 车牌工具

先准备你训练好的车牌 YOLO 模型，例如：

```text
models/plate/best.pt
```

调用：

```python
from plate_tool import PlateTool

plate = PlateTool(
    model_path="models/plate/best.pt",
    device="cpu",       # 有 GPU 可改成 "0" 或 "cuda"
    ocr_use_gpu=False,  # PaddleOCR 是否用 GPU
)

ret = plate.recognize("samples/car.jpg")
print(ret)

best = plate.recognize_best("samples/car.jpg")
print(best)
```

返回格式示例：

```python
{
    "count": 1,
    "plates": [
        {
            "plate": "粤B12345",
            "valid_cn_plate": True,
            "bbox": [100.0, 200.0, 300.0, 260.0],
            "det_score": 0.91,
            "ocr_score": 0.96,
            "raw_text": "粤B12345"
        }
    ]
}
```

## 备注

- 人脸注册照建议只包含一张清晰人脸。
- 车牌识别必须提供你自己的车牌检测 YOLO 权重。
- 云端 Milvus / Zilliz Cloud 只需要传 `milvus_uri` 和 `milvus_token`。
