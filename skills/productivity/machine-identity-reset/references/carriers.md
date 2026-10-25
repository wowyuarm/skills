# 载体分类

跨应用通用的判断方法。Claude 的具体位置在 [claude-map.md](claude-map.md)。

## 分类

每个身份载体落进五档之一。只有前两档允许重置。

| 档位 | 判据 | 处置 | 例子 |
| --- | --- | --- | --- |
| 身份标识 | 换掉不影响功能 | 重置 | 本地随机生成的设备 ID |
| 登录凭据 | 换掉需要重新登录 | 重置或换占位值 | OAuth token、session cookie |
| 结构必需 | 删了应用直接坏 | 保留 | 数据目录的索引、schema 版本 |
| 个人数据 | 属于用户的记录，不是凭据 | 保留，除非明确要求 | 会话历史、浏览记录 |
| 遥测重采集 | 删了下次启动又生成 | 无法重置，只能关遥测 | CPU 型号、屏幕分辨率、开机时间 |

## 判断「本地随机生成」

结论：删掉就会自动换新值，不会从硬件派生。

方法：在可执行文件里找字段名和生成函数的同现。

```bash
# 从二进制提取字符串
strings -n 10 /path/to/binary > /tmp/app.strings

# 找字段名附近的生成调用
grep -o ".\{200\}machineID.\{0,300\}" /tmp/app.strings
```

Claude 实测结果：`machineID` 和 `userID` 都是 `crypto.randomBytes(32).toString('hex')` 本地生成，不读 Windows MachineGuid，也不读 `/etc/machine-id`。

反例：如果字段值等于 `MachineGuid` 或 `/etc/machine-id` 的内容，说明是从硬件派生的，删了会重新读取同样的值，等于没换。

## 判断「结构必需」

方法：备份 → 删 → 跑命令 → 还原。

Claude 实测：

| 删掉的东西 | 结果 |
| --- | --- |
| `.credentials.json` 整个删 | `Not logged in · Please run /login`，不可用 |
| `.credentials.json` 换成假 token | 正常工作（走网关时 OAuth 不参与） |
| `.claude.json` 的 `userID` + `machineID` | 自动生成新值，功能正常 |
| `.claude.json` 的 `oauthAccount` | 自动重建，但只恢复 accountUuid + email，其他字段丢失 |
| `.claude.json` 的 `customApiKeyResponses` | 不重建，功能正常 |

所以：`userID` / `machineID` / `customApiKeyResponses` 可以删；`credentials.json` 只能换占位值不能删；`oauthAccount` 删不干净。

## 判断「遥测重采集」

方法：删 → 重启应用 → 检查是否原样出现。

Claude 桌面版实测：`sentry/scope_v3.json` 里的设备上下文每次启动现场采集，删了立刻重建，内容一样：

```
device: {
  cpu_description: "Intel(R) Core(TM) i7-14650HX",
  processor_count: 24,
  memory_size: <实际内存>,
  screen_resolution: "1920x1080",
  boot_time: "<本次开机时间>"
}
```

这类数据删文件无效。唯一办法是关掉遥测，或在应用层屏蔽上报域名。

## 判断「ID 是否是目录名」

有些应用把设备 ID 直接当数据目录名。改 ID 时如果不迁移目录，用户的会话会从界面上消失（文件还在，但应用找不到）。

检查方法：

```bash
# 拿到旧 ID 后，找所有以它命名的路径
find <数据目录> -name "*<旧ID>*" 2>/dev/null
find <数据目录> -name "*<旧ID前8位>*" 2>/dev/null
```

Claude 桌面版实测，一个 `ant-did` 对应四处目录：

```
claude-code-sessions/<完整ID>/
local-agent-mode-sessions/<前8位>/
local-agent-mode-sessions/skills-plugin/<固定UUID>/<完整ID>/
spaces-present/<前8位>/
```

## 判断「波及面」

有些密钥不是单个应用的，改了影响全系统：

| 位置 | 影响 |
| --- | --- |
| 浏览器 `Local State` 的 `os_crypt.encrypted_key` | 所有网站的 cookie 解密失败，等于全浏览器重新登录 |
| Windows `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` | 影响所有软件授权 |
| WSL `/etc/machine-id` | 影响 systemd 和部分软件授权 |

这些超出「单个应用身份」的范围。除非用户明确要求全系统重置，否则保留并在报告里说明。
