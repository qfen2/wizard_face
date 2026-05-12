# coding: utf-8
"""
企业级多智能体系统

扩展原有的研究助手，提供客服、审批、数据分析等专用智能体
"""

import operator
from typing import Annotated, List, Literal, TypedDict, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import config


# ==================== 智能体类型枚举 ====================
class AgentType(Enum):
    """智能体类型"""
    CUSTOMER_SERVICE = "customer_service"  # 客服智能体
    APPROVAL = "approval"  # 审批智能体
    DATA_ANALYSIS = "data_analysis"  # 数据分析智能体
    DOCUMENT_REVIEW = "document_review"  # 文档审核智能体
    WORKFLOW_ORCHESTRATOR = "workflow_orchestrator"  # 流程编排智能体


# ==================== 客服智能体 ====================
class CustomerServiceState(TypedDict):
    """客服智能体状态"""
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str
    query: str
    intent: str
    response: str
    confidence: float
    needs_human: bool
    current_stage: Literal["detect_intent", "search_knowledge", "generate_response", "escalate", "done"]


class CustomerServiceAgent:
    """智能客服智能体"""
    
    def __init__(self, knowledge_base_service=None):
        """
        初始化客服智能体
        
        Args:
            knowledge_base_service: 知识库服务实例
        """
        self.knowledge_base = knowledge_base_service
        self.llm = self._create_llm()
        self.graph = self._create_graph()
    
    def _create_llm(self):
        """创建LLM实例"""
        llm_cfg = config.LLM.get('openai', config.LLM.get('modelscope', {}))
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=llm_cfg.get('api_key'),
            base_url=llm_cfg.get('base_url'),
            temperature=0.7
        )
    
    def _create_graph(self):
        """创建工作流图"""
        workflow = StateGraph(CustomerServiceState)
        
        workflow.add_node("detect_intent", self._detect_intent)
        workflow.add_node("search_knowledge", self._search_knowledge)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("escalate", self._escalate_to_human)
        
        workflow.set_entry_point("detect_intent")
        workflow.add_edge("detect_intent", "search_knowledge")
        workflow.add_edge("search_knowledge", "generate_response")
        workflow.add_conditional_edges(
            "generate_response",
            self._should_escalate,
            {
                "escalate": "escalate",
                "done": END
            }
        )
        workflow.add_edge("escalate", END)
        
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _detect_intent(self, state: CustomerServiceState) -> CustomerServiceState:
        """检测用户意图"""
        prompt = f"""分析用户查询的意图和情感倾向。

用户查询：{state['query']}

请识别：
1. 主要意图（如：咨询、投诉、建议、技术支持等）
2. 情感倾向（积极、中性、消极）
3. 紧急程度（低、中、高）

以JSON格式返回：
{{
    "intent": "意图",
    "sentiment": "情感",
    "urgency": "紧急程度",
    "confidence": 0.95
}}"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            result = self._parse_json_response(response.content)
            state['intent'] = result.get('intent', 'general')
            state['confidence'] = result.get('confidence', 0.8)
            state['current_stage'] = "search_knowledge"
        except Exception as e:
            state['intent'] = 'general'
            state['confidence'] = 0.5
            state['current_stage'] = "search_knowledge"
        
        return state
    
    def _search_knowledge(self, state: CustomerServiceState) -> CustomerServiceState:
        """在知识库中搜索相关信息"""
        if self.knowledge_base:
            try:
                search_results = self.knowledge_base.search(
                    query=state['query'],
                    collection_name="customer_service",
                    k=3
                )
                state['messages'].append(
                    AIMessage(content=f"找到 {len(search_results)} 条相关知识")
                )
            except Exception as e:
                print(f"知识库搜索失败: {e}")
        
        state['current_stage'] = "generate_response"
        return state
    
    def _generate_response(self, state: CustomerServiceState) -> CustomerServiceState:
        """生成响应"""
        prompt = f"""你是一位专业的客服代表。基于用户的问题和知识库信息，提供友好、专业、有帮助的回答。

用户问题：{state['query']}
用户意图：{state['intent']}

请提供：
1. 直接回答用户的问题
2. 如果需要，提供相关的解决方案或建议
3. 保持友好、专业的语调
4. 如果问题无法解决，明确告知并建议联系人工客服

