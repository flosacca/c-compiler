from llvmlite import ir

from Generator.Constants import Constants


class SymbolTable:
    """
    符号表类
    """

    def __init__(self):
        """
        功能：建立符号表
        参数：无
        返回：无
        """
        # table：table[i]是一个字典，存着key，value组
        self.table = [{}]
        self.current_level = 0

    def GetItem(self, item):
        """
        功能：从符号表中获取元素
        参数：待获取的元素的key
        返回：成功：返回元素，失败返回None
        """
        i = self.current_level
        while i >= 0:
            the_item_list = self.table[i]
            if item in the_item_list:
                return the_item_list[item]
            i -= 1
        return None

    def AddItem(self, key, value):
        """
        功能：向符号表中添加元素
        参数：待添加的key，value
        返回：成功{"result":"success"}，失败{"result":"fail","reason":具体原因码}
        """
        if key in self.table[self.current_level]:
            result = {"result": "fail", "reason": Constants.ERROR_TYPE_REDEFINATION}
            return result
        self.table[self.current_level][key] = value
        return {"result": "success"}

    def JudgeExist(self, item):
        """
        功能：判断元素是否在符号表里
        参数：待判断的元素
        返回：如果表里有，true，否则false
        """
        i = self.current_level
        while i >= 0:
            if item in self.table[i]:
                return True
            i -= 1
        return False

    def EnterScope(self):
        """
        功能：进入一个新的作用域，增加一层
        参数：无
        返回：无
        """
        self.current_level += 1
        self.table.append({})

    def QuitScope(self):
        """
        功能：退出一个作用域，退出一层
        参数：无
        返回：无
        """
        if self.current_level == 0:
            return
        self.table.pop(-1)
        self.current_level -= 1

    def JudgeWhetherGlobal(self):
        """
        功能：判断当前变量是否全局
        参数：无
        返回：是true，否则false
        """
        if len(self.table) == 1:
            return True
        else:
            return False


class Structure:
    """
    结构体类
    """

    def __init__(self):
        """
        描述：初始化
        参数：无
        返回：无
        """
        self.List = {}

    def AddItem(self, name, member_list, type_list):
        """
        描述：添加一个元素
        参数：名称，成员列表，类型列表
        返回：成功{"result":"success"}，失败{"result":"fail","reason":具体原因码}
        """
        # todo:处理这个错误
        if name in self.List:
            result = {"result": "fail", "reason": Constants.ERROR_TYPE_REDEFINATION}
            return result
        NewStruct = {"Members": member_list, "Type": ir.LiteralStructType(type_list)}
        self.List[name] = NewStruct
        return {"result": "success"}

    def GetMemberType(self, name, member):
        """
        描述：获取成员类型
        参数：结构体名称，结构体成员名
        返回：类型,不存在返回None
        """
        if name not in self.List:
            return None
        StructItem = self.List[name]
        TheIndex = StructItem["Members"].index(member)
        TheType = StructItem["Type"].elements[TheIndex]
        return TheType

    def GetMemberIndex(self, name, member):
        """
        描述：获取成员编号
        参数：结构体名称，结构体成员名
        返回：类型,不存在返回None
        """
        if name not in self.List:
            return None
        StructItem = self.List[name]["Members"]
        TheIndex = StructItem.index(member)
        return TheIndex
