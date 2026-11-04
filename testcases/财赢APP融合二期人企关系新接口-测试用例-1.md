# 财赢APP融合二期

## 【人企关系】财赢APP融合二期人企关系新接口

> 范围说明：新接口为给基础账/经营账调用的纯接口（包一层 EIAM 接口转发封装），只出接口用例。新接口 URL 文档标注「待提供」，不捏造 URL；`调用的接口:` 写被包装的 EIAM RPC。本期区别点：appId（74323799365384202609041712684）、platformCode（DZ）不需要外部传，代码里指定。

### 接口

#### 初始化eiam企业

##### 不传appId和platformCode初始化企业时按代码指定值初始化成功

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.common.InitFacade#initTenant（新接口 URL 待提供）；企业未初始化过 EIAM | 测试数据: 未初始化 EIAM 的新企业 customerId（可在白名单机构下新造一个企业）

- 调用新接口初始化企业，仅传企业标识（customerId），不传 appId 和 platformCode
  - 初始化成功
  - EIAM 租户 platformCode 为 DZ、appId 为代码指定值 74323799365384202609041712684
  - cy_app_customer_open_record 落开通记录，sync_source 为调用方来源（基础账 BASE_DZ / 经营账 BUSINESS_ACCOUNT）
  - EIAM 侧完成企业本部组织初始化

##### 重复初始化已初始化的企业时幂等不产生重复数据

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.common.InitFacade#initTenant（新接口 URL 待提供）；企业已初始化过 EIAM | 测试数据: 已初始化 EIAM 的企业 customerId

- 对已初始化的企业重复调用初始化接口
  - 返回成功或幂等提示，不报错
  - EIAM 不产生重复租户
  - cy_app_customer_open_record 不产生重复开通记录

##### 外部传参appId和platformCode时以代码指定值为准不被透传覆盖

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.common.InitFacade#initTenant（新接口 URL 待提供）；企业未初始化过 EIAM | 测试数据: 未初始化 EIAM 的企业 customerId；故意传错误值 appId=000、platformCode=XXX

- 调用初始化接口时外部额外传参 appId 与 platformCode（故意传错误值）
  - 初始化仍成功
  - 生效值为代码指定值（appId=74323799365384202609041712684、platformCode=DZ），外部传参不透传覆盖

##### EIAM初始化返回异常时新接口透传错误且本地不落开通记录

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.common.InitFacade#initTenant（新接口 URL 待提供）；可构造 EIAM 侧初始化失败（如 EIAM 服务异常） | 测试数据: 未初始化 EIAM 的企业 customerId

- EIAM 侧初始化返回异常时调用新接口
  - 新接口返回失败，错误信息透传 EIAM 原因不吞错
  - 本地不落 cy_app_customer_open_record 开通记录

##### 企业标识为空或不存在时初始化失败并返回参数错误

> 优先级: P4 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 测试数据: customerId 传空字符串/null、customerId 传系统不存在的值

- 企业标识 customerId 传空或传不存在的值调用初始化接口
  - 返回参数错误或业务校验失败，不报 500
  - EIAM 不创建租户，本地不落数据

#### 加员工

##### 基础账加员工时同步成功并落来源BASE_DZ的人企关系

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#addEmployee（新接口 URL 待提供）；企业已初始化 EIAM | 测试数据: 已初始化企业的 customerId + 合法手机号（满足 UC 规则）+ 在线角色（0/1/2 任一）

- 基础账调用加员工接口，传入合法手机号与在线角色
  - EIAM 创建员工成功
  - cy_app_customer_employee_relation 落人企关系记录，source=BASE_DZ、is_delete=0

##### 经营账加员工时同步成功并落来源BUSINESS_ACCOUNT的人企关系

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#addEmployeeByTenantAndAccount（新接口 URL 待提供）；企业已初始化 EIAM | 测试数据: 已初始化企业的 customerId + 合法手机号 + 在线角色

- 经营账调用加员工接口按账号维度加员工
  - EIAM 创建员工成功
  - cy_app_customer_employee_relation 落人企关系记录，source=BUSINESS_ACCOUNT

##### 批量加员工且角色覆盖员工老板财务时全部同步成功

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#batchAddEmployee（新接口 URL 待提供）；企业已初始化 EIAM | 测试数据: 3 名不同合法手机号员工，角色分别为员工(0)、老板(1)、财务(2)

