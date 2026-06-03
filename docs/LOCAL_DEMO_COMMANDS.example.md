# Local Demo Commands Example

展示说明：这是本地演示命令模板，适合复制为仓库根目录下的 `LOCAL_DEMO_COMMANDS.md` 后按个人机器路径修改。真实本地路径、私有 Python/Maven 安装路径和密钥不要提交到 GitHub。

## 推荐通用命令

```powershell
cd ./ai-service
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd ./backend
mvn spring-boot:run
```

```powershell
cd ./frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## Windows 固定路径模板

如果本机 Python、Maven 没有加入 `PATH`，可以在未提交的 `LOCAL_DEMO_COMMANDS.md` 中改成类似下面的形式：

```powershell
cd "<your-project-path>\ai-service"
<your-python-path>\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd "<your-project-path>\backend"
& "<your-maven-path>\bin\mvn.cmd" spring-boot:run
```

```powershell
cd "<your-project-path>\frontend"
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

## 发布前复验

```powershell
make test
make rag-index
make rag-eval
```

```powershell
cd ./ai-service
python -m pytest
```

```powershell
cd ./backend
mvn test
```

```powershell
cd ./frontend
npm run build
```