回答要求：
- 使用中文
- 保持简洁明了
- 使用适当的表情符号增加亲和力
- 提供行动指引（如果适用）"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state['response'] = response.content
            state['needs_human'] = "无法解决" in response.content or "联系人工" in response.content
        except Exception as e:
            state['response'] = "抱歉，我遇到了一些技术问题。请稍后再试或联系人工客服。"
            state['needs_human'] = True
        
        state['current_stage'] = "generate_response"
        return state
    
    def _escalate_to_human(self, state: CustomerServiceState) -> CustomerServiceState:
        """转接到人工客服"""
        state['response'] = "已为您转接到人工客服，请稍候..."
        state['needs_human'] = True
        state['current_stage'] = "done"
        return state
    
    def _should_escalate(self, state: CustomerServiceState) -> Literal["escalate", "done"]:
        """判断是否需要转人工"""
        if state['needs_human']:
            return "escalate"
        return "done"
    
    def _parse_json_response(self, text: str) -> Dict:
        """解析JSON响应"""
        try:
            import json
            # 简单的JSON提取逻辑
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
        except:
            pass
        return {}
    
    def chat(self, user_id: str, query: str, config: dict = None) -> Dict[str, Any]:
        """
        进行客服对话
        
        Args:
            user_id: 用户ID
            query: 用户查询
            config: 配置参数
            
        Returns:
            对话结果
        """
        initial_state = {
            "messages": [SystemMessage(content="你是一位专业的客服代表")],
            "user_id": user_id,
            "query": query,
            "intent": "",
            "response": "",
            "confidence": 0.0,
            "needs_human": False,
            "current_stage": "detect_intent"
        }
        
        config = config or {"configurable": {"thread_id": f"cs_{user_id}"}}
        
        final_state = None
        for event in self.graph.stream(initial_state, config):
            for node_name, node_output in event.items():
                if node_name != "__end__":
                    final_state = node_output
        
        return {
            "user_id": user_id,
            "query": query,
            "response": final_state.get("response", ""),
            "intent": final_state.get("intent", ""),
            "confidence": final_state.get("confidence", 0.0),
            "needs_human": final_state.get("needs_human", False)
        }


# ==================== 审批智能体 ====================
class ApprovalState(TypedDict):
    """审批智能体状态"""
    messages: Annotated[List[BaseMessage], operator.add]
    request_id: str
    request_type: str
    request_data: str
    requester: str
    approval_rules: str
    risk_level: str
    decision: str
    decision_reason: str
    current_stage: Literal["analyze_request", "check_rules", "assess_risk", "make_decision", "done"]


class ApprovalAgent:
    """审批智能体"""
    
    def __init__(self):
        """初始化审批智能体"""
        self.llm = self._create_llm()
        self.graph = self._create_graph()
    
    def _create_llm(self):
        """创建LLM实例"""
        llm_cfg = config.LLM.get('openai', config.LLM.get('modelscope', {}))
        return ChatOpenAI(
            model="gpt-4o",
            api_key=llm_cfg.get('api_key'),
            base_url=llm_cfg.get('base_url'),
            temperature=0.3
        )
    
    def _create_graph(self):
        """创建工作流图"""
        workflow = StateGraph(ApprovalState)
        
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("check_rules", self._check_rules)
        workflow.add_node("assess_risk", self._assess_risk)
        workflow.add_node("make_decision", self._make_decision)
        
        workflow.set_entry_point("analyze_request")
        workflow.add_edge("analyze_request", "check_rules")
        workflow.add_edge("check_rules", "assess_risk")
        workflow.add_edge("assess_risk", "make_decision")
        workflow.add_edge("make_decision", END)
        
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _analyze_request(self, state: ApprovalState) -> ApprovalState:
        """分析请求内容"""
        prompt = f"""分析以下审批请求的内容和关键信息：

请求类型：{state['request_type']}
请求人：{state['requester']}
请求数据：{state['request_data']}

请提取：
1. 请求的关键要素
2. 涉及的金额（如果有）
3. 影响范围
4. 时限要求

以结构化方式总结。"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state['messages'].append(AIMessage(content=response.content))
        except Exception as e:
            print(f"分析请求失败: {e}")
        
        state['current_stage'] = "check_rules"
        return state
    
    def _check_rules(self, state: ApprovalState) -> ApprovalState:
        """检查审批规则"""
        # 这里可以根据业务规则进行检查
        rules = {
            "leave_request": {
                "auto_approve": {"days": 3},
                "requires_manager": {"days": 7},
                "requires_director": {"days": 15}
            },
            "expense": {
                "auto_approve": {"amount": 500},
                "requires_manager": {"amount": 5000},
                "requires_director": {"amount": 20000}
            }
        }
        
        state['approval_rules'] = str(rules.get(state['request_type'], {}))
        state['current_stage'] = "assess_risk"
        return state
    
    def _assess_risk(self, state: ApprovalState) -> ApprovalState:
        """评估风险等级"""
        prompt = f"""评估以下审批请求的风险等级：

