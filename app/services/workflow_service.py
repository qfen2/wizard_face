# coding: utf-8
"""
工作流服务模块

提供会话管理、意图识别、流程编排等功能
"""

import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum

import config
from app.models.document_model import ChatSession, ChatMessage, WorkflowTask
from app.utils.db_utils import db_manager
from app.services.enterprise_agents import CustomerServiceAgent, ApprovalAgent, DataAnalysisAgent


# ==================== 意图类型枚举 ====================
class IntentType(Enum):
    """意图类型"""
    GREETING = "greeting"  # 问候
    QUESTION = "question"  # 提问
    COMPLAINT = "complaint"  # 投诉
    REQUEST = "request"  # 请求
    APPROVAL = "approval"  # 审批
    ANALYSIS = "analysis"  # 分析
    OTHER = "other"  # 其他


# ==================== 会话管理器 ====================
class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        """初始化会话管理器"""
        self.active_sessions = {}  # 内存中的活跃会话缓存
    
    def create_session(
        self,
        user_id: str,
        agent_type: str,
        title: str = None,
        metadata: Dict = None
    ) -> str:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            agent_type: 智能体类型
            title: 会话标题
            metadata: 元数据
            
        Returns:
            会话ID
        """
        session_id = str(uuid.uuid4())
        
        if not title:
            title = f"{agent_type}会话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # 保存到数据库
        ChatSession.create(
            session_id=session_id,
            user_id=user_id,
            agent_type=agent_type,
            title=title,
            status='active',
            metadata=str(metadata or {}),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 添加到缓存
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'agent_type': agent_type,
            'created_at': datetime.now()
        }
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息字典
        """
        # 先从缓存获取
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # 从数据库获取
        try:
            session = ChatSession.get(ChatSession.session_id == session_id)
            return {
                'session_id': session.session_id,
                'user_id': session.user_id,
                'agent_type': session.agent_type,
                'title': session.title,
                'status': session.status,
                'created_at': session.created_at.isoformat()
            }
        except ChatSession.DoesNotExist:
            return None
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens_used: int = 0
    ) -> bool:
        """
        添加消息到会话
        
        Args:
            session_id: 会话ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            tokens_used: 使用的Token数
            
        Returns:
            是否添加成功
        """
        try:
            ChatMessage.create(
                session_id=session_id,
                role=role,
                content=content,
                tokens_used=tokens_used,
                created_at=datetime.now()
            )
            
            # 更新会话时间
            session = ChatSession.get(ChatSession.session_id == session_id)
            session.updated_at = datetime.now()
            session.save()
            
            return True
        except Exception as e:
            print(f"添加消息失败: {e}")
            return False
    
    def get_messages(self, session_id: str, limit: int = 20) -> List[Dict]:
        """
        获取会话消息历史
        
        Args:
            session_id: 会话ID
            limit: 返回消息数量限制
            
        Returns:
            消息列表
        """
        try:
            messages = ChatMessage.select().where(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.desc()).limit(limit)
            
            return [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'tokens_used': msg.tokens_used,
                    'created_at': msg.created_at.isoformat()
                }
                for msg in reversed(list(messages))
            ]
        except Exception as e:
            print(f"获取消息失败: {e}")
            return []
    
    def close_session(self, session_id: str) -> bool:
        """
        关闭会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否关闭成功
        """
        try:
            session = ChatSession.get(ChatSession.session_id == session_id)
            session.status = 'closed'
            session.updated_at = datetime.now()
            session.save()
            
            # 从缓存移除
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            return True
        except Exception as e:
            print(f"关闭会话失败: {e}")
            return False


