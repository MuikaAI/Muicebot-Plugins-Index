# 插件贡献指南(Beta)

首先非常感谢您为 MuiceBot 贡献插件⭐本指南旨在指导您如何科学规范地提交插件

## 前提条件

Muicebot 的插件发布准备工作是与 [Nonebot 插件发布之前的准备工作](https://nonebot.dev/docs/developer/plugin-publishing) 是一致的，这里只简单提一些要点

- 插件依赖中需要加入 Muicebot 并指定版本号区间以防止出现版本兼容性问题
- 需要在插件的入口文件中填写插件元数据 `__plugin_meta__` 才能通过工作流审核
- **不需要**发布到 Pypi, Muicebot 是通过 `git clone` 方式安装插件的。如需保证版本稳定性，建议另开一个开发分支

## 发布插件

提交 [Issue 表单](https://github.com/MuikaAI/Muicebot-Plugins-Index/issues) ，然后等待工作流测试通过，测试通过后 MuiceAI Bot 会创建含有该插件信息的 Pull Requests 请求

> [!TIP]
>
> 若插件检查未通过或信息有误，不必关闭当前 Issue。只需更新插件并在 issue 线程中输入 `/retest` 即可重新进行测试

之后，Muicebot 维护团队 (@MuikaAI/bot) 和一些插件开发者会初步检查插件代码，帮助减少该插件的问题。