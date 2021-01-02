grammar CCompiler;

@parser::header {
from .RuleContextWithAltNum import *
}

// Old syntax {{{
// prog :(include)* (initialBlock | arrayInitBlock | structInitBlock | mStructDef | mFunctionDefinition | mFunctionDeclaration )*;
// // prog : (forBlock)*;
//
// //-------------语法规则----------------------------------------------
// include : '#include' '<' mHEADER '>';
//
// // 结构体定义
// mStructDef : mStruct '{' (structParam)+ '}'';';
//
// // 结构体中参数定义
// structParam : (mType | mStruct) (mID | mArray) (',' (mID | mArray))* ';';
//
// // 函数类型
// mFunctionType: (mType | mVoid | mStruct) mID '(' params ')';
//
// // 函数
// mFunctionDefinition : mFunctionType '{' funcBody '}';
// mFunctionDeclaration : mFunctionType ';';
//
// // 函数参数
// params : (param (','param)* (',' '...')? | ('...')?);
// param : namedValue;
//
// namedValue : mType mID;
//
// // 函数体
// funcBody : body returnBlock;
//
// // 语句块/函数快
// body : (block | func';')*;
//
// // 语句块
// block : initialBlock | arrayInitBlock | structInitBlock | assignBlock | ifBlocks | whileBlock | forBlock | returnBlock;
//
// // 初始化语句
// initialBlock : (mType) mID ('=' expr)? (',' mID ('=' expr)?)* ';';
// arrayInitBlock : mType mID '[' mINT ']'';';
// structInitBlock : mStruct (mID | mArray)';';
//
//
// // 赋值语句
// assignBlock : ((arrayItem|mID|structMember) '=')+  expr ';';
//
//
// // if 语句
// ifBlocks : ifBlock (elifBlock)* (elseBlock)?;
// ifBlock : 'if' '('condition')' '{' body '}';
// elifBlock : 'else' 'if' '(' condition ')' '{' body '}';
// elseBlock : 'else' '{' body '}';
//
// condition :  expr;
//
// // while 语句
// whileBlock : 'while' '(' condition ')' '{' body '}';
//
// // for 语句
// forBlock : 'for' '(' for1Block  ';' condition ';' for3Block ')' ('{' body '}'|';');
// for1Block :  mID '=' expr (',' for1Block)?|;
// for3Block : mID '=' expr (',' for3Block)?|;
//
// // return 语句
// returnBlock : 'return' (mINT|mID)? ';';
//
// expr
//     : '(' expr ')'                                         # parens
//     | structMember                                         # structmember
//     | expr '[' expr ']'                                    # arrayIndex
//     | op='!' expr                                          # Neg
//     | op='&' expr                                          # addressOf
//     | op='*' expr                                          # dereference
//     | expr op=('*' | '/' | '%') expr                       # MulDiv
//     | expr op=('+' | '-') expr                             # AddSub
//     | expr op=('==' | '!=' | '<' | '<=' | '>' | '>=') expr # Judge
//     | expr '&&' expr                                       # AND
//     | expr '||' expr                                       # OR
//     | (op='-')? mINT                                       # int
//     | (op='-')? mDOUBLE                                    # double
//     | mCHAR                                                # char
//     | mSTRING                                              # string
//     | mID                                                  # identifier
//     | func                                                 # function
//     ;
//
// mType : mBaseType pointer?;
// mBaseType : ('int' | 'double' | 'char');
//
// pointer : qualifiedPointer | pointer qualifiedPointer;
// qualifiedPointer : '*' typeQualifierList?;
//
// typeQualifierList : typeQualifier | typeQualifierList typeQualifier;
//
// typeQualifier : 'const' | 'volatile';
//
// mArray : mID '[' mINT ']';
//
// mVoid : 'void';
//
// mStruct : 'struct' mID;
//
// structMember: (mID | arrayItem)'.'(mID | arrayItem);
//
// arrayItem : mID '[' expr ']';
//
//
// //函数
// func : (strlenFunc | atoiFunc | printfFunc | scanfFunc | getsFunc | selfDefinedFunc);
//
// strlenFunc : 'strlen' '(' mID ')';
//
// atoiFunc : 'atoi' '(' mID ')' ;
//
// printfFunc : 'printf' '(' (mSTRING | mID) (','expr)* ')';
//
// scanfFunc : 'scanf' '(' mSTRING (','('&')?(mID | arrayItem | structMember))* ')';
//
// getsFunc : 'gets' '(' mID ')';
//
// selfDefinedFunc : mID '('((argument | mID)(','(argument | mID))*)? ')';
//
// argument : mINT | mDOUBLE | mCHAR | mSTRING;
//
//
// mID : Identifier;
//
// mINT : IntegerConstant;
//
// mDOUBLE : FloatingConstant;
//
// mCHAR : CharacterConstant;
//
// mSTRING : StringLiteral;
//
// mHEADER : HEADER;
// }}}

