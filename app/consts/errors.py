# coding=u8

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import six

import collections
import functools
import sys

from app.consts import ConstGroup, Item


class Error(Exception):
    code    = 0
    message = ''
    extra   = None

    def __init__(self, message=None, code=None, extra=None):
        code = code or self.code
        message = '%s|%s' % (self.message, message) \
            if message else self.message
        super(Error, self).__init__(code, message)
        self.code    = code
        self.message = message
        self.extra   = extra

    @classmethod
    def cls(cls, name, code, message):
        new_cls = type(str(name), (cls,), dict(code=code, message=message))
        return new_cls

    @classmethod
    def clsf(cls, code, message):
        return ErrorDef(cls, code, message)

    @classmethod
    def _enum_item(cls, name, code, message):
        return Item(code, cls.cls(name, code, message))

    def __str__(self):
        s = '<Error[%s]%s>' % (self.code, self.message)
        return str(s)

    def to_dict(self):
        r = dict(code=self.code, message=self.message)
        if self.extra:
            r['extra'] = self.extra
        return r

    def to_result(self):
        r = dict(result=self.code, message=self.message)
        if self.extra:
            r['extra'] = self.extra
        return r

    @functools.wraps(Exception.with_traceback)
    def with_traceback(self, tb=None):
        if tb is None:
            tb = sys.exc_info()[2]
        return super(Error, self).with_traceback(tb)


class ErrorDef(object):
    def __init__(self, error_cls, code, message):
        self.error_cls = error_cls
        self.code      = code
        self.message   = message
        self._cls      = None

    def clsf(cls, code, message):
        return ErrorDef(cls, code, message)

    def get_error(self, name):
        error_cls = self.error_cls
        if isinstance(error_cls, ErrorDef):
            if error_cls._cls is None:
                raise Exception('Error {0.code} not init !'.format(error_cls))
            error_cls = self.error_cls._cls
        self._cls = type(str(name), (error_cls,),
                         dict(code=self.code, message=self.message))
        return self._cls


class ErrorNumGroup(ConstGroup):
    '''错误类型常量组基类'''
    @classmethod
    def init_cls(cls):
        code_map = collections.OrderedDict()
        for field_name, field_value in cls.__dict__.items():
            if isinstance(field_value, ErrorDef):
                field_value = field_value.get_error(field_name)
                setattr(cls, field_name, field_value)
            if not (isinstance(field_value, type) and
                    issubclass(field_value, Error)):
                continue
            if field_value.code in code_map:
                raise ValueError('Duplicated error code %d in %s' % (
                    field_value.code, cls.__name__))
            code_map[field_value.code] = field_value
        cls.__code_map__ = code_map


