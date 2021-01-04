from typing import Dict, List, Union, Optional, Tuple

from llvmlite import ir

from generator.parser_util import Result


class DeclarationSpecifiers:
    """
    对应文法中的 declarationSpecifiers，表示能够作用在 declarator 上的各种修饰符，包括:
     - typeSpecifier            : int | double | ...        (存储为 ir.Type)
     - typeQualifier            : const                     (存储为 str)
     - storageClassQualifier    : extern | static           (存储为 str)
     - functionSpecifier        : __stdcall | __cdecl | ... (存储为 str)
    """

    def __init__(self):
        self.specifiers: List[Tuple[str, Union[str, ir.Type]]] = []
        pass

    def append_type_specifier(self, specifier: ir.Type):
        self.specifiers.append(("type", specifier))

    def append_type_qualifier(self, qualifier: str):
        self.specifiers.append(("type_qualifier", qualifier))

    def append_storage_class_specifier(self, qualifier: str):
        self.specifiers.append(("storage", qualifier))

    def append_function_specifier(self, specifier: str):
        self.specifiers.append(("function_specifier", specifier))

    def append(self, typ: str, val: Union[str, ir.Type]):
        if typ == "type":
            self.append_type_specifier(val)
        if typ == "type_qualifier":
            self.append_type_qualifier(val)
        if typ == "storage":
            self.append_storage_class_specifier(val)
        if typ == "function_specifier":
            self.append_function_specifier(val)

    def get_function_specifiers(self):
        return map(lambda x: x[1], filter(lambda x: x[0] == "function_specifier", self.specifiers))

    def get_type(self):
        for (typ, val) in self.specifiers:
            if typ == "type":
                return val
        return None

    def is_typedef(self):
        return ("storage", "typedef") in self.specifiers

    def is_extern(self):
        return ("storage", "extern") in self.specifiers

    def is_static(self):
        return ("storage", "static") in self.specifiers

    def is_extern(self):
        for (typ, val) in self.specifiers:
            if typ == "storage" and val == "extern":
                return True
        return False


class ParameterList:

    def __init__(self, parameters: List[Tuple[ir.Type, Optional[str]]], var_arg: bool, calling_convention: str = ''):
        self.parameters = parameters
        self.var_arg = var_arg
        self.arg_list = [param[0] for param in self.parameters]
        self.calling_convention = calling_convention

    def __getitem__(self, item: int):
        return self.parameters[item]

    def __len__(self):
        return len(self.parameters)


class TypedValue:

    def __init__(self, ir_value: ir.Value, typ: ir.Type, constant: bool, name: str = None, lvalue_ptr: bool = False):
        """
        初始化
        @param ir_value:    llvm ir 中对应的值
        @param typ:         值的实际类型 (这与 ir_value.type 是不同的。比如一个 alloca 的 i32 局部变量，ir_value 的 type 会是 i32*，而这个字段是 i32
        @param constant:    值是否是常量
        @param name:        值的名称 (可以为 None，默认为 None)
        @param lvalue_ptr:  值是否是一个左值 (这意味着 ir_value 的类型会是 typ.as_pointer()，需要用 load 和 store 访问。默认为 False)
        """
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
        TypedValue: 常量值的 TypedValue 封装. 右值, constant
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
        self.table: List[Dict[str, Union[TypedValue, ir.Type, ir.Function]]] = [{}]
        self.current_level: int = 0

    def get_item(self, item: str) -> Optional[Union[TypedValue, ir.Type]]:
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

    def add_item(self, key: str, value: Union[TypedValue, ir.Type, ir.Function]) -> Result[None]:
        """
        向符号表中添加元素.

        Args:
            key (str): 待添加的 key
            value (TypedValue): 待添加的 value

        Returns:
            Optional[str]: 如果出现了异常，返回具体错误信息，否则返回 None
        """
        if key in self.table[self.current_level]:
            return Result(False, message="redefinition")
        self.table[self.current_level][key] = value
        return Result(True, value=None)

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


class ElementNamedLiteralStructType(ir.LiteralStructType):
    """
    成员具名结构体类类型封装
    """

    def __init__(self, elems: List[ir.Type], names: List[str], packed=False):
        """
        *elems* is a sequence of types to be used as members.
        *names* is a sequence of names to be used for name lookup.
        *packed* controls the use of packed layout.
        """
        ir.LiteralStructType.__init__(self, elems, packed)
        self.names = tuple(names)

    def index(self, name: str) -> int:
        """
        寻找名字对应的下标. 找不到时抛出异常.
        @param name: 名字
        @return: 下标
        """
        return self.names.index(name)
