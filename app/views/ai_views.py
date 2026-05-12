# coding: utf-8
"""
企业级 AI 服务 API 视图

提供知识库、智能体、工作流、报告、安全等功能的API接口
"""

from flask import request, jsonify
from app.views.basic_views import LoginRequiredDispatchView
from app._webapi import rpc, InputType, required, optional

from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.enterprise_agents import CustomerServiceAgent, ApprovalAgent, DataAnalysisAgent
from app.services.workflow_service import WorkflowOrchestrator
from app.services.report_service import DataAnalysisService
from app.services.security_service import SecurityService
from app.models.document_model import UserPermission, create_tables


# ==================== 初始化服务 ====================
# 创建数据库表
try:
    create_tables()
except Exception as e:
    print(f"创建数据表失败: {e}")

# 初始化服务实例
kb_service = KnowledgeBaseService(persist_directory="./data/vector_store")
workflow_orchestrator = WorkflowOrchestrator()
analysis_service = DataAnalysisService()
security_service = SecurityService()


# ==================== API 视图类 ====================
class AI(LoginRequiredDispatchView):
    """AI 服务 API"""
    
    # ==================== 知识库相关 ====================
    
    @rpc(
        '上传文档到知识库',
        args=dict(
            file_path=required.StringField(desc='文件路径'),
            collection_name=optional.StringField(desc='集合名称', default='default'),
            metadata=optional.StringField(desc='元数据JSON', default='{}')
        ),
        returns=dict(
            success=required.BooleanField(desc='是否成功'),
            message=optional.StringField(desc='消息'),
            document_id=optional.IntegerField(desc='文档ID'),
            chunk_count=optional.IntegerField(desc='分块数量')
        ),
        input_type=InputType.JSON
    )
    def upload_document_POST(self, req, rsp):
        """上传文档到知识库"""
        import json
        metadata = json.loads(req.get('metadata', '{}'))
        
        result = kb_service.upload_document(
            file_path=req.get('file_path'),
            collection_name=req.get('collection_name', 'default'),
            metadata=metadata
        )
        
        rsp.data = result
    
    @rpc(
        '在知识库中搜索',
        args=dict(
            query=required.StringField(desc='查询文本'),
            collection_name=optional.StringField(desc='集合名称', default='default'),
            k=optional.IntegerField(desc='返回结果数量', default=4)
        ),
        returns=dict(
            results=optional.StringField(desc='搜索结果')
        ),
        input_type=InputType.JSON
    )
    def search_knowledge_POST(self, req, rsp):
        """在知识库中搜索"""
        import json
        results = kb_service.search(
            query=req.get('query'),
            collection_name=req.get('collection_name', 'default'),
            k=req.get('k', 4)
        )
        
        rsp.data = {'results': json.dumps(results, ensure_ascii=False)}
    
    @rpc(
        '向知识库提问',
        args=dict(
            question=required.StringField(desc='问题'),
            collection_name=optional.StringField(desc='集合名称', default='default')
        ),
        returns=dict(
            answer=optional.StringField(desc='回答'),
            sources=optional.StringField(desc='来源')
        ),
        input_type=InputType.JSON
    )
    def ask_knowledge_POST(self, req, rsp):
        """向知识库提问"""
        import json
        result = kb_service.ask(
            question=req.get('question'),
            collection_name=req.get('collection_name', 'default'),
            return_sources=True
        )
        
        rsp.data = {
            'answer': result.get('answer', ''),
            'sources': json.dumps(result.get('sources', []), ensure_ascii=False)
        }
    
    @rpc(
        '列出知识库文档',
        args=dict(
            collection_name=optional.StringField(desc='集合名称')
        ),
        returns=dict(
            documents=optional.StringField(desc='文档列表')
        ),
        input_type=InputType.JSON
    )
    def list_documents_POST(self, req, rsp):
        """列出知识库文档"""
        import json
        documents = kb_service.list_documents(
            collection_name=req.get('collection_name')
        )
        
        rsp.data = {'documents': json.dumps(documents, ensure_ascii=False)}
    
    # ==================== 智能体相关 ====================
    
    @rpc(
        '客服智能体对话',
        args=dict(
            user_id=required.StringField(desc='用户ID'),
            query=required.StringField(desc='用户查询')
        ),
        returns=dict(
            response=optional.StringField(desc='响应'),
            intent=optional.StringField(desc='意图'),
            needs_human=optional.BooleanField(desc='是否需要人工')
        ),
        input_type=InputType.JSON
    )
    def customer_service_chat_POST(self, req, rsp):
        """客服智能体对话"""
        agent = CustomerServiceAgent()
        result = agent.chat(
            user_id=req.get('user_id'),
            query=req.get('query')
        )
        
        rsp.data = {
            'response': result.get('response', ''),
            'intent': result.get('intent', ''),
            'needs_human': result.get('needs_human', False)
        }
    
    @rpc(
        '审批请求处理',
        args=dict(
            request_id=required.StringField(desc='请求ID'),
            request_type=required.StringField(desc='请求类型'),
            request_data=required.StringField(desc='请求数据'),
            requester=required.StringField(desc='请求人')
        ),
        returns=dict(
            decision=optional.StringField(desc='决定'),
            reason=optional.StringField(desc='理由'),
            risk_level=optional.StringField(desc='风险等级')
        ),
        input_type=InputType.JSON
    )
    def approval_request_POST(self, req, rsp):
        """审批请求处理"""
        agent = ApprovalAgent()
        result = agent.approve_request(
            request_id=req.get('request_id'),
            request_type=req.get('request_type'),
            request_data=req.get('request_data'),
            requester=req.get('requester')
        )
        
        rsp.data = {
            'decision': result.get('decision', ''),
            'reason': result.get('reason', ''),
            'risk_level': result.get('risk_level', '')
        }
    
    @rpc(
        '数据分析',
        args=dict(
            analysis_task=required.StringField(desc='分析任务'),
            data_source=required.StringField(desc='数据源')
        ),
        returns=dict(
            insights=optional.StringField(desc='洞察'),
            report=optional.StringField(desc='报告')
        ),
        input_type=InputType.JSON
    )
    def data_analysis_POST(self, req, rsp):
        """数据分析"""
        import json
        agent = DataAnalysisAgent()
        result = agent.analyze(
            analysis_task=req.get('analysis_task'),
            data_source=req.get('data_source')
        )
        
        rsp.data = {
            'insights': json.dumps(result.get('insights', []), ensure_ascii=False),
            'report': result.get('report', '')
        }
    
    # ==================== 工作流相关 ====================
    
    @rpc(
        '处理用户消息',
        args=dict(
            user_id=required.StringField(desc='用户ID'),
            message=required.StringField(desc='消息'),
            session_id=optional.StringField(desc='会话ID'),
            context=optional.StringField(desc='上下文JSON', default='{}')
        ),
        returns=dict(
            session_id=optional.StringField(desc='会话ID'),
            intent=optional.StringField(desc='意图'),
            agent_type=optional.StringField(desc='智能体类型'),
            response=optional.StringField(desc='响应')
        ),
        input_type=InputType.JSON
    )
    def process_message_POST(self, req, rsp):
        """处理用户消息（工作流编排）"""
        import json
        context = json.loads(req.get('context', '{}'))
        
        result = workflow_orchestrator.process_message(
            user_id=req.get('user_id'),
            message=req.get('message'),
            session_id=req.get('session_id'),
            context=context
        )
        
        rsp.data = result
    
    @rpc(
        '获取会话历史',
        args=dict(
            session_id=required.StringField(desc='会话ID')
        ),
        returns=dict(
            messages=optional.StringField(desc='消息历史')
        ),
        input_type=InputType.JSON
    )
    def get_session_history_POST(self, req, rsp):
        """获取会话历史"""
        import json
        messages = workflow_orchestrator.get_session_history(
            session_id=req.get('session_id')
        )
        
        rsp.data = {'messages': json.dumps(messages, ensure_ascii=False)}
    
    @rpc(
        '关闭会话',
        args=dict(
            session_id=required.StringField(desc='会话ID')
        ),
        returns=dict(
            success=optional.BooleanField(desc='是否成功')
        ),
        input_type=InputType.JSON
    )
    def close_session_POST(self, req, rsp):
        """关闭会话"""
        success = workflow_orchestrator.close_session(
            session_id=req.get('session_id')
        )
        
        rsp.data = {'success': success}
    
    # ==================== 报告相关 ====================
    
    @rpc(
        '生成数据分析报告',
        args=dict(
            data_source=optional.StringField(desc='数据源'),
            data_type=optional.StringField(desc='数据类型', default='sales'),
            query=optional.StringField(desc='SQL查询'),
            report_type=optional.StringField(desc='报告类型', default='general')
        ),
        returns=dict(
            success=optional.BooleanField(desc='是否成功'),
            summary=optional.StringField(desc='报告摘要'),
            report=optional.StringField(desc='完整报告'),
            insights=optional.StringField(desc='洞察')
        ),
        input_type=InputType.JSON
    )
    def generate_report_POST(self, req, rsp):
        """生成数据分析报告"""
        import json
        result = analysis_service.analyze_report(
            data_source=req.get('data_source'),
            data_type=req.get('data_type', 'sales'),
            query=req.get('query'),
            report_type=req.get('report_type', 'general')
        )
        
        rsp.data = {
            'success': result.get('success', False),
            'summary': result.get('summary', ''),
            'report': result.get('report', ''),
            'insights': json.dumps(result.get('insights', []), ensure_ascii=False)
        }
    
    @rpc(
        '快速数据分析',
        args=dict(
            data_source=required.StringField(desc='数据源'),
            columns=optional.StringField(desc='列名JSON数组', default='[]')
        ),
        returns=dict(
            success=optional.BooleanField(desc='是否成功'),
            statistics=optional.StringField(desc='统计信息'),
            insights=optional.StringField(desc='洞察')
        ),
        input_type=InputType.JSON
    )
    def quick_analysis_POST(self, req, rsp):
        """快速数据分析"""
        import json
        columns = json.loads(req.get('columns', '[]'))
        
        result = analysis_service.quick_analysis(
            data_source=req.get('data_source'),
            columns=columns if columns else None
        )
        
        rsp.data = {
            'success': result.get('success', False),
            'statistics': json.dumps(result.get('statistics', {}), ensure_ascii=False),
            'insights': json.dumps(result.get('insights', []), ensure_ascii=False)
        }
    
    # ==================== 安全相关 ====================
    
    @rpc(
        '用户登录',
        args=dict(
            user_id=required.StringField(desc='用户ID'),
            password=required.StringField(desc='密码')
        ),
        returns=dict(
            success=optional.BooleanField(desc='是否成功'),
            token=optional.StringField(desc='访问令牌'),
            role=optional.StringField(desc='角色'),
            expires_in=optional.IntegerField(desc='过期时间')
        ),
        input_type=InputType.JSON
    )
    def login_POST(self, req, rsp):
        """用户登录"""
        result = security_service.login(
            user_id=req.get('user_id'),
            password=req.get('password')
        )
        
        rsp.data = result
    
    @rpc(
        '用户登出',
        args=dict(
            token=required.StringField(desc='访问令牌')
        ),
        returns=dict(
            success=optional.BooleanField(desc='是否成功'),
            message=optional.StringField(desc='消息')
        ),
        input_type=InputType.JSON
    )
    def logout_POST(self, req, rsp):
        """用户登出"""
        result = security_service.logout(token=req.get('token'))
        rsp.data = result
    
    @rpc(
        '检查访问权限',
        args=dict(
            token=required.StringField(desc='访问令牌'),
            permission=required.StringField(desc='权限名称')
        ),
        returns=dict(
            success=optional.BooleanField(desc='是否有权限'),
            message=optional.StringField(desc='消息')
        ),
        input_type=InputType.JSON
    )
    def check_access_POST(self, req, rsp):
        """检查访问权限"""
        result = security_service.check_access(
            token=req.get('token'),
            permission=req.get('permission')
        )
        rsp.data = result
    
    @rpc(
        '脱敏敏感数据',
        args=dict(
            data=required.StringField(desc='数据JSON'),
            fields=optional.StringField(desc='字段JSON数组', default='[]')
        ),
        returns=dict(
            masked_data=optional.StringField(desc='脱敏后数据')
        ),
        input_type=InputType.JSON
    )
    def mask_data_POST(self, req, rsp):
        """脱敏敏感数据"""
        import json
        data = json.loads(req.get('data'))
        fields = json.loads(req.get('fields', '[]'))
        
        masked_data = security_service.mask_sensitive_data(
            data=data,
            fields=fields if fields else None
        )
        
        rsp.data = {'masked_data': json.dumps(masked_data, ensure_ascii=False)}
    
    @rpc(
        '分配用户角色',
        args=dict(
            user_id=required.StringField(desc='用户ID'),
            role=required.StringField(desc='角色')
        ),
        returns=dict(
            success=optional.BooleanField(desc='是否成功')
        ),
        input_type=InputType.JSON
    )
    def assign_role_POST(self, req, rsp):
        """分配用户角色"""
        from app.services.security_service import PermissionManager
        perm_manager = PermissionManager()
        
        success = perm_manager.assign_role(
            user_id=req.get('user_id'),
            role=req.get('role')
        )
        
        rsp.data = {'success': success}