- 通用组件调用批量加员工接口，一次传入多名员工且角色覆盖员工(0)/老板(1)/财务(2)
  - 全部员工同步成功
  - EIAM 与新表各员工角色与传参一致
  - 新表记录 source 为调用方来源

##### 重复添加同一手机号员工时幂等不产生重复记录

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#addEmployee / #batchAddEmployee（新接口 URL 待提供）；企业已存在该手机号的员工 | 测试数据: 企业已添加过的手机号

- 对同一手机号重复调用加员工接口
  - 返回已存在提示（幂等，不报错）
  - 新表不产生重复人企记录，EIAM 无重复员工

##### 批量中含手机号不满足UC规则员工时该员工跳过其余员工正常同步

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#batchAddEmployee（新接口 URL 待提供）；企业已初始化 EIAM | 测试数据: 批量 3 名员工，其中 1 名手机号不合法（如 'abc123'），另 2 名正常

- 批量加员工中包含手机号不满足 UC 规则的员工（如 'abc123'）
  - 该员工被跳过，错误日志记录企业标识+员工标识+原因
  - 其余正常员工全部同步成功（单条失败不影响批量）
  - 被跳过员工在 EIAM 与新表均无记录

##### 加员工分别传在线角色员工老板财务时按传入角色同步

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#addEmployee（新接口 URL 待提供）；企业已初始化 EIAM | 测试数据: 3 个不同手机号分别传 roleId=0、roleId=1、roleId=2

- 分别以角色员工(0)、老板(1)、财务(2)调用加员工接口
  - 三次均加员工成功
  - EIAM 与新表中角色与传参一致

##### 加员工传非法角色值时报参数错误不落库

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#addEmployee（新接口 URL 待提供）；企业已初始化 EIAM | 测试数据: roleId=9（有效域外值）

- 加员工传入未配置的角色值（如 roleId=9）
  - 返回参数错误（非法角色值），不落库
  - EIAM 不创建员工

##### 企业未初始化EIAM时加员工失败并明确提示

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#addEmployee（新接口 URL 待提供）；企业未初始化 EIAM | 测试数据: 未初始化 EIAM 的企业 customerId + 合法手机号

- 对未初始化 EIAM 的企业调用加员工接口
  - 返回失败并明确提示企业未初始化（不自动补初始化）
  - 本地不落人企关系记录

##### 批量加员工入参为空列表或仅1名员工时按边界约定处理

> 优先级: P4 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#batchAddEmployee（新接口 URL 待提供）；企业已初始化 EIAM | 测试数据: 空员工列表；仅 1 名员工的列表

- 批量加员工入参传空列表
  - 返回参数错误，不落任何数据
- 批量加员工入参仅 1 名员工
  - 同步成功，与单条加员工效果一致

##### EIAM加员工返回异常时透传错误且不产生脏数据

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#addEmployee（新接口 URL 待提供）；可构造 EIAM 侧加员工失败 | 测试数据: 已初始化企业的 customerId + 合法手机号

- EIAM 侧加员工返回异常时调用新接口
  - 返回失败且错误原因透传不吞错
  - 本地不落记录或与 EIAM 实际状态一致（不出现 EIAM 未成功而本地已落的脏数据）

#### 删员工

##### 基础账删员工时EIAM删除且新表记录逻辑删除

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#cancel（新接口 URL 待提供）；企业已初始化且存在该员工的人企关系记录 | 测试数据: 已添加员工的手机号

- 基础账调用删员工接口删除已有员工
  - EIAM 中该员工被删除
  - 新表对应记录逻辑删除 is_delete=1，source=BASE_DZ 保留可追溯

##### 经营账删员工时同步删除且来源标记BUSINESS_ACCOUNT

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#deleteEmployeeByTenantAndAccount（新接口 URL 待提供）；企业已初始化且存在该员工的人企关系记录 | 测试数据: 已添加员工的账号/手机号

- 经营账调用删员工接口按账号维度删除员工
  - EIAM 中该员工被删除
  - 新表对应记录逻辑删除，来源标记 BUSINESS_ACCOUNT

##### 删除人企关系不存在的员工时返回友好提示不报500

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#cancel / #deleteEmployeeByTenantAndAccount（新接口 URL 待提供）；企业下不存在该手机号的员工 | 测试数据: 未绑定该企业的手机号

