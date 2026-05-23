# session-wrap

<p align="center">
    <a href="https://linux.do" alt="LINUX DO"><img src="https://shorturl.at/ggSqS" /></a>
</p>

[![License](https://img.shields.io/github/license/leonsong09/session-wrap)](https://github.com/leonsong09/session-wrap/blob/main/LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/leonsong09/session-wrap)](https://github.com/leonsong09/session-wrap/commits/main)
[![Repo Size](https://img.shields.io/github/repo-size/leonsong09/session-wrap)](https://github.com/leonsong09/session-wrap)

> 面向**当前会话**的收尾 skill，用于压缩已完成工作、关键决策、验证情况、经验风险与下一步建议。

## 适用场景

当用户想要：
- 总结会话
- 会话总结
- 收尾
- 会话收尾
- 结束会话
- 总结本次会话

## 不适用场景

以下情况更适合其他 skill：
- 同日多会话/多项目日报：`project-daily-summary`
- 纯提交维度总结：`commit-daily-summary`
- 调研分析纪要：`research-note-wrap`

## 触发词

中文：
- 总结会话
- 会话总结
- 收尾
- 会话收尾
- 结束会话
- 总结本次会话

English:
- wrap up this session
- summarize the current session
- session closeout

## 工作流

1. 默认只看**当前会话**。
2. 检查工作树、差异与最近提交，收集最小必要证据。
3. 按工作流/主题总结已完成内容，而不是按时间流水账总结。
4. 抽取 learnings、风险、未完成项。
5. 给出下一步建议与 commit guidance，但不自动 commit。

## 安装

将整个目录复制到本地技能目录，例如：

```text
~/.codex/skills/session-wrap
```

或：

```text
~/.agents/skills/session-wrap
```

## 仓库结构

```text
session-wrap/
  SKILL.md
  README.md
  LICENSE
  .gitignore
  references/
```

## 配置

该 skill 不要求固定输出目录；通常直接在当前会话中输出即可。
若项目有 handoff 或 wrap-up 文档规范，可由项目 `AGENTS.md` 进一步约束。

## 用法示例

### 示例输入

```text
总结会话
```

### 预期行为

- 只总结当前会话
- 明确已完成 / 未完成 / 风险 / 下一步
- 如实报告验证情况
- 不假装“已经完成、已经可提交”

## 输出示例

```markdown
## 本次会话总结

### 已完成
- ...

### 关键决策
- ...

### 涉及文件 / 模块
- ...

### 验证情况
- 已验证：...
- 未验证：...

### 经验与风险
- ...

### 下一步建议
- ...
```

## 限制

- 它只适合当前会话，不适合跨天/跨会话的大范围汇总。
- 需要依赖会话证据或 git 状态，不能虚构成果。
- 如果用户真正要的是日报或研究笔记，应切换到对应 skill。

## License

MIT


