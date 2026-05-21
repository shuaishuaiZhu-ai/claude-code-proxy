# claude-code-proxy

[English](README.md) | [简体中文](README.zh-CN.md)

用一个 `ccproxy` 命令，让 Claude Code 使用 OpenAI API Key、ChatGPT 订阅、
DeepSeek、Kimi、智谱 GLM、MiniMax 和本地 adapter。

![claude-code-proxy overview](docs/assets/readme-hero.svg)

`ccproxy` 是 Claude Code 的 provider 切换器。安装一次，用
`ccproxy model set` 选择 provider 和模型，然后用 `ccproxy run` 启动 Claude
Code。

## 快速开始

### Windows PowerShell

```powershell
git clone https://github.com/shuaishuaiZhu-ai/claude-code-proxy.git
cd claude-code-proxy
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
ccproxy model set
ccproxy run -- -p "reply ccproxy-ok"
```

### macOS / Linux / WSL

```sh
git clone https://github.com/shuaishuaiZhu-ai/claude-code-proxy.git
cd claude-code-proxy
sh scripts/install.sh
ccproxy model set
ccproxy run -- -p "reply ccproxy-ok"
```

以后切换 provider 或模型，只需要重新运行 `ccproxy model set`。

## 支持什么

![provider modes](docs/assets/readme-provider-map.svg)

| 你拥有的入口 | 选择的 provider | 模式 | 示例模型 |
| --- | --- | --- | --- |
| OpenAI API Key | `openai-key` | API key | `gpt-4.1`, `gpt-4.1-mini` |
| ChatGPT 订阅 | `chatgpt-subscription` | 订阅登录 | `ChatGPT5.5`, `ChatGPT5.4` |
| DeepSeek API Key | `deepseek` | API key | `deepseek-v4-pro`, `deepseek-v4-flash` |
| DeepSeek 订阅 adapter | `deepseek-subscription` | 本地 adapter | adapter 暴露的模型 |
| Kimi / Moonshot API Key | `kimi` | API key | `moonshot-v1-128k` |
| Kimi 订阅 adapter | `kimi-subscription` | 本地 adapter | adapter 暴露的模型 |
| 智谱 GLM API Key | `zhipu` | API key | `glm-4-plus`, `glm-4-air` |
| 智谱订阅 adapter | `zhipu-subscription` | 本地 adapter | adapter 暴露的模型 |
| MiniMax 中国区 API Key | `minimax-cn` | API key | `MiniMax-M2.7` |
| MiniMax 国际区 API Key | `minimax-global` | API key | `MiniMax-M2.7` |
| MiniMax Token Plan | `minimax-subscription` | 订阅 key | `MiniMax-M2.7` |
| 自己的 adapter | `custom` | 本地 adapter | adapter 暴露什么就用什么 |

MiniMax 默认推荐 OpenAI-compatible endpoint。Anthropic-compatible 的 MiniMax
profile 仍然保留给高级用户，但普通 `ccproxy model set` 菜单不会再显示这些协议细节。

## API Key 配置

当缺少 API key 时，`ccproxy model set` 会打印对应平台的取 key 地址，然后等待你粘贴
key。它不会主动打开浏览器。

取 key 地址：

| Provider | API key 地址 |
| --- | --- |
| OpenAI | https://platform.openai.com/api-keys |
| DeepSeek | https://platform.deepseek.com/api_keys |
| Kimi / Moonshot | https://platform.kimi.com/console/api-keys |
| 智谱 GLM | https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys |
| MiniMax 中国区 | https://platform.minimaxi.com/user-center/basic-information/interface-key |
| MiniMax 国际区 | https://platform.minimax.io/user-center/basic-information/interface-key |

示例：

```sh
ccproxy model set --provider deepseek --model deepseek-v4-pro
ccproxy run -- -p "reply ccproxy-ok"
```

粘贴过的 API key 会保存到 `~/.ccproxy/secrets.toml`。环境变量仍然可用，并且优先级
高于本地保存的 key。

## 订阅模式

ChatGPT 订阅模式由 `ccproxy` 托管：

```sh
ccproxy model set --provider chatgpt-subscription --model ChatGPT5.5
ccproxy run -- -p "reply ccproxy-ok"
```

默认使用 device-code 登录。打开终端打印的 URL，输入一次性 code，然后回到终端等待。

MiniMax 订阅使用 MiniMax Token Plan key，并走推荐的 OpenAI-compatible endpoint：

```sh
ccproxy model set --provider minimax-subscription --model MiniMax-M2.7
ccproxy run -- -p "reply ccproxy-ok"
```

DeepSeek、Kimi、智谱的订阅 provider 是本地 adapter profile。你已经运行兼容的本地
subscription adapter 时使用它们；否则优先使用同平台的 API-key provider。

## 安装和卸载

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1
```

macOS / Linux / WSL：

```sh
sh scripts/install.sh
sh scripts/uninstall.sh
```

卸载脚本会移除 `claude-code-proxy` 包和 `~/.ccproxy` 状态目录。它不会卸载 Python、
pip 或 Claude Code。

## 常用命令

```sh
ccproxy model set
ccproxy model current
ccproxy run -- -p "reply ccproxy-ok"
ccproxy doctor
ccproxy test --profile custom --claude
```

## 常见问题

| 现象 | 处理 |
| --- | --- |
| Claude Code 显示 `Not logged in` | 用 `ccproxy run` 启动，不要直接运行 `claude`。 |
| `/skills` 显示没有 skills | 更新 `ccproxy` 并重新通过 `ccproxy run` 启动 Claude；普通运行会保留 Claude 的插件和 skill 加载。`--bare` 只用于最小 smoke test。 |
| 工具调用报 `Invalid tool parameters` | 更新 `ccproxy`；新版会在转发给 Claude Code 前校验工具调用参数。 |
| API key 设置直接退出 | 更新 `ccproxy`；新版会等待你粘贴并保存 key。 |
| 浏览器 consent 页面一直转圈 | 停止这次运行，使用默认 ChatGPT device-code 登录，不带 `--browser-login`。 |
| MiniMax 菜单出现太多协议选项 | 更新 `ccproxy`；普通菜单已经隐藏高级 Anthropic-compatible profile。 |
| 订阅 adapter 连不上 | 先启动对应平台的本地 adapter，或切换到 API-key provider。 |

## 相关文档

- Provider 细节：[docs/providers.md](docs/providers.md)
- 架构说明：[docs/architecture.md](docs/architecture.md)
- 配置示例：[examples/ccproxy.example.toml](examples/ccproxy.example.toml)
- 贡献说明：[CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT. See [LICENSE](LICENSE).