# ==================== 意图识别器 ====================
class IntentRecognizer:
    """意图识别器"""
    
    def __init__(self):
        """初始化意图识别器"""
        from langchain_openai import ChatOpenAI
        
        llm_cfg = config.LLM.get('openai', config.LLM.get('modelscope', {}))
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=llm_cfg.get('api_key'),
            base_url=llm_cfg.get('base_url'),
            temperature=0.1
        )
        
        # 意图关键词映射
        self.intent_keywords = {
            IntentType.GREETING: ['你好', 'hello', 'hi', '早上好', '下午好', '晚上好'],
            IntentType.QUESTION: ['怎么', '如何', '什么', '为什么', '哪里', '哪个', '吗', '?', '？'],
            IntentType.COMPLAINT: ['投诉', '抱怨', '不满', '问题', '错误', '故障'],
            IntentType.REQUEST: ['请', '帮忙', '需要', '想要', '申请', '请求'],
            IntentType.APPROVAL: ['审批', '批准', '同意', '通过', '审核'],
            IntentType.ANALYSIS: ['分析', '统计', '报告', '数据', '趋势']
        }
    
    def recognize(self, text: str) -> Dict[str, Any]:
        """
        识别用户意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            意图识别结果
        """
        # 基于关键词的快速识别
        for intent_type, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    return {
                        'intent': intent_type.value,
                        'confidence': 0.8,
                        'method': 'keyword'
                    }
        
        # 使用LLM进行意图识别
        prompt = f"""识别以下用户查询的意图类型。

用户查询：{text}

可能的意图类型：
- greeting: 问候
- question: 提问
- complaint: 投诉
- request: 请求
- approval: 审批
- analysis: 分析
- other: 其他

请以JSON格式返回：
{{
    "intent": "意图类型",
    "confidence": 0.95,
    "reasoning": "推理过程"
}}"""
        
        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt)])
            result = self._parse_json_response(response.content)
            
            return {
                'intent': result.get('intent', 'other'),
                'confidence': result.get('confidence', 0.7),
                'method': 'llm',
                'reasoning': result.get('reasoning', '')
            }
        except Exception as e:
            print(f"LLM意图识别失败: {e}")
            return {
                'intent': 'other',
                'confidence': 0.5,
                'method': 'fallback'
            }
    
    def _parse_json_response(self, text: str) -> Dict:
        """解析JSON响应"""
        try:
            import json
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
        except:
            pass
        return {}


