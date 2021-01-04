# c-compiler
Compile C to LLVM with Python.

## 部署方法

首先安装必备的 python3 库：
```shell script
pip install -r requirements.txt
```

### 使用 Makefile 启动（推荐）
生成 parser：
```shell script
make parser
```

生成 preprocessor：
```shell script
make preprocessor
```

### 通过 antlrbook 启动（可选）
运行库安装后，使用 [python antlrbook](https://github.com/jszheng/py3antlr4book) 项目下的 `bin/antlr4env.bat` 脚本设置 dos 宏环境：
```shell script
call <root_dir>/bin/antlr4env.bat
```

之后生成本项目的 antlr 框架：
```shell script
antlr4py3 -visitor Parser/CCompiler.g4
```

## 使用方法

编译到 LLVM IR:
```text
Usage: python3 main.py [-h] [-o output_name] [-t target] [-I include_dirs] [-D<macro<=value>>] filename
        -h, --help: 语法帮助
        -o, --output=: 输出的文件名
        -t, --target=: LLVM IR 目标平台架构，默认为 x86_64-pc-linux-gnu
        -I, --include=: 头文件搜寻目录，允许多个
        -D<macro<=value>>: 定义宏 macro，值设为 value，允许定义多个宏
```
```shell script
python3 main.py -o snake.ll -Itest/libc/include -Itest/windows/include -D_WIN64 test/snake.c
```

LLVM IR 编译到二进制文件 (示例: clang)
```shell script
clang snake.ll -o snake
```