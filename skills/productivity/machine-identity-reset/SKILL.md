---
name: machine-identity-reset
description: 重置 AI CLI 或桌面应用在本机的身份标识（设备 ID、机器指纹、登录凭据），保留自定义配置。手动触发。
disable-model-invocation: "true"
---

# Machine Identity Reset

重置某个应用在本机的身份，保留你自定义的配置。

这个动作会改动登录态和数据目录，属于破坏性操作。默认先列清单给用户确认，再动手。

## 完成标准

四条全部满足才算完成，缺一条就是没做完：

- 每个载体都落进了 [分类](references/carriers.md#分类) 的五档之一，无漏项
- 目标应用的真实命令跑通，不是只看进程在
- 自定义配置逐项确认仍在：env、provider、model、插件、会话历史
- 旧身份全盘 grep 0 命中

## 1 列载体

```bash
python3 <本 skill 目录>/scripts/scan_carriers.py            # 列清单
python3 <本 skill 目录>/scripts/scan_carriers.py --old-id X  # 顺便查残留
```

脚本只读不改。在 WSL 里跑能同时看到 Windows 侧（经 `/mnt/c`）。

四类位置都要扫。漏掉任一类，身份就留在那里：

| 类别 | 典型位置 |
| --- | --- |
| 应用数据目录 | 版本化数据目录、旧版本残留目录 |
| 应用配置文件 | 主配置、凭据文件、状态文件 |
| 浏览器侧 | cookie、localStorage、IndexedDB、Session Storage |
| 系统层 | 注册表、原生消息宿主、凭据管理器、定时任务 |

Claude 的具体位置见 [Claude 载体地图](references/claude-map.md)。换其他应用时照判据重新扫一遍，不要照抄路径。

## 2 分类

每个载体先归类再决定动作。判据和实测方法见 [载体分类](references/carriers.md)。

只有**身份标识**和**登录凭据**两档允许重置。结构必需、个人数据、遥测重采集三档要保留或换别的办法。

## 3 先验证再删

删之前必须确认「删了会重建」或「删了不影响功能」。三种办法：

- 二进制字符串分析：在可执行文件里找 `randomUUID` / `randomBytes` 与字段名同现
- 试删 + 立即还原：备份 → 删 → 跑命令 → 看行为 → 还原
- 观察重建：删 → 跑命令 → 检查字段是否重新出现

不许靠猜。删错结构必需字段会让应用直接不可用。

## 4 备份

按应用和浏览器分目录，落到 `~/<name>-backup-<日期>/`。记录每个文件的原值和恢复方法。

备份要覆盖「会改的」和「可能连带坏的」两类，不只是配置文件。

## 5 重置

顺序固定，颠倒会出问题：

1. 关闭目标应用（所有进程，含子进程）
2. 改配置文件里的身份字段
3. 改数据目录名（ID 同时是目录名时，连带迁移所有引用该 ID 的目录）
4. 清浏览器存储层
5. 重启应用，确认没有复活

**复活**是最常见的失败：应用运行时会从浏览器存储读回旧 ID 并写回配置。见 [失败模式](references/failure-modes.md#复活)。

## 6 验证

```bash
python3 <本 skill 目录>/scripts/verify_reset.py \
  --old-id <旧ID1> --old-id <旧ID2>
```

四项全过才算完成：功能真跑通、身份已换新、旧身份 0 命中、自定义配置仍在。

脚本会用 PowerShell 调 Windows 侧 CLI（`claude.cmd` 是批处理，直接 subprocess 调会报 `too many arguments`）。

不想消耗额度时加 `--skip-run`，但那样不算完整验证。

## 恢复路径

重置后官方账号能力会消失。怎么恢复见 [Claude 载体地图的恢复段](references/claude-map.md#恢复)。

## 报告

给用户报四件事：换了哪些 ID（旧值 → 新值）、清了哪些凭据、哪些无法清理及原因、备份在哪。
