@echo off
REM Windows启动脚本 - 多智能体学习系统

echo ========================================
echo   智能学习卡片生成系统
echo   Multi-Agent Learning System
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

echo [信息] Python已安装
echo.

REM 检查虚拟环境
if not exist "venv\" (
    echo [警告] 虚拟环境不存在，正在创建...
    python -m venv venv
    echo [信息] 虚拟环境创建完成
)

REM 激活虚拟环境
echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

REM 检查依赖
echo [信息] 检查依赖包...
pip install -r requirements.txt --quiet

REM 创建必要的目录
if not exist "data\" mkdir data
if not exist "data\uploads\" mkdir data\uploads
if not exist "logs\" mkdir logs

echo.
echo [信息] 启动后端API服务...
start "MAS-API" cmd /k "venv\Scripts\activate.bat && python api/app.py"

REM 等待几秒让API启动
timeout /t 3 /nobreak >nul

echo [信息] 启动前端UI界面...
start "MAS-UI" cmd /k "venv\Scripts\activate.bat && streamlit run ui/app.py"

echo.
echo ========================================
echo   系统启动完成！
echo ========================================
echo.
echo   前端界面: http://localhost:8501
echo   API文档:  http://localhost:8000/docs
echo.
echo   按任意键关闭此窗口...
echo ========================================

pause >nul

