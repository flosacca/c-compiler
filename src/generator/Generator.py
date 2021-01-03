from antlr4 import *
from llvmlite import ir

import re
import os
import sys
from typing import Dict, List, Union, Optional, Tuple, Any, Type

from generator.ErrorListener import SemanticError
from generator.ErrorListener import SyntaxErrorListener
from generator.SymbolTable import SymbolTable, Structure, TypedValue, const_value, ParameterList, DeclarationSpecifiers, \
    ElementNamedLiteralStructType
from cparser.CCompilerLexer import CCompilerLexer
from cparser.CCompilerParser import CCompilerParser
from cparser.CCompilerVisitor import CCompilerVisitor
from generator.parser_util import Result

from cpreprocess.preprocessor import preprocess

double = ir.DoubleType()
int1 = ir.IntType(1)
int16 = ir.IntType(16)
int32 = ir.IntType(32)
int64 = ir.IntType(64)
int8 = ir.IntType(8)
void = ir.VoidType()

int_types = [int1, int8, int16, int32, int64]

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

        # 待生成的 llvm 语句块
        self.builder: ir.IRBuilder

        # 用于控制语句的标号
        self.continue_blocks: ir.BasicBlock = []
        self.break_blocks: ir.BasicBlock = []

        # 函数列表 Dict[名称, 是否有定义]
        self.functions: Dict[str, ir.Function] = dict()

        # 结构体列表
        self.structure: Structure = Structure()

        # 当前所在函数名
        self.current_function: str = ''
        self.constants = 0

        # 符号表
        self.symbol_table: SymbolTable = SymbolTable()
        self.symbol_table.add_item("short", int16)
        self.symbol_table.add_item("int", int32)
        self.symbol_table.add_item("long", int32)
        self.symbol_table.add_item("longlong", int64)
        self.symbol_table.add_item("double", double)
        self.symbol_table.add_item("char", int8)
        self.symbol_table.add_item("void", void)
        self.symbol_table.add_item("bool", int1)

        # 字符串常量表
        self.string_constants: Dict[str, TypedValue] = {}

    def is_global_scope(self) -> bool:
        """
        当前是否在全局作用域下.
        """
        return self.symbol_table.is_global()

    def visitFunctionDefinition(self, ctx: CCompilerParser.FunctionDefinitionContext) -> None:
        """
        函数定义.

        语法规则：
            functionDefinition
                :   declarationSpecifiers declarator compoundStatement
                ;

        Args:
            ctx (CCompilerParser.FunctionDefinitionContext):

        Returns:
            None
        """
        specifiers: DeclarationSpecifiers = self.visit(ctx.declarationSpecifiers())
        ret_type: ir.Type = specifiers.get_type()
        if ret_type is None:
            ret_type = int32
            print(f"Return type not specified, assuming int.")
        declarator_func = self.visit(ctx.declarator())
        function_name, function_type, parameter_list = declarator_func(ret_type, specifiers)
        parameter_list: ParameterList

        # 判断重定义，存储函数
        if function_name in self.functions:
            llvm_function = self.functions[function_name]
            if parameter_list.calling_convention and parameter_list.calling_convention != llvm_function.calling_convention:
                raise SemanticError("Calling convention not identical: "
                                    f"previous {llvm_function.calling_convention} "
                                    f"new {parameter_list.calling_convention}")
            if len(llvm_function.blocks) > 0:
                raise SemanticError(ctx=ctx, msg='函数重定义: ' + function_name)
        else:
            llvm_function = ir.Function(self.module, function_type, name=function_name)
            result = self.symbol_table.add_item(function_name, TypedValue(ir_value=llvm_function,
                                                                          typ=llvm_function.type,
                                                                          constant=False,
                                                                          name=function_name,
                                                                          lvalue_ptr=False))
            if not result.success:
                raise SemanticError('函数重定义: ' + function_name, ctx)

        # 函数的参数名
        for i in range(len(parameter_list)):
            typ, name = parameter_list[i]
            llvm_function.args[i].name = name

        # 函数 block
        block: ir.Block = llvm_function.append_basic_block(name=f'{function_name}.entry')
        self.functions[function_name] = llvm_function

        self.builder = ir.IRBuilder(block)

        # 进入函数作用域
        self.current_function = function_name
        self.symbol_table.enter_scope()

        # 存储函数的变量
        for i in range(len(parameter_list)):
            func_arg = llvm_function.args[i]
            variable = self.builder.alloca(func_arg.type)
            self.builder.store(func_arg, variable)
            result = self.symbol_table.add_item(func_arg.name, TypedValue(ir_value=variable,
                                                                          typ=func_arg.type,
                                                                          constant=False,
                                                                          lvalue_ptr=True,
                                                                          name=parameter_list[i][1]))
            if not result.success:
                raise SemanticError(ctx=ctx, msg=result.message)

        # 处理函数体
        self.visit(ctx.compoundStatement())  # funcBody
        if not self.builder.basic_block.is_terminated:
            if function_name == 'main':
                self.builder.ret(ir.Constant(int32, 0))
            else:
                self.builder.ret_void()

        # 处理完毕，退出函数作用域
        self.current_function = ''
        self.builder = None
        self.symbol_table.quit_scope()
        return

    def visitDirectDeclarator_1(self, ctx: CCompilerParser.DirectDeclarator_1Context):
        """
        directDeclarator : Identifier
        """
        identifier = ctx.getText()
        return lambda typ, _: (identifier, typ, None)

    def visitDirectDeclarator_2(self, ctx: CCompilerParser.DirectDeclarator_2Context):
        """
        directDeclarator : '(' declarator ')'
        """
        return self.visit(ctx.declarator())

    def visitDirectDeclarator_3(self, ctx: CCompilerParser.DirectDeclarator_3Context):
        """
        directDeclarator : directDeclarator '[' assignmentExpression? ']'
        """
        arr_len = -1  # todo: 想一个别的办法处理一下
        if ctx.assignmentExpression() is not None:
            exp_const: ir.Constant = self.visit(ctx.assignmentExpression()).ir_value
            if isinstance(exp_const, ir.Constant):
                arr_len = exp_const.constant
            else:
                raise SemanticError("数组的长度必须是常量表达式", ctx)
        declarator_func = self.visit(ctx.directDeclarator())

        def create_arr_ret(typ: ir.Type, _):
            id1, typ1, pl = declarator_func(typ)
            return id1, ir.ArrayType(typ1, arr_len), pl

        return create_arr_ret

    def visitDirectDeclarator_4(self, ctx: CCompilerParser.DirectDeclarator_4Context):
        """
        directDeclarator : directDeclarator '(' parameterTypeList ')'
        """
        declarator_func = self.visit(ctx.directDeclarator())
        parameter_list = self.visit(ctx.parameterTypeList())

        def create_func_ret(typ: ir.Type, specifiers: DeclarationSpecifiers):
            typ1 = ir.FunctionType(typ, parameter_list.arg_list, parameter_list.var_arg)
            identifier2, typ2, _ = declarator_func(typ1, specifiers)
            for func_spec in specifiers.get_function_specifiers():
                if func_spec == "__cdcel":
                    parameter_list.calling_convention = "ccc"
                elif func_spec == "__stdcall":
                    parameter_list.calling_convention = "cc 65"
            return identifier2, typ2, parameter_list
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
            raise SemanticError("未指定类型", ctx)
        declarator_func = self.visit(ctx.declarator())
        identifier, typ, parameter_list = declarator_func(base_type, specifiers)
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
                |   functionSpecifier
                ;
        """
        if ctx.storageClassSpecifier():
            return "storage", ctx.getText()
        if ctx.typeSpecifier():
            return "type", self.visit(ctx.typeSpecifier())
        if ctx.typeQualifier():
            return "type_qualifier", self.visit(ctx.typeQualifier())
        if ctx.functionSpecifier():
            return "function_specifier", self.visit(ctx.functionSpecifier())
        raise SemanticError('impossible')

    def visitDeclarator(self, ctx: CCompilerParser.DeclaratorContext):
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

            def pointer_declarator(typ: ir.Type, specifier):
                identifier1, typ1, parameter_list1 = declarator_func(typ, specifier)
                for _ in pointer:
                    typ1 = typ1.as_pointer()
                return identifier1, typ1, parameter_list1
            return pointer_declarator
        return declarator_func

    def visitForDeclaration(self, ctx: CCompilerParser.ForDeclarationContext) -> None:
        """
        声明.

        语法规则：
            forDeclaration
                :   declarationSpecifiers initDeclaratorList ';'
                | 	declarationSpecifiers ';'
                ;

        Args:
            ctx (CCompilerParser.DeclarationContext):

        Returns:
            None
        """
        specifiers: DeclarationSpecifiers = self.visit(ctx.declarationSpecifiers())
        if ctx.initDeclaratorList():
            init_decl_list = self.visit(ctx.initDeclaratorList())
        else:
            init_decl_list = []
        base_type = specifiers.get_type()
        if base_type is None:
            raise SemanticError("Unspecified declarator type", ctx)
        for decl, initializer in init_decl_list:
            identifier, typ, parameter_list = decl(base_type, specifiers)
            if specifiers.is_typedef():
                if initializer is not None:
                    raise SemanticError("Illegal initializer (only variables can be initialized)", ctx)
                result = self.symbol_table.add_item(identifier, typ)
                if not result.success:
                    raise SemanticError("Symbol redefined: " + identifier, ctx)
            else:
                if self.is_global_scope():
                    if self.symbol_table.exist(identifier):
                        raise SemanticError("Symbol redefined: " + identifier, ctx)
                    if isinstance(typ, ir.FunctionType):
                        variable = ir.Function(self.module, typ, identifier)
                        self.functions[identifier] = variable
                        self.symbol_table.add_item(identifier, TypedValue(ir_value=variable,
                                                                          typ=variable.type,
                                                                          constant=False,
                                                                          name=identifier,
                                                                          lvalue_ptr=False))
                    else:
                        variable = ir.GlobalVariable(self.module, typ, identifier)
                        self.symbol_table.add_item(identifier, TypedValue(ir_value=variable,
                                                                          typ=typ,
                                                                          constant=False,
                                                                          name=identifier,
                                                                          lvalue_ptr=True))
                        if initializer is not None:
                            variable.initializer = self.load_lvalue(initializer)
                else:
                    ir_builder = self.builder
                    variable = ir_builder.alloca(typ, 1, identifier)
                    result = self.symbol_table.add_item(identifier, TypedValue(ir_value=variable,
                                                                               typ=typ,
                                                                               constant=False,
                                                                               name=identifier,
                                                                               lvalue_ptr=True))
                    if not result.success:
                        raise SemanticError("Symbol redefined: " + identifier, ctx)
                    if initializer:
                        ir_builder.store(self.convert_type(initializer, typ, ctx), variable)

    def visitInitDeclarator(self, ctx: CCompilerParser.InitDeclaratorContext):
        """
        初始化声明.

        语法规则:
            initDeclarator
                :   declarator
                |   declarator '=' initializer
                ;
        Returns:
            lambda typ : (str, ir.Type, Optional[ParameterList])
                str: 标识符
                ir.Type: 类型
                Optional[ParameterList]: 参数列表 (对于函数声明/定义有效)
            initializer: ir.Value
        """
        declarator = self.visit(ctx.declarator())
        initializer_ctx = ctx.initializer()
        if initializer_ctx is not None:
            initializer = self.visit(ctx.initializer())
        else:
            initializer = None
        return declarator, initializer

    def visitInitDeclaratorList(self, ctx: CCompilerParser.InitDeclaratorListContext) -> List[tuple]:
        """
        初始化声明列表.

        语法规则:
            initDeclaratorList
                :   initDeclarator
                |   initDeclaratorList ',' initDeclarator
                ;
        Returns:
            List[tuple]: 一串初始化声明，列表的成员定义见 Generator#visitInitDeclarator
        """
        init_declarator_list_ctx = ctx.initDeclaratorList()
        if init_declarator_list_ctx is not None:
            init_declarator_list = self.visit(ctx.initDeclaratorList())
        else:
            init_declarator_list = []
        init_declarator_list.append(self.visit(ctx.initDeclarator()))
        return init_declarator_list

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

    def visitTypeSpecifier_1(self, ctx: CCompilerParser.TypeSpecifier_3Context) -> ir.Type:
        # typeSpecifier : primitiveType
        return self.visit(ctx.primitiveType())

    def visitTypeSpecifier_2(self, ctx: CCompilerParser.TypeSpecifier_2Context) -> ir.Type:
        # typeSpecifier : typedefName
        type_id: str = ctx.getText()
        actual_type = self.symbol_table.get_item(type_id)
        if actual_type is None:
            raise SemanticError("Undefined type: " + type_id, ctx)
        if not isinstance(actual_type, ir.Type):
            raise SemanticError("Invalid type: " + type_id, ctx)
        return actual_type

    def visitTypeSpecifier_3(self, ctx: CCompilerParser.TypeSpecifier_1Context) -> ir.Type:
        # typeSpecifier : typeSpecifier pointer
        base_type: ir.Type = self.visit(ctx.typeSpecifier())
        pointer_list: list = self.visit(ctx.pointer())
        for _ in pointer_list:  # const 之类的访问修饰符被省略
            base_type = base_type.as_pointer()
        return base_type

    def visitCompoundStatement(self, ctx: CCompilerParser.CompoundStatementContext) -> None:
        self.symbol_table.enter_scope()
        self.visitChildren(ctx)
        self.symbol_table.quit_scope()

    def visitSelectionStatement(self, ctx: CCompilerParser.SelectionStatementContext) -> None:
        """
        selectionStatement
            : 'if' '(' expression ')' statement ('else' statement)?
            | 'switch' '(' expression ')' statement
            ;
        """
        kw = ctx.getChild(0).getText()
        if kw == 'if':
            has_else = len(ctx.statement()) > 1
            builder = self.builder
            block_true = builder.append_basic_block(name='if.then')
            blocks = [block_true]
            if has_else:
                block_false = builder.append_basic_block(name='if.else')
                block_end = builder.append_basic_block(name='if.end')
                blocks.append(block_false)
            else:
                block_end = builder.append_basic_block(name='if.end')
                block_false = block_end
            cond = self.ir_bool(self.visit(ctx.expression()))
            builder.cbranch(cond, block_true, block_false)
            for i, block in enumerate(blocks):
                self.builder = ir.IRBuilder(block)
                self.visit(ctx.statement()[i])
                if not self.builder.basic_block.is_terminated:
                    self.builder.branch(block_end)
            self.builder = ir.IRBuilder(block_end)
            return
        if kw == 'switch':
            raise SemanticError("Not implemented", ctx)
        raise SemanticError('impossible')

    def visitIterationStatement(self, ctx: CCompilerParser.SelectionStatementContext) -> None:
        """
        iterationStatement
            : 'while' '(' expression ')' statement
            | 'do' statement 'while' '(' expression ')' ';'
            | 'for' '(' forCondition ')' statement
            ;
        """
        kw = ctx.getChild(0).getText()
        if ctx.first:
            self.symbol_table.enter_scope()
            self.visit(ctx.first)
        block_cond = self.builder.append_basic_block(name='loop.cond')
        block_body = self.builder.append_basic_block(name='loop.body')
        block_end = self.builder.append_basic_block(name='loop.end')
        # Terminate last block
        if kw == 'do':
            self.builder.branch(block_body)
        else:
            self.builder.branch(block_cond)
        # Build blocks
        self.builder = ir.IRBuilder(block_cond)
        if kw == 'for':
            cond_ctx = ctx.second
        else:
            cond_ctx = ctx.expression()
        if cond_ctx:
            cond = self.ir_bool(self.visit(cond_ctx))
            self.builder.cbranch(cond, block_body, block_end)
        else:
            self.builder.branch(block_body)
        if ctx.third:
            block_update = self.builder.append_basic_block(name='loop.update')
            self.builder = ir.IRBuilder(block_update)
            self.visit(ctx.third)
            self.builder.branch(block_cond)
            self.continue_blocks.append(block_update)
        else:
            self.continue_blocks.append(block_cond)
        self.break_blocks.append(block_end)
        self.builder = ir.IRBuilder(block_body)
        self.visit(ctx.statement())
        if not self.builder.basic_block.is_terminated:
            self.builder.branch(self.continue_blocks[-1])
        self.continue_blocks.pop()
        self.break_blocks.pop()
        if ctx.first:
            self.symbol_table.quit_scope()
        self.builder = ir.IRBuilder(block_end)

    def visitJumpStatement(self, ctx: CCompilerParser.JumpStatementContext) -> None:
        """
        jumpStatement
            : 'continue' ';'
            | 'break' ';'
            | 'return' expression? ';'
            ;
        """
        kw = ctx.getChild(0).getText()
        if kw == 'continue':
            if not self.continue_blocks:
                raise SemanticError('Nothing to continue', ctx)
            self.builder.branch(self.continue_blocks[-1])
            return
        if kw == 'break':
            if not self.break_blocks:
                raise SemanticError('Nothing to break', ctx)
            self.builder.branch(self.break_blocks[-1])
            return
        if kw == 'return':
            ret_value_ctx = ctx.expression()
            ret_value = None
            builder = self.builder
            if ret_value_ctx is not None:
                ret_value = self.visit(ret_value_ctx)
                builder.ret(self.load_lvalue(ret_value))
            else:
                builder.ret_void()
            return
        raise SemanticError('impossible')

    def visitStructSpecifier_1(self, ctx:CCompilerParser.StructSpecifier_1Context) -> ElementNamedLiteralStructType:
        # structSpecifier : 'struct' Identifier? '{' structDeclarationList '}'
        identifier_ctx = ctx.Identifier()
        if identifier_ctx is not None:
            identifier = f'struct {identifier_ctx.getText()}'
            item = self.symbol_table.get_item(identifier)
            if item is not None:
                raise SemanticError("Symbol redefined: " + identifier)
        else:
            identifier = None
        struct_member_list = self.visit(ctx.structDeclarationList())
        type_list = [member[0] for member in struct_member_list]
        name_list = [member[1] for member in struct_member_list]
        struct_type = ElementNamedLiteralStructType(type_list, name_list)
        if identifier:
            self.symbol_table.add_item(identifier, struct_type)
        return struct_type

    def visitStructSpecifier_2(self, ctx: CCompilerParser.StructSpecifier_2Context) -> ElementNamedLiteralStructType:
        # structSpecifier : 'struct' Identifier
        identifier = f'struct {ctx.Identifier().getText()}'
        item = self.symbol_table.get_item(identifier)
        if item is None:
            raise SemanticError("Undefined identifier: " + identifier)
        return item

    def visitStructDeclarationList(self, ctx: CCompilerParser.StructDeclarationListContext) -> List[Tuple[ir.Type, str]]:
        """
        语法规则：
            structDeclarationList
                :   structDeclaration
                |   structDeclarationList structDeclaration
                ;
        """
        if ctx.structDeclarationList():
            prev_list = self.visit(ctx.structDeclarationList())
        else:
            prev_list = []
        prev_list += self.visit(ctx.structDeclaration())
        return prev_list

    def visitStructDeclaration(self, ctx: CCompilerParser.StructDeclarationContext) -> List[Tuple[ir.Type, str]]:
        # structDeclaration : declarationSpecifiers structDeclaratorList ';' ;
        specifiers: DeclarationSpecifiers = self.visit(ctx.declarationSpecifiers())
        decl_list = self.visit(ctx.structDeclaratorList())
        base_type: ir.Type = specifiers.get_type()
        if base_type is None:
            raise SemanticError("Unspecified declarator type", ctx)
        member_list = []
        for decl in decl_list:
            identifier, typ, parameter_list = decl(base_type)
            if specifiers.is_typedef():
                raise SemanticError("Illegal typedef here")
            member_list.append((typ, identifier))
        return member_list

    def visitStructDeclaratorList(self, ctx:CCompilerParser.StructDeclaratorListContext):
        """
        语法规则:
            structDeclaratorList
                :   declarator
                |   structDeclaratorList ',' declarator
                ;
        """
        if ctx.structDeclaratorList():
            prev_list = self.visit(ctx.structDeclaratorList())
        else:
            prev_list = []
        prev_list.append(self.visit(ctx.declarator()))
        return prev_list

    def load_lvalue(self, lvalue_ptr: TypedValue) -> Union[ir.Value, ir.NamedValue]:
        """
        从左值地址加载出一个值.
        如果是数组，不会被加载. 不要试图加载数组.

        :param lvalue_ptr: 待加载的值
        :type lvalue_ptr: TypedValue
        :return: 如果这个值是右值，返回原始值，否则返回加载后的值
        :rtype: ir.Value
        """
        if not lvalue_ptr.lvalue_ptr or isinstance(lvalue_ptr.type, ir.ArrayType):
            return lvalue_ptr.ir_value
        builder = self.builder
        return builder.load(lvalue_ptr.ir_value)

    def store_lvalue(self, value: ir.Value, lvalue_ptr: TypedValue, new_type: ir.Type = None) -> None:
        """
        将值存入左值地址处.

        :param value: 待存储的值
        :type value: ir.Value
        :param lvalue_ptr: 左值的地址(的 TypedValue)
        :type lvalue_ptr: TypedValue
        :param new_type: 如果不为 None，则替换旧类型
        :type new_type: ir.Type
        :return: 如果 lvalue_ptr 是右值，则替换原来的 value，存储 value 至 lvalue_ptr 处
        :rtype: None
        """
        if not lvalue_ptr.lvalue_ptr:
            lvalue_ptr.ir_value = value
        else:
            builder = self.builder
            builder.store(value, lvalue_ptr.ir_value)

        if new_type is not None:
            lvalue_ptr.type = new_type

    def str_constant(self, str_value: str) -> TypedValue:
        if str_value in self.string_constants:
            return self.string_constants[str_value]
        str_bytes = bytearray(str_value + "\0", "utf-8")
        variable_name = ".str" + str(len(self.string_constants))
        ir_value = ir.GlobalVariable(self.module, ir.ArrayType(int8, len(str_bytes)), variable_name)
        ir_value.initializer = ir.Constant(ir.ArrayType(int8, len(str_bytes)), str_bytes)
        typed_value = TypedValue(ir_value, typ=ir_value.type, constant=True)
        self.string_constants[str_value] = typed_value
        return typed_value

    def typed_bool(self, value: TypedValue, negation: bool = False) -> TypedValue:
        # 根据值是否为 0 转为 TypedValue(int1)
        if negation:
            op = '=='
        else:
            op = '!='
        builder = self.builder
        rvalue = self.load_lvalue(value)
        new_v1, new_v2, new_type = self.bit_extend(rvalue, int32_zero)
        if new_type == double:
            result: ir.Instruction = builder.fcmp_ordered(op, new_v1, new_v2)
        else:
            result: ir.Instruction = builder.icmp_signed(op, new_v1, new_v2)
        return TypedValue(result, int1, constant=False, name=None, lvalue_ptr=False)

    def ir_bool(self, value: TypedValue, negation: bool = False) -> int1:
        # 根据值是否为 0 转为 int1
        return self.typed_bool(value, negation=negation).ir_value

    def bit_extend(self, value1, value2, ctx=None) -> Tuple[Any, Any, ir.Type]:
        """
        将 value1 和 value2 拓展成相同的位数, 都为 ir.Value.
        目前为方便起见，若有浮点数，都拓展为 Double

        :param value1:
        :type value1:
        :param value2:
        :type value2:
        :param ctx: 用于报错
        :return:
        :rtype:
        """
        builder = self.builder
        if isinstance(value1.type, ir.types.DoubleType) and not isinstance(value2.type, ir.types.DoubleType):
            new_v1 = value1
            new_v2 = builder.sitofp(value2, double)
            return new_v1, new_v2, double
        elif not isinstance(value1.type, ir.types.DoubleType) and isinstance(value2.type, ir.types.DoubleType):
            new_v1 = builder.sitofp(value1, double)
            new_v2 = value2
            return new_v1, new_v2, double
        elif isinstance(value1.type, ir.types.DoubleType) and isinstance(value2.type, ir.types.DoubleType):
            return value1, value2, double
        elif isinstance(value1.type, ir.types.IntType) and isinstance(value2.type, ir.types.IntType):
            new_type = value1.type if value1.type.width >= value2.type.width else value2.type
            new_v1 = builder.sext(value1, new_type)
            new_v2 = builder.sext(value2, new_type)
            return new_v1, new_v2, new_type

        raise SemanticError('Bit extend error.', ctx=ctx)

    def convert_type(self, value: TypedValue, type: ir.Type, ctx=None) -> ir.Value:
        """
        将 ir_value 转为 type 类型.

        :param value:
        :type value:
        :param type:
        :type type:
        :param ctx:
        :type ctx:
        :return: 转换后的 ir.Value
        :rtype:
        """
        builder = self.builder
        ir_value = self.load_lvalue(value)
        if value.type == type:
            return ir_value
        elif value.type in int_types:
            if type in int_types:
                if type.width <= value.type.width:
                    return builder.trunc(ir_value, type)
                else:
                    return builder.sext(ir_value, type)
            elif type == double:
                return builder.sitofp(ir_value, type)
            elif type.is_pointer:
                return builder.inttoptr(ir_value, type)
            else:
                raise SemanticError('Not supported type conversion.', ctx=ctx)
        elif value.type == double:
            if type in int_types:
                return builder.fptosi(ir_value, type)
            elif type == double:
                return value.ir_value
            elif type.is_pointer:
                raise SemanticError('Illegal type conversion.', ctx=ctx)
            else:
                raise SemanticError('Not supported type conversion.', ctx=ctx)
        elif value.type.is_pointer:
            if type in int_types:
                return builder.ptrtoint(ir_value, type)
            elif type == double:
                raise SemanticError('Illegal type conversion.', ctx=ctx)
            elif type.is_pointer:
                return builder.bitcast(ir_value, type)
            else:
                raise SemanticError('Not supported type conversion.', ctx=ctx)
        elif isinstance(value.type, ir.ArrayType):
            if type.is_pointer:
                type: ir.PointerType
                value_type: ir.ArrayType = value.type
                if type.pointee != value_type.element:
                    raise SemanticError(f'Invalid conversion from {value_type} to {type}.', ctx=ctx)
                return builder.gep(ir_value, [int32_zero, int32_zero], inbounds=False)
            else:
                raise SemanticError('Not supported type conversion.', ctx=ctx)
        else:
            raise SemanticError('Not supported type conversion.', ctx=ctx)

    def visitConstant(self, ctx: CCompilerParser.ConstantContext) -> TypedValue:
        text = ctx.getText()
        if ctx.IntegerConstant():
            if re.fullmatch('0[0-7]*', text):
                value = int(text, 8)
            else:
                value = int(text, 0)
            return const_value(ir.Constant(int32, value))
        if ctx.FloatingConstant():
            return const_value(ir.Constant(double, float(text)))
        if ctx.CharacterConstant():
            return const_value(ir.Constant(int8, ord(text[1])))
        raise SemanticError('impossible')

    def visitPrimaryExpression(self, ctx: CCompilerParser.PrimaryExpressionContext) -> TypedValue:
        """
        Primary Expression
        """
        if ctx.Identifier():
            identifier = ctx.getText()
            item = self.symbol_table.get_item(identifier)
            if item is None:
                raise SemanticError("Undefined identifier: " + identifier)
            return item
        if ctx.StringLiteral():
            str_result = ""
            for childCtx in ctx.StringLiteral():
                str_result += childCtx.getText()[1:-1].encode('utf-8').decode('unicode_escape')
            return self.str_constant(str_result)
        if ctx.constant():
            return self.visit(ctx.constant())
        if ctx.expression():
            return self.visit(ctx.expression())
        raise SemanticError('impossible')

    def visitPrimitiveType(self, ctx: CCompilerParser.PrimitiveTypeContext) -> ir.Type:
        """
        Primitive type
        """
        return self.symbol_table.get_item(ctx.getText())

    def visitPostfixExpression_1(self, ctx: CCompilerParser.PostfixExpression_1Context) -> TypedValue:
        # primaryExpression
        v1: TypedValue = self.visit(ctx.getChild(0))
        return v1
        # pass

    def visitPostfixExpression_2(self, ctx: CCompilerParser.PostfixExpression_2Context) -> TypedValue:
        # postfixExpression '[' expression ']'
        v1: TypedValue = self.visit(ctx.getChild(0))
        builder = self.builder
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
            result_type = v1.type.pointee
        elif is_array:
            result = builder.gep(base_ptr, [int32_zero, offset], inbounds=True)
            result_type = v1.type.element
        else:
            raise SemanticError("Postfix expression(#2) is not a array or pointer.", ctx=ctx)
        return TypedValue(result, result_type, constant=False, name=None, lvalue_ptr=True)

    def visitPostfixExpression_3(self, ctx: CCompilerParser.PostfixExpression_3Context) -> TypedValue:
        # postfixExpression '(' argumentExpressionList? ')'
        # 函数调用
        func_value: TypedValue = self.visit(ctx.postfixExpression())
        if func_value is None:
            raise SemanticError('Function not declared')
        func_pointer = self.load_lvalue(func_value)
        if not func_pointer.type.is_pointer:
            raise SemanticError('Invalid function.')
        func_type: ir.FunctionType = func_pointer.type.pointee
        if ctx.argumentExpressionList():
            argument_expressions = self.visit(ctx.argumentExpressionList())
        else:
            argument_expressions = []
        func_args = []
        func_arg_count = len(func_type.args)
        if func_type.var_arg:
            if len(argument_expressions) < func_arg_count:
                raise SemanticError("Too few arguments")
        else:
            if len(argument_expressions) != func_arg_count:
                raise SemanticError("Incorrect number of arguments")
        for i in range(len(argument_expressions)):
            if i < func_arg_count:
                func_args.append(self.convert_type(argument_expressions[i], func_type.args[i], ctx))
            else:
                if isinstance(argument_expressions[i].type, ir.ArrayType):
                    func_args.append(self.convert_type(argument_expressions[i],
                                                       argument_expressions[i].type.element.as_pointer(),
                                                       ctx))
                else:
                    func_args.append(self.load_lvalue(argument_expressions[i]))
        ret_value = self.builder.call(func_pointer, func_args)
        return TypedValue(ir_value=ret_value, typ=ret_value.type, constant=False, name=None, lvalue_ptr=False)

    def visitPostfixExpression_4(self, ctx: CCompilerParser.PostfixExpression_4Context) -> TypedValue:
        # postfixExpression '.' Identifier
        v1: TypedValue = self.visit(ctx.getChild(0))
        builder = self.builder
        if not v1.lvalue_ptr:
            raise SemanticError('Postfix Expression(#2) needs lvalue.', ctx=ctx)
        rvalue: ir.NamedValue = self.load_lvalue(v1)
        if not isinstance(rvalue.type, ElementNamedLiteralStructType):
            raise SemanticError("Postfix expression(#4) is not literal struct.", ctx=ctx)
        member_name = ctx.Identifier().getText()
        ls_type: ElementNamedLiteralStructType = rvalue.type
        try:
            member_index = ls_type.index(member_name)
            member_type = ls_type.elements[member_index]
        except ValueError:
            raise SemanticError("Postfix expression(#4) has not such attribute.", ctx=ctx)
        # 获得地址
        result = builder.gep(v1.ir_value, [int32_zero, ir.Constant(int32, member_index)], inbounds=False)
        return TypedValue(result, member_type, constant=False, name=None, lvalue_ptr=True)

    def visitPostfixExpression_5(self, ctx: CCompilerParser.PostfixExpression_5Context) -> TypedValue:
        # postfixExpression '->' Identifier
        v1: TypedValue = self.visit(ctx.getChild(0))
        builder = self.builder
        rvalue: ir.NamedValue = self.load_lvalue(v1)  # 这里事实上获得一个指针
        if not isinstance(rvalue.type, ir.types.PointerType):
            raise SemanticError("Postfix expression(#5) is not pointer.", ctx=ctx)
        # 转到结构体类型
        pointee_type = v1.type.pointee
        member_name = ctx.Identifier().getText()
        ls_type: ElementNamedLiteralStructType = pointee_type
        try:
            member_index = ls_type.index(member_name)
            member_type = ls_type.elements[member_index]
        except ValueError:
            raise SemanticError("Postfix expression(#5) has not such attribute.", ctx=ctx)
        # 获得地址
        result = builder.gep(rvalue, [int32_zero, ir.Constant(int32, member_index)], inbounds=False)
        return TypedValue(result, member_type, constant=False, name=None, lvalue_ptr=True)

    def visitPostfixExpression_6(self, ctx: CCompilerParser.PostfixExpression_6Context) -> TypedValue:
        # postfixExpression '++'
        v1: TypedValue = self.visit(ctx.getChild(0))
        builder = self.builder
        rvalue = self.load_lvalue(v1)
        result = builder.add(rvalue, ir.Constant(v1.type, 1))
        self.store_lvalue(result, v1)
        return TypedValue(rvalue, v1.type, constant=False, name=None, lvalue_ptr=False)

    def visitPostfixExpression_7(self, ctx: CCompilerParser.PostfixExpression_7Context) -> TypedValue:
        # postfixExpression '--'
        v1: TypedValue = self.visit(ctx.getChild(0))
        builder = self.builder
        rvalue = self.load_lvalue(v1)
        result = builder.sub(rvalue, ir.Constant(v1.type, 1))
        self.store_lvalue(result, v1)
        return TypedValue(rvalue, v1.type, constant=False, name=None, lvalue_ptr=False)

    def visitArgumentExpressionList(self, ctx: CCompilerParser.ArgumentExpressionListContext) -> List[TypedValue]:
        """
        语法规则:
        argumentExpressionList
            :   assignmentExpression
            |   argumentExpressionList ',' assignmentExpression
            ;
        @return: expression 的计算结果列表
        """
        arg_expr_list_ctx = ctx.argumentExpressionList()
        if arg_expr_list_ctx is not None:
            arg_expr_list = self.visit(ctx.argumentExpressionList())
        else:
            arg_expr_list = []
        arg_expr_list.append(self.visit(ctx.assignmentExpression()))
        return arg_expr_list

    def visitUnaryExpression_1(self, ctx: CCompilerParser.UnaryExpression_1Context) -> TypedValue:
        # postfixExpression
        return self.visit(ctx.getChild(0))

    def visitUnaryExpression_2(self, ctx: CCompilerParser.UnaryExpression_2Context) -> TypedValue:
        # '++' unaryExpression
        v1: TypedValue = self.visit(ctx.unaryExpression())
        builder = self.builder
        rvalue = self.load_lvalue(v1)
        result = builder.add(rvalue, ir.Constant(v1.type, 1))
        self.store_lvalue(result, v1)
        return v1

    def visitUnaryExpression_3(self, ctx: CCompilerParser.UnaryExpression_3Context) -> TypedValue:
        # '--' unaryExpression
        v1 = self.visit(ctx.unaryExpression())
        builder = self.builder
        rvalue = self.load_lvalue(v1)
        result = builder.sub(rvalue, ir.Constant(v1.type, 1))
        self.store_lvalue(result, v1)
        return v1

    def visitUnaryExpression_4(self, ctx: CCompilerParser.UnaryExpression_4Context) -> TypedValue:
        # unaryOperator castExpression
        op: str = ctx.unaryOperator().getText()
        v2: TypedValue = self.visit(ctx.castExpression())
        builder = self.builder
        # '&' | '*' | '+' | '-' | '~' | '!'
        if op == '&':
            # 必须对左值取地址
            if not v2.lvalue_ptr:
                raise SemanticError('Operator & needs a lvalue.', ctx=ctx)
            return TypedValue(v2.ir_value, v2.type.as_pointer(), constant=False, name=None, lvalue_ptr=False)
        elif op == '*':
            pointer_type: ir.PointerType = v2.type
            if not pointer_type.is_pointer:
                raise SemanticError('Operator * needs a pointer.', ctx=ctx)
            if v2.lvalue_ptr:
                # v2 是存放指针类型的左值时
                ptr_value = self.load_lvalue(v2)
                return TypedValue(ptr_value, pointer_type.pointee, constant=False, name=None, lvalue_ptr=True)
            else:
                return TypedValue(v2.ir_value, pointer_type.pointee, constant=False, name=None, lvalue_ptr=True)
        elif op == '+':
            return self.visit(ctx.castExpression())
        elif op == '-':
            rvalue = self.load_lvalue(v2)
            result: ir.Instruction = builder.neg(rvalue)
            return TypedValue(result, v2.type, constant=False, name=None, lvalue_ptr=False)
        elif op == '~':
            rvalue = self.load_lvalue(v2)
            result: ir.Instruction = builder.not_(rvalue)
            return TypedValue(result, v2.type, constant=False, name=None, lvalue_ptr=False)
        elif op == '!':
            return self.typed_bool(v2, negation=True)

    def visitUnaryExpression_5(self, ctx: CCompilerParser.UnaryExpression_5Context) -> TypedValue:
        # 'sizeof' unaryExpression
        # TODO 不知道返回什么类型
        raise SemanticError('Not implemented yet.', ctx=ctx)

    def visitUnaryExpression_6(self, ctx: CCompilerParser.UnaryExpression_6Context) -> TypedValue:
        # 'sizeof' '(' typeName ')'
        # TODO 不知道返回什么类型
        raise SemanticError('Not implemented yet.', ctx=ctx)

    def visitCastExpression_1(self, ctx: CCompilerParser.CastExpression_1Context) -> TypedValue:
        # '(' typeName ')' castExpression
        # TODO 需要直到 type 在哪里获取
        raise SemanticError('Not implemented yet.', ctx=ctx)

    def visitCastExpression_2(self, ctx: CCompilerParser.CastExpression_2Context) -> TypedValue:
        # unaryExpression
        return self.visitChildren(ctx)

    def visitMultiplicativeExpression_2(self, ctx: CCompilerParser.MultiplicativeExpression_2Context):
        # multiplicativeExpression '*' castExpression
        v1: TypedValue = self.visit(ctx.multiplicativeExpression())
        v2: TypedValue = self.visit(ctx.castExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            result = builder.fmul(new_rvalue1, new_rvalue2)
        else:
            result = builder.mul(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitMultiplicativeExpression_3(self, ctx: CCompilerParser.MultiplicativeExpression_3Context):
        # multiplicativeExpression '/' castExpression
        v1: TypedValue = self.visit(ctx.multiplicativeExpression())
        v2: TypedValue = self.visit(ctx.castExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            result = builder.fdiv(new_rvalue1, new_rvalue2)
        else:
            result = builder.sdiv(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitMultiplicativeExpression_4(self, ctx: CCompilerParser.MultiplicativeExpression_4Context):
        # multiplicativeExpression '%' castExpression
        v1: TypedValue = self.visit(ctx.multiplicativeExpression())
        v2: TypedValue = self.visit(ctx.castExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            result = builder.frem(new_rvalue1, new_rvalue2)
        else:
            result = builder.srem(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitAdditiveExpression_2(self, ctx: CCompilerParser.AdditiveExpression_2Context):
        # additiveExpression '+' multiplicativeExpression
        v1: TypedValue = self.visit(ctx.additiveExpression())
        v2: TypedValue = self.visit(ctx.multiplicativeExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            result = builder.fadd(new_rvalue1, new_rvalue2)
        else:
            result = builder.add(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitAdditiveExpression_3(self, ctx: CCompilerParser.AdditiveExpression_3Context):
        # additiveExpression '-' multiplicativeExpression
        v1: TypedValue = self.visit(ctx.additiveExpression())
        v2: TypedValue = self.visit(ctx.multiplicativeExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            result = builder.fsub(new_rvalue1, new_rvalue2)
        else:
            result = builder.sub(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitShiftExpression_2(self, ctx: CCompilerParser.ShiftExpression_2Context):
        # shiftExpression '<<' additiveExpression
        v1: TypedValue = self.visit(ctx.shiftExpression())
        v2: TypedValue = self.visit(ctx.additiveExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            raise SemanticError('Bitwise shifting is only available to integer.')
        else:
            result = builder.shl(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitShiftExpression_3(self, ctx: CCompilerParser.ShiftExpression_3Context):
        # shiftExpression '>>' additiveExpression
        v1: TypedValue = self.visit(ctx.shiftExpression())
        v2: TypedValue = self.visit(ctx.additiveExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            raise SemanticError('Bitwise shifting is only available to integer.')
        else:
            result = builder.ashr(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def _relational_expression(self, op: str, ctx: ParserRuleContext):
        v1: TypedValue = self.visit(ctx.getChild(0))
        v2: TypedValue = self.visit(ctx.getChild(2))
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            result = builder.fcmp_ordered(op, new_rvalue1, new_rvalue2)
        else:
            result = builder.add(new_rvalue1, new_rvalue2)
            result = builder.icmp_signed(op, new_rvalue1, new_rvalue2)
        return TypedValue(result, int1, constant=False, name=None, lvalue_ptr=False)

    def visitRelationalExpression_2(self, ctx: CCompilerParser.RelationalExpression_2Context):
        # relationalExpression '<' shiftExpression
        return self._relational_expression('<', ctx)

    def visitRelationalExpression_3(self, ctx: CCompilerParser.RelationalExpression_3Context):
        # relationalExpression '>' shiftExpression
        return self._relational_expression('>', ctx)

    def visitRelationalExpression_4(self, ctx: CCompilerParser.RelationalExpression_4Context):
        # relationalExpression '<=' shiftExpression
        return self._relational_expression('<=', ctx)

    def visitRelationalExpression_5(self, ctx: CCompilerParser.RelationalExpression_5Context):
        # relationalExpression '>=' shiftExpression
        return self._relational_expression('>=', ctx)

    def visitEqualityExpression_2(self, ctx: CCompilerParser.EqualityExpression_2Context):
        # equalityExpression '==' relationalExpression
        return self._relational_expression('==', ctx)

    def visitEqualityExpression_3(self, ctx: CCompilerParser.EqualityExpression_3Context):
        # equalityExpression '!=' relationalExpression
        return self._relational_expression('!=', ctx)

    def visitAndExpression_2(self, ctx: CCompilerParser.AndExpression_2Context):
        # andExpression '&' equalityExpression
        v1: TypedValue = self.visit(ctx.andExpression())
        v2: TypedValue = self.visit(ctx.equalityExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            raise SemanticError('Bitwise operation is only available to integer.')
        else:
            result = builder.and_(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitExclusiveOrExpression_2(self, ctx: CCompilerParser.ExclusiveOrExpression_2Context):
        # exclusiveOrExpression '^' andExpression
        v1: TypedValue = self.visit(ctx.exclusiveOrExpression())
        v2: TypedValue = self.visit(ctx.andExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            raise SemanticError('Bitwise operation is only available to integer.')
        else:
            result = builder.xor(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitInclusiveOrExpression_2(self, ctx: CCompilerParser.InclusiveOrExpression_2Context):
        # inclusiveOrExpression '|' exclusiveOrExpression
        v1: TypedValue = self.visit(ctx.inclusiveOrExpression())
        v2: TypedValue = self.visit(ctx.exclusiveOrExpression())
        rvalue1 = self.load_lvalue(v1)
        rvalue2 = self.load_lvalue(v2)
        new_rvalue1, new_rvalue2, new_type = self.bit_extend(rvalue1, rvalue2, ctx)
        builder = self.builder
        if new_type == double:
            raise SemanticError('Bitwise operation is only available to integer.')
        else:
            result = builder.or_(new_rvalue1, new_rvalue2)
        return TypedValue(result, new_type, constant=False, name=None, lvalue_ptr=False)

    def visitLogicalAndExpression(self, ctx: CCompilerParser.LogicalAndExpressionContext):
        """
        logicalAndExpression
            : inclusiveOrExpression
            | logicalAndExpression '&&' inclusiveOrExpression
            ;
        """
        return self._visitLogicalExpression(ctx)

    def visitLogicalOrExpression(self, ctx: CCompilerParser.LogicalOrExpressionContext):
        """
        logicalOrExpression
            : logicalAndExpression
            | logicalOrExpression '||' logicalAndExpression
            ;
        """
        return self._visitLogicalExpression(ctx)

    def _visitLogicalExpression(self, ctx: ParserRuleContext):
        if ctx.getChildCount() == 1:
            return self.visitChildren(ctx)

        block_rhs = self.builder.append_basic_block(name='logical.rhs')
        block_end = self.builder.append_basic_block(name='logical.end')

        value_entry = self.ir_bool(self.visit(ctx.getChild(0)))
        op = ctx.getChild(1).getText()
        if op == '&&':
            self.builder.cbranch(value_entry, block_rhs, block_end)
        elif op == '||':
            self.builder.cbranch(value_entry, block_end, block_rhs)
        block_entry = self.builder.basic_block

        self.builder = ir.IRBuilder(block_rhs)
        value_rhs = self.ir_bool(self.visit(ctx.getChild(2)))
        self.builder.branch(block_end)
        block_rhs = self.builder.basic_block

        self.builder = ir.IRBuilder(block_end)
        result = self.builder.phi(int1)
        result.add_incoming(value_entry, block_entry)
        result.add_incoming(value_rhs, block_rhs)
        return TypedValue(result, int1, constant=False, name=None, lvalue_ptr=False)

    def visitConditionalExpression(self, ctx: CCompilerParser.ConditionalExpressionContext):
        # logicalOrExpression ('?' expression ':' conditionalExpression)?
        first = self.visit(ctx.logicalOrExpression())
        if ctx.getChildCount() == 1:
            return first

        block_true = self.builder.append_basic_block(name='ternary.true')
        block_false = self.builder.append_basic_block(name='ternary.false')
        block_end = self.builder.append_basic_block(name='ternary.end')

        cond = self.ir_bool(first)
        self.builder.cbranch(cond, block_true, block_false)

        self.builder = ir.IRBuilder(block_true)
        value_true = self.visit(ctx.expression()).ir_value
        self.builder.branch(block_end)
        block_true = self.builder.basic_block

        self.builder = ir.IRBuilder(block_false)
        value_false = self.visit(ctx.conditionalExpression()).ir_value
        self.builder.branch(block_end)
        block_false = self.builder.basic_block

        self.builder = ir.IRBuilder(block_end)
        result = self.builder.phi(value_true.type)
        result.add_incoming(value_true, block_true)
        result.add_incoming(value_false, block_false)
        return TypedValue(result, int1, constant=False, name=None, lvalue_ptr=False)

    def visitAssignmentExpression_2(self, ctx: CCompilerParser.AssignmentExpression_2Context):
        # unaryExpression assignmentOperator assignmentExpression
        v1: TypedValue = self.visit(ctx.unaryExpression())
        op: str = ctx.assignmentOperator().getText()
        v3: TypedValue = self.visit(ctx.assignmentExpression())
        builder = self.builder
        # lhs 必须为左值
        if not v1.lvalue_ptr:
            raise SemanticError('Assignment needs a lvalue at left.', ctx=ctx)
        rvalue1 = self.load_lvalue(v1)
        rvalue3 = self.load_lvalue(v3)
        # '=' | '*=' | '/=' | '%=' | '+=' | '-=' | '<<=' | '>>=' | '&=' | '^=' | '|='
        if op == '=':
            result = self.convert_type(v3, v1.type, ctx=ctx)
        elif op == '*=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type != double:
                result = builder.mul(rvalue1, tmp)
            else:
                result = builder.fmul(rvalue1, tmp)
        elif op == '/=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type != double:
                result = builder.sdiv(rvalue1, tmp)
            else:
                result = builder.fdiv(rvalue1, tmp)
        elif op == '%=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type != double:
                result = builder.srem(rvalue1, tmp)
            else:
                result = builder.frem(rvalue1, tmp)
        elif op == '+=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type != double:
                result = builder.add(rvalue1, tmp)
            else:
                result = builder.fadd(rvalue1, tmp)
        elif op == '-=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type != double:
                result = builder.sub(rvalue1, tmp)
            else:
                result = builder.fsub(rvalue1, tmp)
        elif op == '<<=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type == double:
                raise SemanticError('Floating point number cannot shift bits.')
            result = builder.shl(rvalue1, tmp)
        elif op == '>>=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type == double:
                raise SemanticError('Floating point number cannot shift bits.')
            result = builder.ashr(rvalue1, tmp)
        elif op == '&=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type == double:
                raise SemanticError('Floating point number cannot shift bits.')
            result = builder.and_(rvalue1, tmp)
        elif op == '^=':
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type == double:
                raise SemanticError('Floating point number cannot shift bits.')
            result = builder.xor(rvalue1, tmp)
        else:   # op == '|='
            tmp = self.convert_type(v3, v1.type, ctx=ctx)
            if v1.type == double:
                raise SemanticError('Floating point number cannot shift bits.')
            result = builder.or_(rvalue1, tmp)
        self.store_lvalue(result, v1)
        return

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
    def as_pointer(self: ir.Type, addrspace=0):
        if isinstance(self, ir.VoidType):
            return int8.as_pointer(addrspace)
        return ir.PointerType(self, addrspace)
    ir.Type.as_pointer = as_pointer

    include_dirs = [os.getcwd(), './test']
    precessed_text = preprocess(input_filename, include_dirs, None)

    # 加入宏处理
    include_dirs = [os.getcwd(), './test', './test/libc/include', './test/windows/include']
    macros = {'_WIN64': None}
    precessed_text = preprocess(input_filename, include_dirs, macros)
    lexer = CCompilerLexer(InputStream(precessed_text))
    stream = CommonTokenStream(lexer)
    parser = CCompilerParser(stream)
    parser.removeErrorListeners()
    errorListener = SyntaxErrorListener()
    parser.addErrorListener(errorListener)

    tree = parser.compilationUnit()
    v = Visitor()
    # v.builders.append(None)
    v.visit(tree)
    v.save(output_filename)

# del CCompilerParser
