#!/bin/bash
# Linux/Mac启动脚本 - 多智能体学习系统

echo "========================================"
echo "  智能学习卡片生成系统"
echo "  Multi-Agent Learning System"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装Python 3.10+"
    exit 1
fi

echo "[信息] Python3已安装: $(python3 --version)"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "[警告] 虚拟环境不存在，正在创建..."
    python3 -m venv venv
    echo "[信息] 虚拟环境创建完成"
fi

# 激活虚拟环境
echo "[信息] 激活虚拟环境..."
source venv/bin/activate

# 检查依赖
echo "[信息] 检查依赖包..."
pip install -r requirements.txt --quiet

# 创建必要的目录
mkdir -p data/uploads
mkdir -p logs

echo ""
echo "[信息] 启动后端API服务..."
python api/app.py &
API_PID=$!

# 等待几秒让API启动
sleep 3

echo "[信息] 启动前端UI界面..."
streamlit run ui/app.py &
UI_PID=$!

echo ""
echo "========================================"
echo "  系统启动完成！"
echo "========================================"
echo ""
echo "  前端界面: http://localhost:8501"
echo "  API文档:  http://localhost:8000/docs"
echo ""
echo "  按 Ctrl+C 停止服务..."
echo "========================================"

# 等待用户中断
trap "echo ''; echo '[信息] 正在停止服务...'; kill $API_PID $UI_PID; exit" INT

# 保持脚本运行
wait

