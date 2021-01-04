from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker

import sys
import os
import platform
import re

from preprocessor.parser.CPreprocessorListener import CPreprocessorListener
from preprocessor.parser.CPreprocessorParser import CPreprocessorParser
from preprocessor.parser.CPreprocessorLexer import CPreprocessorLexer

from .errorlistener import MacroError

from typing import Dict, List, Any, Optional, Tuple

# 文件路径分隔符
separator: str = '\\' if platform.system().lower() == 'windows' else '/'


class IfStack:
    """
    用来存放宏中 if else 等块的栈，每一层表示一个 scope
    """
    def __init__(self):
        self.stack: List[Tuple[str, bool]] = list()

    def __len__(self):
        return self.size()

    def push_ifdef(self, b: bool) -> None:
        """
        推入一个 if 宏.

        Args:
            b (bool): 宏是否有效

        Returns:
            None
        """
        self.stack.append(('ifdef', b))

    def push_ifndef(self, b: bool) -> None:
        """
        推入一个 ifndef 宏.

        Args:
            b (bool): 宏是否有效

        Returns:
            None
        """
        self.stack.append(('ifndef', b))

    def push_else(self, b: bool) -> None:
        """
        推入一个 ifndef 宏.

        Args:
            b (bool): 宏是否有效

        Returns:
            None
        """
        self.stack.append(('else', b))

    def pop(self) -> Optional[Tuple[str, bool]]:
        """
        弹出一个宏.

        Returns:
            Tuple[str, bool]:
                返回一个 Tuple。str 代表宏名称，bool 表示是否生效。
        """
        return self.stack.pop() if len(self.stack) != 0 else None

    def peek(self) -> Optional[Tuple[str, bool]]:
        """
        获得栈顶宏.

        Returns:
            Tuple[str, bool]:
                返回一个 Tuple。str 代表宏名称，bool 表示是否生效。
        """
        return self.stack[-1] if len(self.stack) != 0 else None

    def size(self) -> int:
        return len(self.stack)

    def is_valid(self) -> bool:
        """
        返回栈顶宏是否生效.

        Returns:
            bool
        """
        for s in self.stack:
            if not s[1]:
                return False
        return True


