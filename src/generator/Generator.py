from antlr4 import *
from llvmlite import ir

import re
from typing import Dict, List, Union, Optional, Tuple, Any

from generator.ErrorListener import SemanticError
from generator.ErrorListener import SyntaxErrorListener
from generator.SymbolTable import SymbolTable, Structure, TypedValue, const_value, ParameterList, DeclarationSpecifiers
from cparser.CCompilerLexer import CCompilerLexer
from cparser.CCompilerParser import CCompilerParser
from cparser.CCompilerVisitor import CCompilerVisitor
from generator.parser_util import Result

double = ir.DoubleType()
int1 = ir.IntType(1)
int32 = ir.IntType(32)
int8 = ir.IntType(8)
void = ir.VoidType()

int32_zero = ir.Constant(int32, 0)


class Visitor(CCompilerVisitor):
    """
    生成器类，用于进行语义分析并且转化为LLVM
    """

    def __init__(self):
        super(CCompilerVisitor, self).__init__()

        # 控制llvm生成
        self.module: ir.Module = ir.Module()
        self.module.triple = 'x86_64-pc-linux-gnu'  # llvm.Target.from_default_triple()
        # llvm.create_mcjit_compiler(backing_mod, target_machine)
        self.module.data_layout = 'e-m:e-i64:64-f80:128-n8:16:32:64-S128'

        # 语句块
        self.blocks: List[ir.Block] = []

        # 待生成的 llvm 语句块
        self.builders: List[ir.IRBuilder] = []

        # 函数列表 Dict[名称, 是否有定义]
        self.functions: Dict[str, ir.Function] = dict()

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

        # 字符串常量表
        self.string_constants: Dict[str, TypedValue] = {}

    # Old code {{{
    #
    # def visitProg(self, ctx: CCompilerParser.ProgContext) -> None:
    #     """
    #     代码主文件.
    #
    #     语法规则：
    #         prog :(include)* (initialBlock | arrayInitBlock | structInitBlock | mStructDef| mFunction)*;
    #
    #     Args:
    #         ctx (CCompilerParser.ProgContext):
    #
    #     Returns:
    #         None
    #     """
    #     for i in range(ctx.getChildCount()):
    #         self.visit(ctx.getChild(i))
    #
    # # 结构体相关函数
    # def visitMStructDef(self, ctx: CCompilerParser.MStructContext) -> None:
    #     """
    #     结构体定义.
    #
    #     语法规则：
    #         mStructDef : mStruct '{' (structParam)+ '}' ';';
    #
    #     Args:
    #         ctx (CCompilerParser.MStructContext):
    #
    #     Returns:
    #         None
    #     """
    #     new_struct_name: str = ctx.getChild(0).getChild(1).getText()
    #
    #     # 遍历结构体的变量，并且存储
    #     i = 2
    #     parameter_type_list = []
    #     parameter_name_list = []
    #     total_params = ctx.getChildCount() - 2
    #     # 逐行读取并且存储
    #     while i < total_params:
    #         parameter_type_line, parameter_name_line = self.visit(ctx.getChild(i))
    #         parameter_type_list = parameter_type_list + parameter_type_line
    #         parameter_name_list = parameter_name_list + parameter_name_line
    #         i += 1
    #
    #     # 存储结构体
    #     result = self.structure.add_item(new_struct_name, parameter_name_list, parameter_type_list)
    #     if result['status'] != 'success':
    #         raise SemanticError(ctx=ctx, msg=result['reason'])
    #
    # def visitStructParam(self, ctx: CCompilerParser.StructParamContext):
    #     """
    #     处理一行结构体参数.
    #
    #     语法规则：
    #         structParam : (mType | mStruct) (mID | mArray) (',' (mID | mArray))* ';';
    #
    #     Args:
    #         ctx (CCompilerParser.StructParamContext):
    #
    #     Returns:
    #         None
    #     """
    #     parameter_type_line = []
    #     parameter_name_line = []
    #     # TODO: 此处只支持非 struct 的变量类型
    #     # 必须有类型
    #     if ctx.getChild(0).getChildCount() == 1:
    #         i = 1
    #         parameter_type = self.visit(ctx.getChild(0))
    #         length = ctx.getChildCount()
    #         while i < length:
    #             # 处理MID的情况（单一变量）
    #             if ctx.getChild(i).getChildCount() == 1:
    #                 parameter_name_line.append(ctx.getChild(i).getText())
    #                 parameter_type_line.append(parameter_type)
    #             # 处理mArray的情况（数组）
    #             else:
    #                 array_info = self.visit(ctx.getChild(i))
    #                 parameter_name_line.append(array_info['id_name'])
    #                 parameter_type_line.append(ir.ArrayType(parameter_type, array_info['length']))
    #             i = i + 2
    #         return parameter_type_line, parameter_name_line
    #
    # def visitStructInitBlock(self, ctx: CCompilerParser.StructInitBlockContext):
    #     """
    #     结构体初始化
    #
    #     语法规则：
    #         structInitBlock : mStruct (mID|mArray)';';
    #
    #     Args:
    #         ctx (CCompilerParser.StructParamContext):
    #
    #     Returns:
    #         None
    #     """
    #     variable_info = self.visit(ctx.getChild(0))
    #     variable_type = variable_info['type']
    #     struct_name = ctx.getChild(0).getChild(1).getText()
    #
    #     # 处理结构体变量是单一变量的情况
    #     if ctx.getChild(1).getChildCount() == 1:
    #         id_name = ctx.getChild(1).getText()
    #         current_type = variable_type
    #         # 全局变量
    #         if self.symbol_table.is_global():
    #             new_variable = ir.GlobalVariable(self.module, variable_type, name=id_name)
    #             new_variable.linkage = 'internal'
    #             new_variable.initializer = ir.Constant(current_type, None)
    #         # 局部变量
    #         else:
    #             the_builder = self.builders[-1]
    #             new_variable = the_builder.alloca(current_type, name=id_name)
    #
    #     # 处理结构体变量是数组的情况
    #     else:
    #         variable_info = self.visit(ctx.getChild(1))
    #         id_name = variable_info['id_name']
    #         current_type = ir.ArrayType(variable_type, variable_info['length'])
    #         # 全局变量
    #         if self.symbol_table.is_global():
    #             new_variable = ir.GlobalVariable(self.module, current_type, name=id_name)
    #             new_variable.linkage = 'internal'
    #             new_variable.initializer = ir.Constant(current_type, None)
    #         else:
    #             the_builder = self.builders[-1]
    #             new_variable = the_builder.alloca(current_type, name=id_name)
    #
    #     # 存储这个结构体变量
    #     the_variable = {'struct_name': struct_name, 'type': current_type, 'name': new_variable}
    #     result = self.symbol_table.add_item(id_name, the_variable)
    #     if result['status'] != 'success':
    #         raise SemanticError(ctx=ctx, msg=result['reason'])
    #     return
    #
    # def visitStructMember(self, ctx: CCompilerParser.StructMemberContext) -> Dict[str, Union[Optional[str], Any]]:
    #     """
    #     获取结构体成员变量信息.
    #
    #     语法规则：
    #         structMember: (mID | arrayItem)'.'(mID | arrayItem);
    #
    #     Args:
    #         ctx (CCompilerParser.StructMemberContext):
    #
    #     Returns:
    #         Dict[str, Union[Optional[str], Any]]
    #     """
    #     the_builder = self.builders[-1]
    #     # 处理成员元素是单一变量的情况，TODO g4修改后删除
    #     if ctx.getChild(2).getChildCount() == 1:  # mID
    #         current_need_load = self.whether_need_load
    #         self.whether_need_load = False
    #         struct_info = self.visit(ctx.getChild(0))
    #         self.whether_need_load = current_need_load
    #
    #         # 读取结构体信息
    #         struct_name = struct_info['struct_name']
    #         father_name = struct_info['name']
    #         index = self.structure.get_member_index(struct_name, ctx.getChild(2).getText())
    #         if index is None:
    #             raise SemanticError(ctx=ctx, msg='未找到这个变量')
    #         type = self.structure.get_member_type(struct_name, ctx.getChild(2).getText())
    #
    #         zero = ir.Constant(int32, 0)
    #         idx = ir.Constant(int32, index)
    #         new_variable = the_builder.gep(father_name, [zero, idx], inbounds=True)
    #
    #         if self.whether_need_load:
    #             new_variable = the_builder.load(new_variable)
    #
    #         result = {'type': type, 'name': new_variable}
    #         return result
    #     else:
    #         raise NotImplementedError()
    #
    # # 函数相关函数
    # def visitMFunctionType(self, ctx: CCompilerParser.MFunctionTypeContext) \
    #         -> Tuple[ir.FunctionType, str, List[Dict[str, Union[str, ir.Type]]]]:
    #     """
    #     函数的类型.
    #
    #     语法规则:
    #         mFunctionType: (mType | mVoid | mStruct) mID '(' params ')';
    #
    #     Args:
    #         ctx (CCompilerParser.MFunctionTypeContext):
    #
    #     Returns:
    #         Tuple
    #          - ir.FunctionType 函数类型
    #          - str 函数名
    #          - List 函数参数
    #     """
    #     children_count = ctx.getChildCount()
    #
    #     # 获取返回值类型
    #     return_type = self.visit(ctx.getChild(0))  # mtype
    #
    #     # 获取函数名
    #     function_name = ctx.getChild(1).getText()  # func name
    #
    #     # 获取参数列表
    #     parameter_list, varargs = self.visit(ctx.getChild(3))  # func params
    #
    #     # 根据返回值，函数名称和参数生成 llvm 函数
    #     parameter_type_list = []
    #     for i in range(len(parameter_list)):
    #         parameter_type_list.append(parameter_list[i]['type'])
    #     llvm_function_type = ir.FunctionType(return_type, parameter_type_list, var_arg=varargs)
    #     return llvm_function_type, function_name, parameter_list
    #
    # def visitMFunctionDeclaration(self, ctx: CCompilerParser.MFunctionDeclarationContext) -> None:
    #     """
    #     函数的声明.
    #
    #     语法规则:
    #         mFunctionDeclaration : mFunctionType ';';
    #
    #     Args:
    #         ctx (CCompilerParser.MFunctionDeclarationContext):
    #
    #     Returns:
    #         None
    #     """
    #     function_type: ir.FunctionType
    #     function_name: str
    #     parameter_list: List[Dict[str, Union[str, ir.Type]]]
    #     function_type, function_name, parameter_list = self.visit(ctx.getChild(0))
    #     # 存入符号表
    #     if function_name in self.functions:
    #         llvm_function = self.functions[function_name]
    #         if llvm_function.function_type != function_type:
    #             raise SemanticError(ctx=ctx, msg='函数类型与先前的定义冲突: ' + function_name)
    #     else:
    #         self.functions[function_name] = ir.Function(self.module, function_type, name=function_name)
    #
    # def visitMFunctionDefinition(self, ctx: CCompilerParser.MFunctionDefinitionContext) -> None:
    #     """
    #     函数的定义.
    #
    #     语法规则:
    #         mFunctionDefinition : mFunctionType '{' funcBody '}';
    #
    #     Args:
    #         ctx (CCompilerParser.MFunctionDefinitionContext):
    #
    #     Returns:
    #         None
    #     """
    #     function_type: ir.FunctionType
    #     function_name: str
    #     parameter_list: List[Dict[str, Union[str, ir.Type]]]
    #     function_type, function_name, parameter_list = self.visit(ctx.getChild(0))
    #
    #     # 判断重定义，存储函数
    #     if function_name in self.functions:
    #         llvm_function = self.functions[function_name]
    #         if len(llvm_function.blocks) > 0:
    #             raise SemanticError(ctx=ctx, msg='函数重定义: ' + function_name)
    #     else:
    #         llvm_function = ir.Function(self.module, function_type, name=function_name)
    #
    #     # 函数的参数名
    #     for i in range(len(parameter_list)):
    #         llvm_function.args[i].name = parameter_list[i]['id_name']
    #
    #     # 函数 block
    #     the_block: ir.Block = llvm_function.append_basic_block(name=function_name + '.entry')
    #     self.functions[function_name] = llvm_function
    #
    #     ir_builder: ir.IRBuilder = ir.IRBuilder(the_block)
    #     self.blocks.append(the_block)
    #     self.builders.append(ir_builder)
    #
    #     # 进入函数作用域
    #     self.current_function = function_name
    #     self.symbol_table.enter_scope()
    #
    #     # 存储函数的变量
    #     for i in range(len(parameter_list)):
    #         func_arg = llvm_function.args[i]
    #         variable = ir_builder.alloca(func_arg.type)
    #         ir_builder.store(func_arg, variable)
    #         result = self.symbol_table.add_item(func_arg.name, {'type': func_arg.type, 'name': variable})
    #         if result['status'] != 'success':
    #             raise SemanticError(ctx=ctx, msg=result['reason'])
    #
    #     # 处理函数体
    #     self.visit(ctx.getChild(2))  # funcBody
    #
    #     # 处理完毕，退出函数作用域
    #     self.current_function = ''
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.symbol_table.quit_scope()
    #     return
    #
    # def visitParams(self, ctx: CCompilerParser.ParamsContext) -> Tuple[List[Dict[str, Union[ir.Type, str]]], bool]:
    #     """
    #     函数的参数列表.
    #
    #     语法规则：
    #         params : (param (','param)* |) ('...')?;
    #
    #     Args:
    #         ctx (CCompilerParser.ParamsContext):
    #
    #     Returns:
    #         List[Dict[str, Union[ir.Type, str]]]: 处理后的函数参数列表
    #         bool: 是否有 vararg
    #     """
    #     length = ctx.getChildCount()
    #     varargs = False
    #     if length == 0:
    #         return [], varargs
    #     if ctx.getChild(length - 1).getText() == '...':
    #         varargs = True
    #         length -= 1
    #     parameter_list: List[Dict[str, Union[ir.Type, str]]] = []
    #     i = 0
    #     while i < length:
    #         new_parameter: Dict[str, Union[ir.Type, str]] = self.visit(ctx.getChild(i))
    #         parameter_list.append(new_parameter)
    #         i += 2
    #     return parameter_list, varargs
    #
    # def visitNamedValue(self, ctx: CCompilerParser.NamedValueContext) -> Dict[str, Union[ir.Type, str]]:
    #     """
    #     返回具名值.
    #
    #     语法规则：
    #         namedValue : mType mID;
    #
    #     Args:
    #         ctx (CCompilerParser.NamedValueContext):
    #
    #     Returns:
    #         Dict[str, Union[ir.Type, str]]: 一个字典，字典的 type 是类型，name 是参数名
    #     """
    #     value_type = self.visit(ctx.getChild(0))
    #     id_name = ctx.getChild(1).getText()
    #     result = {'type': value_type, 'id_name': id_name}
    #     return result
    #
    # def visitParam(self, ctx: CCompilerParser.ParamContext) -> Dict[str, Union[ir.Type, str]]:
    #     """
    #     返回函数参数.
    #
    #     语法规则：
    #         param : namedValue;
    #
    #     Args:
    #         ctx (CCompilerParser.ParamContext):
    #
    #     Returns:
    #         Dict[str, Union[ir.Type, str]]: 一个字典，字典的 type 是类型，name 是参数名
    #     """
    #     return self.visit(ctx.getChild(0))
    #
    # def visitFuncBody(self, ctx: CCompilerParser.FuncBodyContext):
    #     """
    #     语法规则：funcBody : body returnBlock;
    #     描述：函数体
    #     返回：无
    #     """
    #     self.symbol_table.enter_scope()
    #     for index in range(ctx.getChildCount()):
    #         self.visit(ctx.getChild(index))
    #     self.symbol_table.quit_scope()
    #     return
    #
    # def visitBody(self, ctx: CCompilerParser.BodyContext):
    #     """
    #     语法规则：body : (block | func';')*;
    #     描述：语句块/函数块
    #     返回：无
    #     """
    #     for i in range(ctx.getChildCount()):
    #         self.visit(ctx.getChild(i))
    #         if self.blocks[-1].is_terminated:
    #             break
    #     return
    #
    # # 调用函数相关函数
    # def visitFunc(self, ctx: CCompilerParser.FuncContext):
    #     """
    #     语法规则：func : (strlenFunc | atoiFunc | printfFunc | scanfFunc | getsFunc | selfDefinedFunc);
    #     描述：函数
    #     返回：无
    #     """
    #     return self.visit(ctx.getChild(0))
    #
    # def visitStrlenFunc(self, ctx: CCompilerParser.StrlenFuncContext):
    #     """
    #     语法规则：strlenFunc : 'strlen' '(' mID ')';
    #     描述：strlen函数
    #     返回：函数返回值
    #     """
    #     if 'strlen' in self.functions:
    #         strlen = self.functions['strlen']
    #     else:
    #         strlenType = ir.FunctionType(int32, [ir.PointerType(int8)], var_arg=False)
    #         strlen = ir.Function(self.module, strlenType, name='strlen')
    #         self.functions['strlen'] = strlen
    #
    #     the_builder = self.builders[-1]
    #     zero = ir.Constant(int32, 0)
    #
    #     # 加载变量
    #     previous_need_load = self.whether_need_load
    #     self.whether_need_load = False
    #     res = self.visit(ctx.getChild(2))
    #     self.whether_need_load = previous_need_load
    #
    #     arguments = the_builder.gep(res['name'], [zero, zero], inbounds=True)
    #     return_variable_name = the_builder.call(strlen, [arguments])
    #
    #     result = {'type': int32, 'name': return_variable_name}
    #     return result
    #
    # def visitPrintfFunc(self, ctx: CCompilerParser.PrintfFuncContext):
    #     """
    #     语法规则：printfFunc : 'printf' '(' (mSTRING | mID) (','expr)* ')';
    #     描述：printf函数
    #     返回：函数返回值
    #     """
    #     if 'printf' in self.functions:
    #         printf = self.functions['printf']
    #     else:
    #         printfType = ir.FunctionType(int32, [ir.PointerType(int8)], var_arg=True)
    #         printf = ir.Function(self.module, printfType, name='printf')
    #         self.functions['printf'] = printf
    #
    #     the_builder = self.builders[-1]
    #     zero = ir.Constant(int32, 0)
    #
    #     # 就一个变量
    #     if ctx.getChildCount() == 4:
    #         parameter_info = self.visit(ctx.getChild(2))
    #         argument = the_builder.gep(parameter_info['name'], [zero, zero], inbounds=True)
    #         return_variable_name = the_builder.call(printf, [argument])
    #     else:
    #         parameter_info = self.visit(ctx.getChild(2))
    #         arguments = [the_builder.gep(parameter_info['name'], [zero, zero], inbounds=True)]
    #
    #         length = ctx.getChildCount()
    #         i = 4
    #         while i < length - 1:
    #             one_parameter = self.visit(ctx.getChild(i))
    #             arguments.append(one_parameter['name'])
    #             i += 2
    #         return_variable_name = the_builder.call(printf, arguments)
    #     result = {'type': int32, 'name': return_variable_name}
    #     return result
    #
    # def visitScanfFunc(self, ctx: CCompilerParser.ScanfFuncContext):
    #     """
    #     语法规则：scanfFunc : 'scanf' '(' mSTRING (','('&')?(mID|arrayItem|structMember))* ')';
    #     描述：scanf函数
    #     返回：函数返回值
    #     """
    #     if 'scanf' in self.functions:
    #         scanf = self.functions['scanf']
    #     else:
    #         scanfType = ir.FunctionType(int32, [ir.PointerType(int8)], var_arg=True)
    #         scanf = ir.Function(self.module, scanfType, name='scanf')
    #         self.functions['scanf'] = scanf
    #
    #     the_builder = self.builders[-1]
    #     zero = ir.Constant(int32, 0)
    #     parameter_list = self.visit(ctx.getChild(2))  # MString
    #     arguments = [the_builder.gep(parameter_list['name'], [zero, zero], inbounds=True)]
    #
    #     length = ctx.getChildCount()
    #     i = 4
    #     while i < length - 1:
    #         if ctx.getChild(i).getText() == '&':
    #             # 读取变量
    #             previous_need_load = self.whether_need_load
    #             self.whether_need_load = False
    #             the_parameter = self.visit(ctx.getChild(i + 1))
    #             self.whether_need_load = previous_need_load
    #             arguments.append(the_parameter['name'])
    #             i += 3
    #         else:
    #             previous_need_load = self.whether_need_load
    #             self.whether_need_load = True
    #             the_parameter = self.visit(ctx.getChild(i))
    #             self.whether_need_load = previous_need_load
    #             arguments.append(the_parameter['name'])
    #             i += 2
    #
    #     return_variable_name = the_builder.call(scanf, arguments)
    #     result = {'type': int32, 'name': return_variable_name}
    #     return result
    #
    # def visitGetsFunc(self, ctx: CCompilerParser.GetsFuncContext):
    #     """
    #     语法规则：getsFunc : 'gets' '(' mID ')';
    #     描述：gets函数
    #     返回：函数返回值
    #     """
    #     if 'gets' in self.functions:
    #         gets = self.functions['gets']
    #     else:
    #         getsType = ir.FunctionType(int32, [], var_arg=True)
    #         gets = ir.Function(self.module, getsType, name='gets')
    #         self.functions['gets'] = gets
    #
    #     the_builder = self.builders[-1]
    #     zero = ir.Constant(int32, 0)
    #
    #     previous_need_load = self.whether_need_load
    #     self.whether_need_load = False
    #     ParameterInfo = self.visit(ctx.getChild(2))
    #     self.whether_need_load = previous_need_load
    #
    #     arguments = [the_builder.gep(ParameterInfo['name'], [zero, zero], inbounds=True)]
    #     return_variable_name = the_builder.call(gets, arguments)
    #     result = {'type': int32, 'name': return_variable_name}
    #     return result
    #
    # def visitSelfDefinedFunc(self, ctx: CCompilerParser.SelfDefinedFuncContext) -> Dict[str, ir.CallInstr]:
    #     """
    #     自定义函数.
    #
    #     语法规则：
    #         selfDefinedFunc : mID '('((argument | mID)(','(argument | mID))*)? ')';
    #
    #     Args:
    #         ctx (CCompilerParser.SelfDefinedFuncContext):
    #
    #     Returns:
    #         Dict[str, CallInstr]: 函数返回值
    #     """
    #     the_builder = self.builders[-1]
    #     function_name = ctx.getChild(0).getText()  # func name
    #     if function_name in self.functions:
    #         func = self.functions[function_name]
    #
    #         length = ctx.getChildCount()
    #         parameter_list = []
    #         func_arg_count = len(func.args)
    #         i = 2
    #         arg_index = 0
    #         while i < length - 1:
    #             prev_need_load = self.whether_need_load
    #             self.whether_need_load = True
    #             param = self.visit(ctx.getChild(i))
    #             self.whether_need_load = prev_need_load
    #             if arg_index >= func_arg_count:
    #                 if not func.function_type.var_arg:
    #                     raise SemanticError(ctx=ctx, msg='参数数量不匹配')
    #             else:
    #                 param = self.assignConvert(param, func.args[arg_index].type)
    #             parameter_list.append(param['name'])
    #             arg_index += 1
    #             i += 2
    #         return_variable_name = the_builder.call(func, parameter_list)
    #         result = {'type': func.function_type.return_type, 'name': return_variable_name}
    #         return result
    #     else:
    #         raise SemanticError(ctx=ctx, msg='未找到函数声明: ' + function_name)
    #
    # # 语句块相关函数
    # def visitBlock(self, ctx: CCompilerParser.BlockContext):
    #     """
    #     语法规则：block : initialBlock | arrayInitBlock | structInitBlock
    #         | assignBlock | ifBlocks | whileBlock | forBlock | returnBlock;
    #     描述：语句块
    #     返回：无
    #     """
    #     for i in range(ctx.getChildCount()):
    #         self.visit(ctx.getChild(i))
    #     return
    #
    # def visitInitialBlock(self, ctx: CCompilerParser.InitialBlockContext):
    #     """
    #     语法规则：initialBlock : (mType) mID ('=' expr)? (',' mID ('=' expr)?)* ';';
    #     描述：初始化语句块
    #     返回：无
    #     """
    #     # 初始化全局变量
    #     parameter_type = self.visit(ctx.getChild(0))
    #     length = ctx.getChildCount()
    #
    #     i = 1
    #     while i < length:
    #         id_name = ctx.getChild(i).getText()
    #         if self.symbol_table.is_global():
    #             new_variable = ir.GlobalVariable(self.module, parameter_type, name=id_name)
    #             new_variable.linkage = 'internal'
    #         else:
    #             the_builder = self.builders[-1]
    #             new_variable = the_builder.alloca(parameter_type, name=id_name)
    #         the_variable = {'type': parameter_type, 'name': new_variable}
    #         result = self.symbol_table.add_item(id_name, the_variable)
    #         if result['status'] != 'success':
    #             raise SemanticError(ctx=ctx, msg=result['reason'])
    #
    #         if ctx.getChild(i + 1).getText() != '=':
    #             i += 2
    #         else:
    #             # 初始化
    #             value = self.visit(ctx.getChild(i + 2))
    #             if self.symbol_table.is_global():
    #                 # 全局变量
    #                 new_variable.initializer = ir.Constant(value['type'], value['name'].constant)
    #                 # print(value['name'].constant)
    #             else:
    #                 # 局部变量，可能有强制类型转换
    #                 value = self.assignConvert(value, parameter_type)
    #                 the_builder = self.builders[-1]
    #                 the_builder.store(value['name'], new_variable)
    #             i += 4
    #     return
    #
    # def visitArrayInitBlock(self, ctx: CCompilerParser.ArrayInitBlockContext):
    #     """
    #     语法规则：arrayInitBlock : mType mID '[' mINT ']'';';
    #     描述：数组初始化块
    #     返回：无
    #     """
    #     type = self.visit(ctx.getChild(0))
    #     id_name = ctx.getChild(1).getText()
    #     length = int(ctx.getChild(3).getText())
    #
    #     if self.symbol_table.is_global():
    #         # 全局变量
    #         new_variable = ir.GlobalVariable(self.module, ir.ArrayType(type, length), name=id_name)
    #         new_variable.linkage = 'internal'
    #     else:
    #         the_builder = self.builders[-1]
    #         new_variable = the_builder.alloca(ir.ArrayType(type, length), name=id_name)
    #
    #     the_variable = {'type': ir.ArrayType(type, length), 'name': new_variable}
    #     result = self.symbol_table.add_item(id_name, the_variable)
    #     if result['status'] != 'success':
    #         raise SemanticError(ctx=ctx, msg=result['reason'])
    #     return
    #
    # def visitAssignBlock(self, ctx: CCompilerParser.AssignBlockContext):
    #     """
    #     语法规则：assignBlock : ((arrayItem|mID|structMember) '=')+  expr ';';
    #     描述：赋值语句块
    #     返回：无
    #     """
    #     the_builder = self.builders[-1]
    #     length = ctx.getChildCount()
    #     id_name = ctx.getChild(0).getText()
    #     if ('[' not in id_name) and not self.symbol_table.exist(id_name):
    #         raise SemanticError(ctx=ctx, msg='变量未定义！')
    #
    #     # 待赋值结果
    #     value_to_be_assigned = self.visit(ctx.getChild(length - 2))
    #
    #     i = 0
    #     result = {'type': value_to_be_assigned['type'], 'name': value_to_be_assigned['name']}
    #     # 遍历全部左边变量赋值
    #     while i < length - 2:
    #         previous_need_load = self.whether_need_load
    #         self.whether_need_load = False
    #         the_variable = self.visit(ctx.getChild(i))
    #         self.whether_need_load = previous_need_load
    #
    #         the_value_to_be_assigned = value_to_be_assigned
    #         the_value_to_be_assigned = self.assignConvert(the_value_to_be_assigned, the_variable['type'])
    #         the_builder.store(the_value_to_be_assigned['name'], the_variable['name'])
    #         if i > 0:
    #             ReturnVariable = the_builder.load(the_variable['name'])
    #             result = {'type': the_variable['type'], 'name': ReturnVariable}
    #         i += 2
    #     return result
    #
    # # TODO
    # def visitCondition(self, ctx: CCompilerParser.ConditionContext):
    #     """
    #     语法规则：condition :  expr;
    #     描述：判断条件
    #     返回：无
    #     """
    #     result = self.visit(ctx.getChild(0))
    #     return self.toBoolean(result, notFlag=False)
    #
    # def visitIfBlocks(self, ctx: CCompilerParser.IfBlocksContext):
    #     """
    #     语法规则：ifBlocks : ifBlock (elifBlock)* (elseBlock)?;
    #     描述：if语句块
    #     返回：无
    #     """
    #     # 增加两个block，对应If分支和If结束后的分支
    #     the_builder = self.builders[-1]
    #     if_block = the_builder.append_basic_block()
    #     endif_block = the_builder.append_basic_block()
    #     the_builder.branch(if_block)
    #
    #     # 载入IfBlock
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(if_block)
    #     self.builders.append(ir.IRBuilder(if_block))
    #
    #     tmp = self.endif_block
    #     self.endif_block = endif_block
    #     length = ctx.getChildCount()
    #     for i in range(length):
    #         self.visit(ctx.getChild(i))  # 分别处理每个if ,elseif, else块
    #     self.endif_block = tmp
    #
    #     # 结束后导向EndIf块
    #     blockTemp = self.blocks.pop()
    #     builderTemp = self.builders.pop()
    #     if not blockTemp.is_terminated:
    #         builderTemp.branch(endif_block)
    #
    #     self.blocks.append(endif_block)
    #     self.builders.append(ir.IRBuilder(endif_block))
    #     return
    #
    # def visitIfBlock(self, ctx: CCompilerParser.IfBlockContext):
    #     """
    #     语法规则：ifBlock : 'if' '(' condition ')' '{' body '}';
    #     描述：单一if语句块
    #     返回：无
    #     """
    #     # 在If块中，有True和False两种可能的导向
    #     self.symbol_table.enter_scope()
    #     the_builder = self.builders[-1]
    #     true_block = the_builder.append_basic_block()
    #     false_block = the_builder.append_basic_block()
    #
    #     # 根据condition结果转向某个代码块
    #     result = self.visit(ctx.getChild(2))
    #     the_builder.cbranch(result['name'], true_block, false_block)
    #
    #     # 如果condition为真，处理TrueBlock,即body部分
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(true_block)
    #     self.builders.append(ir.IRBuilder(true_block))
    #     self.visit(ctx.getChild(5))  # body
    #
    #     if not self.blocks[-1].is_terminated:
    #         self.builders[-1].branch(self.endif_block)
    #
    #     # 处理condition为假的代码部分
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(false_block)
    #     self.builders.append(ir.IRBuilder(false_block))
    #     self.symbol_table.quit_scope()
    #     return
    #
    # def visitElifBlock(self, ctx: CCompilerParser.ElifBlockContext):
    #     """
    #     语法规则：elifBlock : 'else' 'if' '(' condition ')' '{' body '}';
    #     描述：单一elseif语句块
    #     返回：无
    #     """
    #     # 在ElseIf块中，有True和False两种可能的导向
    #     self.symbol_table.enter_scope()
    #     the_builder = self.builders[-1]
    #     true_block = the_builder.append_basic_block()
    #     false_block = the_builder.append_basic_block()
    #
    #     # 根据condition结果转向某个代码块
    #     result = self.visit(ctx.getChild(3))
    #     the_builder.cbranch(result['name'], true_block, false_block)
    #
    #     # 如果condition为真，处理TrueBlock,即body部分
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(true_block)
    #     self.builders.append(ir.IRBuilder(true_block))
    #     self.visit(ctx.getChild(6))  # body
    #
    #     if not self.blocks[-1].is_terminated:
    #         self.builders[-1].branch(self.endif_block)
    #
    #     # 处理condition为假的代码部分
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(false_block)
    #     self.builders.append(ir.IRBuilder(false_block))
    #     self.symbol_table.quit_scope()
    #     return
    #
    # def visitElseBlock(self, ctx: CCompilerParser.ElseBlockContext):
    #     """
    #     语法规则：elseBlock : 'else' '{' body '}';
    #     描述：单一else语句块
    #     返回：无
    #     """
    #     # Else分块直接处理body内容
    #     self.symbol_table.enter_scope()
    #     self.visit(ctx.getChild(2))  # body
    #     self.symbol_table.quit_scope()
    #     return
    #
    # def visitWhileBlock(self, ctx: CCompilerParser.WhileBlockContext):
    #     """
    #     语法规则：whileBlock : 'while' '(' condition ')' '{' body '}';
    #     描述：while语句块
    #     返回：无
    #     """
    #     self.symbol_table.enter_scope()
    #     the_builder = self.builders[-1]
    #     # while语句分为三个分块
    #     while_condition = the_builder.append_basic_block()
    #     while_body = the_builder.append_basic_block()
    #     while_end = the_builder.append_basic_block()
    #
    #     # 首先执行Condition分块
    #     the_builder.branch(while_condition)
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(while_condition)
    #     self.builders.append(ir.IRBuilder(while_condition))
    #
    #     # 根据condition结果决定执行body还是结束while循环
    #     result = self.visit(ctx.getChild(2))  # condition
    #     self.builders[-1].cbranch(result['name'], while_body, while_end)
    #
    #     # 执行body
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(while_body)
    #     self.builders.append(ir.IRBuilder(while_body))
    #     self.visit(ctx.getChild(5))  # body
    #
    #     # 执行body后重新判断condition
    #     self.builders[-1].branch(while_condition)
    #
    #     # 结束while循环
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(while_end)
    #     self.builders.append(ir.IRBuilder(while_end))
    #     self.symbol_table.quit_scope()
    #     return
    #
    # def visitForBlock(self, ctx: CCompilerParser.ForBlockContext):
    #     """
    #     语法规则：forBlock : 'for' '(' for1Block  ';' condition ';' for3Block ')' ('{' body '}'|';');
    #     描述：for语句块
    #     返回：无
    #     """
    #     self.symbol_table.enter_scope()
    #
    #     # for循环首先初始化局部变量
    #     self.visit(ctx.getChild(2))
    #     # for循环的三种block
    #     the_builder = self.builders[-1]
    #     for_condition = the_builder.append_basic_block()
    #     for_body = the_builder.append_basic_block()
    #     for_end = the_builder.append_basic_block()
    #
    #     # 判断condition
    #     the_builder.branch(for_condition)
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(for_condition)
    #     self.builders.append(ir.IRBuilder(for_condition))
    #
    #     # 根据condition结果决定跳转到body或者结束
    #     result = self.visit(ctx.getChild(4))  # condition block
    #     self.builders[-1].cbranch(result['name'], for_body, for_end)
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(for_body)
    #     self.builders.append(ir.IRBuilder(for_body))
    #
    #     # 处理body
    #     if ctx.getChildCount() == 11:
    #         self.visit(ctx.getChild(9))  # main body
    #
    #     # 处理step语句
    #     self.visit(ctx.getChild(6))  # step block
    #
    #     # 一次循环后重新判断condition
    #     self.builders[-1].branch(for_condition)
    #
    #     # 结束循环
    #     self.blocks.pop()
    #     self.builders.pop()
    #     self.blocks.append(for_end)
    #     self.builders.append(ir.IRBuilder(for_end))
    #     self.symbol_table.quit_scope()
    #     return
    #
    # def visitFor1Block(self, ctx: CCompilerParser.For1BlockContext):
    #     """
    #     语法规则：for1Block :  mID '=' expr (',' for1Block)?|;
    #     描述：for语句块的第一个参数
    #     返回：无
    #     """
    #     # 初始化参数为空
    #     length = ctx.getChildCount()
    #     if length == 0:
    #         return
    #
    #     tmp_need_load = self.whether_need_load
    #     self.whether_need_load = False
    #     result0 = self.visit(ctx.getChild(0))  # mID
    #     self.whether_need_load = tmp_need_load
    #
    #     # 访问表达式
    #     result1 = self.visit(ctx.getChild(2))  # expr
    #     result1 = self.assignConvert(result1, result0['type'])
    #     self.builders[-1].store(result1['name'], result0['name'])
    #
    #     if length > 3:
    #         self.visit(ctx.getChild(4))
    #     return
    #
    # def visitFor3Block(self, ctx: CCompilerParser.For3BlockContext):
    #     """
    #     语法规则：for3Block : mID '=' expr (',' for3Block)?|;
    #     描述：for语句块的第三个参数
    #     返回：无
    #     """
    #     length = ctx.getChildCount()
    #     if length == 0:
    #         return
    #
    #     tmp_need_load = self.whether_need_load
    #     self.whether_need_load = False
    #     result0 = self.visit(ctx.getChild(0))
    #     self.whether_need_load = tmp_need_load
    #
    #     result1 = self.visit(ctx.getChild(2))
    #     result1 = self.assignConvert(result1, result0['type'])
    #     self.builders[-1].store(result1['name'], result0['name'])
    #
    #     if length > 3:
    #         self.visit(ctx.getChild(4))
    #     return
    #
    # def visitReturnBlock(self, ctx: CCompilerParser.ReturnBlockContext):
    #     """
    #     语法规则：returnBlock : 'return' (mINT|mID)? ';';
    #     描述：return语句块
    #     返回：无
    #     """
    #     # 返回空
    #     if ctx.getChildCount() == 2:
    #         real_return_value = self.builders[-1].ret_void()
    #         judge_truth = False
    #         return {
    #             'type': void,
    #             'const': judge_truth,
    #             'name': real_return_value
    #         }
    #
    #     # 访问返回值
    #     return_index = self.visit(ctx.getChild(1))
    #     real_return_value = self.builders[-1].ret(return_index['name'])
    #     judge_truth = False
    #     return {
    #         'type': void,
    #         'const': judge_truth,
    #         'name': real_return_value
    #     }
    #
    # # 运算和表达式求值，类型转换相关函数
    # def assignConvert(self, calc_index, DType):
    #     if calc_index['type'] == DType:
    #         return calc_index
    #     if self.isInteger(calc_index['type']) and self.isInteger(DType):
    #         if calc_index['type'] == int1:
    #             calc_index = self.convertIIZ(calc_index, DType)
    #         else:
    #             calc_index = self.convertIIS(calc_index, DType)
    #     elif self.isInteger(calc_index['type']) and DType == double:
    #         calc_index = self.convertIDS(calc_index)
    #     elif self.isInteger(DType) and calc_index['type'] == double:
    #         calc_index = self.convertDIS(calc_index, DType)
    #     return calc_index
    #
    # def convertIIZ(self, calc_index, DType):
    #     builder = self.builders[-1]
    #     confirmed_val = builder.zext(calc_index['name'], DType)
    #     is_constant = False
    #     return {
    #         'type': DType,
    #         'const': is_constant,
    #         'name': confirmed_val
    #     }
    #
    # def convertIIS(self, calc_index, DType):
    #     builder = self.builders[-1]
    #     confirmed_val = builder.sext(calc_index['name'], DType)
    #     is_constant = False
    #     return {
    #         'type': DType,
    #         'const': is_constant,
    #         'name': confirmed_val
    #     }
    #
    # def convertDIS(self, calc_index, DType):
    #     builder = self.builders[-1]
    #     confirmed_val = builder.fptosi(calc_index['name'], DType)
    #     is_constant = False
    #     return {
    #         'type': DType,
    #         'const': is_constant,
    #         'name': confirmed_val
    #     }
    #
    # def convertDIU(self, calc_index, DType):
    #     builder = self.builders[-1]
    #     confirmed_val = builder.fptoui(calc_index['name'], DType)
    #     is_constant = False
    #     return {
    #         'type': DType,
    #         'const': is_constant,
    #         'name': confirmed_val
    #     }
    #
    # def convertIDS(self, calc_index):
    #     builder = self.builders[-1]
    #     confirmed_val = builder.sitofp(calc_index['name'], double)
    #     is_constant = False
    #     return {
    #         'type': double,
    #         'const': is_constant,
    #         'name': confirmed_val
    #     }
    #
    # def convertIDU(self, calc_index):
    #     builder = self.builders[-1]
    #     is_constant = False
    #     confirmed_val = builder.uitofp(calc_index['name'], double)
    #     return {
    #         'type': double,
    #         'const': is_constant,
    #         'name': confirmed_val
    #     }
    #
    # # 类型转换至布尔型
    # def toBoolean(self, manipulate_index, notFlag=True):
    #     builder = self.builders[-1]
    #     if notFlag:
    #         operation_char = '=='
    #     else:
    #         operation_char = '!='
    #     if manipulate_index['type'] == int8 or manipulate_index['type'] == int32:
    #         real_return_value = builder.icmp_signed(operation_char, manipulate_index['name'],
    #                                                 ir.Constant(manipulate_index['type'], 0))
    #         return {
    #             'type': int1,
    #             'const': False,
    #             'name': real_return_value
    #         }
    #     elif manipulate_index['type'] == double:
    #         real_return_value = builder.fcmp_ordered(operation_char, manipulate_index['name'], ir.Constant(double, 0))
    #         return {
    #             'type': int1,
    #             'const': False,
    #             'name': real_return_value
    #         }
    #     return manipulate_index
    #
    # def arrayDecay(self, array_ptr, pointer_type: ir.PointerType):
    #     """
    #     将数组指针退化为指针
    #     """
    #     assert array_ptr.pointee.element == pointer_type.pointee
    #     arr = self.builders[-1].gep(array_ptr, [ir.Constant(int32, 0), ir.Constant(int32, 0)], inbounds=True)
    #     is_constant = False
    #     return {
    #         'type': pointer_type,
    #         'const': is_constant,
    #         'name': arr,
    #     }
    #
    # def visitNeg(self, ctx: CCompilerParser.NegContext):
    #     """
    #     语法规则：expr :  op='!' expr
    #     描述：非运算
    #     返回：无
    #     """
    #     real_return_value = self.visit(ctx.getChild(1))
    #     real_return_value = self.toBoolean(real_return_value, notFlag=True)
    #     # res 未返回
    #     return self.visitChildren(ctx)
    #
    # def visitOR(self, ctx: CCompilerParser.ORContext):
    #     """
    #     语法规则：expr : expr '||' expr
    #     描述：或运算
    #     返回：无
    #     """
    #     index1 = self.visit(ctx.getChild(0))
    #     index1 = self.toBoolean(index1, notFlag=False)
    #     index2 = self.visit(ctx.getChild(2))
    #     index2 = self.toBoolean(index2, notFlag=False)
    #     builder = self.builders[-1]
    #     real_return_value = builder.or_(index1['name'], index2['name'])
    #     return {
    #         'type': index1['type'],
    #         'const': False,
    #         'name': real_return_value
    #     }
    #
    # def visitAND(self, ctx: CCompilerParser.ANDContext):
    #     """
    #     语法规则：expr : expr '&&' expr
    #     描述：且运算
    #     返回：无
    #     """
    #     index1 = self.visit(ctx.getChild(0))
    #     index1 = self.toBoolean(index1, notFlag=False)
    #     index2 = self.visit(ctx.getChild(2))
    #     index2 = self.toBoolean(index2, notFlag=False)
    #     builder = self.builders[-1]
    #     is_constant = False
    #     real_return_value = builder.and_(index1['name'], index2['name'])
    #     return {
    #         'type': index1['type'],
    #         'const': is_constant,
    #         'name': real_return_value
    #     }
    #
    # def visitIdentifier(self, ctx: CCompilerParser.IdentifierContext):
    #     """
    #     语法规则：expr : mID
    #     描述：常数
    #     返回：无
    #     """
    #     return self.visit(ctx.getChild(0))
    #
    # def visitParens(self, ctx: CCompilerParser.ParensContext):
    #     """
    #     语法规则：expr : '(' expr ')'
    #     描述：括号
    #     返回：无
    #     """
    #     return self.visit(ctx.getChild(1))
    #
    # def visitAddressOf(self, ctx: CCompilerParser.AddressOfContext):
    #     """
    #     语法规则：expr : '&' expr
    #     描述：取地址
    #     返回：无
    #     """
    #     builder = self.builders[-1]
    #     # 保证 expr 部分在内存上
    #     prev_need_load = self.whether_need_load
    #     self.whether_need_load = False
    #     index1 = self.visit(ctx.getChild(1))
    #     self.whether_need_load = prev_need_load
    #     ptr_type: ir.Type = index1['name'].type
    #     if not ptr_type.is_pointer:
    #         raise SemanticError(ctx=ctx, msg='不是合法的左值')
    #     is_constant = False
    #     return {
    #         'type': ptr_type,
    #         'const': is_constant,
    #         'name': index1['name']
    #     }
    #
    # def visitDereference(self, ctx: CCompilerParser.DereferenceContext):
    #     """
    #     语法规则：expr : '*' expr
    #     描述：取内容
    #     返回：无
    #     """
    #     builder = self.builders[-1]
    #     index1 = self.visit(ctx.getChild(1))
    #     ptr = builder.load(index1['name'])
    #     is_constant = False
    #     return {
    #         'type': ptr.type,
    #         'const': is_constant,
    #         'name': ptr
    #     }
    #
    # def visitArrayIndex(self, ctx: CCompilerParser.ArrayIndexContext):
    #     """
    #     语法规则：expr : expr '[' expr ']'
    #     描述：数组元素
    #     返回：无
    #     """
    #     temp_require_load = self.whether_need_load
    #     self.whether_need_load = False
    #     arr = self.visit(ctx.getChild(0))  # array / pointer
    #     is_constant = False
    #     self.whether_need_load = temp_require_load
    #
    #     is_pointer = isinstance(arr['type'], ir.types.PointerType)
    #     is_array = isinstance(arr['type'], ir.types.ArrayType)
    #
    #     if is_array | is_pointer:
    #         builder = self.builders[-1]
    #         temp_require_load = self.whether_need_load
    #         self.whether_need_load = True
    #         index_re1 = self.visit(ctx.getChild(2))  # subscript
    #         self.whether_need_load = temp_require_load
    #
    #         if is_pointer:
    #             # 如果是指针，需要 load 进来
    #             ptr = builder.load(arr['name'])
    #             real_return_value = builder.gep(ptr, [index_re1['name']], inbounds=False)
    #         else:
    #             int32_zero = ir.Constant(int32, 0)
    #             real_return_value = builder.gep(arr['name'], [int32_zero, index_re1['name']], inbounds=True)
    #         if self.whether_need_load:
    #             real_return_value = builder.load(real_return_value)
    #         return {
    #             'type': arr['type'].element if is_array else arr['type'].pointee,
    #             'const': is_constant,
    #             'name': real_return_value,
    #             'struct_name': arr['struct_name'] if 'struct_name' in arr else None
    #         }
    #     else:  # error!
    #         raise SemanticError(ctx=ctx, msg='类型错误')
    #
    # def visitString(self, ctx: CCompilerParser.StringContext):
    #     """
    #     语法规则：expr : mSTRING
    #     描述：字符串
    #     返回：无
    #     """
    #     return self.visit(ctx.getChild(0))
    #
    # @staticmethod
    # def isInteger(typ):
    #     return_value = 'width'
    #     return hasattr(typ, return_value)
    #
    # @staticmethod
    # def isArray(typ):
    #     return isinstance(typ['type'], ir.ArrayType)
    #
    # @staticmethod
    # def isPointer(typ):
    #     return isinstance(typ, ir.PointerType)
    #
    # def exprConvert(self, index1, index2):
    #     if index1['type'] == index2['type']:
    #         return index1, index2
    #     if self.isInteger(index1['type']) and self.isInteger(index2['type']):
    #         if index1['type'].width < index2['type'].width:
    #             if index1['type'].width == 1:
    #                 index1 = self.convertIIZ(index1, index2['type'])
    #             else:
    #                 index1 = self.convertIIS(index1, index2['type'])
    #         else:
    #             if index2['type'].width == 1:
    #                 index2 = self.convertIIZ(index2, index1['type'])
    #             else:
    #                 index2 = self.convertIIS(index2, index1['type'])
    #     elif self.isInteger(index1['type']) and index2['type'] == double:
    #         # index1 = convertIDS(index1, index2['type'])
    #         index1 = self.convertIDS(index1)
    #     elif self.isInteger(index2['type']) and index1['type'] == double:
    #         # index2 = convertIDS(index2, index1['type'])
    #         index2 = self.convertIDS(index2)
    #     else:
    #         raise SemanticError(msg='类型不匹配')
    #     return index1, index2
    #
    # def visitMulDiv(self, ctx: CCompilerParser.MulDivContext):
    #     """
    #     语法规则：expr : expr op=('*' | '/' | '%') expr
    #     描述：乘除
    #     返回：无
    #     """
    #     builder = self.builders[-1]
    #     index1 = self.visit(ctx.getChild(0))
    #     index2 = self.visit(ctx.getChild(2))
    #     index1, index2 = self.exprConvert(index1, index2)
    #     is_constant = False
    #     if ctx.getChild(1).getText() == '*':
    #         real_return_value = builder.mul(index1['name'], index2['name'])
    #     elif ctx.getChild(1).getText() == '/':
    #         real_return_value = builder.sdiv(index1['name'], index2['name'])
    #     elif ctx.getChild(1).getText() == '%':
    #         real_return_value = builder.srem(index1['name'], index2['name'])
    #     return {
    #         'type': index1['type'],
    #         'const': is_constant,
    #         'name': real_return_value
    #     }
    #
    # def visitAddSub(self, ctx: CCompilerParser.AddSubContext):
    #     """
    #     语法规则：expr op=('+' | '-') expr
    #     描述：加减
    #     返回：无
    #     """
    #     builder = self.builders[-1]
    #     index1 = self.visit(ctx.getChild(0))
    #     index2 = self.visit(ctx.getChild(2))
    #     index1, index2 = self.exprConvert(index1, index2)
    #     is_constant = False
    #     if ctx.getChild(1).getText() == '+':
    #         real_return_value = builder.add(index1['name'], index2['name'])
    #     elif ctx.getChild(1).getText() == '-':
    #         real_return_value = builder.sub(index1['name'], index2['name'])
    #     return {
    #         'type': index1['type'],
    #         'const': is_constant,
    #         'name': real_return_value
    #     }
    #
    # def visitDouble(self, ctx: CCompilerParser.DoubleContext):
    #     """
    #     语法规则：expr : (op='-')? mDOUBLE
    #     描述：double类型
    #     返回：无
    #     """
    #     if ctx.getChild(0).getText() == '-':
    #         IndexMid = self.visit(ctx.getChild(1))
    #         builder = self.builders[-1]
    #         real_return_value = builder.neg(IndexMid['name'])
    #         return {
    #             'type': IndexMid['type'],
    #             'name': real_return_value
    #         }
    #     return self.visit(ctx.getChild(0))
    #
    # def visitFunction(self, ctx: CCompilerParser.FunctionContext):
    #     """
    #     语法规则：expr : func
    #     描述：函数类型
    #     返回：无
    #     """
    #     return self.visit(ctx.getChild(0))
    #
    # def visitChar(self, ctx: CCompilerParser.CharContext):
    #     """
    #     语法规则：expr : mCHAR
    #     描述：字符类型
    #     返回：无
    #     """
    #     return self.visit(ctx.getChild(0))
    #
    # def visitInt(self, ctx: CCompilerParser.IntContext):
    #     """
    #     语法规则：(op='-')? mINT
    #     描述：int类型
    #     返回：无
    #     """
    #     if ctx.getChild(0).getText() == '-':
    #         IndexMid = self.visit(ctx.getChild(1))
    #         builder = self.builders[-1]
    #         real_return_value = builder.neg(IndexMid['name'])
    #         return {
    #             'type': IndexMid['type'],
    #             'name': real_return_value
    #         }
    #     return self.visit(ctx.getChild(0))
    #
    # def visitMVoid(self, ctx: CCompilerParser.MVoidContext):
    #     """
    #     语法规则：mVoid : 'void';
    #     描述：void类型
    #     返回：无
    #     """
    #     return void
    #
    # def visitMArray(self, ctx: CCompilerParser.MArrayContext):
    #     """
    #     语法规则：mArray : mID '[' mINT ']';
    #     描述：数组类型
    #     返回：无
    #     """
    #     return {
    #         'id_name': ctx.getChild(0).getText(),
    #         'length': int(ctx.getChild(2).getText())
    #     }
    #
    # def visitJudge(self, ctx: CCompilerParser.JudgeContext):
    #     """
    #     语法规则：expr : expr op=('==' | '!=' | '<' | '<=' | '>' | '>=') expr
    #     描述：比较
    #     返回：无
    #     """
    #     builder = self.builders[-1]
    #     index1 = self.visit(ctx.getChild(0))
    #     index2 = self.visit(ctx.getChild(2))
    #     index1, index2 = self.exprConvert(index1, index2)
    #     operation_char = ctx.getChild(1).getText()
    #     is_constant = False
    #     if index1['type'] == double:
    #         real_return_value = builder.fcmp_ordered(operation_char, index1['name'], index2['name'])
    #     elif self.isInteger(index1['type']):
    #         real_return_value = builder.icmp_signed(operation_char, index1['name'], index2['name'])
    #     return {
    #         'type': int1,
    #         'const': is_constant,
    #         'name': real_return_value
    #     }
    #
    # # 变量和变量类型相关函数
    # def visitMType(self, ctx: CCompilerParser.MTypeContext) -> ir.Type:
    #     """
    #     类型主函数.
    #
    #     语法规则：
    #         mType : mBaseType pointer?;
    #
    #     Args:
    #         ctx (CCompilerParser.MTypeContext):
    #
    #     Returns:
    #         ir.Type: 变量类型
    #     """
    #     base_type: ir.Type = self.visit(ctx.getChild(0))
    #     if ctx.getChildCount() > 1:
    #         # 指针类型信息
    #         pointers: List[Dict[str, bool]] = self.visit(ctx.getChild(1))
    #         pointers.reverse()
    #         for _ in pointers:
    #             base_type: ir.PointerType = base_type.as_pointer()
    #     return base_type
    #
    # def visitMBaseType(self, ctx: CCompilerParser.MBaseTypeContext) -> ir.Type:
    #     """
    #     基础类型
    #
    #     语法规则：
    #         mBaseType : ('int' | 'double' | 'char')
    #
    #     Args:
    #         ctx (CCompilerParser.MBaseTypeContext):
    #
    #     Returns:
    #         ir.Type 基础类型
    #     """
    #     base_type = ctx.getText()
    #     if base_type == 'int':
    #         return int32
    #     if base_type == 'char':
    #         return int8
    #     if base_type == 'double':
    #         return double
    #     return void
    #
    #
    # def visitArrayItem(self, ctx: CCompilerParser.ArrayItemContext):
    #     """
    #     语法规则：arrayItem : mID '[' expr ']';
    #     描述：数组元素
    #     返回：无
    #     """
    #     temp_require_load = self.whether_need_load
    #     self.whether_need_load = False
    #     res = self.visit(ctx.getChild(0))  # mID
    #     is_constant = False
    #     self.whether_need_load = temp_require_load
    #
    #     if isinstance(res['type'], ir.types.ArrayType):
    #         builder = self.builders[-1]
    #
    #         temp_require_load = self.whether_need_load
    #         self.whether_need_load = True
    #         index_re1 = self.visit(ctx.getChild(2))  # subscript
    #         self.whether_need_load = temp_require_load
    #
    #         int32_zero = ir.Constant(int32, 0)
    #         real_return_value = builder.gep(res['name'], [int32_zero, index_re1['name']], inbounds=True)
    #         if self.whether_need_load:
    #             real_return_value = builder.load(real_return_value)
    #         return {
    #             'type': res['type'].element,
    #             'const': is_constant,
    #             'name': real_return_value,
    #             'struct_name': res['struct_name'] if 'struct_name' in res else None
    #         }
    #     else:  # error!
    #         raise SemanticError(ctx=ctx, msg='类型错误')
    #
    # def visitArgument(self, ctx: CCompilerParser.ArgumentContext):
    #     """
    #     语法规则：argument : mINT | mDOUBLE | mCHAR | mSTRING;
    #     描述：函数参数
    #     返回：无
    #     """
    #     return self.visit(ctx.getChild(0))
    #
    # def visitMStruct(self, ctx: CCompilerParser.MStructContext) -> Dict[str, Union[List[str], ir.LiteralStructType]]:
    #     """
    #     结构体类型变量的使用.
    #
    #     语法规则：
    #         mStruct : 'struct' mID;
    #
    #     Args:
    #         ctx (CCompilerParser.MStructContext):
    #
    #     Returns:
    #          Dict[str, Union[List[str], ir.LiteralStructType]]:
    #             {'Members': member_list, 'Type': ir.LiteralStructType(type_list)}
    #     """
    #     return self.structure.list[ctx.getChild(1).getText()]
    #
    # def visitMID(self, ctx: CCompilerParser.MIDContext):
    #     """
    #     ID 处理.
    #
    #     语法规则：
    #         mID : ID;
    #
    #     Args:
    #         ctx (CCompilerParser.MIDContext):
    #
    #     Returns:
    #
    #     """
    #     id_name = ctx.getText()
    #     is_constant = False
    #     if not self.symbol_table.exist(id_name):
    #         return {
    #             'type': int32,
    #             'const': is_constant,
    #             'name': ir.Constant(int32, None)
    #         }
    #     builder = self.builders[-1]
    #     the_item = self.symbol_table.get_item(id_name)
    #     # print(the_item)
    #     if the_item is not None:
    #         if self.whether_need_load:
    #             return_value = builder.load(the_item['name'])
    #             return {
    #                 'type': the_item['type'],
    #                 'const': is_constant,
    #                 'name': return_value,
    #                 'struct_name': the_item['struct_name'] if 'struct_name' in the_item else None
    #             }
    #         else:
    #             return {
    #                 'type': the_item['type'],
    #                 'const': is_constant,
    #                 'name': the_item['name'],
    #                 'struct_name': the_item['struct_name'] if 'struct_name' in the_item else None
    #             }
    #     else:
    #         return {
    #             'type': void,
    #             'const': is_constant,
    #             'name': ir.Constant(void, None)
    #         }
    #
    # def visitMINT(self, ctx: CCompilerParser.MINTContext):
    #     """
    #     int 类型处理.
    #
    #     语法规则：
    #         mINT : INT;
    #
    #     Args:
    #         ctx (CCompilerParser.MINTContext):
    #
    #     Returns:
    #
    #     """
    #     is_constant = True
    #     return {
    #         'type': int32,
    #         'const': is_constant,
    #         'name': ir.Constant(int32, int(ctx.getText()))
    #     }
    #
    # def visitMDOUBLE(self, ctx: CCompilerParser.MDOUBLEContext):
    #     """
    #     double 类型处理.
    #
    #     语法规则：
    #         mDOUBLE : DOUBLE;
    #
    #     Args:
    #         ctx (CCompilerParser.MDOUBLEContext):
    #
    #     Returns:
    #
    #     """
    #     is_constant = True
    #     return {
    #         'type': double,
    #         'const': is_constant,
    #         'name': ir.Constant(double, float(ctx.getText()))
    #     }
    #
    # def visitMCHAR(self, ctx: CCompilerParser.MCHARContext):
    #     """
    #     char 类型处理.
    #
    #     语法规则：
    #         mCHAR : CHAR;
    #
    #     Args:
    #         ctx (CCompilerParser.MCHARContext):
    #
    #     Returns:
    #
    #     """
    #     is_constant = True
    #     return {
    #         'type': int8,
    #         'const': is_constant,
    #         'name': ir.Constant(int8, ord(ctx.getText()[1]))
    #     }
    #
    # def visitMSTRING(self, ctx: CCompilerParser.MSTRINGContext):
    #     """
    #     string 类型处理.
    #
    #     语法规则：
    #         mSTRING : STRING;
    #
    #     Args:
    #         ctx (CCompilerParser.MSTRINGContext):
    #
    #     Returns:
    #
    #     """
    #     mark_index = self.constants
    #     self.constants += 1
    #     process_index = ctx.getText().replace('\\n', '\n')
    #     process_index = process_index[1:-1]
    #     process_index += '\0'
    #     length = len(bytearray(process_index, 'utf-8'))
    #     is_constant = False
    #     real_return_value = ir.GlobalVariable(self.module, ir.ArrayType(int8, length), '.str%d' % mark_index)
    #     real_return_value.global_constant = True
    #     real_return_value.initializer = ir.Constant(ir.ArrayType(int8, length), bytearray(process_index, 'utf-8'))
    #     return {
    #         'type': ir.ArrayType(int8, length),
    #         'const': is_constant,
    #         'name': real_return_value
    #     }
    #
    # }}} Old code

    def visitProg(self, ctx: CCompilerParser.ProgContext) -> None:
        """
        代码主文件.

        语法规则：
            prog : translationUnit* EOF;

        Args:
            ctx (CCompilerParser.ProgContext):

        Returns:
            None
        """
        # initialize symbol table
        self.symbol_table.add_item("int", int32)
        self.symbol_table.add_item("long", int32)
        self.symbol_table.add_item("double", double)
        self.symbol_table.add_item("char", int8)
        self.symbol_table.add_item("void", void)
        self.symbol_table.add_item("bool", int1)

        for i in range(ctx.getChildCount()):
            self.visit(ctx.getChild(i))

    def visitTranslationUnit(self, ctx: CCompilerParser.TranslationUnitContext) -> None:
        """
        翻译单元.

        语法规则：
            translationUnit : functionDefinition | declaration | ';' ;

        Args:
            ctx (CCompilerParser.TranslationUnitContext):

        Returns:
            None
        """
        self.visit(ctx.getChild(0))

    def visitFunctionDefinition(self, ctx: CCompilerParser.FunctionDefinitionContext) -> None:
        """
        函数定义.

        语法规则：
            functionDefinition
                :   typeSpecifier declarator compoundStatement
                ;

        Args:
            ctx (CCompilerParser.FunctionDefinitionContext):

        Returns:
            None
        """
        ret_type: ir.Type = self.visit(ctx.typeSpecifier())
        if ret_type is None:
            raise SemanticError(ctx, "返回类型未指定")
        declarator_func = self.visit(ctx.declarator())
        function_name, function_type, parameter_list = declarator_func(ret_type)

        # 判断重定义，存储函数
        if function_name in self.functions:
            llvm_function = self.functions[function_name]
            if len(llvm_function.blocks) > 0:
                raise SemanticError(ctx=ctx, msg='函数重定义: ' + function_name)
        else:
            llvm_function = ir.Function(self.module, function_type, name=function_name)

        # 函数的参数名
        for i in range(len(parameter_list)):
            typ, name = parameter_list[i]
            llvm_function.args[i].name = name

        # 函数 block
        block: ir.Block = llvm_function.append_basic_block(name=function_name + '.entry')
        self.functions[function_name] = llvm_function

        ir_builder: ir.IRBuilder = ir.IRBuilder(block)
        self.blocks.append(block)
        self.builders.append(ir_builder)

        # 进入函数作用域
        self.current_function = function_name
        self.symbol_table.enter_scope()

        # 存储函数的变量
        for i in range(len(parameter_list)):
            func_arg = llvm_function.args[i]
            variable = ir_builder.alloca(func_arg.type)
            ir_builder.store(func_arg, variable)
            result = self.symbol_table.add_item(func_arg.name, TypedValue(variable, func_arg.type, False))
            if not result.success:
                raise SemanticError(ctx=ctx, msg=result.message)

        # 处理函数体
        self.visit(ctx.getChild(2))  # funcBody

        # 处理完毕，退出函数作用域
        self.current_function = ''
        self.blocks.pop()
        self.builders.pop()
        self.symbol_table.quit_scope()
        return

    def visitDirectDeclarator1(self, ctx: CCompilerParser.DirectDeclarator1Context):
        """
        directDeclarator : Identifier
        """
        identifier = ctx.getText()
        return lambda typ: (identifier, typ, None)

    def visitDirectDeclarator2(self, ctx: CCompilerParser.DirectDeclarator2Context):
        """
        directDeclarator : '(' declarator ')'
        """
        return self.visit(ctx.declarator())

    def visitDirectDeclarator3(self, ctx: CCompilerParser.DirectDeclarator3Context):
        """
        directDeclarator : directDeclarator '[' assignmentExpression? ']'
        """
        arr_len = -1  # todo: 想一个别的办法处理一下
        if ctx.assignmentExpression() is not None:
            exp_const: ir.Constant = self.visit(ctx.assignmentExpression()).ir_value
            if isinstance(exp_const, ir.Constant):
                arr_len = exp_const.constant
            else:
                raise SemanticError(ctx, "数组的长度必须是常量表达式")
        declarator_func = self.visit(ctx.directDeclarator())

        def create_arr_ret(typ: ir.Type):
            id1, typ1, _ = declarator_func(typ)
            return id1, ir.ArrayType(typ1, arr_len), None

        return create_arr_ret

    def visitDirectDeclarator4(self, ctx: CCompilerParser.DirectDeclarator4Context):
        """
        directDeclarator : directDeclarator '(' parameterTypeList ')'
        """
        declarator_func = self.visit(ctx.directDeclarator())
        parameter_list = self.visit(ctx.parameterTypeList())

        def create_func_ret(typ: ir.Type):
            identifier1, typ1, _ = declarator_func(typ)
            return identifier1, ir.FunctionType(typ1, parameter_list.arg_list, parameter_list.var_arg), parameter_list
        return create_func_ret

    def visitParameterTypeList(self, ctx: CCompilerParser.ParameterTypeListContext) -> ParameterList:
        """
        Parameter type list
        语法规则: parameterTypeList : | parameterList | parameterList ',' '...' ;
        Return: ParameterList: 参数列表
        """
        if ctx.parameterList():
            return ParameterList(self.visit(ctx.parameterList()), ctx.getChildCount() == 3)
        return ParameterList([], False)

    def visitParameterList(self, ctx: CCompilerParser.ParameterListContext) -> List[Tuple[ir.Type, Optional[str]]]:
        """
        Parameters

        语法规则:
            parameterList
                :   parameterDeclaration
                |   parameterList ',' parameterDeclaration
                ;
        Returns:
            List[Tuple[ir.Type, Optional[str]]]: (类型, 可选名称) 的列表
        """
        if ctx.parameterList() is not None:
            prev_list = self.visit(ctx.parameterList())
        else:
            prev_list = []
        param = self.visit(ctx.parameterDeclaration())
        prev_list.append(param)
        return prev_list

    def visitParameterDeclaration(self, ctx: CCompilerParser.ParameterDeclarationContext) -> Tuple[ir.Type, Optional[str]]:
        """
        Parameter declaration
        语法规则: parameterDeclaration : declarationSpecifiers declarator ;
        """
        specifiers: DeclarationSpecifiers = self.visit(ctx.declarationSpecifiers())
        base_type = specifiers.get_type()
        if base_type is None:
            raise SemanticError(ctx, "未指定类型")
        declarator_func = self.visit(ctx.declarator())
        identifier, typ, parameter_list = declarator_func(base_type)
        if isinstance(typ, ir.ArrayType):
            # decay
            typ: ir.ArrayType
            typ = typ.element.as_pointer()
        return typ, identifier

    def visitDeclarationSpecifiers(self, ctx: CCompilerParser.DeclarationSpecifiersContext) -> DeclarationSpecifiers:
        """
        声明限定符列表.

        语法规则：
            declarationSpecifiers: declarationSpecifier*;

        Args:
            ctx (CCompilerParser.DeclarationSpecifiersContext):

        Returns:
            List[Tuple[str, Any]]: 限定符列表
        """
        specifiers = DeclarationSpecifiers()
        for i in range(ctx.getChildCount()):
            typ, val = self.visit(ctx.getChild(i))
            specifiers.append(typ, val)
        return specifiers

    def visitDeclarationSpecifier(self, ctx: CCompilerParser.DeclarationSpecifierContext) -> (str, Union[str, ir.Type]):
        """
        声明限定符

        语法规则:
            declarationSpecifier
                :   storageClassSpecifier
                |   typeSpecifier
                |   typeQualifier
                ;
        """
        altNum = ctx.getAltNumber()
        if altNum == 1:
            return "storage", ctx.getText()
        if altNum == 2:
            return "type", self.visit(ctx.typeSpecifier())
        if altNum == 3:
            return "type_qualifier", self.visit(ctx.typeQualifier())

    def visitDeclarator(self, ctx:CCompilerParser.DeclaratorContext):
        """
        描述符.

        语法规则：
            declarator
                :   pointer? directDeclarator
                ;

        Args:
            ctx (CCompilerParser.DeclaratorContext):

        Returns:
            lambda typ : (str, ir.Type, Optional[ParameterList])
                str: 标识符
                ir.Type: 类型
                Optional[ParameterList]: 参数列表 (对于函数声明/定义有效)
        """
        declarator_func = self.visit(ctx.directDeclarator())
        if ctx.pointer():
            pointer = self.visit(ctx.pointer())

            def pointer_declarator(typ: ir.Type):
                identifier1, typ1, parameter_list1 = declarator_func(typ)
                for _ in pointer:
                    typ1 = typ1.as_pointer()
                return identifier1, typ1, parameter_list1
            return pointer_declarator
        return declarator_func

    def visitDeclaration(self, ctx: CCompilerParser.DeclarationContext) -> None:
        """
        声明.

        语法规则：
            declaration
                :   declarationSpecifiers initDeclaratorList ';'
                | 	declarationSpecifiers ';'
                ;

        Args:
            ctx (CCompilerParser.DeclarationContext):

        Returns:
            None
        """
        pass

    def visitQualifiedPointer(self, ctx: CCompilerParser.QualifiedPointerContext) -> Dict[str, bool]:
        """
        指针修饰符

        语法规则：
            pointer : '*' typeQualifierList?

        Args:
            ctx (CCompilerParser.QualifiedPointerContext):

        Returns:
            {
                'const': bool 是否为 const
                'volatile': bool 是否为 volatile
            }
        """
        qualifiers = []
        if ctx.getChildCount() > 1:
            qualifiers = self.visit(ctx.getChild(1))
        return {
            'const': 'const' in qualifiers,
            'volatile': 'volatile' in qualifiers,
        }

    def visitPointer(self, ctx: CCompilerParser.PointerContext) -> List[Dict[str, bool]]:
        """
        指针修饰符列表

        语法规则：
            pointer : qualifiedPointer | pointer qualifiedPointer

        Args:
            ctx (CCompilerParser.PointerContext):

        Returns:
            {
                'const': bool 是否为 const
                'volatile': bool 是否为 volatile
            }[]
        """
        if ctx.getChildCount() > 1:
            pointers: List[Dict[str, bool]] = self.visit(ctx.getChild(0))
            pointers.append(self.visit(ctx.getChild(1)))
            return pointers
        else:
            return [self.visit(ctx.getChild(0))]

    def visitTypeQualifierList(self, ctx: CCompilerParser.TypeQualifierListContext) -> List[str]:
        """
        修饰符列表

        语法规则：
            typeQualifierList : typeQualifier+

        Args:
            ctx (CCompilerParser.TypeQualifierListContext):

        Returns:
            List[str]: 修饰符列表
        """
        qualifiers = []
        for i in range(ctx.getChildCount()):
            qualifiers.append(self.visit(ctx.getChild(i)))
        return qualifiers

    def visitTypeQualifier(self, ctx: CCompilerParser.TypeQualifierContext) -> str:
        """
        修饰符

        语法规则：
            typeQualifier : 'const' | 'volatile' ;

        Args:
            ctx (CCompilerParser.TypeQualifierContext):

        Returns:
            str: 修饰符
        """
        return ctx.getText()

    def visitTypeSpecifier(self, ctx: CCompilerParser.TypeSpecifierContext) -> ir.Type:
        """
        Type Specifier

        语法规则:
            typeSpecifier
                :   primitiveType
                |   typedefName
                |   typeSpecifier pointer
                ;
        """
        altNum = ctx.getAltNumber()
        if altNum == 1:
            return self.visit(ctx.primitiveType())
        if altNum == 2:
            type_id: str = ctx.getText()
            actual_type = self.symbol_table.get_item(type_id)
            if actual_type is None:
                raise SemanticError(ctx, "未定义的类型: " + type_id)
            if not isinstance(actual_type, ir.Type):
                raise SemanticError(ctx, "不是合法的类型: " + type_id)
            return actual_type
        if altNum == 3:
            base_type: ir.Type = self.visit(ctx.typeSpecifier())
            pointer_list: list = self.visit(ctx.pointer())
            for _ in pointer_list:  # const 之类的访问修饰符被省略
                base_type = base_type.as_pointer()
            return base_type

    def load_lvalue(self, lvalue_ptr: TypedValue) -> Union[ir.Value, ir.NamedValue]:
        """
        从左值地址加载出一个值.

        :param lvalue_ptr: 待加载的值
        :type lvalue_ptr: TypedValue
        :return: 如果这个值是右值，返回原始值，否则返回加载后的值
        :rtype: ir.Value
        """
        if not lvalue_ptr.lvalue_ptr:
            return lvalue_ptr.ir_value
        builder = self.builders[-1]
        return builder.load(lvalue_ptr.ir_value)

    def store_lvalue(self, value: ir.Value, lvalue_ptr: TypedValue) -> None:
        """
        存储一个值到左值中.

        :param value: 待存储的值
        :type value: TypedValue
        :param lvalue_ptr 左值的地址
        :type lvalue_ptr TypedValue
        :return: 如果 ptr 是右值，不做事，否则存储 value 至 lvalue_ptr 处
        :rtype: None
        """
        if not lvalue_ptr.lvalue_ptr:
            return
        builder = self.builders[-1]
        builder.store(value, lvalue_ptr.ir_value)

    def str_constant(self, str_value: str) -> TypedValue:
        if str_value in self.string_constants:
            return self.string_constants[str_value]
        str_bytes = bytearray(str_value + "\0", "utf-8")
        variable_name = ".str" + str(len(self.string_constants))
        ir_value = ir.GlobalVariable(ir.ArrayType(int8, len(str_bytes)), str_bytes, variable_name)
        typed_value = TypedValue(ir_value, typ=ir_value.type, constant=True)
        self.string_constants[str_value] = typed_value
        return typed_value

    def visitStringLiteral(self, ctx: CCompilerParser.StringLiteralContext) -> str:
        """
        处理字符串字面值
        """
        # todo 处理更多的转义字符
        return ctx.getText()[1:-1].replace(r"\n", "\n").replace(r"\r", "\r")

    def visitConstant(self, ctx: CCompilerParser.ConstantContext) -> TypedValue:
        # This rule has only lexical elements. In this case, getAltNumber()
        # always returns 1 so we cannot use it.
        if ctx.IntegerConstant():
            def parseInt(s):
                if re.fullmatch('0[0-7]*', s):
                    return int(s, 8)
                return int(s, 0)

            return const_value(ir.Constant(int32, parseInt(ctx.getText())))
        if ctx.FloatingConstant():
            return const_value(ir.Constant(double, float(ctx.getText())))
        if ctx.CharacterConstant():
            return const_value(ir.Constant(int8, ord(ctx.getText()[1])))
        raise SemanticError('impossible')

    def visitPrimaryExpression(self, ctx: CCompilerParser.PrimaryExpressionContext) -> TypedValue:
        """
        Primary Expression
        """
        altNum = ctx.getAltNumber()
        if altNum == 1:  # Indentifer
            identifier = ctx.getText()
            item = self.symbol_table.get_item(identifier)
            if item is None:
                raise SemanticError("Undefined identifier: " + identifier)
            return item
        elif altNum == 2:  # String literals
            count = ctx.getChildCount()
            str_result = ""
            for i in range(count):
                str_result += self.visit(ctx.getChild(i))
            return self.str_constant(str_result)
        elif altNum == 3:  # Constant
            # primaryExpression: constant
            return self.visitChildren(ctx)
        elif altNum == 4:  # (expression)
            # primaryExpression : '(' expression ')'
            return self.visit(ctx.getChild(1))
        return self.visitChildren(ctx)

    def visitPrimitiveType(self, ctx: CCompilerParser.PrimitiveTypeContext) -> ir.Type:
        """
        Primitive type
        """
        return self.symbol_table.get_item(ctx.getText())

    def visitPostfixExpression(self, ctx: CCompilerParser.PostfixExpressionContext) -> TypedValue:
        """
        Postfix Expression.

        :param ctx:
        :type ctx:
        :return:
        :rtype:
        """
        altNum = ctx.getAltNumber()
        builder = self.builders[-1]
        v1: TypedValue = self.visit(ctx.getChild(0))
        if altNum == 1:     # primaryExpression
            return v1
        elif altNum == 2:   # postfixExpression '[' expression ']'
            if not v1.lvalue_ptr:
                raise SemanticError('Postfix Expression(#2) needs lvalue.', ctx=ctx)
            is_pointer = isinstance(v1.type, ir.types.PointerType)
            is_array = isinstance(v1.type, ir.types.ArrayType)
            if not is_array and not is_pointer:
                raise SemanticError("Postfix Expression is not a array or pointer.", ctx=ctx)
            v2: TypedValue = self.visit(ctx.getChild(2))
            # 数组地址
            base_ptr = self.load_lvalue(v1)
            # 偏移
            offset = self.load_lvalue(v2)
            result: ir.Instruction
            if is_pointer:
                result = builder.gep(base_ptr, [offset], inbounds=False)
            elif is_array:
                result = builder.gep(base_ptr, [int32_zero, offset], inbounds=True)
            else:
                raise SemanticError("Postfix expression(#2) is not a array or pointer.", ctx=ctx)
            return TypedValue(result, result.type, constant=False, name=None, lvalue_ptr=True)
        elif altNum == 3:   # postfixExpression '(' argumentExpressionList? ')'
            # TODO 暂时不做好吗
            pass
        elif altNum == 4:   # postfixExpression '.' Identifier
            if not v1.lvalue_ptr:
                raise SemanticError('Postfix Expression(#2) needs lvalue.', ctx=ctx)
            rvalue: ir.NamedValue = self.load_lvalue(v1)
            if not isinstance(rvalue.type, ir.types.LiteralStructType):
                raise SemanticError("Postfix expression(#4) is not literal struct.", ctx=ctx)
            member_name = ctx.Identifier().getText()
            ls_type: ir.LiteralStructType = rvalue.type
            try:
                member_index = ls_type.elements.index(member_name)
            except ValueError:
                raise SemanticError("Postfix expression(#4) has not such attribute.", ctx=ctx)
            # 获得地址
            result = builder.gep(v1.ir_value, [int32_zero, member_index], inbounds=False)
            return TypedValue(result, result.type, constant=False, name=None, lvalue_ptr=True)
        elif altNum == 5:   # postfixExpression '->' Identifier
            rvalue: ir.NamedValue = self.load_lvalue(v1)    # 这里事实上获得一个指针
            if not isinstance(rvalue.type, ir.types.PointerType):
                raise SemanticError("Postfix expression(#5) is not pointer.", ctx=ctx)
            # 转到结构体类型
            pointee_type = rvalue.pointee
            member_name = ctx.Identifier().getText()
            ls_type: ir.LiteralStructType = pointee_type
            try:
                member_index = ls_type.elements.index(member_name)
            except ValueError:
                raise SemanticError("Postfix expression(#5) has not such attribute.", ctx=ctx)
            # 获得地址
            result = builder.gep(rvalue, [int32_zero, member_index], inbounds=False)
            return TypedValue(result, result.type, constant=False, name=None, lvalue_ptr=True)
        elif altNum == 6:   # postfixExpression '++'
            rvalue = self.load_lvalue(v1)
            result = builder.add(rvalue, ir.Constant(v1.type, 1))
            self.store_lvalue(result, v1)
            return TypedValue(rvalue, result.type, constant=False, name=None, lvalue_ptr=False)
        elif altNum == 7:   # postfixExpression '--'
            rvalue = self.load_lvalue(v1)
            result = builder.sub(rvalue, ir.Constant(v1.type, 1))
            self.store_lvalue(result, v1)
            return TypedValue(rvalue, result.type, constant=False, name=None, lvalue_ptr=False)

    def visitArgumentExpressionList(self, ctx: CCompilerParser.ArgumentExpressionListContext):
        pass

    def visitUnaryExpression(self, ctx: CCompilerParser.UnaryExpressionContext) -> TypedValue:
        """
        Unary Expression
        """
        altNum = ctx.getAltNumber()
        builder = self.builders[-1]
        if altNum == 1:     # postfixExpression
            return self.visit(ctx.getChild(0))
        elif altNum == 2:   # '++' unaryExpression
            v1 = self.visit(ctx.unaryExpression())
            rvalue = self.load_lvalue(v1)
            result = builder.add(rvalue, ir.Constant(v1.type, 1))
            self.store_lvalue(result, v1)
            return TypedValue(result, result.type, False, name=None, lvalue_ptr=False)
        elif altNum == 3:   # '--' unaryExpression
            v1 = self.visit(ctx.unaryExpression())
            rvalue = self.load_lvalue(v1)
            result = builder.sub(rvalue, ir.Constant(v1.type, 1))
            self.store_lvalue(result, v1)
            return TypedValue(result, result.type, False, name=None, lvalue_ptr=False)
        elif altNum == 4:   # unaryOperator castExpression
            op: str = ctx.unaryOperator().getText()
            v1 = self.visit(ctx.castExpression())
            # '&' | '*' | '+' | '-' | '~' | '!'
            if op == '&':
                # builder.gep
                # TODO 累了，我再思考
                pass
            elif op == '*':
                pass
            elif op == '+':
                return self.visit(ctx.castExpression())
            elif op == '-':
                rvalue = self.load_lvalue(v1)
                result: ir.Instruction = builder.neg(rvalue)
                return TypedValue(result, result.type, constant=False, name=None, lvalue_ptr=False)
            elif op == '~':
                pass
            elif op == '!':
                pass
        elif altNum == 5:   # 'sizeof' unaryExpression
            # TODO 不知道返回什么类型
            pass
        elif altNum == 6:   # 'sizeof' '(' typeName ')'
            v1 = self.visit(ctx.typeName())
            # TODO 不知道返回什么类型
            pass

    def save(self, filename: str) -> None:
        """
        保存分析结果到文件.

        Args:
            filename (str): 文件名含后缀

        Returns:
            None
        """
        with open(filename, 'w') as f:
            f.write(repr(self.module))


def generate(input_filename: str, output_filename: str):
    """
    将C代码文件转成IR代码文件
    :param input_filename: C代码文件
    :param output_filename: IR代码文件
    :return: 生成是否成功
    """
    # TODO: 加入宏处理
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