class ErrorNum(ErrorNumGroup):
    UN_KNOWN        = Error.clsf(-9999, '未定义错误')
    MUST_BE_STRING  = Error.clsf(1201, '必须是字符串')
    PARAMS_REQUIRED = Error.clsf(2101, '缺乏必填参数')

    UserNameOrPasswordError = Error.clsf(1000, '用户名，密码或企业编码错误')
    UserStatusNotNormal     = Error.clsf(1001, '账号状态异常，暂时无法登录')
    VerifyCodeError         = Error.clsf(1002, '验证码错误')
    IPLoginInhibit          = Error.clsf(1003, '该IP禁止登录')
    MobileFormatError       = Error.clsf(1004, '手机号格式错误')
    SmsProcessing           = Error.clsf(1006, '相关服务正在处理中')
    SmsIntervalNotReached   = Error.clsf(1007, '未达到1分钟短信发送时间间隔')
    CaptchaUnavailable      = Error.clsf(1008, '验证码失效')
    CaptchaError            = Error.clsf(1009, '验证码错误')
    SmsTokenUnavailable     = Error.clsf(1010, 'token已失效, 请重新进行注册')
    SmsServiceError         = Error.clsf(1011, '短信服务异常')
    MobileAlreadyRegistered = Error.clsf(1012, '该手机号已注册')
    MobileNotVerified       = Error.clsf(1013, '手机号未验证')
    InitSequenceProcessing  = Error.clsf(1014, '初始化服务正在处理中')
    SmsMobileDailyLimitExceeded = Error.clsf(1015, '该手机号当日短信数量达到上限')
    SmsIPDailyLimitExceeded   = Error.clsf(1016, '该IP当日短信数量达到上限')

    InvitationNotFound      = Error.clsf(1101, '未找到相关邀请信息')
    RequestNotFound         = Error.clsf(1102, '未找到相关申请信息')
    InvitationClosed        = Error.clsf(1103, '该邀请已关闭')
    RequestClosed           = Error.clsf(1104, '该申请已处理')
    UserAlreadyInOrg        = Error.clsf(1109, '当前账号已加入该组织')

    AppEntryNotFound        = Error.clsf(101001, '没有找到相关的App入口信息')

    UnknowError             = Error.clsf(503, '未知错误')
    ArgError                = Error.clsf(406, '参数有误')
    PermissionDenied        = Error.clsf(401, '您无此功能权限')
    AccessDenied            = Error.clsf(403, '您无法进行此操作')

    # 内部API调用类异常
    ApiCallerFailed       = Error.clsf(3001, 'API调用失败')
    ApiCallerRemoteFailed = ApiCallerFailed.clsf(3002, 'API调用远端异常')
    # 包装内部异常用（屏蔽敏感信息等），通常不直接抛出
    HidePeeweeDoesNotExist = Error.clsf(4011, '查询的数据不存在')
    HidePeeweeError        = Error.clsf(4012, '请求数据库失败')

    ''' 90000至100000之间为用于兼容性支持的异常信息 每个子段长100 begin '''
    CeleryError = Error.clsf(90100, '异步任务错误')
    ''' 90000至100000之间为用于兼容性支持的异常信息 每个子段长100 end '''

    ''' 200000 用户 权限相关 zhijian_server_ucenter项目 begin '''
    GroupInfoNotFound           = Error.clsf(202001, '没有找到相关的集团信息')
    GroupCodeExists             = Error.clsf(202002, '企业编码已存在')
    TeamInfoNotFound            = Error.clsf(202011, '没有找到相关的公司信息')
    CreateTeamError             = Error.clsf(202012, '新建公司失败')
    EditTeamError               = Error.clsf(202013, '编辑公司失败')
    DeleteTeamError             = Error.clsf(202014, '删除公司失败')
    CreateGroupError            = Error.clsf(202015, '新建集团失败')
    EditGroupOwnerError         = Error.clsf(202016, '编辑集团拥有者失败')
    InitGroupModuleStatusError  = Error.clsf(202017, '初始化集团模块状态失败')
    InitGroupModuleVersionError = Error.clsf(202018, '初始化集团模块版本失败')
    InitGroupRolesError         = Error.clsf(202019, '初始化集团角色失败')
    TeamCannotChangeGroup       = Error.clsf(202020, '不能跨集团调整公司')
    GroupCannotLinkUp           = Error.clsf(202021, '不能调整集团的父级')
    TeamCannotBeCycleLinked     = Error.clsf(202022, '不能产生环形层级链')
    TeamAlreadyExists           = Error.clsf(202023, '已有相关公司数据')
    GroupAlreadyInited          = Error.clsf(202024, '当前集团已进行过初始化')

    UserInfoNotFound      = Error.clsf(202120, '没有找到相关的用户信息')
    UserNameExists        = Error.clsf(202121, '用户名已存在')
    AddUserError          = Error.clsf(202122, '创建用户失败')
    EditUserBaseInfoError = Error.clsf(202123, '修改用户信息失败')
    OldPasswordNotCorrent = Error.clsf(202124, '旧密码不正确')
    EditUserPasswordError = Error.clsf(202125, '修改密码失败')
    EditUserGroupError    = Error.clsf(202126, '修改账号集团失败')
    UserAlreadyHasGroup   = Error.clsf(202127, '账号已有集团信息')

    EditUserInGroupRoleError     = Error.clsf(202240, '修改用户集团角色失败')
    EditUserInTeamRoleError      = Error.clsf(202241, '修改用户公司角色失败')
    EditUserInProjectRoleError   = Error.clsf(202242, '修改用户项目角色失败')
    DeleteUserInProjectRoleError = Error.clsf(202243, '删除用户项目角色失败')
    GroupOwnerCanNotBeModified   = Error.clsf(202244, '集团拥有者不能被修改')

    ProjectCreateNeeded = Error.clsf(202350, '请创建一个项目')
    ProjectInfoNotFound = Error.clsf(202351, '没有找到相关的项目信息')
    AddProjectError     = Error.clsf(202352, '添加项目失败')
    EditProjectError    = Error.clsf(202353, '编辑项目失败')
    DeleteProjectError = Error.clsf(202354, '删除项目失败')

    ProjectTypeNotFound = Error.clsf(202355, '没有找到相关的项目类型信息')
    ProjectTypeNameError = Error.clsf(202364, '项目类型名错误')
    AddProjectTypeError     = Error.clsf(202356, '添加项目类型失败')
    EditProjectTypeError    = Error.clsf(202357, '编辑项目类型失败')
    DeleteProjectTypeError = Error.clsf(202358, '删除项目类型失败')

    ProjectStageNotFound = Error.clsf(202359, '没有找到相关的项目阶段信息')
    ProjectStageNameError = Error.clsf(202363, '项目阶段名错误')
    AddProjectStageError     = Error.clsf(202360, '添加项目阶段失败')
    EditProjectStageError    = Error.clsf(202361, '编辑项目阶段失败')
    DeleteProjectStageError = Error.clsf(202362, '删除项目阶段失败')
    SwitchIdNotFoundError = Error.clsf(202372, '未找到对应开关id')
    ProjectStateNotFound = Error.clsf(202365, '没有找到相关的项目阶段信息')

    CustomFieldNotFound = Error.clsf(202366, '没有找到相关的项目字段信息')
    AddCustomFieldError = Error.clsf(202367, '添加自定义字段失败')
    DeleteCustomFieldError = Error.clsf(202368, '删除自定义字段失败')
    EditCustomFieldError = Error.clsf(202369, '删除自定义字段失败')
    LackRequiredFieldError = Error.clsf(202370, '缺少必填字段')
    FormatExtractFieldError = Error.clsf(202371, '字段格式错误')

    RoleInfoNotFound     = Error.clsf(202461, '没有找到相关的角色信息')
    RoleNameExists       = Error.clsf(202462, '此角色名已存在')
    AddRoleError         = Error.clsf(202463, '创建角色失败')
    EditRoleError        = Error.clsf(202464, '修改角色失败')
    EditRoleStatusError  = Error.clsf(202465, '修改角色状态失败')
    RoleCanNotBeModified = Error.clsf(202466, '系统角色不能被修改')
    RoleNameToShort      = Error.clsf(202467, '角色名过短')
    PasswordToShort      = Error.clsf(202468, '密码长度过短')
    RolePermBindFailed   = Error.clsf(202470, '绑定角色权限失败')
    PermEntryNotFound    = Error.clsf(202471, '权限点未找到')

    AddTeamRoleError    = Error.clsf(202570, '创建公司角色失败')
    AddProjectRoleError = Error.clsf(202571, '创建项目角色失败')

    PartnerNotExists = Error.clsf(203001, '合作伙伴公司不存在')
    PartnerNameEmpty = Error.clsf(203002, '合作伙伴公司名不能为空')
    PartnerAlreadyExists = Error.clsf(203003, '合作伙伴公司已存在')

    PartnerAlreadyLinked = Error.clsf(203011, '该合作伙伴已联结')
    PartnerCircularLink = Error.clsf(203012, '该联结会导致递归联结')

    UpdateProjectError = Error.cls('UpdateProjectError', 202590, '更新项目失败')

    CrmSsoTokenError = Error.cls('CrmSsoTokenError', 210010, 'crm_token无效')
    ''' 用户 权限相关 zhijian_server_ucenter项目 end '''

    ''' 300000 巡检 zhijian_server_xunjian begin '''
    CreateTaskGroupError         = Error.clsf(300000, '任务组创建失败')
    TaskGroupNotFound            = Error.clsf(300001, '任务组未找到')
    TaskGroupEditError           = Error.clsf(300002, '任务组编辑错误')
    TaskGroupDeleteError         = Error.clsf(300003, '任务组删除错误')
    TaskGroupExtendNotFound      = Error.clsf(300004, '任务组扩展未找到')

    TaskNotFound                 = Error.clsf(300100, '任务未找到')
    TaskNotStart                 = Error.clsf(300101, '任务未开始')
    TaskFinish                   = Error.clsf(300102, '任务已结束')
    TaskEditError                = Error.clsf(300103, '编辑任务错误')
    TaskDeleteError              = Error.clsf(300104, '删除任务错误')
    TaskUpdateError              = Error.clsf(300105, '更新任务错误')

    TaskCheckItemUpdateError     = Error.clsf(300200, '顶层检查项更新错误')
    TaskCheckItemClose           = Error.clsf(300201, '顶层检查项关闭')
    TaskCheckItemNotFound        = Error.clsf(300202, '顶层检查项未找到')
    TaskCheckItemDeleteError     = Error.clsf(300203, '顶层检查项未找到')

    TopCheckItemNotFound         = Error.clsf(300301, 'category_v3顶层检查项未找到')
    CheckItemNotFound            = Error.clsf(300300, '检查项未找到')
    CategoryTreeLeafNodeNotFound = Error.clsf(300302, '未查到顶层检查项的叶子节点')
    CategoryTypeError            = Error.clsf(300303, '检查项类型错误')

    QualifiedItemNotFound        = Error.clsf(300400, '未找到对应检查项检查数据')
    QualifiedItemUpdateError     = Error.clsf(300401, '检查项检查数据更新错误')

    MeasureRuleNotFound          = Error.clsf(300501, '未查到测区规则')
    MeasureZoneNotFound          = Error.clsf(300502, '未查到测区')
    MeasureZoneResultsNotFound   = Error.clsf(300503, '未查到测区结果')
    CreateMeasureZoneError       = Error.clsf(300504, '创建测区失败')
    CreateMeasureZoneResultError = Error.clsf(300505, '创建测区结果失败')
    AreaNotFound                 = Error.clsf(300506, '未查到区域')
    CategoryNotFound             = Error.clsf(300507, '未查到检查项')
    MeasureZoneDeleteError       = Error.clsf(300508, '删除测区失败')
    MeasureZoneResultDeleteError = Error.clsf(300509, '删除测区结果失败')

    CreateUserInTaskGroupError   = Error.clsf(300600, '创建UserInTaskGroup失败')
    CreateUserInTaskError        = Error.clsf(300601, '创建UserInTask失败')
    DeleteUserInTaskGroupError   = Error.clsf(300602, '删除UserInTaskGroup失败')
    DeleteUserInTaskError        = Error.clsf(300603, '删除UserInTask失败')

    IssueDeleteError             = Error.clsf(300700, '删除Issue失败')
    IssueLogDeleteError          = Error.clsf(300701, '删除IssueLog失败')

    MeasureZonesJsonError        = Error.clsf(310001, '上传测区的Json格式错误')
    MeasureZoneResultsJsonError  = Error.clsf(310002, '上传测区结果的Json格式错误')

    # 巡检人员Error
    TaskFollowerNotInProjectFollowerError = Error.clsf(320000, '巡检跟进人不在项目的跟进人内')
    TaskCheckerNotInTaskGroupCheckerError = Error.clsf(320001, '任务的巡检小组人员不在任务组的巡检小组人员内')
    ChargerNotInTaskCheckersError         = Error.clsf(320002, '任务的负责人不在任务的巡检小组内')
    ChargerIsNotDeletable                 = Error.clsf(320003, '任务的负责人不能删除')
    TaskGroupCheckerNotInTeamError        = Error.clsf(320004, '任务组的巡检小组人员不在集团内')

    # 巡检小组Error
    CreateSquadError                 = Error.clsf(330000, '小组创建错误')
    CreateSquadMemberError           = Error.clsf(330001, '小组人员创建错误')
    UpdateSquadMemberError           = Error.clsf(330002, '小组人员更新错误')
    SquadMemberDeleteError           = Error.clsf(330003, '小组人员删除错误')
    SquadDeleteError                 = Error.clsf(330004, '小组删除错误')

    JsonDumpsError               = Error.cls('JsonDumpsError', 340000, '对象转Json错误')
    JsonLoadsError               = Error.cls('JsonLoadsError', 340001, 'Json转对象错误')

    CopyScoreRuleError           = Error.clsf(350001, '复制评分规则失败')
    CopyScoreRuleAttachmentError = Error.clsf(350002, '复制评分规则文件失败')
    CopyQuaCheckItemError        = Error.clsf(350003, '复制检合格检查项失败')
    CopyTaskGroupError           = Error.clsf(350004, '复制任务组失败')
    CopyTaskError                = Error.clsf(350005, '复制任务失败')
    CopyTaskCheckItemError       = Error.clsf(350006, '复制任务中检查项失败')
    CopyIssueError               = Error.clsf(350007, '复制问题失败')
    CopyIssueLogError            = Error.clsf(350008, '复制问题记录失败')

    FeiJianDownloadError         = Error.clsf(350009, '下载失败!')
    SavePictureError             = Error.clsf(350010, '保存图片失败')
    SaveCheckAreaError           = Error.clsf(350011, '保存检查区错误')
    UpdateCheckAreaError         = Error.clsf(350012, '更新检查区失败')
    DecompositError              = Error.clsf(350013, '自动分解任务失败')
    SaveTaskGroupExtendError     = Error.clsf(350014, '保存任务组扩展失败')
    CreateTaskResultError        = Error.clsf(350015, '创建任务结果记录失败')
    CreateTaskFinalScoreError    = Error.clsf(350016, '创建综合得分记录失败')
    CreateReEvaluationError      = Error.clsf(350017, '创建复评任务失败')
    LockTaskError                = Error.clsf(350018, '不满足锁定条件')
    ReEvaluationError            = Error.clsf(350019, '不满足复评条件')
    UpdateEvaluationStatusError  = Error.clsf(350020, '首评状态更新失败')
    NoCheckItemError             = Error.clsf(350021, '未规划检查项')
    LockError                    = Error.clsf(350022, '已锁定不支持修改')
    UnLockTaskError              = Error.clsf(350023, '不满足解锁条件')
    UnLockTaskCheckItemError     = Error.clsf(350024, '请先解锁任务')


    #  第三方检查统计
    NotInTaskGroupError                 = Error.clsf(360001, '该公司未参与此轮检查')
    CheckerHadDataIsNotDeletable        = Error.clsf(360002, '该成员已在任务组内产生数据不能删除')
    CheckerIsNotDeletable               = Error.clsf(360003, '删除失败，至少保留一名检查人员')
    ProjIsNotDeletable                  = Error.clsf(360004, '删除失败，至少保留一个参检项目')
    ProjExist                           = Error.clsf(360005, '添加失败，参数错误或该项目已参与此轮任务')
    CheckItemRepeat                     = Error.clsf(360006, '检查项名称重复，请检查')
    CompanyTooMany                      = Error.clsf(360007, '公司数量超出限制，最多选择5个')

    '''  zhijian_server_xunjian end '''

    ''' 400000 检查项错误相关 zj_checkitem_data项目 begin '''
    CreateCategoryRootError = Error.clsf(400002, '创建顶层检查项失败')
    CreateCheckItemAttachementError = Error.cls('CreateCheckItemAttachementError', 400003, '创建顶层检查项失败')
    DeleteCheckItemAttachementError = Error.cls('DeleteCheckItemAttachementError', 400004, '删除顶层检查项失败')
    EditCategoryError = Error.cls('EditCategoryError', 400005, '编辑检查项失败')
    CopyDataError = Error.clsf(400020, '复制数据失败!')
    NewTeamIDError = Error.clsf(400021, '新公司ID已被占用')

    ParseScoreRuleError = Error.cls('ParseScoreRuleError', 400006, '评分规则文件不完整')
    UpdateScoreRuleError = Error.cls('UpdateScoreRuleError', 400007, '更新检查项评分规则失败')
    SaveScoreRuleError = Error.cls('SaveScoreRuleError', 400008, '保存检查项评分规则失败')
    CannotDeleteCharger = Error.cls('CannotDeleteCharger', 400009, '不能删除负责人')
    DoubleCheckItemError = Error.cls('DoubleCheckItemError', 400010, '检查项ID重复!')
    ScoreRuleFileParseError = Error.cls('ScoreRuleFileParseError', 400011, '检查项ID不存在')
    CheckItemIDError = Error.cls('CheckItemIDError', 400012, '检查项ID错误')
    UploadReportError = Error.cls('UploadReportError', 400013, '上传报告失败!')
    FileResourceNotFoundError = Error.cls('FileResourceNotFoundError', 400014, '找不到文件!')
    DelFileResourceError = Error.cls('DelFileResourceError', 400015, '删除文件失败')
    ScoreRuleJsonNotFound = Error.cls('ScoreRuleJsonNotFound', 400016, '顶层检查项没有找到规则')
    ScoreNotComplete = Error.cls('ScoreNotComplete', 400022, '评分规则缺少检查项!')
    ScoreTooMany = Error.cls('ScoreTooMany', 400031, '评分规则检查项过多')
    TeamParentRecircle = Error.clsf(400030, '公司父节出现循环')

    CreateFixingPresetError = Error.clsf(400017, '新增整改预设失败!')
    UpdateFixingPresetError = Error.clsf(400018, '更新整改预设失败!')
    DeleteFixingPresetError = Error.clsf(400019, '删除整改预设失败!')
    ''' 400000 检查项错误相关 zj_checkitem_data项目 end '''

    ''' 500000 zhijian_server_plan 项目 begin '''
    FormParameterError     = Error.clsf(500002, '表格参数错误')

    UserPrivilegeError     = Error.clsf(500101, '用户权限错误')
    GroupIDNotMatch        = Error.clsf(500102, '集团ID不匹配')

    TaskStatusError        = Error.clsf(500202, '任务状态错误')
    TaskTimeAdjustError    = Error.clsf(500203, '任务时间更改失败')
    TaskTimeNotWorkDay     = Error.clsf(500204, '任务时间不在工作日范围之内')

    UpdateDatabaseError    = Error.clsf(500301, '更新数据库失败')
    QueryUserCenterError   = Error.clsf(500302, '查询用户资料中心服务失败')

    FileResourceError      = Error.clsf(500401, '文件MD5无效')
    OpenFileError          = Error.clsf(500402, '文件打开失败')

    TemplateNotFound       = Error.clsf(500501, '模板不存在')
    ''' 500000 zhijian_server_plan 项目 end '''

    ''' 600000 检查项错误相关 zj_checkitem_data项目 begin '''
    UploadFileFileNameNotFound = Error.clsf(604001, '上传的数据有误')
    UploadFileExtNotAllow = Error.clsf(604002, '文件类型有误')
    UploadFileInsertDbError = Error.clsf(604003, '文件上传失败')
    UploadFileError = Error.clsf(604004, '文件上传失败')
    ''' 600000 检查项错误相关 zj_checkitem_data项目 end '''

    ''' 700000 区域错误相关 core_srv_area 项目 begin '''
    CreateProjAreaError       = Error.clsf(700000, '创建区域失败')
    UpdateProjAreaError       = Error.clsf(700001, '更新区域失败')
    DeleteProjAreaError       = Error.clsf(700002, '删除区域失败')

    AreaTypeError             = Error.clsf(700010, '区域类型错误')

    FatherAreaNotFound              = Error.clsf(700100, '父级区域未找到')
    FatherAreaCustomCodeDuplicated  = Error.clsf(700101, '同一个项目下父级区域代码重复')
    PathCircle                      = Error.clsf(700102, '更新父级id成环发生错误')

    AreaError = Error.clsf(700200, '区域错误')
    AreaLocked = Error.clsf(700201, '区域已绑定')

    AreaClassSubsAllocated = Error.clsf(700300, '该户型下还有绑定到户')

    ''' 700000 区域错误相关 core_srv_area 项目 end '''

    ''' 800000 检查项错误相关 core_srv_organ 项目 begin '''
    DisrelatePersonError = Error.clsf(800001, '解除人员与部门职位关系错误')

    PersonInPosition = Error.clsf(800502, '人员在部门职位还有任职')

    DeletePositionError = Error.clsf(801001, '删除部门职位错误')

    DeletePersonError = Error.clsf(801101, '删除人员错误')
    UpdatePersonError = Error.clsf(801102, '更新人员错误')
    ''' 800000 检查项错误相关 core_srv_organ 项目 end '''

    ''' 900000 检查项错误相关 开放平台 项目 begin '''
    # 系统级别901
    RequestFailed = Error.clsf(901001, '请求失败')
    RequestDataParseFailed = Error.clsf(901002, '请求回来数据解析失败')
    OperateFailed = Error.clsf(901003, '操作错误')

    # 业务模块902
    # 机构模块02
    OrgNoFoundFailed = Error.clsf(902201, '机构找不到')
    OrgCreateAppTypeFailed = Error.clsf(902202, '机构创建应用的类型不正确')
    OrgNameRepeatFailed = Error.clsf(902203, '机构名重复')
    OrgNoRepeatFailed = Error.clsf(902204, '集团id重复')

    # 应用模块03
    AppNoFoundFailed = Error.clsf(902301, '应用找不到')
    AppUpdateFailed = Error.clsf(902302, '应用信息更新错误')
    AppKeyRepeatFailed = Error.clsf(902303, '应用APP_KEY重复存在错误')
    AppNameRepeatFailed = Error.clsf(902304, '应用名重复')
    AppOrgNoFoundFailed = Error.clsf(902305, '应用还没开通')

    # 回调模块04
    CallbackOperateNoFoundFailed = Error.clsf(902401, '回调操作不存在')

    # 开放平台系统模块#05
    LoginRepeatFailed = Error.clsf(902501, '用户重复登陆')
    LoginNotYetFailed = Error.clsf(902502, '用户还没登陆')
    UploadImgSizeFailed = Error.clsf(902503, '上传图片尺寸错误')
    UploadImgSpaceFailed = Error.clsf(902504, '上传图片大小错误')

    # 应用配置模块#05
    AppSettingItemNotFound = Error.clsf(902601, '应用配置项找不到')
    AppSettingItemPowerNotAllowAddValue = Error.clsf(902602, '应用配置项添加值权限不足')
    AppSettingValueIllegal = Error.clsf(902603, '应用配置值非法')
    AppSettingItemRepeatCreate = Error.clsf(902604, '应用配置项重复创建')
    AppSettingItemNameIllegal = Error.clsf(902605, '应用配置项名非法，必须是数字+26英文字母+下划线，3到20个字符之间')
    AppSettingItemTypeAndRangeTypeIllegal = Error.clsf(902606, '应用配置项值范围类型与值类型不符')
    AppSettingItemValueRangeIllegal = Error.clsf(902607, '应用配置项值范围值不合法')
    AppSettingItemValueIllegal = Error.clsf(902608, '应用配置项值不合法')
    AppSettingValueNotFound = Error.clsf(902609, '应用配置值找不到')

    ''' 900000 检查项错误相关 开放平台 项目 end '''

    ''' 1000000 对接适配器相关 begin '''
    SyncAdapterError = Error.clsf(1000000, '对接适配器异常')
    ''' 1000000 对接适配器相关 end '''

    ''' 1100000 单点登录相关 begin '''
    SSOError = Error.clsf(1100000, '单点登录异常')
    ''' 1100000 单点登录相关 end '''

    ''' 1200000 实测相关 begin '''
    MeasureError = Error.clsf(1200000, '实测相关')
    ''' 1299999 实测相关 end '''

    ''' 1300000 文档协同相关 begin '''
    # 系统级别1301

    # 业务模块02
    # 空间模块1
    SpaceNoFound = Error.clsf(1302100, '空间不存在')
    SpaceCreateError = Error.clsf(1302101, '空间创建失败')
    SpaceCreating = Error.clsf(1302102, '空间初始化中')
    SpaceClassifyNotAllowUpload = Error.clsf(1302103, '上传类型不允许')
    SpaceOverSize = Error.clsf(1302104, '超出容量')

    # 集团模块2
    GroupNoFound = Error.clsf(1302200, '集团不存在')

    # 公司模块3
    CompanyNoFound = Error.clsf(1302300, '公司不存在')

    # 项目模块4
    ProjectNoFound = Error.clsf(13024200, '项目不存在')

    # 文件模块5
    FileNoFound = Error.clsf(13025200, '文件(夹)不存在或已删除')
    FileCreateError = Error.clsf(13025201, '文件创建失败')
    FileCreateRepeat = Error.clsf(13025202, '文件(夹)重复创建')
    FileAlreadyDel = Error.clsf(13025203, '文件已删除或者已经存在回收站')
    FileMoveCreateRepeat = Error.clsf(13025204, '文件不能移动到已经存在的目录')
    FileCopyError = Error.clsf(13025205, '文件复制错误')

    # 文件夹模块6
    FolderCreateRepeat = Error.clsf(13026200, '文件夹重复创建')
    FolderMoveError = Error.clsf(13026201, '文件夹移动失败')
    FolderCreateError = Error.clsf(13026202, '文件夹创建失败')
    FolderMoveCreateRepeat = Error.clsf(13026203, '文件不能移动到已经存在的目录')
    FolderMoveLimit = Error.clsf(13026204, '要移动文件目录数量过多')

    # 图纸模块7
	# 废弃
    DrawingTypeNotAllowUpload = Error.clsf(13027100, '上传类型不允许')

    # 标注模块8
    MarkNoFound = Error.clsf(13028100, '标注不存在或已删除')
    MarkNoSupportModel = Error.clsf(13028101, '标注不支持外链到模型空间')

    # bimface模块9
    BimfaceFileUploaded = Error.clsf(13029100, 'bimface文件重复上传')
    ''' 1399999 文档协同相关 end '''

    ''' 1400000 业主报事（万达）相关 begin '''
    YzbsIssueNotFound               = Error.clsf(1400100, '问题不存在或已删除')
    YzbsAreaNotFound                = Error.clsf(1400101, '区域不存在或已删除')
    YzbsCategoryNotFound            = Error.clsf(1400102, '检查项不存在或已删除')
    YzbsProjectNotFound             = Error.clsf(1400103, '项目不存在或已删除')
    ''' 1499999 业主报事（万达）相关 end '''

    ''' 1500000 core_srv_check_item 检查项服务 相关 begin '''
    CheckItemError = Error.clsf(1500000, 'core_srv_check_item 检查项服务 相关')
    ''' 1599999 core_srv_check_item 检查项服务 相关 end '''

    ''' 1600000 core_srv_share 项目 end '''
    ShareCreateError = Error.clsf(1600000, '创建分享记录失败')
    ShareClosed = Error.clsf(1600001, '分享已关闭')
    ShareOverdue = Error.clsf(1600002, '分享已过期')
    GetShareParamsError = Error.clsf(1600003, '获取分享参数失败')
    ''' 1699999 core_srv_organ 项目 end '''

    ''' 1700000 配置相关 begin '''
    AddConfError = Error.clsf(1700000, '添加配置失败')
    DelConfError = Error.clsf(1700001, '删除配置失败')
    ConfNotFound = Error.clsf(1700002, '配置不存在')
    SaveError = Error.clsf(1700003, '保存失败')
    EditError = Error.clsf(1700004, '编辑失败')
    DelError = Error.clsf(1700005, '删除失败')
    NotExists = Error.clsf(1700006, '记录不存在')

    ''' 1799999 配置相关 end '''


    ''' 1800000 app_safety_inspection begin '''
    CategoryClsErr = Error.clsf(1800000, '非安全检查模块下的检查项类型')
    CheckTimeErr = Error.clsf(1800001, '请检查首次检查时间与截止时间')
    PlanOnErr = Error.clsf(1800002, '任务结束时间应大于任务起始时间')
    InspectionObjectsErr = Error.clsf(1800003, '无有效检查对象')
    CheckItemKeysErr = Error.clsf(1800004, '无有效检查项')
    AuthSettingErr = Error.clsf(1800005, '未规划角色或人员')
    CreateScheduledTaskErr = Error.clsf(1800006, '创建（按期）排查任务失败')
    DeleteScheduledTaskErr = Error.clsf(1800007, '删除任务失败')
    FrequencyErr = Error.clsf(1800008, '按期排查任务请规划检查频率')
    CanNotEditFirstCheckTime = Error.clsf(1800009, '首次检查截止时间已生效，不可编辑')
    CanNotEditPlanBeginOn = Error.clsf(1800010, '任务起始时间已生效，不可编辑')
    CanNotDelInspectionObject = Error.clsf(1800011, '检查对象已生效，不可删除')
    AddRecordErr = Error.clsf(1800012, '添加检查记录失败')
    InspectionObjectsIllegality = Error.clsf(1800013, '存在非法检查对象')
    EditScheduledTaskErr = Error.clsf(1800014, '编辑（按期）排查任务失败')
    ExecTaskDisable = Error.clsf(1800015, '无效周期任务，添加检查记录失败')
    CanNotEditLastCheckTime = Error.clsf(1800016, '截止时间已生效，不可编辑')

    ''' 1899999 app_safety_inspection end '''

    ''' 1900000 流程相关 begin '''
    FlowError = Error.clsf(1900000, '流程处理异常')
    ''' 1999999 流程相关 end '''

    ''' 2000000 微信相关 begin '''
    WechatUnionidNotFound = Error.clsf(2000001, '没有找到相关的unionid')
    WechatUserNotFoundInWechat = Error.clsf(2000002, '在微信中没有找到对应的用户')
    ''' 2099999 微信相关 end '''

    ''' 2100000 形象进度 begin '''
    RootCategoryKeyErr = Error.clsf(2100000, '该检查项已产生数据，不可编辑')
    VisualProgressCategoryNotFound = Error.clsf(2100001, '未查到检查项')
    ProjectAuthSettingErr = Error.clsf(2100002, '未规划角色或人员')
    AddProjectSettingErr = Error.clsf(2100003, '添加项目配置失败')
    DelProjectSettingErr = Error.clsf(2100004, '删除项目配置失败')
    AddProgressRecordErr = Error.clsf(2100005, '添加进度记录失败')
    ''' 2199999 形象进度 end '''

    ''' 2200000 看版 begin '''
    InspectionLotNotFound = Error.clsf(2200000, "检查批不存在")
    DefaultDataNotSet = Error.clsf(2200001, "此项目未设置默认的检查项")
    ''' 2299999 看板 end '''

    ''' 2300000 crm相关 begin'''
    MobileAlreadyApply = Error.clsf(2300000, "当前手机号已经提交过申请了，您可直接拨打4008224699与我们联系")
    CustomerNotFound = Error.clsf(2300001, "客户信息不存在")
    ''' 2399999 crm相关 end  '''

    ''' 2400000 管控平台相关 begin'''
    ControlPlatformError = Error.clsf(2400000, "管控平台异常")
    ''' 2499999 管控平台相关 end  '''


ErrorNum.init_cls()

if __name__ == '__main__':
    print(Error.cls('MakerExists', 'E01', '问题')('测试'))
