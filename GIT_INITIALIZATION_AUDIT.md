# Git 初始化审计报告（GIT_INITIALIZATION_AUDIT）

- **审计对象**：深圳建设工程投标 AI 工作台（`D:\测试\助手`）
- **审计日期**：2026-11-03
- **审计方式**：只读审计。未修改任何业务代码、未删除/移动文件、未执行 `git init`、未上传任何内容。
- **审计结论**：✅ **项目具备 Git 初始化条件**。现有 `.gitignore` 质量良好，敏感运行数据（数据库、上传文件、备份）已被正确排除；有 4 个事项需用户确认后方可进入下一阶段（详见第十节）。

---

## 一、项目目录结构

```
D:\测试\助手\                        ← 项目根（Git 仓库根）
├─ .gitignore                       # 已存在，质量良好（详见第七节）
├─ README.md                        # 项目总说明（第一阶段）
├─ 第二阶段报告.md                   # 第二阶段交付报告 ⚠ 含真实项目信息（见第五节）
├─ 启动平台.bat                      # 一键启动（生产模式，端口 8000）
├─ 开发模式启动.bat                  # 开发模式（前端 5173 + 后端 8000 热更新）
├─ 备份数据库.bat                    # 在线快照备份到 backend/backups/
│
├─ backend\                          # Python 后端
│  ├─ main.py                       # FastAPI 入口（托管 SPA 静态资源）
│  ├─ database.py                   # SQLite 连接（WAL，支持测试隔离）
│  ├─ models.py                     # 12 张数据表（SQLAlchemy 2.0）
│  ├─ schemas.py                    # Pydantic 请求/响应模型
│  ├─ seed.py                       # 演示数据种子 ⚠ 含真实机构名（见第五节）
│  ├─ smoke_test.py                 # 54 项接口冒烟测试（需服务运行）
│  ├─ acceptance_test.py            # 验收测试脚本
│  ├─ requirements.txt              # 后端依赖清单
│  ├─ alembic.ini + alembic\        # 数据库迁移（0001~0004）
│  ├─ routers\                      # 10 个路由模块（ai/announcements/bids/dashboard/
│  │                                #   documents/history/parse/projects/requirements/settings_api）
│  ├─ services\                     # file_storage / history_service / doc_parser\（PDF/DOCX 解析引擎）
│  ├─ scripts\                      # backup_db / db_migrate / migrate_phase_b
│  ├─ tests\                        # run_tests.py（166 项隔离套件）/ browser_acceptance.py（Playwright）
│  ├─ venv\                         # ❌ 虚拟环境（已忽略，不入库）
│  ├─ data\                         # ❌ SQLite 运行数据库（已忽略）
│  ├─ uploads\                      # ❌ 用户上传文件（已忽略，含真实招标文件）
│  ├─ backups\                      # ❌ 数据库快照备份 + UI 截图（已忽略）
│  ├─ server.log / acc-server.log   # ❌ 运行日志（已忽略）
│  └─ **\__pycache__\               # ❌ Python 字节码缓存（已忽略）
│
└─ frontend\                         # React 前端
   ├─ src\                          # 全部源码（api/ components/ layouts/ pages/ 11 个页面）
   ├─ index.html / vite.config.ts / tsconfig.json
   ├─ package.json + package-lock.json   # 依赖清单与锁定版本（必须入库）
   ├─ public\                       # 静态资源（favicon）
   ├─ dist\                         # ❌ 构建产物（已忽略，启动脚本自动重建）
   ├─ tsconfig.tsbuildinfo          # ❌ TS 构建缓存 ⚠ 当前未被忽略（见第七节）
   └─ node_modules\                 # ❌ 前端依赖（已忽略）
```

## 二、当前技术架构

| 层 | 技术 | 版本要求 | 依据文件 |
|---|---|---|---|
| 前端 | React 18 + TypeScript 5.6 + Vite 5 + Ant Design 5 + ECharts | Node.js 18+（本机 24.15.0 ✅） | `frontend/package.json` |
| 后端 | Python + FastAPI + SQLAlchemy 2.0 + Pydantic 2 + Alembic + PyMuPDF + python-docx + openpyxl | Python 3.10+（本机 3.12.3 ✅） | `backend/requirements.txt` |
| 数据库 | SQLite（WAL 模式），`backend/data/platform.db`，12 张表 | 零配置 | `backend/database.py` |
| 文件存储 | 本地文件系统 `backend/uploads/`（tender-docs / deliverables） | — | `backend/services/file_storage.py` |
| 工具链 | Git 2.54.0（已安装 ✅）、Git Bash | — | 本机验证 |

