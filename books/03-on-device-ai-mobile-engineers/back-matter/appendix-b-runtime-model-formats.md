# 附录 B Runtime 与模型格式对照

本附录用于记录后续正式扩写时需要核验的 runtime 和模型格式。出版前应重新查阅官方资料。

| 方向 | 需要核验 |
| --- | --- |
| iOS | Core ML、Metal、Neural Engine、模型包更新 |
| Android | TensorFlow Lite、NNAPI、GPU delegate、设备兼容 |
| 跨平台 | ONNX Runtime、MediaPipe、Flutter/RN 原生桥接 |
| LLM | 本地 tokenizer、KV cache、量化格式、内存占用 |

正式书稿应为每个 runtime 补充最小可运行示例或伪代码流程，并说明适用边界。
