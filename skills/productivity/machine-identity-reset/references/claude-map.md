# Claude 载体地图

Claude 在本机的全部身份载体。快照日期 **2026-10-25**，版本：

| 形态 | 版本 | 位置 |
| --- | --- | --- |
| WSL CLI（原生二进制） | 2.1.300 | `~/.local/bin/claude` → `~/.local/share/claude/versions/2.1.300` |
| Windows CLI（npm 全局） | 2.1.310 | `%APPDATA%\npm\node_modules\@anthropic-ai\claude-code` |
| Windows 桌面版（MSIX） | 3.6556.2.0 | `C:\Program Files\WindowsApps\Claude_3.6556.2.0_x64__pzs8sxrjxfjjc` |
| 桌面版内置 CLI | 2.1.308 | `<桌面版数据目录>\claude-code\` |

三套配置**互相独立**，各有自己的 `userID` / `machineID`。改一处不影响另外两处。

---

## 一、WSL

### 身份字段

`~/.claude.json`：

| 字段 | 值形态 | 实测结论 |
| --- | --- | --- |
| `userID` | 64 位 hex | 本地 `randomBytes(32)` 生成，删了自动换新 |
| `machineID` | 64 位 hex | 同上 |
| `oauthAccount` | `{accountUuid, emailAddress, organizationUuid, displayName, ...}` | 删了自动重建，但只恢复前三个字段 |
| `customApiKeyResponses` | `{approved: [...], rejected: [...]}` | 不重建，可安全删 |

### 凭据

`~/.claude/.credentials.json`（权限 600）：

```json
{"claudeAiOauth": {
  "accessToken": "sk-ant-oat01-...",
  "refreshToken": "sk-ant-ort01-...",
  "expiresAt": <ms>,
  "refreshTokenExpiresAt": <ms>,
  "scopes": [...],
  "subscriptionType": "pro",
  "rateLimitTier": "default_claude_ai"
}}
```

不含 accountUuid 或 email。整个删掉 → `Not logged in · Please run /login`。换成占位 token 则正常工作（前提是走第三方网关）。

### 其他目录

| 路径 | 内容 | 是否含身份 |
| --- | --- | --- |
| `~/.claude/projects/` | 会话记录 jsonl | 含旧用户名路径，属个人数据 |
| `~/.claude/history.jsonl` | 输入历史，含 `project` 字段 | 含旧用户名路径 |
| `~/.claude/sessions/` | 运行中会话的 pid/token | 含 `pidDomain` 里的 machine-id |
| `~/.claude/shell-snapshots/` | shell 环境快照 | 无 |
| `~/.claude/plugins/` | 插件 + marketplace git 仓库 | 含 GitHub 用户名（remote URL） |
| `~/.claude/skills/` | 技能 | 无 |
| `~/.claude/remote/` | ccd-cli 二进制 + 运行 socket | 含 daemon token |
| `~/.claude/daemon/` | `control.key`（32 字节随机） | 是，但为进程通信密钥 |
| `~/.claude/file-history/` | 编辑前的文件快照 | 属个人数据 |
| `~/.claude/backups/` | `.claude.json` 自动备份 | 含旧身份 |
| `~/.claude/session-env/` | 空目录 | 无 |
| `~/.claude/telemetry/` | 空目录 | 无 |
| `~/.cache/claude-cli-nodejs/` | MCP 日志，按项目分目录 | 目录名含旧用户名 |
| `~/.local/share/claude/versions/` | 多版本二进制 | 无 |

### 身份派生链

```
~/.claude.json 的 machineID / userID
  → 本地 crypto.randomBytes(32).toString('hex')
  → 不读 /etc/machine-id
  → 不读 Windows MachineGuid
