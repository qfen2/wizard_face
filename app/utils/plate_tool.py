import os

os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["GLOG_minloglevel"] = "2"

import re
import cv2
import os

from ultralytics import YOLO
from paddleocr import PaddleOCR

# 理 OCR 结果多余符号
def clean_plate_text(text: str) -> str:
    text = text.upper().replace(" ", "").replace("-", "").replace(".", "").replace("·", "")
    return re.sub(r"[^A-Z0-9\u4e00-\u9fa5]", "", text)

# 把车牌小图放大 2 倍
def resize_plate(crop, scale=2):
    return cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

# 检测车牌格式
def is_possible_plate(text: str) -> bool:
    """
    判断 OCR 结果是否像一个合法车牌
    """

    if not text:
        return False

    # 普通车牌一般 7 位
    # 新能源一般 8 位
    if len(text) not in [7, 8]:
        return False

    # 必须包含中文省份简称
    has_chinese = bool(re.search(r"[\u4e00-\u9fa5]", text))

    # 必须包含字母或数字
    has_alnum = bool(re.search(r"[A-Z0-9]", text))

    return has_chinese and has_alnum

class PlateTool:
    def __init__(self, model_path="models/plate/best.pt", device="cpu", conf=0.25, scale=2):
        self.detector = YOLO(model_path)
        self.device = device
        self.conf = conf
        self.scale = scale

        self.ocr = PaddleOCR(
            lang="ch",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

    def _ocr_plate(self, crop):
        crop = resize_plate(crop, self.scale)

        # 文字识别
        result = self.ocr.predict(crop)

        if not result:
            return "", "", 0.0

        item = result[0]

        texts = item.get("rec_texts", [])
        scores = item.get("rec_scores", [])

        raw_text = "".join(texts)
        score = max(scores) if scores else 0.0

        return clean_plate_text(raw_text), raw_text, float(score)

    def recognize_best(self, image_path):
        os.path.exists(image_path)

        img = cv2.imread(image_path)

        if img is None:
            raise FileNotFoundError(f"无法读取图片，请检查路径：{os.path.abspath(image_path)}")

        results = self.detector.predict(
            img,
            conf=self.conf,
            device=self.device,
            verbose=False
        )

        best = None

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                det_score = float(box.conf[0].cpu().numpy())

                h, w = img.shape[:2]
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(w, x2)
                y2 = min(h, y2)

                crop = img[y1:y2, x1:x2]

                if crop.size == 0:
                    continue

                plate, raw, ocr_score = self._ocr_plate(crop)

                if not is_possible_plate(plate):
                    continue

                item = {
                    "plate": plate,
                    "raw_text": raw,
                    "ocr_score": ocr_score,
                    "det_score": det_score,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)]
                }

                if best is None:
                    best = item
                else:
                    old_score = len(best["plate"]) * 0.1 + best["ocr_score"] + best["det_score"] * 0.3  # type: ignore
                    new_score = len(item["plate"]) * 0.1 + item["ocr_score"] + item["det_score"] * 0.3

                    if new_score > old_score:
                        best = item

        return best