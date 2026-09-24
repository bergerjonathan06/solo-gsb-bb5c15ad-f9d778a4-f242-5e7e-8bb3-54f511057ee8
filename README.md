# 口述史事件先后核对

一个供口述史整理者核对事件先后描述是否自洽的小工具。整理者把多行
`事件甲,事件乙,最少分钟,最多分钟` 粘贴进页面（表示“事件乙比事件甲晚
最少～最多分钟”），服务端会：

1. **逐行校验**：字段数、事件名称（非空、不能是纯数字）、上下界是否为整数、
   下界是否不大于上界；空行自动跳过且原始行号保留；
2. **联立全部区间**：把所有区间当作差分约束一次性求解；
3. **有冲突**：展示一条由**原始行号**及其所用**上界/下界**构成的**闭合矛盾链**，
   并给出把链上不等式相加后得到 `0 ≤ 负数` 的完整推导，点击链上任一步可定位到输入框对应行；
4. **无冲突**：给出以**最早事件为第 0 分钟**、满足全部区间的一条整数可行时间线
   （按时间先后排序，附时间轴条形图）；存在互不相关的多组事件时会明确提示。

页面内置“一键填充示例”，另附一个“填充冲突示例”便于查看矛盾链形态。

## 技术栈

- 后端：Python 3.11 + FastAPI（Pydantic 校验请求）
- 前端：原生 HTML / CSS / JavaScript，无构建步骤、无第三方前端依赖
- 算法：差分约束图 + Bellman–Ford；负环即不可行，沿前驱指针还原闭合矛盾链
- 部署：Docker + Docker Compose，依赖安装与初始化全部在镜像构建时完成

## 一条命令启动（需要 8080 端口）

```bash
docker compose up -d --build
```

启动后打开：

- **页面地址：http://localhost:8080**
- 健康检查：http://localhost:8080/healthz

停止：`docker compose down`，查看日志：`docker compose logs -f`。

## 必要配置

无任何必须配置项，也不需要数据库或环境变量。唯一可能需要调整的是
**宿主机端口**（容器内固定监听 8080）：

```bash
# 方式一：临时改宿主机端口（例如改用 8081，页面为 http://localhost:8081）
HOST_PORT=8081 docker compose up -d --build

# 方式二：在项目目录新建 .env 文件写入 HOST_PORT=8081
```

## 本地直接运行（不用 Docker）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

然后访问 http://localhost:8080 。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 单页应用 |
| POST | `/api/check` | 请求体 `{"text": "…多行文本…"}`，返回校验/联立结果 |
| GET | `/healthz` | 健康检查 |

`/api/check` 返回的 `status` 取值：`feasible`（可行，含 `timeline`）、
`conflict`（冲突，含闭合矛盾链 `cycle`）、`invalid`（存在未通过逐行校验的行）、
`empty`（没有有效内容）。

## 输入示例

```
出门,到车站,15,30
到车站,列车进站,5,10
列车进站,开车铃响,2,5
开车铃响,开车,1,3
出门,到外婆家,90,120
```

- 支持半角逗号 `,` 与中文逗号 `，`；
- 分钟数必须是整数，允许负数；
- 同一对事件出现多行时约束会叠加，系统会自动识别由此产生的冲突。

## 目录结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI 路由与静态资源挂载
│   └── solver.py      # 逐行解析、校验、Bellman–Ford 联立与矛盾链还原
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js         # 原生 JS：示例填充、结果渲染、矛盾链定位
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```
