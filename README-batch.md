# 25 项数据分析批次

本工作区包含 25 个中型全栈数据分析项目。由于技能单批上限为 10，输入拆成：

- `batch-prompts-01.txt`：1-10
- `batch-prompts-02.txt`：11-20
- `batch-prompts-03.txt`：21-25

统一端口全局连续分配；`scripts/qa_project.sh` 使用共享槽位，最多运行 3 个 Docker 栈。

```bash
python3 scripts/generate_batch.py
python3 /Users/ali/.codex/skills/pr-batch-project/scripts/validate_batch.py batch-prompts-01.txt
python3 /Users/ali/.codex/skills/pr-batch-project/scripts/validate_batch.py batch-prompts-02.txt
python3 /Users/ali/.codex/skills/pr-batch-project/scripts/validate_batch.py batch-prompts-03.txt
bash scripts/qa_project.sh gb-7001
```
