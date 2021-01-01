from typing import Dict, List, Union, Optional

from llvmlite import ir

from generator.Constants import Constants
from generator.parser_util import Result, success_result


class TypedValue(object):

    def __init__(self, ir_value: ir.Value, typ: ir.Type, constant: bool, name: str = None, lvalue_ptr: bool = False):
        self.type = typ
        self.constant = constant
        self.ir_value = ir_value
        self.name = name
        self.lvalue_ptr = lvalue_ptr

    def is_named(self) -> bool:
        return self.name is not None


def const_value(value: ir.Constant, name: str = None) -> TypedValue:
    """
    返回一个常量值.

    Args:
        value (ir.Constant): ir 常量值.
        name (str): 常量名 .

    Returns:
        TypedValue:
    """
    return TypedValue(value, value.type, constant=True, name=name, lvalue_ptr=False)


class SymbolTable:
    """
    符号表类
    """

    def __init__(self):
        """
        建立符号表.
        """
        # table：table[i]是一个字典，存着key，value组
        self.table: List[Dict[str, TypedValue]] = [{}]
        self.current_level: int = 0

    def get_item(self, item: str) -> Optional[TypedValue]:
        """
        从符号表中获取元素.

        Args:
            item (str): 待获取的元素的 key

        Returns:
            str: 成功返回元素，失败返回 None
        """
        for i in range(self.current_level, -1, -1):
            if item in self.table[i]:
                return self.table[i][item]
        return None

    def add_item(self, key: str, value: TypedValue) -> Result[None]:
        """
        向符号表中添加元素.

        Args:
            key (str): 待添加的 key
            value (TypedValue): 待添加的 value

        Returns:
            Optional[str]: 如果出现了异常，返回具体错误信息，否则返回 None
        """
        if key in self.table[self.current_level]:
            return Result[None](False, message=Constants.ERROR_TYPE_REDEFINITION)
        self.table[self.current_level][key] = value
        return Result[None](True, value=None)

    def exist(self, item: str) -> bool:
        """
        判断元素是否在符号表里，包括局部和全局.

        Args:
            item (str): 待判断的元素

        Returns:
            bool: 如果表里有，true，否则 false
        """
        return self.get_item(item) is not None

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
        判断当前作用域是否是全局作用域.

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
        # self.list 中每个 key 对应的元素为一个 {'Members': member_list, 'Type': ir.LiteralStructType(type_list)}。
        self.list: Dict[str, Dict[str, Union[List[str], ir.LiteralStructType]]] = {}

    def add_item(self, name: str, member_list: List[str], type_list: List[ir.Type]) -> Dict[str, str]:
        """
        添加一个元素.

        Args:
            name (str): 结构体名称
            member_list (List[str]): 成员列表
            type_list (List[ir.Type]): 类型列表

        Returns:
            Dict[str, str]: 成功则返回 {'status': 'success'}，失败 {'status': 'fail','reason': 具体原因码}
        """
        # TODO: 处理这个错误
        if name in self.list:
            result = {'status': 'fail', 'reason': Constants.ERROR_TYPE_REDEFINITION}
            return result
        newStruct = {'members': member_list, 'type': ir.LiteralStructType(type_list)}
        self.list[name] = newStruct
        return {'status': 'success'}

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
        theIndex = structItem['members'].index(member)
        theType = structItem['type'].elements[theIndex]
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
        structItem = self.list[name]['members']
        theIndex = structItem.index(member)
        return theIndex
