# 企业级人脸识别 + 车牌识别工具

## 一、项目简介

本项目包含两个可直接调用的 AI 工具：

```text
1. 人脸识别工具（InsightFace + Milvus）
2. 车牌识别工具（YOLO + PaddleOCR）
```

适用于：

* 企业门禁
* 停车场
* 园区通行
* AIoT 项目
* 安防系统
* 视频监控
* 违停检测
* 道闸联动

---

# 二、整体架构

```text
摄像头/图片
    ↓
YOLO / InsightFace
    ↓
特征提取
    ↓
Milvus / OCR
    ↓
识别结果
```

---

# 三、人脸识别工具

## 1. 技术栈

```text
InsightFace
SCRFD
ArcFace
Milvus
ONNXRuntime
```

## 2. 人脸识别流程

```text
图片
→ 人脸检测
→ 人脸对齐
→ embedding提取
→ embedding归一化
→ Milvus向量检索
→ cosine similarity
→ 输出匹配结果
```

## 3. embedding 说明

系统使用：

```text
512维 embedding
```

Milvus 中存储的不是图片，而是：

```text
512维人脸向量
```

使用：

```text
COSINE 相似度
```

做人脸匹配。

---

## 4. 人脸识别安装

```bash
pip install insightface
pip install onnxruntime
pip install pymilvus
pip install opencv-python
pip install numpy
```

GPU：

```bash
pip install onnxruntime-gpu
```

---

## 5. 人脸识别调用示例

```python
from face_tool import FaceTool

face_tool = FaceTool(
    milvus_uri="https://你的-zilliz-uri",
    milvus_token="你的-token",
    collection_name="face_vectors",
    device="cpu"
)

# 初始化 collection
face_tool.init_collection()

# 注册人脸
face_tool.register(
    image="medias/faces/zhangsan.jpg",
    person_id="emp_001",
    name="张三"
)

# 识别人脸
result = face_tool.recognize(
    image="medias/faces/test.jpg",
    threshold=0.45
)

print(result)
```

---

## 6. recognize 返回结果

```python
{
    "threshold": 0.45,
    "count": 1,
    "faces": [
        {
            "matched": True,
            "bbox": [212, 192, 483, 553],
            "det_score": 0.88,
            "best": {
                "person_id": "emp_001",
                "name": "张三",
                "score": 0.73
            }
        }
    ]
}
```

---

## 7. 人脸识别关键参数

### threshold

```python
threshold=0.45
```

推荐：

| 场景 | 阈值   |
| -- | ---- |
| 宽松 | 0.35 |
| 推荐 | 0.45 |
| 严格 | 0.55 |

---

### det_score

人脸检测置信度：

```text
越高越像真实人脸
```

推荐：

```python
min_det_score = 0.5
```

---

## 8. 人脸识别优化建议

推荐：

```text
每人注册 3~5 张照片
```

例如：

* 正脸
* 左15°
* 右15°
* 弱光
* 正常光

推荐加入：

* 多帧投票
* 活体检测
* 人脸质量过滤
* AdaFace embedding

---

# 四、车牌识别工具

## 1. 技术栈

```text
YOLO
PaddleOCR 3.x
OpenCV
```

---

## 2. 车牌识别流程

```text
图片
→ YOLO检测车牌位置
→ crop裁剪车牌
→ PaddleOCR识别文字
→ 清洗车牌文本
→ 输出结果
```

---

## 3. 车牌识别安装

```bash
pip install ultralytics
pip install paddleocr
pip install paddlepaddle
pip install opencv-python
pip install numpy
```

---

## 4. 车牌检测模型

需要：

```text
车牌专用 YOLO 模型
```

例如：

```text
models/plate/best.pt
```

注意：

```text
yolo11n.pt
不是车牌模型
只是通用目标检测模型
```

---

## 5. 车牌识别调用示例

```python
from plate_tool import PlateTool

plate_tool = PlateTool(
    model_path="models/plate/best.pt",
    device="cpu",
    conf=0.25,
    scale=2,
)

result = plate_tool.recognize_best(
    r"medias/cars/car1.jpg"
)

print(result)
```

---

## 6. recognize_best 返回结果

```python
{
    "plate": "辽N0575",
    "raw_text": "辽·N0575",
    "ocr_score": 0.92,
    "det_score": 0.88,
    "bbox": [320, 420, 510, 480]
}
```

---

## 7. OCR 内部流程

```text
车牌crop
→ resize
→ PaddleOCR.predict()
→ rec_texts
→ rec_scores
→ clean_plate_text
→ 返回车牌号
```

---

## 8. 车牌识别优化建议

推荐：

```text
视频 + 多帧投票
```

而不是：

```text
单帧识别
```

因为：

* 模糊
* 夜晚
* 反光
* 运动拖影

都会影响 OCR。

---

## 9. 推荐车牌识别策略

```text
YOLO检测
→ 多帧OCR
→ 投票
→ 最终车牌
```

---

# 五、Milvus 说明

## 1. Milvus 作用

```text
向量数据库
```

负责：

```text
embedding存储
embedding搜索
TopK检索
```

---

## 2. 当前使用方式

```text
Zilliz Cloud
```

配置：

```python
milvus_uri
milvus_token
```

---

## 3. 检索方式

```text
COSINE similarity
```

score 越高：

```text
越像同一个人
```

---

# 六、ONNX 说明

InsightFace 内部使用：

```text
ONNXRuntime
```

运行：

```text
SCRFD.onnx
ArcFace.onnx
```

ONNX 的作用：

```text
模型通用部署
CPU/GPU推理
TensorRT加速
```

---

# 七、推荐生产环境

## CPU

推荐：

```text
Intel i7 / Xeon
```

---

## GPU

推荐：

```text
RTX 4060+
```

边缘部署：

```text
Jetson Orin
```

---

## 数据库

```text
Milvus
Redis
PostgreSQL
```

---

# 八、推荐项目结构

```text
project/
├── face_tool.py
├── plate_tool.py
├── medias/
├── models/
│   └── plate/
│       └── best.pt
├── demos/
└── requirements.txt
```

---

# 九、推荐后续升级方向

## 人脸

```text
AdaFace
MagFace
活体检测
多帧融合
```

---

## 车牌

```text
LPRNet
ByteTrack
违停检测
多摄像头跟踪
```

---

# 十、最终总结

当前系统已经具备：

```text
企业级人脸识别
企业级车牌识别
Milvus向量检索
OCR识别
```

适合作为：

```text
AIoT 企业项目 MVP
```

继续扩展即可支持：

* 门禁
* 考勤
* 停车场
* 道闸
* 黑名单
* 违停
* 视频监控
* 告警系统
