# B04 刘明轩：Backlog 与组内交接

## 完成情况

| 编号 | 工作 | 负责人 | 产物与验收条件 | 状态 |
|---|---|---|---|---|
| B04-01 | 对照 A04 公共契约 | 刘明轩 | 公共接口说明引用真实文件，明确字段和格式 | 文档已整理，本人审阅 |
| B04-02 | 记录统一方案 | 刘明轩 | ADR 写清采用理由、替代方案和影响 | 文档已整理，本人审阅 |
| B04-03 | 核对产物读取 | 刘明轩辅助、李昊阳复查 | artifact URI 能解析，引用哈希匹配 | 接收检查中8个引用匹配；完整校验待李昊阳执行 |
| B04-04 | 组内同步 | 刘明轩 | 其他三人收到相同版本并反馈 | 等待反馈 |
| B04-05 | 补充配对讨论 | 刘明轩协调 | 以下待办有结论或负责人 | 沟通结束 |
| B04-06 | 个人贡献入库 | 刘明轩 | AI记录、真实作者与提交SHA可追溯 | 本人已填写和提交 |

## 发给组员的材料

- **段朝睿：**看公共接口说明、create-request 的 draftInput、job 的 draftOutput，以及 examples/requests/draft.json 和 examples/responses/draft-succeeded.json。负责补全 DRAFT 业务细节。
- **张加坤：**看公共接口说明、repairInput、repairOutput、repair.json 和纯 MD 报告。负责修复输入、输出及失败候选说明。
- **李昊阳：**接收本包的 contracts、examples、artifacts、validate.py、requirements.txt 和 tests，按提交说明安装依赖后运行 validate.py 和 tests；记录实际结果，汇总全组提交材料。