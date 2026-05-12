"""
face_tool.py

一个可以直接 import 调用的人脸识别工具：
- InsightFace 提取人脸 embedding
- 云端 Milvus / Zilliz Cloud 存储和检索向量

用法：
    from face_tool import FaceTool

    face = FaceTool(
        milvus_uri="https://xxx.serverless.gcp-us-west1.cloud.zilliz.com",
        milvus_token="your-token",
        device="cuda",  # 或 "cpu"
    )

    face.init_collection()
    face.register("zhangsan.jpg", person_id="emp_001", name="张三")
    result = face.recognize("live.jpg", threshold=0.45)
    print(result)
"""

from __future__ import annotations

import datetime as _dt
import os
import threading
from dataclasses import dataclass
from typing import Any


class FaceToolError(RuntimeError):
    """人脸工具异常。"""


class NoFaceError(FaceToolError):
    """图片中未检测到人脸。"""


class MultipleFacesError(FaceToolError):
    """注册照中检测到多张人脸。"""


@dataclass(slots=True)
class FaceToolConfig:
    milvus_uri: str | None = None
    milvus_token: str | None = '0185a4afeef7d57109afce9b1c8102bcb4b3a1e03bf8da111d034c49d3a027cef475761307c7386830772e23772be0d1f01f334f'
    milvus_user: str | None = None
    milvus_password: str | None = None
    milvus_db_name: str | None = None
    collection_name: str = "face_vectors"
    vector_dim: int = 512

    # InsightFace 参数
    face_model_name: str = "buffalo_l"
    device: str = "cpu"  # "cpu" or "cuda"
    det_size: tuple[int, int] = (640, 640)
    min_det_score: float = 0.5

    # 检索参数
    default_threshold: float = 0.45
    default_top_k: int = 5

    @classmethod
    def from_env(cls) -> "FaceToolConfig":
        return cls(
            milvus_uri=os.getenv("MILVUS_URI"),
            milvus_token=os.getenv("MILVUS_TOKEN"),
            milvus_user=os.getenv("MILVUS_USER"),
            milvus_password=os.getenv("MILVUS_PASSWORD"),
            milvus_db_name=os.getenv("MILVUS_DB_NAME") or None,
            collection_name=os.getenv("FACE_COLLECTION", "face_vectors"),
            face_model_name=os.getenv("FACE_MODEL_NAME", "buffalo_l"),
            device=os.getenv("FACE_DEVICE", "cpu"),
            min_det_score=float(os.getenv("FACE_MIN_DET_SCORE", "0.5")),
            default_threshold=float(os.getenv("FACE_THRESHOLD", "0.45")),
            default_top_k=int(os.getenv("FACE_TOP_K", "5")),
        )


