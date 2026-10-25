# 失败模式

重置身份时最常踩的坑。按后果严重度排列。

## 复活

改完文件，重启应用又变回旧 ID。

**原因**：应用运行时把身份值缓存在浏览器存储层（Local Storage / IndexedDB）。启动时从那里读回内存，再写回配置文件，覆盖你刚改的值。

Claude 桌面版实测：改了 `ant-did`，重启后 `claude_desktop_config.json` 里的 `dframe-code-sections` 键又变回旧 UUID。sentry 的 `did` 也是旧值。

**处置**：顺序必须是

1. 关应用（全部进程，含 `crashpad-handler`、`gpu-process` 这类子进程）
2. 改配置文件
3. 清 Local Storage / Session Storage / IndexedDB
4. 启动应用
5. 再次全盘 grep 旧 ID 确认没复活

如果清完存储还复活，说明还有别的缓存层没清。逐个排查：`Cache/`、`Code Cache/`、`blob_storage/`、`Shared Dictionary/`。

## 目录改名漏项

设备 ID 同时是目录名时，只改主目录会漏掉其他引用。

Claude 桌面版实测：一个 `ant-did` 对应四处：

```
claude-code-sessions/<完整UUID>/
local-agent-mode-sessions/<前8位>/
local-agent-mode-sessions/skills-plugin/<固定UUID>/<完整UUID>/
spaces-present/<前8位>/
```

**后果**：漏掉的目录变成孤儿。文件还在，但应用按新 ID 查找找不到，用户的会话或用量记录从界面上消失。

**处置**：改名前列全部引用路径，两种形式都搜：

```bash
find <数据目录> -name "*<完整UUID>*" 2>/dev/null
find <数据目录> -name "*<UUID前8位>*" 2>/dev/null
```

改名后逐目录核对内容还在。

**迁移时的数据合并**：如果新旧目录都有同名文件（如 `usage-ledger/2026-10-25.ndjson`），要按主键去重合并，不能直接覆盖。Claude 的 ledger 按 `(ts, sessionId)` 去重。

## 波及面失控

改到了影响全系统的密钥。

| 位置 | 改了会怎样 |
| --- | --- |
| 浏览器 `Local State` 的 `os_crypt.encrypted_key` | 所有网站 cookie 解密失败，等于全部重新登录 |
| Windows `MachineGuid` | 影响所有软件授权 |
| WSL `/etc/machine-id` | 影响 systemd 和相关软件授权 |
| 系统级 CA 证书 | 影响所有 TLS 校验 |

**处置**：这些超出「单个应用身份」的范围。默认保留，在报告里向用户说明「没做，原因是波及全系统，需要你单独确认」。

## 删了不可恢复

删错文件导致应用直接不可用。

Claude 实测：

| 操作 | 结果 |
| --- | --- |
| 删 `.credentials.json` | `Not logged in · Please run /login` |
| 删数据目录的 `schema` / `MANIFEST` 文件 | 应用可能无法打开数据库 |
| 删 `Local State` 整个文件 | cookie 全部失效 |

**处置**：删任何文件前先备份。结构必需的文件用「换成占位值」代替删除。

Claude 的 `.credentials.json` 可以换成占位 token：

```json
{"claudeAiOauth": {
  "accessToken": "sk-ant-oat01-" + "0"*70,
  "refreshToken": "sk-ant-ort01-" + "0"*70,
  "expiresAt": <远期时间戳>,
  "refreshTokenExpiresAt": <远期时间戳>,
  "scopes": ["user:inference"],
  "subscriptionType": "pro",
  "rateLimitTier": "default_claude_ai"
}}
```

这样文件结构完整（不会触发 `Not logged in`），但真实凭据已不在本机。

## 误删个人数据

把用户的记录当成凭据清掉。

Claude 里容易误判的：

| 数据 | 是不是凭据 |
| --- | --- |
| `~/.claude/projects/` 会话记录 | 不是，是用户的工作历史 |
| 浏览器 History 里的 claude.ai 访问记录 | 不是，是浏览记录 |
| `~/.claude/file-history/` 编辑快照 | 不是 |
| `~/.claude/history.jsonl` 输入历史 | 不是（但可能含旧用户名路径） |

**处置**：个人数据默认保留。用户明确要求才删。可以清理里面的身份**引用**（如把旧用户名路径替换掉），但保留记录本身。

如果已经误删，从备份恢复。

## 验证不充分

只看进程在，没跑真实命令。

Claude 的验证要覆盖：

```bash
# 1. 真实调用
claude -p "reply OK"

# 2. 身份已换
python3 -c "import json;d=json.load(open('$HOME/.claude.json'));print(d.get('userID'))"

# 3. 旧身份无残留
grep -rl "<旧ID>" ~/.claude/ 2>/dev/null

# 4. 自定义配置还在
python3 -c "
import json;d=json.load(open('$HOME/.claude/settings.json'))
print('base_url:', d['env'].get('ANTHROPIC_BASE_URL'))
print('models:', len(d.get('modelPicker',{}).get('options',[])))
print('hooks:', len(d.get('hooks',{})))
"
```

第 4 项最容易忘。重置身份不应该动用户的 env、provider、model、插件配置。

## 明文密钥扩散

配置里有一把明文 key，改的时候只改了一处。

Claude 实测：`settings.json` 里的 `ANTHROPIC_AUTH_TOKEN` 在 `settings.json.pebrel-bak` 里还有一份副本。

**处置**：改之前全盘搜 key 前缀：

```bash
grep -rl "sk-\|AIza\|ghp_" ~/.claude/ /mnt/c/Users/*/.claude/ 2>/dev/null
```

改完再搜一遍确认 0 命中。
