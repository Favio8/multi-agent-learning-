# 📚 知卡学伴 (AI Learning Companion)

<div align="center">

![Version](https://img.shields.io/badge/version-0.9.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**基于多智能体系统的智能学习卡片助手**

[功能特性](#-核心特性) • [快速开始](#-快速开始) • [技术架构](#-技术架构) • [使用指南](#-使用指南) • [版本历史](#-版本历史)

</div>

---

## 📖 项目简介

知卡学伴是一款基于**多智能体系统（Multi-Agent System）**的智能学习助手，能够自动将学习资料转化为高质量的学习卡片，并通过科学的间隔重复算法帮助用户高效记忆。

### ✨ 亮点

- 🤖 **6个专业AI智能体协同工作** - 自动化处理学习内容
- 📚 **多题型卡片生成** - 知识卡、填空题、选择题、简答题
- 🧠 **SM-2间隔重复算法** - 科学的复习计划
- 🎨 **现代化UI设计** - 参考豆包、GPT等顶级应用
- 💾 **学习进度持久化** - 随时中断，随时继续
- ⚡ **性能优化** - 页面切换提速75%

---

## 🚀 核心特性

### 1. 多智能体协同系统

```
Orchestrator（协调器）
    ↓
┌───┴───┬────────┬────────┬────────┬─────────┐
│       │        │        │        │         │
Content Concept  Quiz    Eval   Schedule
Agent   Agent    Agent   Agent   Agent
```

**6个专业智能体分工协作**：
- **ContentAgent** - 文档解析与智能分段
- **ConceptAgent** - 概念提取与知识图谱构建
- **QuizAgent** - 多题型卡片自动生成
- **EvalAgent** - 智能评测与错因分析
- **ScheduleAgent** - SM-2复习算法调度
- **Orchestrator** - 流程协调与异常处理

### 2. 智能卡片生成

- **📚 知识记忆卡** - 概念与定义，便于快速记忆
- **📝 填空题** - 挖空关键信息，测试理解
- **🎯 选择题** - 多选项测试，巩固知识
- **✍️ 简答题** - 开放性问答，深度掌握

### 3. 科学复习系统

- **SM-2算法** - 根据记忆曲线智能调度
- **自适应难度** - 动态调整复习间隔
- **进度追踪** - 实时记录学习状态
- **数据分析** - 可视化学习报告

### 4. 现代化UI体验

- 🎨 **玻璃拟态设计** - 毛玻璃效果，现代美观
- ✨ **流光动画** - shimmer效果，视觉亮点
- 🌈 **渐变配色** - 紫色主题，优雅专业
- 💡 **智能反馈** - 脉冲/抖动动画，即时反馈

---

## 🛠️ 技术架构

### 技术栈

**后端**:
- FastAPI - 高性能Web框架
- SQLite - 轻量级数据库
- DeepSeek AI - LLM支持

**前端**:
- React + Vite - 现代前端工作台
- Tailwind CSS + shadcn/ui - 极简设计系统
- Recharts - 数据可视化

**核心算法**:
- SM-2间隔重复算法
- 多智能体协同框架
- NLP概念提取
- 语义相似度评测

### 系统架构

```
┌─────────────────────────────────────────┐
│         React + Vite Frontend           │
│   (Apple-like 极简工作台 + shadcn/ui)    │
└──────────────────┬──────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────┐
│            FastAPI Backend              │
│   ┌─────────────────────────────────┐   │
│   │     Orchestrator (协调器)        │   │
│   └─────────────┬───────────────────┘   │
│        ┌────────┴────────┐               │
│   ┌────▼────┐      ┌────▼────┐          │
│   │ Content │      │ Concept │          │
│   │  Agent  │─────▶│  Agent  │          │
│   └─────────┘      └────┬────┘          │
│                          │               │
│   ┌─────────┐      ┌────▼────┐          │
│   │  Eval   │      │  Quiz   │          │
│   │  Agent  │◀─────│  Agent  │          │
│   └────┬────┘      └─────────┘          │
│        │                                 │
│   ┌────▼────┐                            │
│   │Schedule │                            │
│   │  Agent  │                            │
│   └─────────┘                            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│         SQLite Database                 │
│  (文档、卡片、复习记录、学习进度)          │
└─────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- pip (Python包管理器)
- DeepSeek API Key (可选，用于AI增强)

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/ai-learning-companion.git
cd ai-learning-companion
```

2. **创建虚拟环境**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置API（可选）**
```bash
# 编辑 configs/settings.yaml
# 添加 DeepSeek API Key（如需使用AI功能）
```

5. **启动应用**
```bash
# 终端1 - 启动后端API
python api/app.py

# 终端2 - 启动前端工作台
cd frontend
npm install
npm run dev
```

6. **访问应用**
```
http://localhost:5173
```

### 一键启动（可选）

**Windows**:
```bash
start_app.bat
```

**Mac/Linux**:
```bash
./start_app.sh
```

---

## 📖 使用指南

### 1. 上传学习资料

支持的格式：
- 📄 PDF文档
- 📝 TXT文本
- 🌐 HTML网页

**操作步骤**:
1. 点击"📤 上传资料"
2. 选择文件并上传
3. 等待AI处理（约1-3分钟）
4. 自动生成学习卡片

### 2. 练习卡片

**功能**:
- ✍️ 答题练习
- 📊 查看统计
- ⭐ 收藏卡片
- 📈 学习进度

**操作流程**:
```
1. 阅读题目
2. 输入答案
3. 点击"提交答案"
4. 查看反馈和解析
5. 继续下一题
```

### 3. 复习计划

**SM-2算法自动调度**:
- 首次复习：1天后
- 第二次：6天后
- 后续：根据掌握度动态调整

**查看今日复习**:
1. 点击"📅 今日复习"
2. 完成待复习卡片
3. 系统自动更新下次复习时间

### 4. 学习报告

**数据分析**:
- 📊 总练习数和正确率
- 📈 学习进度可视化
- 📚 学习历史记录
- 🎯 错误类型分析

---

## 🎨 UI展示

### 主界面
- 🌈 动态渐变背景（15秒循环）
- ✨ 流光卡片效果
- 💜 紫色渐变侧边栏
- 📱 响应式布局

### 题目卡片
- 💎 玻璃拟态设计
- 🎨 题型颜色区分
- 💫 悬浮动画效果
- 🎭 智能反馈动画

### 按钮布局
- 🎯 主按钮居中突出
- 📦 次要操作卡片化
- 💡 清晰的操作提示
- 🌈 彩色边框区分

---

## 📊 性能数据

### 处理速度
- 10页PDF: ~1分钟
- 30页PDF: ~2-3分钟
- 50页PDF: ~4-5分钟

### 生成质量
- 概念提取准确率: >90%
- 卡片质量评分: 4.5/5
- Fallback成功率: 100%

### 页面性能
- 页面切换速度: 0.3秒（提升75%）
- API响应时间: <100ms
- 缓存命中率: >70%

---

## 🔧 配置说明

### 数据库配置
```yaml
# configs/settings.yaml
database:
  type: "sqlite"
  path: "data/mas.db"
```

### LLM配置
```yaml
llm:
  provider: "deepseek"
  deepseek:
    api_key: "your-api-key"
    base_url: "https://api.deepseek.com"
    model: "deepseek-chat"
```

### UI配置
```yaml
ui:
  theme: "modern"
  primary_color: "#667eea"
  font: "Inter"
```

---

## 📂 项目结构

```
ai-learning-companion/
├── agents/                 # 多智能体系统
│   ├── base_agent.py      # Agent基类
│   ├── content_agent.py   # 内容处理
│   ├── concept_agent.py   # 概念提取
│   ├── quiz_agent.py      # 卡片生成
│   ├── eval_agent.py      # 智能评测
│   ├── schedule_agent.py  # 复习调度
│   └── orchestrator.py    # 协调器
├── api/                   # FastAPI后端
│   └── app.py
├── frontend/              # React + Vite 前端
│   ├── src/
│   └── package.json
├── ui/                    # 旧版 Streamlit 前端（legacy）
│   └── app.py
├── storage/               # 数据存储
│   ├── db.py             # 数据库操作
│   ├── schema.sql        # 数据库schema
│   └── models.py         # 数据模型
├── nlp/                   # NLP处理
│   └── llm_helper.py     # LLM集成
├── configs/               # 配置文件
│   └── settings.yaml
├── data/                  # 数据文件
│   └── mas.db            # SQLite数据库
├── requirements.txt       # Python依赖
└── README.md             # 项目说明
```

---

## 📈 版本历史

### v0.9.1 (Latest) - 按钮布局优化
- ✅ 优化按钮布局，主次分明
- ✅ 添加操作提示引导
- ✅ 卡片式次要操作区
- ✅ 彩色边框视觉区分

### v0.9.0 - UI全面升级
- ✅ 现代化UI设计（参考豆包、GPT）
- ✅ 玻璃拟态效果
- ✅ 流光动画
- ✅ 题目索引重置修复

### v0.8.5 - 性能优化
- ✅ 页面切换速度提升75%
- ✅ API缓存优化
- ✅ 系统名称改为"知卡学伴"

### v0.8.4 - 学习进度保存
- ✅ 进度持久化
- ✅ 自动恢复
- ✅ 学习历史管理

### v0.8.3 - UI优化
- ✅ 界面美化
- ✅ 布局优化
- ✅ 多智能体说明

### 查看完整版本历史
详见各版本文档：
- [按钮布局优化-v0.9.1.md](按钮布局优化-v0.9.1.md)
- [UI全面升级-v0.9.0.md](UI全面升级-v0.9.0.md)
- [页面切换性能优化-v0.8.5.md](页面切换性能优化-v0.8.5.md)
- [学习进度保存完成-v0.8.4.md](学习进度保存完成-v0.8.4.md)

---

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 开发规范

- 代码风格：遵循PEP 8
- 提交信息：使用语义化提交
- 文档：更新相关文档
- 测试：确保所有测试通过

---

## 🐛 问题反馈

如果您遇到任何问题，请通过以下方式反馈：

- 📧 Email: favio9758@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/ai-learning-companion/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/ai-learning-companion/discussions)

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

### 技术支持
- [DeepSeek AI](https://www.deepseek.com/) - LLM支持
- [React](https://react.dev/) - 前端框架
- [Vite](https://vite.dev/) - 前端构建工具
- [shadcn/ui](https://ui.shadcn.com/) - 组件体系
- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架

### 设计灵感
- [豆包](https://www.doubao.com/) - UI设计参考
- [ChatGPT](https://chat.openai.com/) - 交互设计参考
- [Duolingo](https://www.duolingo.com/) - 学习流程参考

---

## 📞 联系我们

- **项目主页**: [GitHub Repository](https://github.com/yourusername/ai-learning-companion)
- **文档**: [Documentation](https://github.com/yourusername/ai-learning-companion/wiki)
- **问题追踪**: [Issue Tracker](https://github.com/yourusername/ai-learning-companion/issues)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个Star！⭐**

Made with ❤️ by Favio~

</div>