class FaceTool:
    """直接调用型人脸识别工具。

    参数优先级：构造函数传参 > 环境变量 > 默认值。

    环境变量可选：
        MILVUS_URI, MILVUS_TOKEN, MILVUS_USER, MILVUS_PASSWORD,
        MILVUS_DB_NAME, FACE_COLLECTION, FACE_DEVICE
    """

    def __init__(
            self,
            *,
            milvus_uri: str | None = None,
            milvus_token: str | None = None,
            milvus_user: str | None = None,
            milvus_password: str | None = None,
            milvus_db_name: str | None = None,
            collection_name: str | None = None,
            face_model_name: str | None = None,
            device: str | None = None,
            det_size: tuple[int, int] = (640, 640),
            min_det_score: float | None = None,
            threshold: float | None = None,
            top_k: int | None = None,
    ) -> None:
        env = FaceToolConfig.from_env()
        self.config = FaceToolConfig(
            milvus_uri=milvus_uri or env.milvus_uri,
            milvus_token=milvus_token or env.milvus_token,
            milvus_user=milvus_user or env.milvus_user,
            milvus_password=milvus_password or env.milvus_password,
            milvus_db_name=milvus_db_name or env.milvus_db_name,
            collection_name=collection_name or env.collection_name,
            vector_dim=512,
            face_model_name=face_model_name or env.face_model_name,
            device=device or env.device,
            det_size=det_size,
            min_det_score=env.min_det_score if min_det_score is None else min_det_score,
            default_threshold=env.default_threshold if threshold is None else threshold,
            default_top_k=env.default_top_k if top_k is None else top_k,
        )
        self._client: Any | None = None
        self._face_app: Any | None = None
        self._lock = threading.Lock()

    @property
    def client(self) -> Any:
        """MilvusClient，首次调用时懒加载。"""
        if self._client is None:
            if not self.config.milvus_uri:
                raise FaceToolError("缺少 milvus_uri。请传入 milvus_uri，或设置环境变量 MILVUS_URI。")
            try:
                from pymilvus import MilvusClient
            except Exception as exc:
                raise FaceToolError(f"无法导入 pymilvus，请先安装：pip install pymilvus。错误：{exc}") from exc

            kwargs: dict[str, Any] = {"uri": self.config.milvus_uri}
            if self.config.milvus_token:
                kwargs["token"] = self.config.milvus_token
            if self.config.milvus_user:
                kwargs["user"] = self.config.milvus_user
            if self.config.milvus_password:
                kwargs["password"] = self.config.milvus_password
            if self.config.milvus_db_name:
                kwargs["db_name"] = self.config.milvus_db_name

            self._client = MilvusClient(**kwargs)
        return self._client

    @property
    def face_app(self) -> Any:
        """InsightFace FaceAnalysis，首次调用时懒加载。"""
        if self._face_app is None:
            with self._lock:
                try:
                    from insightface.app import FaceAnalysis
                except Exception as exc:
                    raise FaceToolError(
                        "无法导入 insightface，请先安装：pip install insightface onnxruntime。"
                        f"错误：{exc}"
                    ) from exc

                if self.config.device.lower() in {"cuda", "gpu"}:
                    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                    ctx_id = 0
                else:
                    providers = ["CPUExecutionProvider"]
                    ctx_id = -1

                app = FaceAnalysis(
                    name=self.config.face_model_name,
                    providers=providers,
                    allowed_modules=["detection", "recognition"],
                )
                app.prepare(ctx_id=ctx_id, det_size=self.config.det_size)
                self._face_app = app
        return self._face_app

    def init_collection(self, *, recreate: bool = False) -> None:
        """初始化云端 Milvus Collection。

        recreate=True 会删除并重建 collection，生产环境慎用。
        """
        try:
            from pymilvus import DataType, MilvusClient
        except Exception as exc:
            raise FaceToolError(f"无法导入 pymilvus，请先安装：pip install pymilvus。错误：{exc}") from exc

        name = self.config.collection_name
        if recreate and self.client.has_collection(name):
            self.client.drop_collection(name)

        if self.client.has_collection(name):
            self._load_collection(name)
            return

        schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="person_id", datatype=DataType.VARCHAR, max_length=128)
        schema.add_field(field_name="name", datatype=DataType.VARCHAR, max_length=256)
        schema.add_field(field_name="image_id", datatype=DataType.VARCHAR, max_length=256)
        schema.add_field(field_name="created_at", datatype=DataType.VARCHAR, max_length=32)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.config.vector_dim)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=name,
            schema=schema,
            index_params=index_params,
        )
        self._load_collection(name)

    def register(
            self,
            image: str | bytes | Any,
            *,
            person_id: str,
            name: str = "",
            image_id: str = "",
    ) -> dict[str, Any]:
        """注册一张人脸到 Milvus。

        image 支持：图片路径、bytes、OpenCV BGR ndarray。
        注册照建议只包含一张清晰人脸。
        """
        self.init_collection()
        image_bgr = self._read_image(image)
        faces = self._extract_faces(image_bgr)

        if not faces:
            raise NoFaceError("未检测到可注册的人脸。")
        if len(faces) > 1:
            raise MultipleFacesError("注册图片中检测到多张人脸，请使用单人照片。")

        face = faces[0]
        row = {
            "person_id": person_id,
            "name": name,
            "image_id": image_id,
            "created_at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
            "vector": face["vector"],
        }
        result = self.client.insert(collection_name=self.config.collection_name, data=[row])
        try:
            self.client.flush(collection_name=self.config.collection_name)
        except Exception:
            # 云端 Milvus / Serverless 通常会自动处理，flush 失败不影响基本使用。
            pass

        vector_id = None
        if isinstance(result, dict):
            ids = result.get("ids") or result.get("insert_ids")
            if ids:
                vector_id = ids[0]

        return {
            "success": True,
            "person_id": person_id,
            "name": name,
            "image_id": image_id,
            "vector_id": vector_id,
            "bbox": face["bbox"],
            "det_score": face["det_score"],
        }

    def recognize(
            self,
            image: str | bytes | Any,
            *,
            threshold: float | None = None,
            top_k: int | None = None,
    ) -> dict[str, Any]:
        """识别图片中的人脸。

        返回每张脸的 bbox、TopK 候选、是否命中。
        COSINE 分数越高越相似；一般 0.40~0.55 根据业务调阈值。
        """
        self.init_collection()
        threshold = self.config.default_threshold if threshold is None else threshold
        top_k = self.config.default_top_k if top_k is None else top_k

        image_bgr = self._read_image(image)
        faces = self._extract_faces(image_bgr)
        output_faces: list[dict[str, Any]] = []

        for face in faces:
            results = self.client.search(
                collection_name=self.config.collection_name,
                data=[face["vector"]],
                anns_field="vector",
                limit=top_k,
                output_fields=["person_id", "name", "image_id"],
                search_params={"metric_type": "COSINE"},
            )
            hits = [self._parse_hit(hit) for hit in (results[0] if results else [])]
            best = hits[0] if hits else None
            matched = bool(best and float(best["score"]) >= threshold)
            output_faces.append(
                {
                    "matched": matched,
                    "bbox": face["bbox"],
                    "det_score": face["det_score"],
                    "best": best if matched else None,
                    "hits": hits,
                }
            )

        return {
            "threshold": threshold,
            "count": len(output_faces),
            "faces": output_faces,
        }

    def delete_person(self, person_id: str) -> dict[str, Any]:
        """删除某个人员的所有人脸向量。"""
        self.init_collection()
        safe_person_id = person_id.replace('"', "")
        result = self.client.delete(
            collection_name=self.config.collection_name,
            filter=f'person_id == "{safe_person_id}"',
        )
        return {"success": True, "person_id": person_id, "result": result}

    def _extract_faces(self, image_bgr: Any) -> list[dict[str, Any]]:
        try:
            import numpy as np
        except Exception as exc:
            raise FaceToolError(f"无法导入 numpy，请先安装：pip install numpy。错误：{exc}") from exc

        raw_faces = self.face_app.get(image_bgr)
        faces: list[dict[str, Any]] = []
        for face in raw_faces:
            # 人脸检测置信度，是否像人脸
            det_score = getattr(face, "det_score", None)
            det_score = float(det_score) if det_score is not None else 0.0
            if det_score < self.config.min_det_score:
                continue

            emb = getattr(face, "normed_embedding", None)
            if emb is None:
                emb = getattr(face, "embedding", None)
            if emb is None:
                continue
            emb = np.asarray(emb, dtype=np.float32)
            norm = float(np.linalg.norm(emb))
            if norm <= 0:
                continue

            # 防止没有归一化
            emb = emb / norm

            bbox = getattr(face, "bbox", [0, 0, 0, 0])
            bbox = [float(x) for x in list(bbox)]
            faces.append(
                {
                    "bbox": bbox,
                    "det_score": det_score,
                    "vector": emb.astype(float).tolist(),
                }
            )
        return faces

    @staticmethod
    def _read_image(image: str | bytes | Any) -> Any:
        try:
            import cv2
            import numpy as np
        except Exception as exc:
            raise FaceToolError("需要安装 opencv-python 和 numpy。") from exc

        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                raise FaceToolError(f"图片读取失败：{image}")
            return img

        if isinstance(image, bytes):
            arr = np.frombuffer(image, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise FaceToolError("图片 bytes 解码失败。")
            return img

        if hasattr(image, "shape"):
            return image

        raise FaceToolError("image 只支持：图片路径、bytes、OpenCV BGR ndarray。")

    @staticmethod
    def _parse_hit(hit: Any) -> dict[str, Any]:
        """解析向量数据"""
        if isinstance(hit, dict):
            entity = hit.get("entity") or {}
            score = hit.get("distance", hit.get("score", 0.0))
            return {
                "vector_id": hit.get("id"),
                "person_id": entity.get("person_id", ""),
                "name": entity.get("name", ""),
                "image_id": entity.get("image_id", ""),
                "score": float(score),
            }

        entity = getattr(hit, "entity", None) or {}
        get = entity.get if hasattr(entity, "get") else lambda key, default=None: getattr(entity, key, default)
        score = getattr(hit, "distance", getattr(hit, "score", 0.0))
        return {
            "vector_id": getattr(hit, "id", None),
            "person_id": get("person_id", ""),
            "name": get("name", ""),
            "image_id": get("image_id", ""),
            "score": float(score),
        }

    @staticmethod
    def _load_collection_static(client: Any, collection_name: str) -> None:
        try:
            client.load_collection(collection_name=collection_name)
        except Exception:
            pass

    def _load_collection(self, collection_name: str) -> None:
        self._load_collection_static(self.client, collection_name)