**启动方式**（全部为相对路径脚本，换电脑可用）：
- 生产：双击 `启动平台.bat` → 自动建 venv、装依赖、构建前端、启动 `http://localhost:8000`
- 开发：双击 `开发模式启动.bat` → 前端 5173（Vite 代理 /api→8000）+ 后端热重载
- 手动命令见 `README.md` 第二节；后端自动文档 `http://localhost:8000/docs`
- 备份：双击 `备份数据库.bat` → `backend/backups/backup_时间戳/`（含恢复步骤 MANIFEST.txt）

## 三、文件纳入 Git 的建议（✅ 入库）

| 文件/目录 | 理由 |
|---|---|
| `README.md` | 项目说明 |
| `.gitignore` | 版本管理必需 |
| `*.bat`（3 个启动/备份脚本） | 启动方式文档化，含自动装机逻辑，均用相对路径 |
| `backend/*.py`（main/database/models/schemas/seed） | 核心源码 |
| `backend/routers/`、`backend/services/`、`backend/scripts/` | 全部业务源码 |
| `backend/tests/`、`backend/smoke_test.py`、`backend/acceptance_test.py` | 测试资产（166 项隔离套件是防止回归的核心保障） |
| `backend/alembic/` + `backend/alembic.ini` | 数据库结构变更历史（0001→0004），换机重建库的关键 |
| `backend/requirements.txt` | 后端依赖清单 |
| `frontend/src/` 全部 | 前端源码 |
| `frontend/package.json` + `package-lock.json` | 依赖清单与锁定版本（保证可重现安装） |
| `frontend/index.html`、`vite.config.ts`、`tsconfig.json`、`public/` | 构建必需 |
| `第二阶段报告.md` | ⚠ 建议脱敏后入库（见第五节、第十节） |

## 四、文件排除 Git 的建议（❌ 不入库）

| 文件/目录 | 理由 | 现状 |
|---|---|---|
| `backend/venv/` | 虚拟环境，按 requirements.txt 可重建 | 已在 .gitignore ✅ |
| `frontend/node_modules/` | 前端依赖，按 package-lock.json 可重建 | 已在 .gitignore ✅ |
| `frontend/dist/` | 构建产物，`npm run build` 可重建 | 已在 .gitignore ✅ |
| `backend/data/` | **SQLite 运行数据库：含真实解析数据**（2460 条解析结果，含招标人/限价/联系方式等原文），属真实业务数据，严禁入库 | 已在 .gitignore ✅ |
| `backend/uploads/` | **7 份真实招标文件**（某车辆段上盖物业项目交易包解包文件，336 页招标文件、合同条款、评定办法附表等），属商业秘密 | 已在 .gitignore ✅ |
| `backend/backups/` | 数据库快照（含真实数据）+ UI 截图（截图中含真实项目内容） | 已在 .gitignore ✅ |
| `*.log`（server.log、acc-server.log） | 运行日志（抽检仅 INFO 级，仍按惯例排除） | 已在 .gitignore ✅ |
| `__pycache__/`、`*.pyc` | Python 缓存 | 已在 .gitignore ✅ |
| `frontend/tsconfig.tsbuildinfo` | TS 增量构建缓存 | ⚠ **未覆盖，需补充**（见第七节） |
| `.env`、`.env.*`（预防性） | 当前不存在，预防将来引入 | ⚠ **未覆盖，需补充** |

**关键区分说明（按要求非一刀切排除 PDF/Word）**：
- `backend/uploads/` 中的 PDF/Word 是**真实招标文件**（招标人：某置业集团，真实限价、真实联系方式）→ 排除；
- 项目中**没有**需要入库的业务 PDF/Word。脱敏测试样本目前不存在——若日后需要文档解析的测试样本，建议另行制作脱敏样本放入 `backend/tests/fixtures/` 并入库。

## 五、敏感信息风险清单

