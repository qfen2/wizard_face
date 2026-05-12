# coding: utf-8
"""
企业知识库与 RAG 服务模块

提供文档管理、向量化存储、智能检索等功能
"""

import os
import traceback
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import hashlib

import peewee
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
    UnstructuredExcelLoader,
    TextLoader
)
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

import config
from app.utils.db_utils import db_manager


# ==================== 数据模型 ====================
class DocumentModel:
    """文档数据模型"""
    
    TABLE_NAME = "documents"
    
    @staticmethod
    def get_table():
        """获取数据库表"""
        from peewee import Model, CharField, TextField, DateTimeField, IntegerField
        db = db_manager.get('zj3')
        
        if not hasattr(DocumentModel, '_table'):
            class DocTable(Model):
                id = IntegerField(primary_key=True)
                title = CharField(max_length=255)
                content = TextField()
                file_path = CharField(max_length=512)
                file_type = CharField(max_length=50)
                file_size = IntegerField()
                file_hash = CharField(max_length=64, unique=True)
                chunk_count = IntegerField(default=0)
                vector_store_id = CharField(max_length=255)
                metadata = TextField(default='{}')
                created_at = DateTimeField()
                updated_at = DateTimeField()
                
                class Meta:
                    database = db
                    table_name = DocumentModel.TABLE_NAME
            
            if not DocTable.table_exists():
                db.create_tables([DocTable])
            
            DocumentModel._table = DocTable
        
        return DocumentModel._table


# ==================== 文档加载器工厂 ====================
class DocumentLoaderFactory:
    """文档加载器工厂类"""
    
    LOADERS = {
        '.pdf': PyPDFLoader,
        '.docx': Docx2txtLoader,
        '.doc': Docx2txtLoader,
        '.md': UnstructuredMarkdownLoader,
        '.markdown': UnstructuredMarkdownLoader,
        '.xlsx': UnstructuredExcelLoader,
        '.xls': UnstructuredExcelLoader,
        '.txt': TextLoader,
        '.csv': TextLoader,
    }
    
    @classmethod
    def get_loader(cls, file_path: str):
        """根据文件类型获取对应的加载器"""
        ext = Path(file_path).suffix.lower()
        loader_class = cls.LOADERS.get(ext)
        
        if loader_class is None:
            raise ValueError(f"不支持的文件类型: {ext}")
        
        return loader_class(file_path)
    
    @classmethod
    def supported_types(cls) -> List[str]:
        """获取支持的文件类型列表"""
        return list(cls.LOADERS.keys())


