# CI 等价命令

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m py_compile src/ai_refactor/*.py
```

这两个命令分别对应测试和静态编译检查。读者让 agent 修改代码后，应要求它至少运行测试命令，并在输出中记录结果。