{state['approval_rules']}
{state['request_data']}

请评估风险等级（低/中/高），并说明理由。"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            if "高" in response.content:
                state['risk_level'] = "high"
            elif "中" in response.content:
                state['risk_level'] = "medium"
            else:
                state['risk_level'] = "low"
        except Exception as e:
            state['risk_level'] = "medium"
        
        state['current_stage'] = "make_decision"
        return state
    
    def _make_decision(self, state: ApprovalState) -> ApprovalState:
        """做出审批决定"""
        prompt = f"""基于以下信息做出审批决定：

请求类型：{state['request_type']}
风险等级：{state['risk_level']}
规则：{state['approval_rules']}

请做出以下决定之一：
- approve: 批准
- reject: 拒绝
- escalate: 上报

并提供理由。"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            if "批准" in response.content or "approve" in response.content.lower():
                state['decision'] = "approve"
            elif "拒绝" in response.content or "reject" in response.content.lower():
                state['decision'] = "reject"
            else:
                state['decision'] = "escalate"
            state['decision_reason'] = response.content
        except Exception as e:
            state['decision'] = "escalate"
            state['decision_reason'] = "系统错误，需要人工审核"
        
        state['current_stage'] = "done"
        return state
    
    def approve_request(
        self,
        request_id: str,
        request_type: str,
        request_data: str,
        requester: str,
        config: dict = None
    ) -> Dict[str, Any]:
        """
        处理审批请求
        
        Args:
            request_id: 请求ID
            request_type: 请求类型
            request_data: 请求数据
            requester: 请求人
            config: 配置参数
            
        Returns:
            审批结果
        """
        initial_state = {
            "messages": [SystemMessage(content="你是一位专业的审批人员")],
            "request_id": request_id,
            "request_type": request_type,
            "request_data": request_data,
            "requester": requester,
            "approval_rules": "",
            "risk_level": "",
            "decision": "",
            "decision_reason": "",
            "current_stage": "analyze_request"
        }
        
        config = config or {"configurable": {"thread_id": f"approval_{request_id}"}}
        
        final_state = None
        for event in self.graph.stream(initial_state, config):
            for node_name, node_output in event.items():
                if node_name != "__end__":
                    final_state = node_output
        
        return {
            "request_id": request_id,
            "decision": final_state.get("decision", "escalate"),
            "reason": final_state.get("decision_reason", ""),
            "risk_level": final_state.get("risk_level", "")
        }


# ==================== 数据分析智能体 ====================
class DataAnalysisState(TypedDict):
    """数据分析智能体状态"""
    messages: Annotated[List[BaseMessage], operator.add]
    analysis_task: str
    data_source: str
    data_summary: str
    insights: List[str]
    recommendations: List[str]
    report: str
    current_stage: Literal["extract_data", "analyze", "generate_insights", "create_report", "done"]


class DataAnalysisAgent:
    """数据分析智能体"""
    
    def __init__(self):
        """初始化数据分析智能体"""
        self.llm = self._create_llm()
        self.graph = self._create_graph()
    
    def _create_llm(self):
        """创建LLM实例"""
        llm_cfg = config.LLM.get('openai', config.LLM.get('modelscope', {}))
        return ChatOpenAI(
            model="gpt-4o",
            api_key=llm_cfg.get('api_key'),
            base_url=llm_cfg.get('base_url'),
            temperature=0.4
        )
    
    def _create_graph(self):
        """创建工作流图"""
        workflow = StateGraph(DataAnalysisState)
        
        workflow.add_node("extract_data", self._extract_data)
        workflow.add_node("analyze", self._analyze_data)
        workflow.add_node("generate_insights", self._generate_insights)
        workflow.add_node("create_report", self._create_report)
        
        workflow.set_entry_point("extract_data")
        workflow.add_edge("extract_data", "analyze")
        workflow.add_edge("analyze", "generate_insights")
        workflow.add_edge("generate_insights", "create_report")
        workflow.add_edge("create_report", END)
        
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _extract_data(self, state: DataAnalysisState) -> DataAnalysisState:
        """提取数据"""
        # 这里可以连接数据库或文件系统提取数据
        state['data_summary'] = "数据已提取：包含销售数据、用户行为数据等"
        state['current_stage'] = "analyze"
        return state
    
    def _analyze_data(self, state: DataAnalysisState) -> DataAnalysisState:
        """分析数据"""
        prompt = f"""分析以下数据并找出关键趋势和模式：