// Parser rules

prog : translationUnit* EOF;

translationUnit : functionDefinition | declaration | ';' ;

statement
    : expressionStatement
    | compoundStatement
    | jumpStatement;

expressionStatement : expression ';' ;

compoundStatement : '{' statementList '}';

jumpStatement
    :   'continue' ';'              # jumpStatement_1
    |   'break' ';'                 # jumpStatement_2
    |   'return' expression? ';'    # jumpStatement_3
    ;

// simplified
statementList : (statement | declaration)*;

constant
    : IntegerConstant
    | FloatingConstant
    | CharacterConstant
    ;

primaryExpression
    :   Identifier
    |   stringLiteral+
    |   constant
    |   '(' expression ')'
    ;

postfixExpression
    :   primaryExpression                                   # postfixExpression_1
    |   postfixExpression '[' expression ']'                # postfixExpression_2
    |   postfixExpression '(' argumentExpressionList? ')'   # postfixExpression_3
    |   postfixExpression '.' Identifier                    # postfixExpression_4
    |   postfixExpression '->' Identifier                   # postfixExpression_5
    |   postfixExpression '++'                              # postfixExpression_6
    |   postfixExpression '--'                              # postfixExpression_7
    ;

// 暂时不做
argumentExpressionList
    :   assignmentExpression
    |   argumentExpressionList ',' assignmentExpression
    ;

unaryExpression
    :   postfixExpression                       # unaryExpression_1
    |   '++' unaryExpression                    # unaryExpression_2
    |   '--' unaryExpression                    # unaryExpression_3
    |   unaryOperator castExpression            # unaryExpression_4
    |   'sizeof' unaryExpression                # unaryExpression_5
    |   'sizeof' '(' typeName ')'               # unaryExpression_6
    ;

unaryOperator
    :   '&' | '*' | '+' | '-' | '~' | '!'
    ;

castExpression
    :   '(' typeName ')' castExpression         # castExpression_1
    |   unaryExpression                         # castExpression_2
    ;

multiplicativeExpression
    :   castExpression                                  # multiplicativeExpression_1
    |   multiplicativeExpression '*' castExpression     # multiplicativeExpression_2
    |   multiplicativeExpression '/' castExpression     # multiplicativeExpression_3
    |   multiplicativeExpression '%' castExpression     # multiplicativeExpression_4
    ;

additiveExpression
    :   multiplicativeExpression                            # additiveExpression_1
    |   additiveExpression '+' multiplicativeExpression     # additiveExpression_2
    |   additiveExpression '-' multiplicativeExpression     # additiveExpression_3
    ;

shiftExpression
    :   additiveExpression                          # shiftExpression_1
    |   shiftExpression '<<' additiveExpression     # shiftExpression_2
    |   shiftExpression '>>' additiveExpression     # shiftExpression_3
    ;

relationalExpression
    :   shiftExpression                                 # relationalExpression_1
    |   relationalExpression '<' shiftExpression        # relationalExpression_2
    |   relationalExpression '>' shiftExpression        # relationalExpression_3
    |   relationalExpression '<=' shiftExpression       # relationalExpression_4
    |   relationalExpression '>=' shiftExpression       # relationalExpression_5
    ;

equalityExpression
    :   relationalExpression                            # equalityExpression_1
    |   equalityExpression '==' relationalExpression    # equalityExpression_2
    |   equalityExpression '!=' relationalExpression    # equalityExpression_3
    ;

andExpression
    :   equalityExpression                              # andExpression_1
    |   andExpression '&' equalityExpression            # andExpression_2
    ;

exclusiveOrExpression
    :   andExpression                                   # exclusiveOrExpression_1
    |   exclusiveOrExpression '^' andExpression         # exclusiveOrExpression_2
    ;

