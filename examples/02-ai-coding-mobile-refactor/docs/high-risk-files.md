# 高风险文件

本示例没有真实签名、证书或发布配置，但练习时仍按真实移动端项目约束处理。

禁止 agent 自动修改：

- `pyproject.toml` 或依赖配置。
- CI 配置。
- 删除测试文件。
- 修改文档中的禁止事项。

真实 iOS/Android 项目中还应包含：

- `Info.plist`
- `*.entitlements`
- `AndroidManifest.xml`
- `gradle.properties`
- `*.keystore`
- signing/release 相关脚本