数据摘要：{state['data_summary']}
分析任务：{state['analysis_task']}

请提供：
1. 主要趋势
2. 异常值
3. 关键指标
4. 数据质量评估"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state['messages'].append(AIMessage(content=response.content))
        except Exception as e:
            print(f"数据分析失败: {e}")
        
        state['current_stage'] = "generate_insights"
        return state
    
    def _generate_insights(self, state: DataAnalysisState) -> DataAnalysisState:
        """生成洞察"""
        prompt = f"""基于数据分析结果，生成业务洞察和建议。

分析任务：{state['analysis_task']}

请提供：
1. 关键发现（3-5条）
2. 业务影响
3. 可行建议（3-5条）"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            # 简单解析
            lines = response.content.split('\n')
            state['insights'] = [line for line in lines if line.strip()]
            state['recommendations'] = [line for line in lines if '建议' in line or '推荐' in line]
        except Exception as e:
            state['insights'] = ["数据分析完成"]
            state['recommendations'] = ["建议进一步分析"]
        
        state['current_stage'] = "create_report"
        return state
    
    def _create_report(self, state: DataAnalysisState) -> DataAnalysisState:
        """创建分析报告"""
        prompt = f"""创建一份专业的数据分析报告。

分析任务：{state['analysis_task']}
关键洞察：{state['insights']}
建议：{state['recommendations']}

报告应包含：
1. 执行摘要
2. 数据概览
3. 关键发现
4. 建议
5. 附录"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state['report'] = response.content
        except Exception as e:
            state['report'] = "报告生成失败"
        
        state['current_stage'] = "done"
        return state
    
    def analyze(
        self,
        analysis_task: str,
        data_source: str,
        config: dict = None
    ) -> Dict[str, Any]:
        """
        执行数据分析
        
        Args:
            analysis_task: 分析任务
            data_source: 数据源
            config: 配置参数
            
        Returns:
            分析结果
        """
        initial_state = {
            "messages": [SystemMessage(content="你是一位专业的数据分析师")],
            "analysis_task": analysis_task,
            "data_source": data_source,
            "data_summary": "",
            "insights": [],
            "recommendations": [],
            "report": "",
            "current_stage": "extract_data"
        }
        
        config = config or {"configurable": {"thread_id": f"analysis_{analysis_task}"}}
        
        final_state = None
        for event in self.graph.stream(initial_state, config):
            for node_name, node_output in event.items():
                if node_name != "__end__":
                    final_state = node_output
        
        return {
            "analysis_task": analysis_task,
            "insights": final_state.get("insights", []),
            "recommendations": final_state.get("recommendations", []),
            "report": final_state.get("report", "")
        }


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 客服智能体示例
    print("=" * 60)
    print("客服智能体示例")
    print("=" * 60)
    cs_agent = CustomerServiceAgent()
    result = cs_agent.chat(
        user_id="user123",
        query="我的订单什么时候能发货？"
    )
    print(f"用户: {result['query']}")
    print(f"客服: {result['response']}")
    print(f"意图: {result['intent']}")
    
    # 审批智能体示例
    print("\n" + "=" * 60)
    print("审批智能体示例")
    print("=" * 60)
    approval_agent = ApprovalAgent()
    result = approval_agent.approve_request(
        request_id="req001",
        request_type="expense",
        request_data="申请报销差旅费 3000 元",
        requester="张三"
    )
    print(f"请求ID: {result['request_id']}")
    print(f"决定: {result['decision']}")
    print(f"理由: {result['reason']}")
    
    # 数据分析智能体示例
    print("\n" + "=" * 60)
    print("数据分析智能体示例")
    print("=" * 60)
    analysis_agent = DataAnalysisAgent()
    result = analysis_agent.analyze(
        analysis_task="分析2024年Q1销售趋势",
        data_source="sales_database"
    )
    print(f"分析任务: {result['analysis_task']}")
    print(f"关键洞察: {result['insights'][:2]}")
    print(f"报告长度: {len(result['report'])} 字符")