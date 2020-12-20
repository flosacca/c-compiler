from antlr4 import *
from llvmlite import ir

from typing import Dict, List, Union, Optional, Any

from generator.ErrorListener import SemanticError
from generator.ErrorListener import SyntaxErrorListener
from generator.SymbolTable import SymbolTable, Structure
from parser.CCompilerLexer import CCompilerLexer
from parser.CCompilerParser import CCompilerParser
from parser.CCompilerVisitor import CCompilerVisitor

double = ir.DoubleType()
int1 = ir.IntType(1)
int32 = ir.IntType(32)
int8 = ir.IntType(8)
void = ir.VoidType()


class Visitor(CCompilerVisitor):
    """
    生成器类，用于进行语义分析并且转化为LLVM
    """

    def __init__(self):
        super(CCompilerVisitor, self).__init__()

        # 控制llvm生成
        self.module: ir.Module = ir.Module()
        self.module.triple = "x86_64-pc-linux-gnu"  # llvm.Target.from_default_triple()
        # llvm.create_mcjit_compiler(backing_mod, target_machine)
        self.module.data_layout = "e-m:e-i64:64-f80:128-n8:16:32:64-S128"

        # 语句块
        self.blocks: List[ir.Block] = []

        # 待生成的 llvm 语句块
        self.builders: List[ir.IRBuilder] = []

        # 函数列表
        self.functions = dict()

        # 结构体列表
        self.structure: Structure = Structure()

        # 当前所在函数名
        self.current_function: str = ''
        self.constants = 0

        # 这个变量是否需要加载
        self.whether_need_load: bool = True

        # endif块
        self.endif_block = None

        # 符号表
        self.symbol_table: SymbolTable = SymbolTable()

    def visitProg(self, ctx: CCompilerParser.ProgContext) -> None:
        """
        代码主文件.

        语法规则：
            prog :(include)* (initialBlock | arrayInitBlock | structInitBlock | mStructDef| mFunction)*;

        Args:
            ctx (CCompilerParser.ProgContext):

        Returns:
            None
        """
        for i in range(ctx.getChildCount()):
            self.visit(ctx.getChild(i))

    # 结构体相关函数
    def visitMStructDef(self, ctx: CCompilerParser.MStructContext) -> None:
        """
        结构体定义.

        语法规则：
            mStructDef : mStruct '{' (structParam)+ '}' ';';

        Args:
            ctx (CCompilerParser.MStructContext):

        Returns:
            None
        """
        new_struct_name: str = ctx.getChild(0).getChild(1).getText()

        # 遍历结构体的变量，并且存储
        i = 2
        parameter_type_list = []
        parameter_name_list = []
        total_params = ctx.getChildCount() - 2
        # 逐行读取并且存储
        while i < total_params:
            parameter_type_line, parameter_name_line = self.visit(ctx.getChild(i))
            parameter_type_list = parameter_type_list + parameter_type_line
            parameter_name_list = parameter_name_list + parameter_name_line
            i += 1

        # 存储结构体
        the_result = self.structure.add_item(new_struct_name, parameter_name_list, parameter_type_list)
        if the_result["result"] != "success":
            raise SemanticError(ctx=ctx, msg=the_result["reason"])

    def visitStructParam(self, ctx: CCompilerParser.StructParamContext):
        """
        处理一行结构体参数.

        语法规则：
            structParam : (mType | mStruct) (mID | mArray) (',' (mID | mArray))* ';';

        Args:
            ctx (CCompilerParser.StructParamContext):

        Returns:
            None
        """
        parameter_type_line = []
        parameter_name_line = []
        # TODO: 此处只支持非 struct 的变量类型
        # 必须有类型
        if ctx.getChild(0).getChildCount() == 1:
            i = 1
            parameter_type = self.visit(ctx.getChild(0))
            length = ctx.getChildCount()
            while i < length:
                # 处理MID的情况（单一变量）
                if ctx.getChild(i).getChildCount() == 1:
                    parameter_name_line.append(ctx.getChild(i).getText())
                    parameter_type_line.append(parameter_type)
                # 处理mArray的情况（数组）
                else:
                    array_info = self.visit(ctx.getChild(i))
                    parameter_name_line.append(array_info['ID_name'])
                    parameter_type_line.append(ir.ArrayType(parameter_type, array_info['length']))
                i = i + 2
            return parameter_type_line, parameter_name_line

    def visitStructInitBlock(self, ctx: CCompilerParser.StructInitBlockContext):
        """
        结构体初始化

        语法规则：
            structInitBlock : mStruct (mID|mArray)';';

        Args:
            ctx (CCompilerParser.StructParamContext):

        Returns:
            None
        """
        variable_info = self.visit(ctx.getChild(0))
        variable_type = variable_info['type']
        struct_name = ctx.getChild(0).getChild(1).getText()

        # 处理结构体变量是单一变量的情况
        if ctx.getChild(1).getChildCount() == 1:
            ID_name = ctx.getChild(1).getText()
            current_type = variable_type
            # 全局变量
            if self.symbol_table.is_global():
                new_variable = ir.GlobalVariable(self.module, variable_type, name=ID_name)
                new_variable.linkage = 'internal'
                new_variable.initializer = ir.Constant(current_type, None)
            # 局部变量
            else:
                the_builder = self.builders[-1]
                new_variable = the_builder.alloca(current_type, name=ID_name)

        # 处理结构体变量是数组的情况
        else:
            variable_info = self.visit(ctx.getChild(1))
            ID_name = variable_info['ID_name']
            current_type = ir.ArrayType(variable_type, variable_info['length'])
            # 全局变量
            if self.symbol_table.is_global():
                new_variable = ir.GlobalVariable(self.module, current_type, name=ID_name)
                new_variable.linkage = 'internal'
                new_variable.initializer = ir.Constant(current_type, None)
            else:
                the_builder = self.builders[-1]
                new_variable = the_builder.alloca(current_type, name=ID_name)

        # 存储这个结构体变量
        the_variable = {"struct_name": struct_name, "type": current_type, "name": new_variable}
        the_result = self.symbol_table.add_item(ID_name, the_variable)
        if the_result["result"] != "success":
            raise SemanticError(ctx=ctx, msg=the_result["reason"])
        return

    def visitStructMember(self, ctx: CCompilerParser.StructMemberContext) -> Dict[str, Union[Optional[str], Any]]:
        """
        获取结构体成员变量信息.

        语法规则：
            structMember: (mID | arrayItem)'.'(mID | arrayItem);

        Args:
            ctx (CCompilerParser.StructMemberContext):

        Returns:
            Dict[str, Union[Optional[str], Any]]
        """
        the_builder = self.builders[-1]
        # 处理成员元素是单一变量的情况，TODO g4修改后删除
        if ctx.getChild(2).getChildCount() == 1:  # mID
            current_need_load = self.whether_need_load
            self.whether_need_load = False
            struct_info = self.visit(ctx.getChild(0))
            self.whether_need_load = current_need_load

            # 读取结构体信息
            struct_name = struct_info['struct_name']
            father_name = struct_info["name"]
            index = self.structure.get_member_index(struct_name, ctx.getChild(2).getText())
            if index is None:
                raise SemanticError(ctx=ctx, msg="未找到这个变量")
            type = self.structure.get_member_type(struct_name, ctx.getChild(2).getText())

            zero = ir.Constant(int32, 0)
            idx = ir.Constant(int32, index)
            new_variable = the_builder.gep(father_name, [zero, idx], inbounds=True)

            if self.whether_need_load:
                new_variable = the_builder.load(new_variable)

            result = {"type": type, "name": new_variable}
            return result
        else:
            raise NotImplementedError()

    # 函数相关函数
    def visitMFunction(self, ctx: CCompilerParser.MFunctionContext) -> None:
        """
        函数的定义.

        语法规则:
            mFunction : (mType|mVoid|mStruct) mID '(' params ')' '{' funcBody '}';

        Args:
            ctx (CCompilerParser.MFunctionContext):

        Returns:
            None
        """
        # 获取返回值类型
        return_type = self.visit(ctx.getChild(0))  # mtype

        # 获取函数名 todo
        function_name = ctx.getChild(1).getText()  # func name

        # 获取参数列表
        parameter_list = self.visit(ctx.getChild(3))  # func params

        # 根据返回值，函数名称和参数生成 llvm 函数
        parameter_type_list = []
        for i in range(len(parameter_list)):
            parameter_type_list.append(parameter_list[i]['type'])
        llvm_function_type = ir.FunctionType(return_type, parameter_type_list)
        llvm_function = ir.Function(self.module, llvm_function_type, name=function_name)

        # 存储函数的变量
        for i in range(len(parameter_list)):
            llvm_function.args[i].name = parameter_list[i]['ID_name']

        # 存储函数的block
        the_block: ir.Block = llvm_function.append_basic_block(name=function_name + '.entry')

        # 判断重定义，存储函数
        if function_name in self.functions:
            raise SemanticError(ctx=ctx, msg="函数重定义错误！")
        else:
            self.functions[function_name] = llvm_function

        the_builder: ir.IRBuilder = ir.IRBuilder(the_block)
        self.blocks.append(the_block)
        self.builders.append(the_builder)

        # 进一层
        self.current_function = function_name
        self.symbol_table.enter_scope()

        # 存储函数的变量
        variable_list = {}
        for i in range(len(parameter_list)):
            new_variable = the_builder.alloca(parameter_list[i]['type'])
            the_builder.store(llvm_function.args[i], new_variable)
            the_variable = {"type": parameter_list[i]['type'], "name": new_variable}
            the_result = self.symbol_table.add_item(parameter_list[i]['ID_name'], the_variable)
            if the_result["result"] != "success":
                raise SemanticError(ctx=ctx, msg=the_result["reason"])

        # 处理函数body
        self.visit(ctx.getChild(6))  # func body

        # 处理完毕，退一层
        self.current_function = ''
        self.blocks.pop()
        self.builders.pop()
        self.symbol_table.quit_scope()
        return

    def visitParams(self, ctx: CCompilerParser.ParamsContext) -> List[Dict[str, Union[ir.Type, str]]]:
        """
        函数的参数列表.

        语法规则：
            params : param (','param)* |;

        Args:
            ctx (CCompilerParser.ParamsContext):

        Returns:
            List[Dict[str, Union[ir.Type, str]]]: 处理后的函数参数列表
        """
        length = ctx.getChildCount()
        if length == 0:
            return []
        parameter_list: List[Dict[str, Union[ir.Type, str]]] = []
        i = 0
        while i < length:
            new_parameter: Dict[str, Union[ir.Type, str]] = self.visit(ctx.getChild(i))
            parameter_list.append(new_parameter)
            i += 2
        return parameter_list

    def visitParam(self, ctx: CCompilerParser.ParamContext) -> Dict[str, Union[ir.Type, str]]:
        """
        返回函数参数.

        语法规则：
            param : mType mID;

        Args:
            ctx (CCompilerParser.ParamContext):

        Returns:
            Dict[str, Union[ir.Type, str]]: 一个字典，字典的 type 是类型，name 是参数名
        """
        type = self.visit(ctx.getChild(0))
        ID_name = ctx.getChild(1).getText()
        result = {'type': type, 'ID_name': ID_name}
        return result

    def visitFuncBody(self, ctx: CCompilerParser.FuncBodyContext):
        """
        语法规则：funcBody : body returnBlock;
        描述：函数体
        返回：无
        """
        self.symbol_table.enter_scope()
        for index in range(ctx.getChildCount()):
            self.visit(ctx.getChild(index))
        self.symbol_table.quit_scope()
        return

    def visitBody(self, ctx: CCompilerParser.BodyContext):
        """
        语法规则：body : (block | func';')*;
        描述：语句块/函数块
        返回：无
        """
        for i in range(ctx.getChildCount()):
            self.visit(ctx.getChild(i))
            if self.blocks[-1].is_terminated:
                break
        return

    # 调用函数相关函数
    def visitFunc(self, ctx: CCompilerParser.FuncContext):
        """
        语法规则：func : (strlenFunc | atoiFunc | printfFunc | scanfFunc | getsFunc | selfDefinedFunc);
        描述：函数
        返回：无
        """
        return self.visit(ctx.getChild(0))

    def visitStrlenFunc(self, ctx: CCompilerParser.StrlenFuncContext):
        """
        语法规则：strlenFunc : 'strlen' '(' mID ')';
        描述：strlen函数
        返回：函数返回值
        """
        if 'strlen' in self.functions:
            strlen = self.functions['strlen']
        else:
            strlenType = ir.FunctionType(int32, [ir.PointerType(int8)], var_arg=False)
            strlen = ir.Function(self.module, strlenType, name="strlen")
            self.functions['strlen'] = strlen

        the_builder = self.builders[-1]
        zero = ir.Constant(int32, 0)

        # 加载变量
        previous_need_load = self.whether_need_load
        self.whether_need_load = False
        res = self.visit(ctx.getChild(2))
        self.whether_need_load = previous_need_load

        arguments = the_builder.gep(res['name'], [zero, zero], inbounds=True)
        return_variable_name = the_builder.call(strlen, [arguments])

        result = {'type': int32, 'name': return_variable_name}
        return result

    def visitPrintfFunc(self, ctx: CCompilerParser.PrintfFuncContext):
        """
        语法规则：printfFunc : 'printf' '(' (mSTRING | mID) (','expr)* ')';
        描述：printf函数
        返回：函数返回值
        """
        if 'printf' in self.functions:
            printf = self.functions['printf']
        else:
            printfType = ir.FunctionType(int32, [ir.PointerType(int8)], var_arg=True)
            printf = ir.Function(self.module, printfType, name="printf")
            self.functions['printf'] = printf

        the_builder = self.builders[-1]
        zero = ir.Constant(int32, 0)

        # 就一个变量
        if ctx.getChildCount() == 4:
            parameter_info = self.visit(ctx.getChild(2))
            argument = the_builder.gep(parameter_info['name'], [zero, zero], inbounds=True)
            return_variable_name = the_builder.call(printf, [argument])
        else:
            parameter_info = self.visit(ctx.getChild(2))
            arguments = [the_builder.gep(parameter_info['name'], [zero, zero], inbounds=True)]

            length = ctx.getChildCount()
            i = 4
            while i < length - 1:
                one_parameter = self.visit(ctx.getChild(i))
                arguments.append(one_parameter['name'])
                i += 2
            return_variable_name = the_builder.call(printf, arguments)
        result = {'type': int32, 'name': return_variable_name}
        return result

    def visitScanfFunc(self, ctx: CCompilerParser.ScanfFuncContext):
        """
        语法规则：scanfFunc : 'scanf' '(' mSTRING (','('&')?(mID|arrayItem|structMember))* ')';
        描述：scanf函数
        返回：函数返回值
        """
        if 'scanf' in self.functions:
            scanf = self.functions['scanf']
        else:
            scanfType = ir.FunctionType(int32, [ir.PointerType(int8)], var_arg=True)
            scanf = ir.Function(self.module, scanfType, name="scanf")
            self.functions['scanf'] = scanf

        the_builder = self.builders[-1]
        zero = ir.Constant(int32, 0)
        parameter_list = self.visit(ctx.getChild(2))  # MString
        arguments = [the_builder.gep(parameter_list['name'], [zero, zero], inbounds=True)]

        length = ctx.getChildCount()
        i = 4
        while i < length - 1:
            if ctx.getChild(i).getText() == '&':
                # 读取变量
                previous_need_load = self.whether_need_load
                self.whether_need_load = False
                the_parameter = self.visit(ctx.getChild(i + 1))
                self.whether_need_load = previous_need_load
                arguments.append(the_parameter['name'])
                i += 3
            else:
                previous_need_load = self.whether_need_load
                self.whether_need_load = True
                the_parameter = self.visit(ctx.getChild(i))
                self.whether_need_load = previous_need_load
                arguments.append(the_parameter['name'])
                i += 2

        return_variable_name = the_builder.call(scanf, arguments)
        result = {'type': int32, 'name': return_variable_name}
        return result

    def visitGetsFunc(self, ctx: CCompilerParser.GetsFuncContext):
        """
        语法规则：getsFunc : 'gets' '(' mID ')';
        描述：gets函数
        返回：函数返回值
        """
        if 'gets' in self.functions:
            gets = self.functions['gets']
        else:
            getsType = ir.FunctionType(int32, [], var_arg=True)
            gets = ir.Function(self.module, getsType, name="gets")
            self.functions['gets'] = gets

        the_builder = self.builders[-1]
        zero = ir.Constant(int32, 0)

        previous_need_load = self.whether_need_load
        self.whether_need_load = False
        ParameterInfo = self.visit(ctx.getChild(2))
        self.whether_need_load = previous_need_load

        arguments = [the_builder.gep(ParameterInfo['name'], [zero, zero], inbounds=True)]
        return_variable_name = the_builder.call(gets, arguments)
        result = {'type': int32, 'name': return_variable_name}
        return result

    def visitSelfDefinedFunc(self, ctx: CCompilerParser.SelfDefinedFuncContext) -> Dict[str, ir.CallInstr]:
        """
        自定义函数.

        语法规则：
            selfDefinedFunc : mID '('((argument | mID)(','(argument | mID))*)? ')';

        Args:
            ctx (CCompilerParser.SelfDefinedFuncContext):

        Returns:
            Dict[str, CallInstr]: 函数返回值
        """
        the_builder = self.builders[-1]
        function_name = ctx.getChild(0).getText()  # func name
        if function_name in self.functions:
            the_function = self.functions[function_name]

            length = ctx.getChildCount()
            parameter_list = []
            i = 2
            while i < length - 1:
                the_parameter = self.visit(ctx.getChild(i))
                the_parameter = self.assignConvert(the_parameter, the_function.args[i // 2 - 1].type)
                parameter_list.append(the_parameter['name'])
                i += 2
            return_variable_name = the_builder.call(the_function, parameter_list)
            result = {'type': the_function.function_type.return_type, 'name': return_variable_name}
            return result
        else:
            raise SemanticError(ctx=ctx, msg="函数未定义！")

    # 语句块相关函数
    def visitBlock(self, ctx: CCompilerParser.BlockContext):
        """
        语法规则：block : initialBlock | arrayInitBlock | structInitBlock
            | assignBlock | ifBlocks | whileBlock | forBlock | returnBlock;
        描述：语句块
        返回：无
        """
        for i in range(ctx.getChildCount()):
            self.visit(ctx.getChild(i))
        return

    def visitInitialBlock(self, ctx: CCompilerParser.InitialBlockContext):
        """
        语法规则：initialBlock : (mType) mID ('=' expr)? (',' mID ('=' expr)?)* ';';
        描述：初始化语句块
        返回：无
        """
        # 初始化全局变量
        parameter_type = self.visit(ctx.getChild(0))
        length = ctx.getChildCount()

        i = 1
        while i < length:
            ID_name = ctx.getChild(i).getText()
            if self.symbol_table.is_global():
                new_variable = ir.GlobalVariable(self.module, parameter_type, name=ID_name)
                new_variable.linkage = 'internal'
            else:
                the_builder = self.builders[-1]
                new_variable = the_builder.alloca(parameter_type, name=ID_name)
            the_variable = {"type": parameter_type, "name": new_variable}
            the_result = self.symbol_table.add_item(ID_name, the_variable)
            if the_result["result"] != "success":
                raise SemanticError(ctx=ctx, msg=the_result["reason"])

            if ctx.getChild(i + 1).getText() != '=':
                i += 2
            else:
                # 初始化
                value = self.visit(ctx.getChild(i + 2))
                if self.symbol_table.is_global():
                    # 全局变量
                    new_variable.initializer = ir.Constant(value['type'], value['name'].constant)
                    # print(value['name'].constant)
                else:
                    # 局部变量，可能有强制类型转换
                    value = self.assignConvert(value, parameter_type)
                    the_builder = self.builders[-1]
                    the_builder.store(value['name'], new_variable)
                i += 4
        return

    def visitArrayInitBlock(self, ctx: CCompilerParser.ArrayInitBlockContext):
        """
        语法规则：arrayInitBlock : mType mID '[' mINT ']'';';
        描述：数组初始化块
        返回：无
        """
        type = self.visit(ctx.getChild(0))
        ID_name = ctx.getChild(1).getText()
        length = int(ctx.getChild(3).getText())

        if self.symbol_table.is_global():
            # 全局变量
            new_variable = ir.GlobalVariable(self.module, ir.ArrayType(type, length), name=ID_name)
            new_variable.linkage = 'internal'
        else:
            the_builder = self.builders[-1]
            new_variable = the_builder.alloca(ir.ArrayType(type, length), name=ID_name)

        the_variable = {"type": ir.ArrayType(type, length), "name": new_variable}
        the_result = self.symbol_table.add_item(ID_name, the_variable)
        if the_result["result"] != "success":
            raise SemanticError(ctx=ctx, msg=the_result["reason"])
        return

    def visitAssignBlock(self, ctx: CCompilerParser.AssignBlockContext):
        """
        语法规则：assignBlock : ((arrayItem|mID|structMember) '=')+  expr ';';
        描述：赋值语句块
        返回：无
        """
        the_builder = self.builders[-1]
        length = ctx.getChildCount()
        ID_name = ctx.getChild(0).getText()
        if ('[' not in ID_name) and not self.symbol_table.exist(ID_name):
            raise SemanticError(ctx=ctx, msg="变量未定义！")

        # 待赋值结果
        value_to_be_assigned = self.visit(ctx.getChild(length - 2))

        i = 0
        result = {'type': value_to_be_assigned['type'], 'name': value_to_be_assigned['name']}
        # 遍历全部左边变量赋值
        while i < length - 2:
            previous_need_load = self.whether_need_load
            self.whether_need_load = False
            the_variable = self.visit(ctx.getChild(i))
            self.whether_need_load = previous_need_load

            the_value_to_be_assigned = value_to_be_assigned
            the_value_to_be_assigned = self.assignConvert(the_value_to_be_assigned, the_variable['type'])
            the_builder.store(the_value_to_be_assigned['name'], the_variable['name'])
            if i > 0:
                ReturnVariable = the_builder.load(the_variable['name'])
                result = {'type': the_variable['type'], 'name': ReturnVariable}
            i += 2
        return result

    # TODO
    def visitCondition(self, ctx: CCompilerParser.ConditionContext):
        """
        语法规则：condition :  expr;
        描述：判断条件
        返回：无
        """
        result = self.visit(ctx.getChild(0))
        return self.toBoolean(result, notFlag=False)

    def visitIfBlocks(self, ctx: CCompilerParser.IfBlocksContext):
        """
        语法规则：ifBlocks : ifBlock (elifBlock)* (elseBlock)?;
        描述：if语句块
        返回：无
        """
        # 增加两个block，对应If分支和If结束后的分支
        the_builder = self.builders[-1]
        if_block = the_builder.append_basic_block()
        endif_block = the_builder.append_basic_block()
        the_builder.branch(if_block)

        # 载入IfBlock
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(if_block)
        self.builders.append(ir.IRBuilder(if_block))

        tmp = self.endif_block
        self.endif_block = endif_block
        length = ctx.getChildCount()
        for i in range(length):
            self.visit(ctx.getChild(i))  # 分别处理每个if ,elseif, else块
        self.endif_block = tmp

        # 结束后导向EndIf块
        blockTemp = self.blocks.pop()
        builderTemp = self.builders.pop()
        if not blockTemp.is_terminated:
            builderTemp.branch(endif_block)

        self.blocks.append(endif_block)
        self.builders.append(ir.IRBuilder(endif_block))
        return

    def visitIfBlock(self, ctx: CCompilerParser.IfBlockContext):
        """
        语法规则：ifBlock : 'if' '(' condition ')' '{' body '}';
        描述：单一if语句块
        返回：无
        """
        # 在If块中，有True和False两种可能的导向
        self.symbol_table.enter_scope()
        the_builder = self.builders[-1]
        true_block = the_builder.append_basic_block()
        false_block = the_builder.append_basic_block()

        # 根据condition结果转向某个代码块
        result = self.visit(ctx.getChild(2))
        the_builder.cbranch(result['name'], true_block, false_block)

        # 如果condition为真，处理TrueBlock,即body部分
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(true_block)
        self.builders.append(ir.IRBuilder(true_block))
        self.visit(ctx.getChild(5))  # body

        if not self.blocks[-1].is_terminated:
            self.builders[-1].branch(self.endif_block)

        # 处理condition为假的代码部分
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(false_block)
        self.builders.append(ir.IRBuilder(false_block))
        self.symbol_table.quit_scope()
        return

    def visitElifBlock(self, ctx: CCompilerParser.ElifBlockContext):
        """
        语法规则：elifBlock : 'else' 'if' '(' condition ')' '{' body '}';
        描述：单一elseif语句块
        返回：无
        """
        # 在ElseIf块中，有True和False两种可能的导向
        self.symbol_table.enter_scope()
        the_builder = self.builders[-1]
        true_block = the_builder.append_basic_block()
        false_block = the_builder.append_basic_block()

        # 根据condition结果转向某个代码块
        result = self.visit(ctx.getChild(3))
        the_builder.cbranch(result['name'], true_block, false_block)

        # 如果condition为真，处理TrueBlock,即body部分
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(true_block)
        self.builders.append(ir.IRBuilder(true_block))
        self.visit(ctx.getChild(6))  # body

        if not self.blocks[-1].is_terminated:
            self.builders[-1].branch(self.endif_block)

        # 处理condition为假的代码部分
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(false_block)
        self.builders.append(ir.IRBuilder(false_block))
        self.symbol_table.quit_scope()
        return

    def visitElseBlock(self, ctx: CCompilerParser.ElseBlockContext):
        """
        语法规则：elseBlock : 'else' '{' body '}';
        描述：单一else语句块
        返回：无
        """
        # Else分块直接处理body内容
        self.symbol_table.enter_scope()
        self.visit(ctx.getChild(2))  # body
        self.symbol_table.quit_scope()
        return

    def visitWhileBlock(self, ctx: CCompilerParser.WhileBlockContext):
        """
        语法规则：whileBlock : 'while' '(' condition ')' '{' body '}';
        描述：while语句块
        返回：无
        """
        self.symbol_table.enter_scope()
        the_builder = self.builders[-1]
        # while语句分为三个分块
        while_condition = the_builder.append_basic_block()
        while_body = the_builder.append_basic_block()
        while_end = the_builder.append_basic_block()

        # 首先执行Condition分块
        the_builder.branch(while_condition)
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(while_condition)
        self.builders.append(ir.IRBuilder(while_condition))

        # 根据condition结果决定执行body还是结束while循环
        result = self.visit(ctx.getChild(2))  # condition
        self.builders[-1].cbranch(result['name'], while_body, while_end)

        # 执行body
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(while_body)
        self.builders.append(ir.IRBuilder(while_body))
        self.visit(ctx.getChild(5))  # body

        # 执行body后重新判断condition
        self.builders[-1].branch(while_condition)

        # 结束while循环
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(while_end)
        self.builders.append(ir.IRBuilder(while_end))
        self.symbol_table.quit_scope()
        return

    def visitForBlock(self, ctx: CCompilerParser.ForBlockContext):
        """
        语法规则：forBlock : 'for' '(' for1Block  ';' condition ';' for3Block ')' ('{' body '}'|';');
        描述：for语句块
        返回：无
        """
        self.symbol_table.enter_scope()

        # for循环首先初始化局部变量
        self.visit(ctx.getChild(2))
        # for循环的三种block
        the_builder = self.builders[-1]
        for_condition = the_builder.append_basic_block()
        for_body = the_builder.append_basic_block()
        for_end = the_builder.append_basic_block()

        # 判断condition
        the_builder.branch(for_condition)
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(for_condition)
        self.builders.append(ir.IRBuilder(for_condition))

        # 根据condition结果决定跳转到body或者结束
        result = self.visit(ctx.getChild(4))  # condition block
        self.builders[-1].cbranch(result['name'], for_body, for_end)
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(for_body)
        self.builders.append(ir.IRBuilder(for_body))

        # 处理body
        if ctx.getChildCount() == 11:
            self.visit(ctx.getChild(9))  # main body

        # 处理step语句
        self.visit(ctx.getChild(6))  # step block

        # 一次循环后重新判断condition
        self.builders[-1].branch(for_condition)

        # 结束循环
        self.blocks.pop()
        self.builders.pop()
        self.blocks.append(for_end)
        self.builders.append(ir.IRBuilder(for_end))
        self.symbol_table.quit_scope()
        return

    def visitFor1Block(self, ctx: CCompilerParser.For1BlockContext):
        """
        语法规则：for1Block :  mID '=' expr (',' for1Block)?|;
        描述：for语句块的第一个参数
        返回：无
        """
        # 初始化参数为空
        length = ctx.getChildCount()
        if length == 0:
            return

        tmp_need_load = self.whether_need_load
        self.whether_need_load = False
        result0 = self.visit(ctx.getChild(0))  # mID
        self.whether_need_load = tmp_need_load

        # 访问表达式
        result1 = self.visit(ctx.getChild(2))  # expr
        result1 = self.assignConvert(result1, result0['type'])
        self.builders[-1].store(result1['name'], result0['name'])

        if length > 3:
            self.visit(ctx.getChild(4))
        return

    def visitFor3Block(self, ctx: CCompilerParser.For3BlockContext):
        """
        语法规则：for3Block : mID '=' expr (',' for3Block)?|;
        描述：for语句块的第三个参数
        返回：无
        """
        length = ctx.getChildCount()
        if length == 0:
            return

        tmp_need_load = self.whether_need_load
        self.whether_need_load = False
        result0 = self.visit(ctx.getChild(0))
        self.whether_need_load = tmp_need_load

        result1 = self.visit(ctx.getChild(2))
        result1 = self.assignConvert(result1, result0['type'])
        self.builders[-1].store(result1['name'], result0['name'])

        if length > 3:
            self.visit(ctx.getChild(4))
        return

    def visitReturnBlock(self, ctx: CCompilerParser.ReturnBlockContext):
        """
        语法规则：returnBlock : 'return' (mINT|mID)? ';';
        描述：return语句块
        返回：无
        """
        # 返回空
        if ctx.getChildCount() == 2:
            real_return_value = self.builders[-1].ret_void()
            judge_truth = False
            return {
                'type': void,
                'const': judge_truth,
                'name': real_return_value
            }

        # 访问返回值
        return_index = self.visit(ctx.getChild(1))
        real_return_value = self.builders[-1].ret(return_index['name'])
        judge_truth = False
        return {
            'type': void,
            'const': judge_truth,
            'name': real_return_value
        }

    # 运算和表达式求值，类型转换相关函数
    def assignConvert(self, calc_index, DType):
        if calc_index['type'] == DType:
            return calc_index
        if self.isInteger(calc_index['type']) and self.isInteger(DType):
            if calc_index['type'] == int1:
                calc_index = self.convertIIZ(calc_index, DType)
            else:
                calc_index = self.convertIIS(calc_index, DType)
        elif self.isInteger(calc_index['type']) and DType == double:
            calc_index = self.convertIDS(calc_index)
        elif self.isInteger(DType) and calc_index['type'] == double:
            calc_index = self.convertDIS(calc_index)
        return calc_index

    def convertIIZ(self, calc_index, DType):
        builder = self.builders[-1]
        confirmed_val = builder.zext(calc_index['name'], DType)
        is_constant = False
        return {
            'type': DType,
            'const': is_constant,
            'name': confirmed_val
        }

    def convertIIS(self, calc_index, DType):
        builder = self.builders[-1]
        confirmed_val = builder.sext(calc_index['name'], DType)
        is_constant = False
        return {
            'type': DType,
            'const': is_constant,
            'name': confirmed_val
        }

    def convertDIS(self, calc_index, DType):
        builder = self.builders[-1]
        confirmed_val = builder.fptosi(calc_index['name'], DType)
        is_constant = False
        return {
            'type': DType,
            'const': is_constant,
            'name': confirmed_val
        }

    def convertDIU(self, calc_index, DType):
        builder = self.builders[-1]
        confirmed_val = builder.fptoui(calc_index['name'], DType)
        is_constant = False
        return {
            'type': DType,
            'const': is_constant,
            'name': confirmed_val
        }

    def convertIDS(self, calc_index):
        builder = self.builders[-1]
        confirmed_val = builder.sitofp(calc_index['name'], double)
        is_constant = False
        return {
            'type': double,
            'const': is_constant,
            'name': confirmed_val
        }

    def convertIDU(self, calc_index):
        builder = self.builders[-1]
        is_constant = False
        confirmed_val = builder.uitofp(calc_index['name'], double)
        return {
            'type': double,
            'const': is_constant,
            'name': confirmed_val
        }

    # 类型转换至布尔型
    def toBoolean(self, manipulate_index, notFlag=True):
        builder = self.builders[-1]
        if notFlag:
            operation_char = '=='
        else:
            operation_char = '!='
        if manipulate_index['type'] == int8 or manipulate_index['type'] == int32:
            real_return_value = builder.icmp_signed(operation_char, manipulate_index['name'],
                                                  ir.Constant(manipulate_index['type'], 0))
            return {
                'tpye': int1,
                'const': False,
                'name': real_return_value
            }
        elif manipulate_index['type'] == double:
            real_return_value = builder.fcmp_ordered(operation_char, manipulate_index['name'], ir.Constant(double, 0))
            return {
                'tpye': int1,
                'const': False,
                'name': real_return_value
            }
        return manipulate_index

    def visitNeg(self, ctx: CCompilerParser.NegContext):
        """
        语法规则：expr :  op='!' expr
        描述：非运算
        返回：无
        """
        real_return_value = self.visit(ctx.getChild(1))
        real_return_value = self.toBoolean(real_return_value, notFlag=True)
        # res 未返回
        return self.visitChildren(ctx)

    def visitOR(self, ctx: CCompilerParser.ORContext):
        """
        语法规则：expr : expr '||' expr
        描述：或运算
        返回：无
        """
        index1 = self.visit(ctx.getChild(0))
        index1 = self.toBoolean(index1, notFlag=False)
        index2 = self.visit(ctx.getChild(2))
        index2 = self.toBoolean(index2, notFlag=False)
        builder = self.builders[-1]
        real_return_value = builder.or_(index1['name'], index2['name'])
        return {
            'type': index1['type'],
            'const': False,
            'name': real_return_value
        }

    def visitAND(self, ctx: CCompilerParser.ANDContext):
        """
        语法规则：expr : expr '&&' expr
        描述：且运算
        返回：无
        """
        index1 = self.visit(ctx.getChild(0))
        index1 = self.toBoolean(index1, notFlag=False)
        index2 = self.visit(ctx.getChild(2))
        index2 = self.toBoolean(index2, notFlag=False)
        builder = self.builders[-1]
        is_constant = False
        real_return_value = builder.and_(index1['name'], index2['name'])
        return {
            'type': index1['type'],
            'const': is_constant,
            'name': real_return_value
        }

    def visitIdentifier(self, ctx: CCompilerParser.IdentifierContext):
        """
        语法规则：expr : mID
        描述：常数
        返回：无
        """
        return self.visit(ctx.getChild(0))

    def visitParens(self, ctx: CCompilerParser.ParensContext):
        """
        语法规则：expr : '(' expr ')'
        描述：括号
        返回：无
        """
        return self.visit(ctx.getChild(1))

    def visitArrayitem(self, ctx: CCompilerParser.ArrayitemContext):
        """
        语法规则：expr : arrayItem
        描述：数组元素
        返回：无
        """
        return self.visit(ctx.getChild(0))

    def visitString(self, ctx: CCompilerParser.StringContext):
        """
        语法规则：expr : mSTRING
        描述：字符串
        返回：无
        """
        return self.visit(ctx.getChild(0))

    def isInteger(self, typ):
        return_value = 'width'
        return hasattr(typ, return_value)

    def exprConvert(self, index1, index2):
        if index1['type'] == index2['type']:
            return index1, index2
        if self.isInteger(index1['type']) and self.isInteger(index2['type']):
            if index1['type'].width < index2['type'].width:
                if index1['type'].width == 1:
                    index1 = self.convertIIZ(index1, index2['type'])
                else:
                    index1 = self.convertIIS(index1, index2['type'])
            else:
                if index2['type'].width == 1:
                    index2 = self.convertIIZ(index2, index1['type'])
                else:
                    index2 = self.convertIIS(index2, index1['type'])
        elif self.isInteger(index1['type']) and index2['type'] == double:
            # index1 = convertIDS(index1, index2['type'])
            index1 = self.convertIDS(index1)
        elif self.isInteger(index2['type']) and index1['type'] == double:
            # index2 = convertIDS(index2, index1['type'])
            index2 = self.convertIDS(index2)
        else:
            raise SemanticError(msg="类型不匹配")
        return index1, index2

    def visitMulDiv(self, ctx: CCompilerParser.MulDivContext):
        """
        语法规则：expr : expr op=('*' | '/' | '%') expr
        描述：乘除
        返回：无
        """
        builder = self.builders[-1]
        index1 = self.visit(ctx.getChild(0))
        index2 = self.visit(ctx.getChild(2))
        index1, index2 = self.exprConvert(index1, index2)
        is_constant = False
        if ctx.getChild(1).getText() == '*':
            real_return_value = builder.mul(index1['name'], index2['name'])
        elif ctx.getChild(1).getText() == '/':
            real_return_value = builder.sdiv(index1['name'], index2['name'])
        elif ctx.getChild(1).getText() == '%':
            real_return_value = builder.srem(index1['name'], index2['name'])
        return {
            'type': index1['type'],
            'const': is_constant,
            'name': real_return_value
        }

    def visitAddSub(self, ctx: CCompilerParser.AddSubContext):
        """
        语法规则：expr op=('+' | '-') expr
        描述：加减
        返回：无
        """
        builder = self.builders[-1]
        index1 = self.visit(ctx.getChild(0))
        index2 = self.visit(ctx.getChild(2))
        index1, index2 = self.exprConvert(index1, index2)
        is_constant = False
        if ctx.getChild(1).getText() == '+':
            real_return_value = builder.add(index1['name'], index2['name'])
        elif ctx.getChild(1).getText() == '-':
            real_return_value = builder.sub(index1['name'], index2['name'])
        return {
            'type': index1['type'],
            'const': is_constant,
            'name': real_return_value
        }

    def visitDouble(self, ctx: CCompilerParser.DoubleContext):
        """
        语法规则：expr : (op='-')? mDOUBLE
        描述：double类型
        返回：无
        """
        if ctx.getChild(0).getText() == '-':
            IndexMid = self.visit(ctx.getChild(1))
            builder = self.builders[-1]
            real_return_value = builder.neg(IndexMid['name'])
            return {
                'type': IndexMid['type'],
                'name': real_return_value
            }
        return self.visit(ctx.getChild(0))

    def visitFunction(self, ctx: CCompilerParser.FunctionContext):
        """
        语法规则：expr : func
        描述：函数类型
        返回：无
        """
        return self.visit(ctx.getChild(0))

    def visitChar(self, ctx: CCompilerParser.CharContext):
        """
        语法规则：expr : mCHAR
        描述：字符类型
        返回：无
        """
        return self.visit(ctx.getChild(0))

    def visitInt(self, ctx: CCompilerParser.IntContext):
        """
        语法规则：(op='-')? mINT
        描述：int类型
        返回：无
        """
        if ctx.getChild(0).getText() == '-':
            IndexMid = self.visit(ctx.getChild(1))
            builder = self.builders[-1]
            real_return_value = builder.neg(IndexMid['name'])
            return {
                'type': IndexMid['type'],
                'name': real_return_value
            }
        return self.visit(ctx.getChild(0))

    def visitMVoid(self, ctx: CCompilerParser.MVoidContext):
        """
        语法规则：mVoid : 'void';
        描述：void类型
        返回：无
        """
        return void

    def visitMArray(self, ctx: CCompilerParser.MArrayContext):
        """
        语法规则：mArray : mID '[' mINT ']';
        描述：数组类型
        返回：无
        """
        return {
            'ID_name': ctx.getChild(0).getText(),
            'length': int(ctx.getChild(2).getText())
        }

    def visitJudge(self, ctx: CCompilerParser.JudgeContext):
        """
        语法规则：expr : expr op=('==' | '!=' | '<' | '<=' | '>' | '>=') expr
        描述：比较
        返回：无
        """
        builder = self.builders[-1]
        index1 = self.visit(ctx.getChild(0))
        index2 = self.visit(ctx.getChild(2))
        index1, index2 = self.exprConvert(index1, index2)
        operation_char = ctx.getChild(1).getText()
        is_constant = False
        if index1['type'] == double:
            real_return_value = builder.fcmp_ordered(operation_char, index1['name'], index2['name'])
        elif self.isInteger(index1['type']):
            real_return_value = builder.icmp_signed(operation_char, index1['name'], index2['name'])
        return {
            'type': int1,
            'const': is_constant,
            'name': real_return_value
        }

    # 变量和变量类型相关函数
    def visitMType(self, ctx: CCompilerParser.MTypeContext) -> ir.Type:
        """
        类型主函数.

        语法规则：
            mType : 'int'| 'double'| 'char'| 'string';

        Args:
            ctx (CCompilerParser.MTypeContext):

        Returns:
            ir.Type: 变量类型
        """
        # TODO: 为什么会有 string 类型返回，而且此处未实现？
        if ctx.getText() == 'int':
            return int32
        if ctx.getText() == 'char':
            return int8
        if ctx.getText() == 'double':
            return double
        return void

    def visitArrayItem(self, ctx: CCompilerParser.ArrayItemContext):
        """
        语法规则：expr : arrayItem
        描述：数组元素
        返回：无
        """
        temp_require_load = self.whether_need_load
        self.whether_need_load = False
        res = self.visit(ctx.getChild(0))  # mID
        # print("res is", res)
        is_constant = False
        self.whether_need_load = temp_require_load

        if isinstance(res['type'], ir.types.ArrayType):
            builder = self.builders[-1]

            temp_require_load = self.whether_need_load
            self.whether_need_load = True
            index_re1 = self.visit(ctx.getChild(2))  # subscript
            self.whether_need_load = temp_require_load

            int32_zero = ir.Constant(int32, 0)
            real_return_value = builder.gep(res['name'], [int32_zero, index_re1['name']], inbounds=True)
            if self.whether_need_load:
                real_return_value = builder.load(real_return_value)
            return {
                'type': res['type'].element,
                'const': is_constant,
                'name': real_return_value,
                'struct_name': res['struct_name'] if 'struct_name' in res else None
            }
        else:  # error!
            raise SemanticError(ctx=ctx, msg="类型错误")

    def visitArgument(self, ctx: CCompilerParser.ArgumentContext):
        """
        语法规则：argument : mINT | mDOUBLE | mCHAR | mSTRING;
        描述：函数参数
        返回：无
        """
        return self.visit(ctx.getChild(0))

    def visitMStruct(self, ctx: CCompilerParser.MStructContext) -> Dict[str, Union[List[str], ir.LiteralStructType]]:
        """
        结构体类型变量的使用.

        语法规则：
            mStruct : 'struct' mID;

        Args:
            ctx (CCompilerParser.MStructContext):

        Returns:
             Dict[str, Union[List[str], ir.LiteralStructType]]:
                {"Members": member_list, "Type": ir.LiteralStructType(type_list)}
        """
        return self.structure.list[ctx.getChild(1).getText()]

    def visitMID(self, ctx: CCompilerParser.MIDContext):
        """
        ID 处理.

        语法规则：
            mID : ID;

        Args:
            ctx (CCompilerParser.MIDContext):

        Returns:

        """
        ID_name = ctx.getText()
        is_constant = False
        if not self.symbol_table.exist(ID_name):
            return {
                'type': int32,
                'const': is_constant,
                'name': ir.Constant(int32, None)
            }
        builder = self.builders[-1]
        the_item = self.symbol_table.get_item(ID_name)
        # print(the_item)
        if the_item is not None:
            if self.whether_need_load:
                return_value = builder.load(the_item["name"])
                return {
                    "type": the_item["type"],
                    "const": is_constant,
                    "name": return_value,
                    "struct_name": the_item["struct_name"] if "struct_name" in the_item else None
                }
            else:
                return {
                    "type": the_item["type"],
                    "const": is_constant,
                    "name": the_item["name"],
                    "struct_name": the_item["struct_name"] if "struct_name" in the_item else None
                }
        else:
            return {
                'type': void,
                'const': is_constant,
                'name': ir.Constant(void, None)
            }

    def visitMINT(self, ctx: CCompilerParser.MINTContext):
        """
        int 类型处理.

        语法规则：
            mINT : INT;

        Args:
            ctx (CCompilerParser.MINTContext):

        Returns:

        """
        is_constant = True
        return {
            'type': int32,
            'const': is_constant,
            'name': ir.Constant(int32, int(ctx.getText()))
        }

    def visitMDOUBLE(self, ctx: CCompilerParser.MDOUBLEContext):
        """
        double 类型处理.

        语法规则：
            mDOUBLE : DOUBLE;

        Args:
            ctx (CCompilerParser.MDOUBLEContext):

        Returns:

        """
        is_constant = True
        return {
            'type': double,
            'const': is_constant,
            'name': ir.Constant(double, float(ctx.getText()))
        }

    def visitMCHAR(self, ctx: CCompilerParser.MCHARContext):
        """
        char 类型处理.

        语法规则：
            mCHAR : CHAR;

        Args:
            ctx (CCompilerParser.MCHARContext):

        Returns:

        """
        is_constant = True
        return {
            'type': int8,
            'const': is_constant,
            'name': ir.Constant(int8, ord(ctx.getText()[1]))
        }

    def visitMSTRING(self, ctx: CCompilerParser.MSTRINGContext):
        """
        string 类型处理.

        语法规则：
            mSTRING : STRING;

        Args:
            ctx (CCompilerParser.MSTRINGContext):

        Returns:

        """
        mark_index = self.constants
        self.constants += 1
        process_index = ctx.getText().replace('\\n', '\n')
        process_index = process_index[1:-1]
        process_index += '\0'
        length = len(bytearray(process_index, 'utf-8'))
        is_constant = False
        real_return_value = ir.GlobalVariable(self.module, ir.ArrayType(int8, length), ".str%d" % mark_index)
        real_return_value.global_constant = True
        real_return_value.initializer = ir.Constant(ir.ArrayType(int8, length), bytearray(process_index, 'utf-8'))
        return {
            'type': ir.ArrayType(int8, length),
            'const': is_constant,
            'name': real_return_value
        }

    def save(self, filename: str) -> None:
        """
        保存分析结果到文件.

        Args:
            filename (str): 文件名含后缀

        Returns:
            None
        """
        with open(filename, "w") as f:
            f.write(repr(self.module))


def generate(input_filename: str, output_filename: str):
    """
    将C代码文件转成IR代码文件
    :param input_filename: C代码文件
    :param output_filename: IR代码文件
    :return: 生成是否成功
    """
    lexer = CCompilerLexer(FileStream(input_filename))
    stream = CommonTokenStream(lexer)
    parser = CCompilerParser(stream)
    parser.removeErrorListeners()
    errorListener = SyntaxErrorListener()
    parser.addErrorListener(errorListener)

    tree = parser.prog()
    v = Visitor()
    v.visit(tree)
    v.save(output_filename)

# del CCompilerParser