inclusiveOrExpression
    :   exclusiveOrExpression                           # inclusiveOrExpression_1
    |   inclusiveOrExpression '|' exclusiveOrExpression # inclusiveOrExpression_2
    ;

logicalAndExpression
    :   inclusiveOrExpression                           # logicalAndExpression_1
    |   logicalAndExpression '&&' inclusiveOrExpression # logicalAndExpression_2
    ;

logicalOrExpression
    :   logicalAndExpression                            # logicalOrExpression_1
    |   logicalOrExpression '||' logicalAndExpression   # logicalOrExpression_2
    ;

conditionalExpression
    :   logicalOrExpression ('?' expression ':' conditionalExpression)?
    ;

assignmentExpression
    :   conditionalExpression                                       # assignmentExpression_1
    |   unaryExpression assignmentOperator assignmentExpression     # assignmentExpression_2
    ;

assignmentOperator
    :   '=' | '*=' | '/=' | '%=' | '+=' | '-=' | '<<=' | '>>=' | '&=' | '^=' | '|='
    ;

expression
    :   assignmentExpression                    # expression_1
    |   expression ',' assignmentExpression     # expression_2
    ;

constantExpression
    :   conditionalExpression
    ;

// The full definition is quite complex
typeName : Identifier pointer? ;

pointer
    : qualifiedPointer
    | pointer qualifiedPointer
    ;

qualifiedPointer : '*' typeQualifierList? ;

typeQualifierList : typeQualifier+;

typeQualifier : 'const' | 'volatile' ;

stringLiteral: StringLiteral;

// simplified to typeSpecifier
functionDefinition
    :   typeSpecifier declarator compoundStatement
    ;

declaration
    :   declarationSpecifiers initDeclaratorList ';'
	| 	declarationSpecifiers ';'
    ;

initDeclaratorList
    :   initDeclarator
    |   initDeclaratorList ',' initDeclarator
    ;

initDeclarator
    :   declarator
    |   declarator '=' initializer
    ;

initializer
    :   assignmentExpression
    |   '{' initializerList '}'
    |   '{' initializerList ',' '}'
    ;

initializerList
    :   initializer
    |   initializerList ',' initializer
    ;

declarationSpecifiers: declarationSpecifier*;

declarationSpecifier
    :   storageClassSpecifier
    |   typeSpecifier
    |   typeQualifier
    ;

storageClassSpecifier
    :   'typedef'
    ;

parameterTypeList
    :
    |   parameterList
    |   parameterList ',' '...'
    ;

parameterList
    :   parameterDeclaration
    |   parameterList ',' parameterDeclaration
    ;

parameterDeclaration
    :   declarationSpecifiers declarator
    ;

directDeclarator
    :   Identifier                                      # directDeclarator_1
    |   '(' declarator ')'                              # directDeclarator_2
    |   directDeclarator '[' assignmentExpression? ']'  # directDeclarator_3
    |   directDeclarator '(' parameterTypeList ')'      # directDeclarator_4
    ;

declarator
    :   pointer? directDeclarator
    ;

typeSpecifier
    :   primitiveType           # typeSpecifier_1
    |   typedefName             # typeSpecifier_2
    |   typeSpecifier pointer   # typeSpecifier_3
    ;

primitiveType
    :   'void'
    |   'char'
    |   'short'
    |   'int'
    |   'long'
    |   'float'
    |   'double'
    |   'signed'
    |   'unsigned'
    ;

typedefName : Identifier;

// Lexer rules

Identifier : Nondigit (Nondigit | Digit)* ;

fragment
Nondigit : [a-zA-Z_] ;

fragment
Digit : [0-9] ;

IntegerConstant
    : [1-9] Digit*
    | '0' [0-7]*
    | ('0x' | '0X') [0-9a-fA-F]+
    ;

FloatingConstant
    : DigitSequence '.' DigitSequence
    ;

fragment
DigitSequence : Digit+ ;

CharacterConstant
    : '\'' . '\''
    ;

StringLiteral
    : '"' .*? '"'
    ;

Whitespace
    :   [ \t]+
        -> skip
    ;

Newline
    :   (   '\r' '\n'?
        |   '\n'
        )
        -> skip
    ;

BlockComment
    :   '/*' .*? '*/'
        -> skip
    ;

LineComment
    :   '//' ~[\r\n]*
        -> skip
    ;