```

验证方法：

```bash
strings -n 10 ~/.local/share/claude/versions/2.1.300 > /tmp/cc.strings
grep -o ".\{200\}machineID.\{0,300\}" /tmp/cc.strings
```

输出里能看到 `let s=Tu(32).toString("hex");return n.setGeneratedMachineID(s)`。

---

## 二、Windows CLI

位置：`C:\Users\<用户>\.claude\`

配置结构与 WSL 相同，但**是独立的一套**：

| 文件 | 说明 |
| --- | --- |
| `.claude\settings.json` | 主配置，env 里可能有明文 API key |
| `.claude.json` | 状态文件，含独立的 userID / machineID |

本机实测：Windows CLI 的 `userID` 和 `machineID` 与 WSL 的完全不同。

### 明文 key 风险

Windows CLI 的 `settings.json` 常见问题：`ANTHROPIC_AUTH_TOKEN` 直接写明文。

```json
"env": {
  "ANTHROPIC_BASE_URL": "https://opencode.ai/zen/go",
  "ANTHROPIC_AUTH_TOKEN": "sk-...64字符明文...",
  "ANTHROPIC_MODEL": "deepseek-v4-flash"
}
```

检查是否有副本：

```bash
grep -rl "sk-" ~/.claude/ /mnt/c/Users/*/.claude/ 2>/dev/null
```

本机发现过 `settings.json.pebrel-bak` 是同一把 key 的备份。

---

## 三、Windows 桌面版

数据目录有三处，注意区分：

| 目录 | 用途 | 判断方法 |
| --- | --- | --- |
| `%LOCALAPPDATA%\Claude-3p` | **当前使用** | 进程命令行 `--user-data-dir` 指向这里 |
| `%LOCALAPPDATA%\Claude` | 引导层，只有 `{"deploymentMode":"3p"}` | 只有 1 个 json + logs |
| `%APPDATA%\Claude` | 旧 Electron 版残留 | `config.json` 里 `appVersion` 是老版本 |

确认哪个在用：

```powershell
Get-CimInstance Win32_Process -Filter "Name='claude.exe'" |
  Select-Object -ExpandProperty CommandLine |
  Select-String "user-data-dir"
```

### 设备 ID（ant-did）

`%LOCALAPPDATA%\Claude-3p\ant-did`：48 字符的 base64，解码后是标准 UUID。

```bash
python3 -c "import base64;print(base64.b64decode(open('ant-did').read()).decode())"
```

这个 ID **同时是四处目录名**：

```
claude-code-sessions/<完整UUID>/
local-agent-mode-sessions/<UUID前8位>/
local-agent-mode-sessions/skills-plugin/00000000-0000-4000-8000-000000000001/<完整UUID>/
spaces-present/<UUID前8位>/
```

改 ID 必须连带迁移这四个目录，否则用户的会话从界面上消失（文件还在）。

### 引用了 ant-did 的配置文件

改完 ant-did 后，这些文件里的旧 ID 也要替换：

| 文件 | 引用形式 |
| --- | --- |
| `config.json` | `lastKnownAccountUuid` |
| `claude_desktop_config.json` | `bypassPermissionsOptInByAccount`、`bypassPermissionsGateByAccount`、`epitaxy-*` 键名 |
| `ccd-session-presets.json` | `byAccount` 的键 |
| `cowork-enabled-cli-ops.json` | `ownerAccountId` |
| `sentry/session.json` | `did` 字段（会自动重建） |

### 浏览器存储层

| 路径 | 内容 |
| --- | --- |
| `Local Storage/leveldb/` | `ccd-session-store`、`epitaxy-*`，含旧 ID |
| `Session Storage/` | 会话态 |
| `IndexedDB/app_localhost_0.indexeddb.leveldb/` | 网关模式的本地存储 |
| `Network/Cookies` | 应用内 cookie |
| `Network/Trust Tokens` | 反欺诈令牌 |
| `DIPS` / `DIPS-wal` | 防跨站跟踪数据库 |
| `Local State` | `os_crypt.encrypted_key`（DPAPI 包裹的 cookie 密钥） |

### 遥测

`sentry/scope_v3.json` 每次启动现场采集：

```json
"device": {
  "boot_time": "<本次开机时间>",
  "arch": "x64",
  "memory_size": <实际内存>,
  "processor_count": <实际核心数>,
  "cpu_description": "<CPU 型号>",
  "processor_frequency": <频率>,
  "screen_resolution": "<分辨率>"
},
"os": {"name": "Windows", "version": "<具体版本号>"},
"user": {"id": "<ant-did>", "organization_id": "<组织 UUID>"}
```

删了立刻重建，内容一样。上报地址：`claude.ai/api/event_logging/v2/batch`、`claude.ai/api/v2/rum`、`ingest.us.sentry.io`。

### 网关配置

`configLibrary/00000000-0000-4000-8000-6d6167706965.json`（magpie 写入）：

```json
{
  "coworkEgressAllowedHosts": ["*"],
  "inferenceGatewayBaseUrl": "http://127.0.0.1:3425",
  "inferenceGatewayApiKey": "magpie-claude-desktop",
  "inferenceProvider": "gateway"
}
```

`coworkEgressAllowedHosts: ["*"]` 是外联白名单全开。

---

## 四、浏览器侧（claude.ai 网页登录）

### 有登录态时存在的载体

**Cookies**（`Network/Cookies`）：

| Cookie | 域 | 性质 |
| --- | --- | --- |
| `sessionKey` / `sessionKeyLC` | `.claude.ai` | 登录会话，最关键 |
| `cf_clearance` | `.claude.ai` | Cloudflare 通行证，有效期约 1 年 |
| `anthropic-device-id` | `claude.ai`、`platform.claude.com` | 设备标识 |
| `__ssid` | `.claude.ai` | 会话标识 |
| `ajs_anonymous_id` / `ajs_user_id` | `.claude.ai` | 分析 ID |
| `lastActiveOrg` | `.claude.ai` | 最后活跃组织 |
| `intercom-device-id-*` | `.claude.ai` | 客服系统设备 ID |
| `__stripe_mid` | `.claude.ai` | 支付指纹 |

**Local Storage**：

| key | 内容 |
| --- | --- |
| `__qk_hint_account_uuid` | 账号 UUID |
| `ccd-sync-owner` / `ccd-sync-org` | 账号 + 组织 UUID |
| `rq-cache-confirmed-account` | 账号 UUID |
| `lastLoginMethod` | `google` 等登录方式 |
| `claude_checkout_journey:v1:<org>:pro` | 组织 UUID + 订阅档 |
| `ajs_user_traits`（在 `a.claude.ai` 域下） | **完整邮箱 + 账号 UUID + 组织 UUID + UA + 国家** |
| `persisted.ccd-session-presets.<uuid>.<org>` | 账号 + 组织 |

**IndexedDB**：

| 库 | 内容 |
| --- | --- |
| `https_claude.ai_0` | `claude-device-binding`（`device_binding_keys`）、`claude-conversation-store`、`outbox` |
| `https_platform.claude.com_0` | `keyval-store` |

`claude-device-binding` 是 Anthropic 服务端的设备绑定凭据，重置浏览器数据会一并失效。

**第三方域**：

| 域 | key | 内容 |
| --- | --- | --- |
| `ip.net.coffee` | `claude_ip_history` | **访问过的 IP 地址 + 时间 + 国家** |

### 各浏览器实测状态（本机 2026-10-25）

| 浏览器 | claude.ai 登录态 | 备注 |
| --- | --- | --- |
| Vivaldi | 有（主力） | 39 条 cookie、163 个 localStorage key |
| Chrome（Windows） | 无（已清） | 26 条 cookie、295 个 key 已删 |
| Edge | 无 | 只有 1 条 GitHub 仓库名缓存 |
| Chrome（WSL） | 无 | 最后访问 2026-09-17 |

### 清理方法

Cookie 用 sqlite 直删：

```python
import sqlite3
con = sqlite3.connect('<profile>/Network/Cookies')
con.execute("delete from cookies where host_key like '%claude%' or host_key like '%anthropic%'")
con.commit()
```

Local Storage 是 LevelDB，需要 plyvel：

```bash
pip install --break-system-packages plyvel
```

```python
import plyvel
db = plyvel.DB('<profile>/Local Storage/leveldb', create_if_missing=False)
for k, v in list(db):
    if 'claude' in k.decode('utf-8', 'replace').lower():
        db.delete(k)
db.close()
```

浏览器必须先关闭，否则写入被锁。

---

## 五、系统层

| 位置 | 内容 | 处置 |
| --- | --- | --- |
| `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.anthropic.claude_browser_extension` | 原生消息宿主，默认值常为空 | 删 |
| `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.anthropic.claude_browser_extension` | 同上 | 删 |
| `HKCU\Software\Classes\claude` | `claude://` 协议处理 | 应用需要，保留 |
| Windows 凭据管理器 | 本机实测无 claude 条目 | — |

检查是否有死链：

```powershell
reg query "HKCU\Software\Google\Chrome\NativeMessagingHosts" /s
```

如果默认值显示「数值未设置」，说明是残留死链，可删。

---

## 六、不属于单个应用的密钥

这些改了影响全系统，默认保留：

| 位置 | 影响 |
| --- | --- |
| 浏览器 `Local State` 的 `os_crypt.encrypted_key` | 所有网站 cookie 解密失败 |
| Windows `MachineGuid` | 所有软件授权 |
| WSL `/etc/machine-id` | systemd 和相关软件 |

Claude 不读这三个（machineID 是本地随机生成），所以留着不影响身份重置效果。

---

## 恢复

### 恢复官方订阅能力

```bash
claude /login
```

会走浏览器 OAuth，重新写入 `.credentials.json` 和 `.claude.json` 的 `oauthAccount`。

### 恢复 claude.ai 网页登录

浏览器打开 `https://claude.ai` 重新登录。会重新建立：
- `sessionKey` cookie
- IndexedDB 里的 `claude-device-binding`（新设备绑定，服务端会视为新设备）
- `anthropic-device-id`

### 恢复会话记录

如果误删了会话目录，从备份拷回：

```bash
cp -a ~/claude-cleanup-backup-<日期>/windows/claude-code-sessions/* \
      %LOCALAPPDATA%/Claude-3p/claude-code-sessions/
```

### 从备份整体还原

```bash
cp -a ~/claude-cleanup-backup-<日期>/wsl/.claude.json ~/
cp -a ~/claude-cleanup-backup-<日期>/wsl/.credentials.json ~/.claude/
```

---

## 实测坑

按踩到的顺序记录：

1. **应用运行时改 ant-did 会复活** —— 桌面版从 Local Storage 读回旧 ID 写回 `claude_desktop_config.json`。必须先关应用，再改文件，再清 Local Storage，最后启动。

2. **目录迁移容易漏** —— 一个 ant-did 对应四处目录，其中 `local-agent-mode-sessions/<前8位>` 这种短 ID 形式最容易漏。漏了会导致 `usage-ledger` 里的用量记录丢失（数据还在旧目录，但应用读不到）。

3. **`oauthAccount` 删不干净** —— 删了启动后自动重建，只恢复 accountUuid + email + organizationUuid。想彻底清需要同时处理 credentials。

4. **Cookie 库被占用** —— 浏览器/应用运行时 `Network/Cookies` 无法读取，WSL、PowerShell、`System.IO.File` 三种方式都失败。必须关进程。

5. **`cf_clearance` 有效期很长** —— 约 1 年，是 Cloudflare 反爬通行证。旧目录留着等于身份留一年。

6. **`ip.net.coffee` 容易被忽略** —— 第三方站点记录了访问过的 IP。扫 claude 关键词时不会命中，要单独查 `ip_history` 类 key。

7. **Service Worker 缓存会误报** —— `grep -r claude` 会命中扩展脚本里的平台匹配列表（`patterns: ['claude.ai']`），不是身份数据。判断方法：看命中文件里有没有 origin hash 对应的目录名。

8. **`sentry` 删了立刻重建** —— 不要以为删了就干净，它每次启动重新采集硬件信息。
