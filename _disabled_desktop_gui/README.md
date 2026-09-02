# 已隔离的桌面 GUI 文件

**隔离日期**: 2026-05-28
**原因**: 怀疑桌面 GUI (pywebview) 干扰了 Web 界面的功能集成

## 文件清单

### 根目录启动器
| 原路径 | 说明 |
|--------|------|
| `desktop_app.py` | pywebview 桌面窗口启动器（启动 FastAPI + 原生窗口） |
| `web_app.py` | 浏览器启动器（启动 FastAPI + 打开浏览器） |
| `desktop_app.bat` | 桌面版批处理启动脚本 |
| `test_desktop.bat` | pywebview 诊断测试脚本 |
| `launcher.py` | PyInstaller 打包入口（显式 import 所有模块） |

### build_files/ — PyInstaller 打包相关
| 原路径 | 说明 |
|--------|------|
| `build.spec` | PyInstaller 打包配置 |
| `build.bat` | 打包构建脚本 |
| `dist/` | 打包输出（含 FinancialAnalyzerPro.exe） |
| `build/` | PyInstaller 中间构建文件 |

### deepseek_tkinter/ — DeepSeek 桌面 GUI
| 原路径 | 说明 |
|--------|------|
| `app.py` | tkinter/ttkbootstrap 独立桌面应用 |

## 保留在项目中的 Web 入口（未受影响）

以下文件是 Web 界面的正常入口，未被移动：

- `run.py` — 标准 CLI 入口（调用 `financial_analyzer.main`）
- `run_web.py` — 直接 uvicorn 启动器
- `run_web.bat` — Web 版批处理启动脚本
- `financial_analyzer/main.py` — 核心入口（uvicorn 启动 FastAPI）
- `financial_analyzer/web/` — FastAPI 后端（路由、服务、模板、静态文件）
- `frontend/` — SPA 前端

## 潜在冲突分析

桌面 GUI 可能干扰 Web 界面的原因：

1. **端口冲突**: `desktop_app.py` 在后台线程启动 FastAPI (port 8000)，与 `run_web.py` 冲突
2. **pywebview 依赖**: `import webview` 可能影响系统 WebView2 环境状态
3. **launcher.py 的强制 import**: 为 PyInstaller 追踪依赖，显式 import 了所有模块，可能导致模块初始化顺序问题
4. **ttkbootstrap 依赖**: `requirements.txt` 包含 ttkbootstrap，可能与 Web 依赖产生包冲突

## 恢复方法

如需恢复桌面 GUI，将文件移回原位即可：

```bash
cd _disabled_desktop_gui
mv desktop_app.py web_app.py desktop_app.bat test_desktop.bat launcher.py ..
mv build_files/build.spec build_files/build.bat ..
mv build_files/dist build_files/build ..
mv deepseek_tkinter/app.py ../financial_analyzer/deepseek/
```
