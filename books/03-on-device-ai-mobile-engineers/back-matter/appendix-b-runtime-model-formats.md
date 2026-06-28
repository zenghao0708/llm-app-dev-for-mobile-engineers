# 附录 B Runtime 与模型格式对照

本附录用于帮助移动端工程师梳理 runtime、模型格式和工程关注点。具体 API 和版本会随平台演进变化，落地前应查阅对应官方文档，并在目标设备上实测。

| 方向 | 常见选择 | 工程关注点 |
| --- | --- | --- |
| iOS | Core ML、Metal、系统机器学习能力 | 模型转换、Neural Engine 支持、内存峰值、App 包体 |
| Android | TensorFlow Lite、NNAPI、GPU delegate、厂商能力 | 设备碎片化、delegate 兼容、低端机性能、ANR 风险 |
| 跨平台 | ONNX Runtime、MediaPipe、原生插件封装 | bridge 传输、平台能力差异、统一错误模型 |
| LLM | 本地推理 runtime、量化格式、tokenizer | KV cache、上下文长度、首 token 延迟、内存占用 |
| 多模态 | OCR、图像分类、视觉 embedding | 图片解码、尺寸控制、旋转和 EXIF、隐私遮挡 |

## B.1 选择 Runtime 的评估维度

选择 runtime 时，不要只看是否“支持某个模型”。建议按下面维度评估：

| 维度 | 问题 |
| --- | --- |
| 模型格式 | 是否支持当前模型或可稳定转换？ |
| 硬件加速 | 是否能使用目标设备的 CPU/GPU/NPU？ |
| 冷启动 | runtime 初始化和模型加载是否可接受？ |
| 内存 | 峰值内存是否覆盖低端设备？ |
| 调试 | 是否能定位加载失败、delegate 失败和性能退化？ |
| 包体 | runtime 本身会增加多少体积？ |
| 许可证 | 是否满足商业产品使用要求？ |
| 更新 | 模型、runtime 和配置能否独立更新？ |

如果一个 runtime 在旗舰设备上表现很好，但低端设备经常加载失败，就不适合直接全量上线。移动端选择要看目标用户分布，而不是只看开发机结果。

## B.2 模型格式转换检查

模型从训练环境进入移动端，通常要经过转换、量化和打包。检查项包括：

- 输入输出名称是否稳定。
- 动态 shape 是否被目标 runtime 支持。
- tokenizer、配置和模型权重是否匹配。
- 量化方式是否被目标硬件加速支持。
- 转换后精度是否经过回归集验证。
- 模型文件是否包含不必要的调试或训练信息。
- 模型版本和 schema 是否写入 manifest。

转换成功不等于可发布。可发布意味着它能在目标设备上加载、推理、降级、回滚，并通过业务评测。

## B.3 移动端模型包建议结构

```text
model_bundle/
  manifest.json
  model/
    model.bin
  tokenizer/
    tokenizer.json
  config/
    runtime.json
    preprocessor.json
  checksums.txt
  license.txt
  smoke_tests.jsonl
```

`smoke_tests.jsonl` 可以保存少量非敏感样本，用于下载后快速验证模型能否输出合法结构。它不是完整评测集，只是防止明显损坏包进入生产路径。

## B.4 Runtime 接入验收

接入 runtime 后至少要完成：

| 验收项 | 说明 |
| --- | --- |
| 加载验收 | 冷启动、懒加载、重复加载和释放 |
| 推理验收 | 小输入、大输入、异常输入 |
| 性能验收 | P50/P95 延迟、峰值内存、发热 |
| 生命周期 | 前后台切换、锁屏、来电、进程回收 |
| 错误处理 | 模型损坏、配置错误、delegate 不可用 |
| 隐私 | 输入、输出和中间结果不进入日志 |
| 回滚 | 新模型失败时可恢复旧版本 |

没有这张验收表，runtime 接入很容易停留在“能跑一个样例”的阶段。