| # | 位置 | 内容 | 风险级别 | 处置建议 |
|---|---|---|---|---|
| 1 | `backend/uploads/tender-docs/`（7 个文件，约 3.9MB） | 真实招标文件全文（含合同条款、否决条款、评标办法、投标函格式） | 🔴 高 | 已被 .gitignore 排除，勿动；首次 `git status` 时人工复核确认未出现 |
| 2 | `backend/data/platform.db`（+wal/shm） | 真实解析数据 2460 条（招标人、代理机构、限价、联系方式原文）、系统设置（含公司名、上传绝对路径） | 🔴 高 | 已被 .gitignore 排除；WAL 文件 1.8MB 未合并，属正常 |
| 3 | `backend/backups/`（9 份快照 + 5 张 UI 截图） | 数据库历史快照；截图含真实项目页面内容 | 🔴 高 | 已被 .gitignore 排除 |
| 4 | `第二阶段报告.md` | 含真实项目名、招标人名、原始 zip 的 SHA-256 与存放位置（具体名称此处不展开，见本地留存的结果报告） | 🟡 中 | **已按确认方案脱敏后入库**：项目名→「某车辆段上盖物业项目」、招标人→「某置业集团」，SHA/位置已删除 |
| 5 | `backend/seed.py`、`backend/tests/run_tests.py`、`backend/smoke_test.py`、`backend/routers/settings_api.py` | 演示数据使用**真实机构名**（政府机构、招标代理公司、施工企业等，完整清单见本地留存的结果报告）；默认企业名硬编码 | 🟡 中 | 项目名称为合成演示性质，但机构名真实；已按确认方案虚构化处理（第十节 Q1/Q3） |
| 6 | `model.api_key` | 数据库中为**空** ✅；代码默认空 ✅；接口只返回“已配置”布尔值，不回传明文 ✅；支持环境变量 `BID_MODEL_API_KEY` 优先 ✅ | 🟢 低 | 机制安全，无需处理 |
| 7 | `.env` / 密钥文件 | 全项目扫描**不存在** .env、.pem、.key、证书文件 ✅ | 🟢 低 | 建议在 .gitignore 预防性加入（第七节） |
| 8 | 代码硬编码扫描 | 无 API Key/Token/密码硬编码；无绝对路径硬编码；CORS 仅限 localhost ✅ | 🟢 低 | 无需处理 |
| 9 | 项目根之外的原始交易包 zip（3.98MB，真实招标原件） | 真实招标原件 | 🔴 高 | 在 Git 仓库根**之外**，不会被 git 管理；提醒：**任何情况下不得上传** |
| 10 | `backend/settings` 默认联系方式 `张工 / 0755-8888XXXX` | 已打码占位符 | 🟢 低 | 无需处理 |

## 六、现有代码修改与备份建议（Git 初始化前）

1. **当前无未完成修改的证据** ✅：全库无 TODO/FIXME/HACK 标记；代码无绝对路径硬编码；README 与第二阶段报告均记载「完整可运行」。
2. **服务当前未运行** ✅：8000/5173 端口无监听、无 python 服务进程，初始化 Git 不会与运行中文件冲突。
3. **初始化前强制备份**（双保险，Git 之外）：
   - 双击 `备份数据库.bat` 生成最新快照；
   - 建议将 `backend/data/` + `backend/uploads/` 复制到项目外位置（如移动硬盘/网盘）。**Git 不管理这两个目录，云端仓库不能替代本地业务数据备份。**
4. **首次提交即“存档点”**：Git 初始化后第一版提交对应当前可运行状态（第二阶段验收通过版），之后任何修改都可回退，反而更安全。
5. **WAL 提示**：`platform.db-wal`（1.8MB）未合并属正常现象；若手工复制数据库文件做备份，请使用 `备份数据库.bat`（在线快照）而非直接复制三件套。

## 七、推荐 .gitignore（在现有文件基础上修订）

现有 `.gitignore` 已覆盖 90% 需求，建议**增量补充**以下 4 处（注释处为新增）：

```gitignore
# 依赖与虚拟环境（不入库，按 requirements.txt / package-lock.json 重装）
backend/venv/
frontend/node_modules/

# 构建产物（启动脚本会按需重建）
frontend/dist/
frontend/tsconfig.tsbuildinfo        # ← 新增：TS 增量构建缓存
frontend/node_modules/.vite/         # ← 新增：Vite 依赖预构建缓存

# 运行数据（业务数据与用户文件，严禁入库/删除）
backend/data/
backend/uploads/
backend/backups/

# 日志与临时文件
*.log
backend/acc-server.log
__pycache__/
*.pyc
.pytest_cache/

# 敏感配置（当前不存在，预防性排除）
.env
.env.*
*.pem
*.key                                # ← 以上为新增

# 系统文件
Thumbs.db
.DS_Store
```

> 说明：`node_modules/.vite/` 实际已被 `frontend/node_modules/` 覆盖，列出的写法仅为冗余保险；真正必须新增的是 `tsconfig.tsbuildinfo` 与 `.env` 系列。

## 八、Git 初始化执行方案（下一阶段执行，本阶段不执行）

