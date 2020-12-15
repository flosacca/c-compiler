# c-compiler
Compile C to LLVM with Python.

## 部署方法

首先安装必备的 python3 库：
```shell script
pip install -r requirements.txt
```

运行库安装后，使用 [python antlrbook](https://github.com/jszheng/py3antlr4book) 项目下的 `bin/antlr4env.bat` 脚本设置 dos 宏环境：
```shell script
call <root_dir>/bin/antlr4env.bat
```

之后生成本项目的 antlr 框架：
```shell script
antlr4py3 -visitor Parser/CCompiler.g4
```

## 使用方法

单文件编译：
```shell script
python3 main.py test/<某个文件>.c
```

`test/` 文件夹下全体 *.c 文件编译：
```shell script
python3 compile_all.py
```