# ==================== 流程编排器 ====================
class WorkflowOrchestrator:
    """流程编排器"""
    
    def __init__(self, session_manager: SessionManager = None):
        """
        初始化流程编排器
        
        Args:
            session_manager: 会话管理器实例
        """
        self.session_manager = session_manager or SessionManager()
        self.intent_recognizer = IntentRecognizer()
        
        # 初始化各智能体
        self.agents = {
            'customer_service': CustomerServiceAgent(),
            'approval': ApprovalAgent(),
            'data_analysis': DataAnalysisAgent()
        }
    
    def route_to_agent(self, intent: str) -> str:
        """
        根据意图路由到对应的智能体
        
        Args:
            intent: 意图类型
            
        Returns:
            智能体类型
        """
        routing_rules = {
            IntentType.GREETING.value: 'customer_service',
            IntentType.QUESTION.value: 'customer_service',
            IntentType.COMPLAINT.value: 'customer_service',
            IntentType.REQUEST.value: 'customer_service',
            IntentType.APPROVAL.value: 'approval',
            IntentType.ANALYSIS.value: 'data_analysis',
            IntentType.OTHER.value: 'customer_service'
        }
        
        return routing_rules.get(intent, 'customer_service')
    
    def process_message(
        self,
        user_id: str,
        message: str,
        session_id: str = None,
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            user_id: 用户ID
            message: 用户消息
            session_id: 会话ID（可选）
            context: 上下文信息
            
        Returns:
            处理结果
        """
        # 记录用户消息
        if session_id:
            self.session_manager.add_message(session_id, 'user', message)
        
        # 识别意图
        intent_result = self.intent_recognizer.recognize(message)
        intent = intent_result['intent']
        
        # 路由到对应的智能体
        agent_type = self.route_to_agent(intent)
        
        # 如果没有会话，创建新会话
        if not session_id:
            session_id = self.session_manager.create_session(
                user_id=user_id,
                agent_type=agent_type,
                title=message[:50]
            )
        
        # 调用对应的智能体处理
        response = self._call_agent(agent_type, user_id, message, context)
        
        # 记录助手消息
        self.session_manager.add_message(
            session_id,
            'assistant',
            response.get('response', ''),
            response.get('tokens_used', 0)
        )
        
        return {
            'session_id': session_id,
            'intent': intent,
            'agent_type': agent_type,
            'response': response.get('response', ''),
            'metadata': {
                'confidence': intent_result.get('confidence', 0),
                'context': context
            }
        }
    
    def _call_agent(
        self,
        agent_type: str,
        user_id: str,
        message: str,
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        调用智能体
        
        Args:
            agent_type: 智能体类型
            user_id: 用户ID
            message: 消息
            context: 上下文
            
        Returns:
            智能体响应
        """
        agent = self.agents.get(agent_type)
        
        if not agent:
            return {
                'response': '抱歉，我暂时无法处理此类请求。',
                'tokens_used': 0
            }
        
        try:
            if agent_type == 'customer_service':
                result = agent.chat(user_id, message)
                return {
                    'response': result['response'],
                    'tokens_used': 0  # 可以根据实际使用计算
                }
            elif agent_type == 'approval':
                # 审批需要更多上下文
                request_data = context.get('request_data', message)
                result = agent.approve_request(
                    request_id=context.get('request_id', str(uuid.uuid4())),
                    request_type=context.get('request_type', 'general'),
                    request_data=request_data,
                    requester=user_id
                )
                return {
                    'response': f"审批决定：{result['decision']}。理由：{result['reason']}",
                    'tokens_used': 0
                }
            elif agent_type == 'data_analysis':
                result = agent.analyze(
                    analysis_task=message,
                    data_source=context.get('data_source', 'default')
                )
                return {
                    'response': result['report'][:500],  # 返回报告摘要
                    'tokens_used': 0
                }
        except Exception as e:
            return {
                'response': f'处理请求时出错：{str(e)}',
                'tokens_used': 0
            }
        
        return {
            'response': '抱歉，我暂时无法处理此类请求。',
            'tokens_used': 0
        }
    
    def get_session_history(self, session_id: str) -> List[Dict]:
        """
        获取会话历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            消息历史列表
        """
        return self.session_manager.get_messages(session_id)
    
    def close_session(self, session_id: str) -> bool:
        """
        关闭会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否关闭成功
        """
        return self.session_manager.close_session(session_id)


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 创建流程编排器
    orchestrator = WorkflowOrchestrator()
    
    print("=" * 60)
    print("智能客服与业务流程自动化示例")
    print("=" * 60)
    
    # 模拟用户对话
    user_id = "user123"
    
    # 对话1：问候
    print("\n用户: 你好")
    result1 = orchestrator.process_message(user_id, "你好")
    print(f"意图: {result1['intent']}")
    print(f"智能体: {result1['agent_type']}")
    print(f"回复: {result1['response']}")
    session_id = result1['session_id']
    
    # 对话2：提问
    print("\n用户: 如何申请退款？")
    result2 = orchestrator.process_message(user_id, "如何申请退款？", session_id)
    print(f"回复: {result2['response']}")
    
    # 对话3：审批请求
    print("\n用户: 我想申请报销3000元")
    result3 = orchestrator.process_message(
        user_id,
        "我想申请报销3000元",
        context={
            'request_type': 'expense',
            'request_data': '申请报销差旅费 3000 元',
            'request_id': 'req123'
        }
    )
    print(f"意图: {result3['intent']}")
    print(f"智能体: {result3['agent_type']}")
    print(f"回复: {result3['response']}")
    
    # 对话4：数据分析请求
    print("\n用户: 帮我分析一下上个月的销售数据")
    result4 = orchestrator.process_message(
        user_id,
        "帮我分析一下上个月的销售数据",
        context={
            'data_source': 'sales_database'
        }
    )
    print(f"意图: {result4['intent']}")
    print(f"智能体: {result4['agent_type']}")
    print(f"回复: {result4['response'][:200]}...")
    
    # 查看会话历史
    print("\n" + "=" * 60)
    print("会话历史")
    print("=" * 60)
    history = orchestrator.get_session_history(session_id)
    for msg in history:
        print(f"{msg['role']}: {msg['content'][:50]}...")
    
    # 关闭会话
    orchestrator.close_session(session_id)
    print("\n会话已关闭")