- 删除人企关系不存在的员工（手机号未绑定该企业）
  - 返回友好的人企关系不存在提示，不报 500

##### 重复删除已删除员工时幂等处理

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#cancel（新接口 URL 待提供）；该员工已被删除过一次 | 测试数据: 已删除员工的手机号

- 对已删除的员工重复调用删员工接口
  - 幂等处理：返回成功或已删除提示，不报错
  - 新表无重复变更

##### 多来源人企记录的员工被删除时仅影响调用方来源记录

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#cancel（新接口 URL 待提供）；按需求文档三方汇合场景造数，同一手机号在 BASE_DZ、CY、BUSINESS_ACCOUNT 三来源均存在人企关系记录 | 测试数据: 三来源均有人企记录的手机号

- 基础账删除同时存在多来源人企记录的员工
  - 仅来源为 BASE_DZ 的记录被逻辑删除
  - CY、BUSINESS_ACCOUNT 来源的记录保持不变（假设：删除只作用调用方来源，需与开发确认）

##### EIAM删员工返回异常时透传错误且本地状态与EIAM一致

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.employee.EmployeeFacade#cancel（新接口 URL 待提供）；可构造 EIAM 侧删除失败 | 测试数据: 已添加员工的手机号

- EIAM 侧删员工返回异常时调用新接口
  - 返回失败且错误原因透传
  - 新表记录不提前逻辑删除（与 EIAM 状态一致）

#### 空间解绑企业

##### 空间解绑企业时不批量删除人企关系记录

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 企业已初始化 EIAM，cy_app_customer_employee_relation 存在多来源人企关系记录（重点逻辑改动：现状解绑会删除人企关系，方案改为只解绑不删） | 测试数据: 已绑定且有多来源人企记录的企业 customerId

- 对已绑定的企业执行空间解绑
  - 解绑成功，企业空间绑定关系解除
  - 新表人企关系记录全部保留，is_delete 均为 0（不批量删除，与老行为「解绑即删人企关系」形成差异）

##### 解绑企业后查询人员列表仍返回原人企关系数据

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 企业已完成空间解绑且解绑时人企关系未删除 | 测试数据: 已解绑企业的 customerId

- 解绑后调用查询企业绑定的人员列表接口
  - 列表仍返回解绑前的原人企关系数据（人企关系保留在查询侧的表现，需与开发确认）

##### 解绑后重新绑定初始化企业时原人企关系继续生效不重复

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 企业已完成空间解绑且人企关系记录保留 | 测试数据: 已解绑企业的 customerId

- 解绑后重新绑定/初始化同一企业
  - 操作成功，原人企关系记录继续生效
  - 不产生重复的人企关系或开通记录

##### 重复解绑已解绑企业时幂等处理

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 企业已完成空间解绑 | 测试数据: 已解绑企业的 customerId

- 对已解绑的企业重复执行解绑
  - 幂等处理，返回成功或已解绑提示，不报错

##### 解绑企业时EIAM返回异常透传不吞错

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 可构造 EIAM 侧解绑失败 | 测试数据: 已绑定企业的 customerId

- 解绑企业时 EIAM 返回异常
  - 返回失败且错误原因透传不吞错
  - 绑定关系与人企关系数据均保持不变

#### 查询企业列表

##### 查询企业列表时返回当前人拥有的主体信息并区分企业与机构

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 新接口 URL 待提供（经营账场景）；当前人名下同时拥有企业主体与机构 | 测试数据: 名下有多家企业+机构的账号

- 调用查询企业列表接口查询当前人的主体信息
  - 返回当前人拥有的主体信息
  - 返回结果区分企业主体与机构（确认主体后返回所选中的企业或机构信息）

##### 人企数据来自多个同步来源时查询企业列表正常合并返回

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 新接口 URL 待提供（经营账场景）；按需求文档三方汇合场景造数（基础账加 2 人 sync_source=BASE_DZ → 财赢进入同步增加 CY → 经营账加 1 人增加 BUSINESS_ACCOUNT） | 测试数据: 多来源汇合的企业 customerId

- 查询人企数据来自多个 sync_source 的企业列表
  - 正常返回合并后的数据，不受多来源 sync_source 影响
  - 数据无遗漏无重复

##### 当前人无任何企业主体时查询企业列表返回空列表