```
步骤 0  前置检查（已由本审计完成）
        ├─ Git 2.54 已安装 ✅     ├─ 服务未运行 ✅     ├─ 无未完成修改 ✅
        └─ 补齐 .gitignore（第七节修订）→ 人工复核文件内容

步骤 1  初始化前备份
        双击 备份数据库.bat；另将 backend/data/ 与 backend/uploads/ 复制到项目外安全位置

步骤 2  配置 Git 身份（仅本仓库）
        cd /d/测试/助手
        git config user.name  "<你的名字>"
        git config user.email "<GitHub no-reply 邮箱>"   # 推荐 xxx@users.noreply.github.com，不暴露真实邮箱
        git config core.autocrlf true                    # Windows 换行符规范

步骤 3  初始化仓库
        git init
        git branch -M main            # 主分支命名为 main（与 GitHub 默认一致）

步骤 4  暂存与安全复核（关键人工关卡）
        git add .
        git status                    # 逐项核对：不得出现 data/ uploads/ backups/ venv/ node_modules/ dist/ *.log
        git ls-files | 检查           # 确认清单只含源码与文档（可对照本报告第三节）

步骤 5  首次提交（当前可运行版本的存档点）
        git commit -m "初始提交：投标 AI 工作台（第二阶段完成版，含文件解析工作台）"

步骤 6  提交后验证
        git log --oneline; git ls-files | wc -l
        确认项目仍可正常启动（双击 启动平台.bat）
```

## 九、GitHub 私有仓库接入方案

1. **创建仓库**（两种方式任选其一，均在用户确认后执行）：
   - 网页：github.com → New repository → 名称（建议 `bid-ai-workbench`）→ **Private** → 不勾选任何初始化选项（README/.gitignore/license 都不勾，避免与本地冲突）；
   - 或 CLI：`gh repo create bid-ai-workbench --private --source . --push`（需先 `gh auth login`）。
2. **关联远程**：
   ```bash
   git remote add origin https://github.com/<用户名>/bid-ai-workbench.git
   git push -u origin main        # 首次推送会弹出浏览器登录 GitHub（HTTPS 凭据管理器）
   ```
3. **推送前二次确认**：Private 可见性；首次 push 后在 GitHub 网页逐目录浏览，确认无任何招标文件/数据库/日志出现。
4. **日常节奏**（供参考）：改代码 → `git add <文件>` → `git commit -m "说明"` → `git push`；数据库/上传文件永远不进 Git。
5. **凭据安全**：Windows 凭据管理器保存 GitHub 登录态，无需在文件中存放 Token；如需 Token 方式，使用 fine-grained PAT 且不入库。

## 十、尚需用户确认的问题

| # | 问题 | 建议 |
|---|---|---|
| Q1 | 默认企业名硬编码在 `settings_api.py`、`smoke_test.py`、`tests/run_tests.py` 中——这是**虚构占位名**还是**你的真实公司名**？ | 若为真实名称，入库前改为明显占位名（如「示例建工有限公司」）【已确认：改为示例建工有限公司】 |
| Q2 | `第二阶段报告.md` 含真实项目名、招标人名与文件 SHA-256。是否**原样入库 / 脱敏后入库 / 暂不入库**？ | 脱敏（项目名→「某车辆段上盖物业项目」、招标人→「某置业集团」）后入库【已确认：脱敏后入库】 |
| Q3 | `seed.py` 等演示数据使用了真实机构名（多家政府机构、招标代理、施工企业，完整清单见本地结果报告）。是否接受随源码上传？ | 已确认：虚构化替换为「示例」前缀名称，保留地区等地理信息，测试逻辑不变 |
| Q4 | Git 提交身份（user.name / 邮箱）用什么？ | 建议 GitHub 用户名 + no-reply 邮箱 |
| Q5 | 仓库名称偏好？（建议 `bid-ai-workbench`） | 确认后下一阶段使用 |
| Q6 | 是否已有 GitHub 账号？是否方便首次 push 时完成浏览器登录授权？ | HTTPS + 凭据管理器最简单 |
| Q7 | `backend/data/`、`backend/uploads/`、`backend/backups/`（Git 不管的部分）需要什么级别的额外备份？（移动硬盘/网盘） | 建议至少一份项目外备份 |

---

**审计范围声明**：本次审计未运行测试套件（避免任何写入）；测试结论引用自 `README.md` 与《第二阶段报告.md》记载（隔离套件 166/166、浏览器验收 13/13、tsc 零错误，2026-11-01）。数据库内容经**只读连接**（`mode=ro`）抽检，未产生任何写入。

**下一步**：请用户回复第十节确认项后，方可进入「Git 初始化 + GitHub 接入」阶段。
