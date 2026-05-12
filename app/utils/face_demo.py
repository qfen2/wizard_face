from face_tool import FaceTool

face_tool = FaceTool(
    milvus_uri="https://in03-f569f448720119c.serverless.aws-eu-central-1.cloud.zilliz.com",
    milvus_token="0185a4afeef7d57109afce9b1c8102bcb4b3a1e03bf8da111d034c49d3a027cef475761307c7386830772e23772be0d1f01f334f",
    collection_name="face_vectors",
    device="cpu"
)

face_tool.init_collection()

# 注册人脸
# face_tool.register(
#     image="jie2.jpg",
#     person_id="emp_001",
#     name="张三"
# )

# 识别人脸
result = face_tool.recognize(
    image="medias/humans/jie3.jpg",
    threshold=0.45,
    top_k=5
)

print(result)