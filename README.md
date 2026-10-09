# 小鹅通视频下载器

小鹅通视频下载器读取已登录的小鹅通学员客户端中的课程目录，将选中的视频、PDF 和 Word 文件保存到电脑。支持按课程展开、多选和批量下载，文件自动按课程名称分类，视频使用播放接口实际提供的最高画质。首次使用需要安装会话桥接补丁；之后打开小鹅通学员客户端并登录，再打开视频下载器即可识别当前账号。当前补丁只验证过小鹅通学员客户端 1.2.18，运行需要 Windows 和 Python 3.11+

### 1. 安装

以下用两个示例路径说明，实际操作时请换成你电脑上的路径：

- 视频下载器源码：`E:\Tools\xiaoetong_download_patch`
- 小鹅通学员客户端：`D:\Apps\xiaoetong\xiaoe-tong-client`
- 小鹅通学员客户端的程序文件：`D:\Apps\xiaoetong\xiaoe-tong-client\小鹅通学员版.exe`

你可以直接将下面两个示例路径换成你的实际路径，再把整段发给能操作本机文件和 PowerShell 的 agent：

```text
请帮我安装并启动小鹅通视频下载器。
视频下载器源码目录：【你的视频下载器的路径】
小鹅通学员客户端安装目录：【你的小鹅通学员客户端的路径】

请先阅读 README.md 和安装脚本，确认目录正确、Python 为 3.11 或更新版本
在源码目录运行 python scripts/setup.py，然后执行补丁 inspect
安装补丁前确认小鹅通学员客户端已完全退出；保留原始备份，并用 --client 指定上述安装目录
安装完成后打开小鹅通学员客户端。需要我手动退出或登录时，请明确告知我
我登录后，启动 launch.cmd，检查能否识别当前账号并显示课程
仅在本项目的 .venv 中安装依赖
请报告安装结果、启动结果和实际遇到的问题，不要声称完成了尚未执行的验证
```

或者你可以尝试手动安装：

#### 1.1 准备 Python 和小鹅通学员客户端

先安装小鹅通学员客户端及 Python 3.11 或更新版本。安装 Python 时勾选 `Add Python to PATH`，然后打开 PowerShell，检查：

```powershell
python --version
```

看到 `Python 3.11.x` 或更新版本即可，若提示找不到 `python`，请检查 Python 安装和 PATH，关闭后重新打开 PowerShell

#### 1.2 下载源码并打开项目目录

下载源码，解压到固定目录，例如 `E:\Tools\xiaoetong_download_patch`，该目录应直接包含 `launch.cmd`、`README.md` 和 `scripts` 文件夹

在 PowerShell 中进入该目录：

```powershell
cd "E:\Tools\xiaoetong_download_patch"
```

#### 1.3 安装视频下载器的依赖

运行：

```powershell
python scripts/setup.py
```

脚本会自动建立本项目的 `.venv` 环境，安装依赖并注册源码路径，看到 `Ready. Open launch.cmd to start the video downloader.` 即表示安装完成。依赖下载沿用你自己的 pip 网络配置，若安装失败，先检查错误信息、Python 和网络连接，再重试此命令

#### 1.4 安装小鹅通学员客户端会话补丁

先确认安装目录，例如下面的路径确实包含 `小鹅通学员版.exe` 和 `resources`：

```powershell
$client = "D:\Apps\xiaoetong\xiaoe-tong-client"
.venv/Scripts/python.exe scripts/patch_client.py inspect --client "$client"
```

然后从系统托盘完全退出小鹅通学员客户端，运行：

```powershell
.venv/Scripts/python.exe scripts/patch_client.py install --client "$client"
```

安装器会核对兼容性，并保留原始备份；若提示安装目录没有写入权限，请用管理员 PowerShell 重新进入项目目录、重新设置 `$client`，再执行安装命令

#### 1.5 登录并使用视频下载器

重新打开小鹅通学员客户端，正常登录并保持它打开，然后双击项目中的 `launch.cmd` 启动视频下载器，之后课程目录会先显示，视频与文档逐门载入，全部读取完成后：

1. 勾选一门或多门课程，也可以只勾选单项资源
2. 点击“保存目录”，选择保存位置；可点击“新建文件夹”并输入名称
3. 点击“下载选中资源”

## 2. 恢复与移动

补丁保留的原始备份位于小鹅通学员客户端的 `resources/app.asar.xiaoetong-downloader.bak`。完全退出小鹅通学员客户端后，可恢复原始程序：

```powershell
$client = "D:\Apps\xiaoetong\xiaoe-tong-client"
.venv/Scripts/python.exe scripts/patch_client.py restore --client "$client"
```

移动视频下载器项目后，先在新位置运行 `python scripts/setup.py`，再完全退出小鹅通学员客户端并重新绑定：

```powershell
$client = "D:\Apps\xiaoetong\xiaoe-tong-client"
.venv/Scripts/python.exe scripts/patch_client.py rebind --client "$client"
```

升级小鹅通学员客户端前先恢复原始程序，升级后重新检查兼容性

## 3. 技术方案与目录

补丁在小鹅通学员客户端中加载自行编写的桥接模块，通过当前窗口的 SDK 检查登录状态并调用正常课程、播放和文档接口。Python 视频下载器通过仅监听本机、带随机访问凭证的通道读取资源，再交给下载核心保存文件。原账号令牌留在小鹅通学员客户端内，账号标识从接口响应取得，不绑定某个使用者。

```text
src/xiaoetong_assistant/   界面、会话桥接、课程目录及下载核心
scripts/                  依赖安装、补丁安装与恢复、命令行和源码打包
tests/                    Python 与 Node 回归测试
.github/workflows/        GitHub 上的 Windows 自动检查
launch.cmd                启动视频下载器
run-tests.cmd             执行开发测试
requirements.txt          运行依赖清单
requirements-lock.txt     安装时使用的依赖版本约束
.venv/                    安装时生成的本机 Python 环境，不发布
runtime/                  运行时生成的本机会话连接信息，不发布
agent/                    本地开发技术记录与联调工具，不发布
AGENTS.md                 agent 技术记录导航与工作规范，不发布
```

`runtime/` 不是源码，也不是废目录：其中的 `native-bridge.json` 由小鹅通学员客户端会话桥接生成，视频下载器依靠它连接当前会话。运行期间不要删除；它包含本机访问凭证，已在 `.gitignore` 和源码打包规则中排除。`.venv/` 同样仅供本机运行使用，新电脑通过安装脚本重新创建。

下载文件保存到用户选择的位置。Python 的 `__pycache__/` 是可重新生成的缓存，不属于公开源码；源码打包生成的 `dist/` 也不会提交。

开发测试需要 Node.js 22+，运行 `run-tests.cmd` 即可，普通安装和使用不需要 Node.js

自行编写的代码采用 MIT 许可证，见 [LICENSE](LICENSE)。