> 优先级: P4 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 测试数据: 名下无任何企业/机构的账号

- 当前人名下无任何企业主体时查询企业列表
  - 返回空列表，不报错

##### 传入不存在的标识查询企业列表时返回空或参数错误

> 优先级: P4 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 测试数据: 系统不存在的人标识/企业标识

- 传入不存在的人或企业标识查询企业列表
  - 返回空列表或参数错误，不报 500

#### 查询企业绑定的人员列表

##### 查询企业绑定的人员列表时返回企业下全量人员

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 新接口 URL 待提供（基础账场景）；企业已初始化且存在多名不同角色员工 | 测试数据: 含员工(0)/老板(1)/财务(2)多角色的企业 customerId

- 基础账调用查询企业绑定的人员列表接口
  - 返回企业下全量人员
  - 人员手机号、角色等字段与新表 cy_app_customer_employee_relation 数据一致

##### 三方汇合场景下人员列表按企业全量返回3人且来源覆盖三值

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 新接口 URL 待提供（基础账场景）；按需求文档示例造数：基础账加 2 名员工（sync_source=BASE_DZ）→ 从财赢进入点同步（增加 CY）→ 经营账先同步再加 1 名员工（增加 BUSINESS_ACCOUNT） | 测试数据: 完成三方汇合的企业 customerId

- 查询该企业绑定的人员列表
  - 返回 3 名人员，无遗漏无重复
  - 数据来源覆盖 BASE_DZ、CY、BUSINESS_ACCOUNT 三值

##### 已删除员工不出现在企业人员列表中

> 优先级: P2 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 新接口 URL 待提供（基础账场景）；企业存在已逻辑删除（is_delete=1）的员工记录 | 测试数据: 删过员工的手机号 + 在册员工手机号

- 查询存在已删除员工的企业人员列表
  - 已删除员工不出现在返回列表中
  - 在册员工正常返回

##### 手机号不满足UC规则被跳过的员工在人员列表中表现符合约定

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 新接口 URL 待提供（基础账场景）；企业存在同步时因手机号不满足 UC 规则被跳过的员工 | 测试数据: 含不合法手机号（如 'abc123'）加员工失败记录的企业 customerId

- 查询存在被跳过员工的企业人员列表
  - 被跳过员工的返回表现符合设计约定（是否落新表/是否返回待确认，与开发对齐后核对）

##### 企业未绑定任何人员时查询人员列表返回空列表

> 优先级: P4 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 测试数据: 已初始化但无员工的 customerId

- 查询未绑定任何人员的企业人员列表
  - 返回空列表，不报错

#### 添加二级组织

##### 添加二级组织成功且挂在企业本部下支持报销场景

> 优先级: P1 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.organization.OrganizationManageFacade#addOrganization（新接口 URL 待提供）；企业已初始化 EIAM（存在企业本部） | 测试数据: 已初始化企业的 customerId + 组织名称

- 对已初始化的企业调用添加二级组织接口（兼容报销场景）
  - EIAM 组织创建成功，父节点为企业本部
  - 报销兼容场景可正常使用该组织

##### 重复添加同名称二级组织时幂等或明确报错

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.organization.OrganizationManageFacade#addOrganization（新接口 URL 待提供）；企业已存在同名二级组织 | 测试数据: 已添加过的组织名称

- 重复添加同名称的二级组织
  - 幂等处理（返回已存在）或明确报错，不产生重复组织节点（行为待确认）

##### 企业未初始化时添加二级组织失败并明确提示

> 优先级: P3 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 前置条件: 调用的接口: cn.com.servyou.baseservice.eiam.sdk.organization.OrganizationManageFacade#addOrganization（新接口 URL 待提供）；企业未初始化 EIAM | 测试数据: 未初始化 EIAM 的企业 customerId

- 对未初始化 EIAM 的企业调用添加二级组织接口
  - 返回失败并明确提示企业未初始化（不自动补初始化，待确认）
  - EIAM 不创建组织

##### 组织入参缺失或非法时添加二级组织返回参数错误

> 优先级: P4 | 关联需求: 财赢APP融合二期人企关系新接口（17work 257263） | 测试数据: 组织名称传空字符串/null；组织名称传特殊字符 `<>&"'`

- 组织入参缺失（组织名称为空）或传非法值调用接口
  - 返回参数错误，EIAM 不创建组织
