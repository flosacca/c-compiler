from llvmlite import ir

from Generator.Constants import Constants
from typing import Dict, List, Union, Optional


class SymbolTable:
    """
    符号表类
    """

    def __init__(self):
        """
        建立符号表.
        """
        # table：table[i]是一个字典，存着key，value组
        self.table: List[Dict[str, str]] = [{}]
        self.current_level: int = 0

    def get_item(self, item: str) -> Optional[str]:
        """
        从符号表中获取元素.

        Args:
            item (str): 待获取的元素的 key

        Returns:
            str: 成功返回元素，失败返回 None
        """
        i = self.current_level
        while i >= 0:
            the_item_list = self.table[i]
            if item in the_item_list:
                return the_item_list[item]
            i -= 1
        return None

    def add_item(self, key: str, value: Dict[str, Union[str, ir.Type, ir.NamedValue]]) -> Dict[str, str]:
        """
        向符号表中添加元素.

        Args:
            key (str): 待添加的 key
            value (Dict[str, Union[str, ir.Type, ir.NamedValue]]):
                一个能标识变量的 Dict:
                    {"struct_name": struct_name, "type": current_type, "name": new_variable}


        Returns:
            Dict[str, str]: 成功 {"result":"success"}，失败 {"result":"fail","reason":具体原因码}
        """
        if key in self.table[self.current_level]:
            result = {"result": "fail", "reason": Constants.ERROR_TYPE_REDEFINATION}
            return result
        self.table[self.current_level][key] = value
        return {"result": "success"}

    def exist(self, item: str) -> bool:
        """
        判断元素是否在符号表里，包括局部和全局.

        Args:
            item (str): 待判断的元素

        Returns:
            bool: 如果表里有，true，否则 false
        """
        i = self.current_level
        while i >= 0:
            if item in self.table[i]:
                return True
            i -= 1
        return False

    def enter_scope(self) -> None:
        """
        进入一个新的作用域，增加一层.

        Returns:
            None
        """
        self.current_level += 1
        self.table.append({})

    def quit_scope(self) -> None:
        """
        退出一个作用域，退出一层.

        Returns:
            None
        """
        if self.current_level == 0:
            return
        self.table.pop(-1)
        self.current_level -= 1

    def is_global(self) -> bool:
        """
        判断当前变量是否全局.

        Returns:
            bool
        """
        return len(self.table) == 1


class Structure:
    """
    结构体类
    """

    def __init__(self):
        """
        初始化 self.List.
        """
        # self.List 中每个 key 对应的元素为一个 {"Members": member_list, "Type": ir.LiteralStructType(type_list)}。
        self.list: Dict[str, Dict[str, Union[List[str], ir.LiteralStructType]]] = {}

    def add_item(self, name: str, member_list: List[str], type_list: List[ir.Type]) -> Dict[str, str]:
        """
        添加一个元素.

        Args:
            name (str): 结构体名称
            member_list (List[str]): 成员列表
            type_list (List[ir.Type]): 类型列表

        Returns:
            Dict[str, str]: 成功则返回 {"result": "success"}，失败 {"result": "fail","reason": 具体原因码}
        """
        # TODO: 处理这个错误
        if name in self.list:
            result = {"result": "fail", "reason": Constants.ERROR_TYPE_REDEFINATION}
            return result
        newStruct = {"members": member_list, "type": ir.LiteralStructType(type_list)}
        self.list[name] = newStruct
        return {"result": "success"}

    def get_member_type(self, name: str, member: str) -> Optional[str]:
        """
        获取成员类型.

        Args:
            name (str): 结构体名称
            member (str): 结构体成员名

        Returns:
            str: 类型，不存在返回 None
        """
        if name not in self.list:
            return None
        structItem = self.list[name]
        theIndex = structItem["members"].index(member)
        theType = structItem["type"].elements[theIndex]
        return theType

    def get_member_index(self, name: str, member: str) -> Optional[int]:
        """
        获取成员编号.

        Args:
            name (str): 结构体名称
            member (str): 结构体成员名

        Returns:
            int: 类型,不存在返回 None
        """
        if name not in self.list:
            return None
        structItem = self.list[name]["members"]
        theIndex = structItem.index(member)
        return theIndex