# ==================== 文档处理器 ====================
class DocumentProcessor:
    """文档处理器：负责文档的分割和预处理"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化文档处理器
        
        Args:
            chunk_size: 文本块大小
            chunk_overlap: 文本块重叠大小
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
    
    def process(self, documents: List[Document]) -> List[Document]:
        """
        处理文档列表，进行分割
        
        Args:
            documents: 原始文档列表
            
        Returns:
            分割后的文档块列表
        """
        chunks = []
        for doc in documents:
            doc_chunks = self.text_splitter.split_documents([doc])
            chunks.extend(doc_chunks)
        
        return chunks
    
    def process_file(self, file_path: str, metadata: Dict = None) -> List[Document]:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            metadata: 额外的元数据
            
        Returns:
            分割后的文档块列表
        """
        try:
            # 对于文本文件，使用自定义的编码处理
            if Path(file_path).suffix.lower() == '.txt':
                # 尝试多种编码读取文本文件
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                content = None
                used_encoding = None
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        used_encoding = encoding
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    raise ValueError(f"无法解码文件: {file_path}")
                
                # 手动创建文档对象
                documents = [Document(page_content=content, metadata={"source": file_path})]
            else:
                loader = DocumentLoaderFactory.get_loader(file_path)
                documents = loader.load()
            
            # 添加文件元数据
            file_stat = os.stat(file_path)
            base_metadata = {
                "source": file_path,
                "file_name": Path(file_path).name,
                "file_type": Path(file_path).suffix,
                "file_size": file_stat.st_size,
                "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            }
            
            if metadata:
                base_metadata.update(metadata)
            
            for doc in documents:
                doc.metadata.update(base_metadata)
            
            return self.process(documents)
        except Exception as e:
            raise Exception(f"Error loading {file_path}: {str(e)}")


# ==================== 向量存储管理器 ====================
class VectorStoreManager:
    """向量存储管理器"""

    def __init__(self, persist_directory: str = "./vector_store"):
        """
        初始化向量存储管理器

        Args:
            persist_directory: 向量存储持久化目录
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # 初始化嵌入模型
        self.embeddings = self._create_embeddings()

        # 向量存储缓存
        self._stores = {}

    def _create_embeddings(self):
        """创建嵌入模型"""
        # 从配置中获取 OpenAI 配置
        llm_cfg = config.LLM.get('modelscope', config.LLM.get('openai', {}))

        # 使用兼容的模型名称
        # 如果使用的是 OpenAI API，使用 text-embedding-ada-002
        # 如果使用的是其他兼容 API（如 ModelScope），使用支持的模型
        model_name = llm_cfg.get('embedding_model', 'text-embedding-ada-002')

        # 如果 base_url 不为空，说明是使用兼容 API
        if llm_cfg.get('base_url'):
            # 使用兼容 API 时的模型名称
            model_name = llm_cfg.get('embedding_model', llm_cfg.get('model_name', 'text-embedding-ada-002'))

        try:
            return OpenAIEmbeddings(
                model=model_name,
                api_key=llm_cfg.get('api_key', os.getenv('OPENAI_API_KEY')),
                base_url=llm_cfg.get('base_url')
            )
        except Exception as e:
            print(f"创建嵌入模型失败: {e}")
            print(f"尝试使用默认模型: text-embedding-ada-002")
            return OpenAIEmbeddings(
                model="text-embedding-ada-002",
                api_key=llm_cfg.get('api_key', os.getenv('OPENAI_API_KEY')),
                base_url=llm_cfg.get('base_url')
            )

    def get_or_create_store(self, collection_name: str = "default") -> Chroma:
        """
        获取或创建向量存储

        Args:
            collection_name: 集合名称

        Returns:
            Chroma 向量存储实例
        """
        if collection_name not in self._stores:
            store_path = os.path.join(self.persist_directory, collection_name)

            # 使用新版本的 Chroma API
            try:
                # 尝试加载已存在的向量存储
                if os.path.exists(store_path):
                    self._stores[collection_name] = Chroma(
                        collection_name=collection_name,
                        embedding_function=self.embeddings,
                        persist_directory=store_path
                    )
                else:
                    # 创建新的向量存储
                    self._stores[collection_name] = Chroma(
                        collection_name=collection_name,
                        embedding_function=self.embeddings,
                        persist_directory=store_path
                    )
            except Exception as e:
                print(f"创建/加载向量存储失败: {e}")
                # 降级到内存模式
                print("使用内存模式作为降级方案")
                self._stores[collection_name] = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embeddings
                )
        
        return self._stores[collection_name]
    
    def add_documents(self, documents: List[Document], collection_name: str = "default") -> List[str]:
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表
            collection_name: 集合名称
            
        Returns:
            文档ID列表
        """
        store = self.get_or_create_store(collection_name)
        ids = store.add_documents(documents)
        return ids
    
    def similarity_search(
        self,
        query: str,
        collection_name: str = "default",
        k: int = 4,
        filter: Dict = None
    ) -> List[Document]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            collection_name: 集合名称
            k: 返回结果数量
            filter: 过滤条件
            
        Returns:
            相似文档列表
        """
        store = self.get_or_create_store(collection_name)
        return store.similarity_search(query, k=k, filter=filter)
    
    def delete_collection(self, collection_name: str):
        """删除集合"""
        if collection_name in self._stores:
            del self._stores[collection_name]
        
        collection_path = os.path.join(self.persist_directory, collection_name)
        if os.path.exists(collection_path):
            import shutil
            shutil.rmtree(collection_path)


# ==================== 知识库服务主类 ====================
class KnowledgeBaseService:
    """企业知识库服务主类"""
    
    def __init__(self, persist_directory: str = "./vector_store"):
        """
        初始化知识库服务
        
        Args:
            persist_directory: 向量存储持久化目录
        """
        self.vector_manager = VectorStoreManager(persist_directory)
        self.document_processor = DocumentProcessor()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def upload_document(
        self,
        file_path: str,
        collection_name: str = "default",
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        上传文档到知识库
        
        Args:
            file_path: 文件路径
            collection_name: 集合名称（默认知识库、部门知识库等）
            metadata: 额外的元数据
            
        Returns:
            上传结果字典
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 检查文件是否已存
        file_hash = self._calculate_file_hash(file_path)
        DocTable = DocumentModel.get_table()
        
        try:
            existing_doc = DocTable.get(DocTable.file_hash == file_hash)
            return {
                "success": False,
                "message": "文件已存在",
                "document_id": existing_doc.id
            }
        except peewee.DoesNotExist:
            traceback.print_exc()
        
        # 处理文档
        try:
            documents = self.document_processor.process_file(file_path, metadata)
            chunk_count = len(documents)
            
            # 添加到向量存储
            doc_ids = self.vector_manager.add_documents(documents, collection_name)
            
            # 保存到数据库 - 从文档内容中提取
            content = "\n".join([doc.page_content for doc in documents])
            if len(content) > 5000:
                content = content[:5000]
            
            now = datetime.now()
            vector_store_id = f"{collection_name}_{doc_ids[0]}"
            
            doc_record = DocTable.create(
                title=Path(file_path).stem,
                content=content,  # 使用处理后的文档内容
                file_path=file_path,
                file_type=Path(file_path).suffix,
                file_size=os.path.getsize(file_path),
                file_hash=file_hash,
                chunk_count=chunk_count,
                vector_store_id=vector_store_id,
                metadata=str(metadata or {}),
                created_at=now,
                updated_at=now
            )
            
            return {
                "success": True,
                "message": "文档上传成功",
                "document_id": doc_record.id,
                "chunk_count": chunk_count,
                "collection_name": collection_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"文档处理失败: {str(e)}",
                "error": str(e)
            }
    
    def search(
        self,
        query: str,
        collection_name: str = "default",
        k: int = 4,
        filter: Dict = None
    ) -> List[Dict[str, Any]]:
        """
        在知识库中搜索
        
        Args:
            query: 查询文本
            collection_name: 集合名称
            k: 返回结果数量
            filter: 过滤条件
            
        Returns:
            搜索结果列表
        """
        documents = self.vector_manager.similarity_search(
            query,
            collection_name=collection_name,
            k=k,
            filter=filter
        )
        
        results = []
        for doc in documents:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": getattr(doc, 'score', None)
            })
        
        return results
    
    def create_qa_chain(
        self,
        collection_name: str = "default",
        model_name: str = "Qwen/Qwen3-Coder-480B-A35B-Instruct"
    ):
        """
        创建问答链（使用 LCEL API）
        
        Args:
            collection_name: 集合名称
            model_name: 使用的模型名称
            
        Returns:
            问答链实例
        """
        store = self.vector_manager.get_or_create_store(collection_name)
        retriever = store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )
        
        llm_cfg = config.LLM.get('modelscope', config.LLM.get('openai', {}))
        llm = ChatOpenAI(
            model=model_name,
            api_key=llm_cfg.get('api_key', os.getenv('OPENAI_API_KEY')),
            base_url=llm_cfg.get('base_url'),
            temperature=0.3
        )
        
        # 定义提示词模板
        template = """你是一个专业的问答助手。请根据以下检索到的上下文信息来回答用户的问题。

        上下文信息：
        {context}
        
        用户问题：{question}
        
        请基于上下文信息提供准确、有用的回答。如果上下文信息不足以回答问题，请诚实地说明。
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # 使用 LCEL 构建链
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        qa_chain = (
            {
                "context": retriever | format_docs,
                "question": RunnablePassthrough()
            }
            | prompt
            | llm
            | StrOutputParser()
        )
        
        return qa_chain
    
    def ask(
        self,
        question: str,
        collection_name: str = "default",
        return_sources: bool = True,
        model_name: str = None
    ) -> Dict[str, Any]:
        """
        向知识库提问
        
        Args:
            question: 问题
            collection_name: 集合名称
            return_sources: 是否返回来源文档
            model_name: 使用的模型名称（可选，默认使用配置中的模型）
            
        Returns:
            问答结果
        """
        try:
            # 获取检索器和 LLM
            store = self.vector_manager.get_or_create_store(collection_name)
            retriever = store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 4}
            )
            
            # 先检索相关文档
            retrieved_docs = retriever.invoke(question)
            
            # 如果没有指定模型名称，使用配置中的模型
            if model_name is None:
                llm_cfg = config.LLM.get('modelscope', config.LLM.get('openai', {}))
                model_name = llm_cfg.get('model_name', 'gpt-4o-mini')
            
            # 创建 QA 链
            qa_chain = self.create_qa_chain(collection_name, model_name=model_name)
            
            # 调用链生成回答
            answer = qa_chain.invoke(question)
            
            response = {
                "answer": answer,
                "success": True
            }
            
            # 添加来源文档
            if return_sources:
                sources = []
                for doc in retrieved_docs:
                    sources.append({
                        "content": doc.page_content[:200],
                        "metadata": doc.metadata
                    })
                response["sources"] = sources
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "answer": f"查询失败: {str(e)}",
                "error": str(e)
            }
    
    def list_documents(self, collection_name: str = None) -> List[Dict]:
        """
        列出知识库中的文档
        
        Args:
            collection_name: 集合名称（可选）
            
        Returns:
            文档列表
        """
        DocTable = DocumentModel.get_table()
        query = DocTable.select()
        
        if collection_name:
            query = query.where(DocTable.vector_store_id.startswith(collection_name))
        
        documents = []
        for doc in query:
            documents.append({
                "id": doc.id,
                "title": doc.title,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "chunk_count": doc.chunk_count,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat()
            })
        
        return documents
    
    def delete_document(self, document_id: int) -> bool:
        """
        删除文档
        
        Args:
            document_id: 文档ID
            
        Returns:
            是否删除成功
        """
        try:
            DocTable = DocumentModel.get_table()
            doc = DocTable.get(DocTable.id == document_id)
            
            # 从向量存储中删除（需要实现具体的删除逻辑）
            # 这里简化处理，实际需要根据 vector_store_id 删除对应的向量
            
            # 从数据库中删除
            doc.delete_instance()
            
            return True
            
        except Exception as e:
            print(f"删除文档失败: {e}")
            return False


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 创建知识库服务
    kb_service = KnowledgeBaseService(persist_directory="./data/vector_store")
    
    # 上传文档
    # print("上传文档...")
    # 使用绝对路径
    # import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(base_dir, "app/utils/langchain_langgraph/user_uploads/manual.txt")
    
    result = kb_service.upload_document(
        file_path='C:/Users/liukk/Desktop/wizard/app/utils/langchain_langgraph/user_uploads/budget.xlsx',
        collection_name="manuals",
        metadata={"category": "预算", "department": "财务部"}
    )
    print(f"上传结果: {result}")
    store = kb_service.vector_manager.get_or_create_store("manuals")
    try:
        # 使用正确的 API 获取文档数量
        count = store._collection.count()
        print(f"向量存储中的文档数量: {count}")
    except Exception as e:
        print(f"获取文档数量失败: {e}")

    query="分析所有部门的的财务情况"
    # 搜索文档
    print("\n搜索文档...")
    search_results = kb_service.search(
        query=query,
        collection_name="manuals",
        k=3
    )
    for i, result in enumerate(search_results):
        print(f"\n结果 {i+1}:")
        print(f"内容: {result['content'][:100]}...")
        print(f"元数据: {result['metadata']}")

    store = kb_service.vector_manager.get_or_create_store("manuals")
    retriever = store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    docs = retriever.invoke(query)
    print(f"检索到的文档数量: {len(docs)}")
    for i, doc in enumerate(docs):
        print(f"\n文档 {i + 1}:")
        print(f"完整内容: {doc.page_content}")
        print(f"元数据: {doc.metadata}")

    # 问答
    print("\n向知识库提问...")
    qa_result = kb_service.ask(
        question=query,
        collection_name="manuals",
        return_sources = True
    )
    print(f"回答: {qa_result['answer']}")
    if 'sources' in qa_result:
        print(f"来源数量: {len(qa_result['sources'])}")
    
    # 列出文档
    print("\n列出所有文档...")
    docs = kb_service.list_documents(collection_name="manuals")
    for doc in docs:
        print(f"- {doc['title']} {doc['file_type']} - {doc['chunk_count']} 个片段")