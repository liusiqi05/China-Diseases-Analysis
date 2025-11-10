# 🧬 可视化传染病分析平台（项目说明）

## 🌍 项目概述
- 一个基于 **Vue + ECharts** 的可视化前端与基于 **FastAPI** 的轻量后端的演示项目。
- 功能包括：🗺️ 省级地图叠加（饼图 / choropleth / 水质热力图）、🔗 Sankey 流向分析、🌳 住院天数 Treemap/Sunburst 切换、📈 前端 PCA 计算水质综合得分、🤖 交互式 AI 小管家及 🧠 TransUNet 人机交互模块示例。
- 数据与静态资源放在 `public/` 目录，便于按需加载与复现（主要文件：`public/china_disease_data.csv`、`public/china_water_pollution_data.csv`）。

---

## 🗂️ 目录结构（重要）
- `src/`：前端源码（组件位于 `src/components/`，视图在 `src/views/`）
  - `MapPieChart.vue`：🗺️ 地图/热力图/饼图主控件（含水质 PCA、热力图、PCA 详情面板）
  - `new5.vue`：🔗 Sankey 流向图/即论文中提到的Sankey.vue
  - `new3.vue`：🌳 住院天数 Treemap/Sunburst
  - `ChatPanel.vue`：🤖 AI 小管家交互面板（前端代理）
  - `TrendChart.vue`、`RobotsaleMap.vue`：📊 其他可视化模块
- `public/`：📂 CSV、geojson、静态资源
- `webapi/`：⚙️ 后端（FastAPI）接口实现（`app.py`）
- `vite.config.js`、`package.json`、`requirements.txt`：🧩 项目配置与依赖

---

## ⚙️ 先决条件
- 🟢 Node.js + npm（建议 Node 16+）
- 🐍 Python 3.8+
- 💻 推荐在 Windows PowerShell 环境中运行（本项目在 Windows 路径下开发）

---

## 🚀 前端安装与运行
1. 进入前端项目目录并安装依赖：
    ```bash
    cd E:\website\art
    npm install
    npm run dev
    ```
2. 打开浏览器访问终端输出的本地地址（通常是 👉 `http://localhost:5173/`）。

---

## 🧩 后端运行说明
1. 安装 Python 依赖：
    ```bash
    pip install -r requirements.txt
    ```
2. 启动 FastAPI 服务：
    ```bash
    cd webapi
    uvicorn app:app --reload
    ```
3. 默认服务地址为 🌐 `http://127.0.0.1:8000`，前端可通过代理或配置直接访问接口。

---

## 🌟 系统特点与亮点
- 🔸 **前后端分离**：支持模块化部署与跨语言开发。  
- 🔸 **多层可视化联动**：地图、Sankey、Treemap、热力图均可交互联动。  
- 🔸 **PCA 综合得分分析**：基于 ECharts 与前端 JS 实现 PCA 主成分计算与展示。  
- 🔸 **AI 小管家模块**：支持简单自然语言交互（可扩展调用后端模型接口）。  
- 🔸 **轻量后端架构**：FastAPI 提供 RESTful API，便于快速测试与部署。

---

## 🔮 未来扩展方向
- 📈 接入真实疾病监测数据与时间序列预测模型；
- 🧠 引入多模态交互模块（如图像识别 + 语义问答）；
- ⚠️ 增强数据异常检测与信任可视化（用户感知层优化）；
- 🐳 支持 Docker 一键部署与 CI/CD 自动化构建。

---

## 🧭 总体运行方法

运行方法：

```bash
1. npm run dev
2. python -m uvicorn webapi.server:app --reload --port 8000
3. python -m uvicorn app:app --host 127.0.0.1 --port 3000 --reload
4. (监听) curl.exe http://127.0.0.1:3000/api/disease_locations