class Listener(CPreprocessorListener):
    def __init__(self, filepath: str, include_dirs: List[str], macro_define_list: Optional[Dict[str, Optional[str]]] = None):
        if macro_define_list is None:
            macro_define_list = dict()
        # 存放预处理后的代码
        self.buffer: str = ''
        # 此文件的路径
        self.filepath = filepath
        # 头文件寻找目录
        self._include_dirs: List[str] = include_dirs
        # 存放 if else 等宏 block 的栈
        self._if_stack: IfStack = IfStack()
        # 宏定义表
        self._macro_define_list: Dict[str, str] = macro_define_list
        # 是否跳过此行，不写入文件
        self._is_skip: bool = False

    def enterLine(self, ctx:CPreprocessorParser.LineContext):
        # 无效 if 块中
        if not self._if_stack.is_valid():
            self._is_skip = True

    def exitLine(self, ctx: CPreprocessorParser.LineContext):
        if not self._is_skip:
            self.buffer += ctx.getText()
            self.buffer += '\n'
        self._is_skip = False
        pass

    def exitDefineStat(self, ctx: CPreprocessorParser.DefineStatContext):
        # WS? '#define' WS macroID restOfLine?
        if self._is_skip:
            return
        # 增加宏
        self._is_skip = True
        m = ctx.macroID().getText()
        self._macro_define_list[m] = ctx.restOfLine().getText() if ctx.restOfLine() is not None else ''

    def exitUndefStat(self, ctx: CPreprocessorParser.UndefStatContext):
        if self._is_skip:
            return
        # 删除宏
        self._is_skip = True
        m = ctx.macroID().getText()
        del(self._macro_define_list[m])

    def exitIncludeCur(self, ctx: CPreprocessorParser.IncludeCurContext):
        if self._is_skip:
            return
        self._is_skip = True
        filename: str = ctx.filename().getText()
        for include_dir in self._include_dirs:
            filepath: str = include_dir + separator + filename
            if os.path.exists(filepath):
                self.buffer += preprocess(filepath, self._include_dirs, self._macro_define_list)
                return
        raise MacroError('头文件未找到', self.filepath, ctx)

    def enterIncludeSys(self, ctx: CPreprocessorParser.IncludeSysContext):
        # TODO: 目前和 exitIncludeCur 一样
        self.exitIncludeCur(ctx)

    def exitIfdefStat(self, ctx: CPreprocessorParser.IfdefStatContext):
        self._is_skip = True
        m = ctx.macroID().getText()
        self._if_stack.push_ifdef(True if self._macro_define_list.get(m) is not None else False)

    def exitIfndefStat(self, ctx: CPreprocessorParser.IfndefStatContext):
        self._is_skip = True
        m = ctx.macroID().getText()
        self._if_stack.push_ifndef(True if self._macro_define_list.get(m) is None else False)

    def exitElseStat(self, ctx:CPreprocessorParser.ElseStatContext):
        # TODO 目前没有 elif，因此逻辑较简单
        self._is_skip = True
        ret = self._if_stack.pop()
        if ret is None:
            raise MacroError('#else 宏未闭合', self.filepath, ctx)
        self._if_stack.push_else(True if not ret[1] else False)

    def exitEndifStat(self, ctx:CPreprocessorParser.EndifStatContext):
        self._is_skip = True
        if self._if_stack.pop() is None:
            raise MacroError('#endif 宏未闭合', self.filepath, ctx)

    @property
    def if_stack(self):
        return self._if_stack

    @property
    def macro_define_list(self):
        return self._macro_define_list


def preprocess(filepath: str, include_dirs: List[str], macro_define_list: Optional[Dict[str, Optional[str]]] = None) -> str:
    """
    预处理 .c 文件.

    Args:
        filepath (str): 文件的路径地址
        include_dirs (List[str]): 头文件目录
        macro_define_list (Dict[str, str]): 预先定义的宏，默认为 None

    Returns:
        str: 预处理后的文本

    Raises:
        MacroError:
            宏处理的错误
    """
    lexer = CPreprocessorLexer(FileStream(filepath))
    stream = CommonTokenStream(lexer)
    parser = CPreprocessorParser(stream)
    parser.removeErrorListeners()
    # errorListener = SyntaxErrorListener()
    # parser.addErrorListener(errorListener)

    listener = Listener(filepath, include_dirs, macro_define_list)
    tree = parser.macro()
    walker = ParseTreeWalker()
    walker.walk(listener, tree)
    if len(listener.if_stack) != 0:
        raise MacroError('缺少 #endif 宏', filepath, None)

    output_data = listener.buffer
    output_data = macro_replace(output_data, listener.macro_define_list)
    output_data = remove_redundant_carriage(output_data)
    return output_data


def macro_replace(text: str, macro_list: Dict[str, Optional[str]]) -> str:
    """
    替换宏.

    :param text: 原来的文本
    :type text: str
    :param macro_list: 宏表
    :type macro_list: Dict[str, str]
    :return: 替换后的文本
    :rtype: str
    """
    result = text
    for (k, v) in macro_list.items():
        result = result.replace(k, v if v is not None else '')
    return result


def remove_redundant_carriage(text: str) -> str:
    """
    去除多余的换行.

    :param text: 文本
    :type text: str
    :return: 处理后的文本
    :rtype: str
    """
    return re.sub('(\r?\n)+', '\n', text)


if __name__ == '__main__':
    print(preprocess(sys.argv[1], ['H:\\github\\c-compiler\\src\\test',
                                   'H:\\github\\c-compiler\\src\\test\libc\include',
                                   'H:\\github\\c-compiler\\src\\test\windows\include']))
