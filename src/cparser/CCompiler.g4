grammar CCompiler;

prog :(include)* (initialBlock | arrayInitBlock | structInitBlock | mStructDef | mFunctionDefinition | mFunctionDeclaration )*;
// prog : (forBlock)*;

//-------------语法规则----------------------------------------------
include : '#include' '<' mHEADER '>';

// 结构体定义
mStructDef : mStruct '{' (structParam)+ '}'';';

// 结构体中参数定义
structParam : (mType | mStruct) (mID | mArray) (',' (mID | mArray))* ';';

// 函数类型
mFunctionType: (mType | mVoid | mStruct) mID '(' params ')';

// 函数
mFunctionDefinition : mFunctionType '{' funcBody '}';
mFunctionDeclaration : mFunctionType ';';

// 函数参数
params : (param (','param)* (',' '...')? | ('...')?);
param : namedValue;

namedValue : mType mID;

// 函数体
funcBody : body returnBlock;

// 语句块/函数快
body : (block | func';')*;

// 语句块
block : initialBlock | arrayInitBlock | structInitBlock | assignBlock | ifBlocks | whileBlock | forBlock | returnBlock;

// 初始化语句
initialBlock : (mType) mID ('=' expr)? (',' mID ('=' expr)?)* ';';
arrayInitBlock : mType mID '[' mINT ']'';';
structInitBlock : mStruct (mID | mArray)';';


// 赋值语句
assignBlock : ((arrayItem|mID|structMember) '=')+  expr ';';


// if 语句
ifBlocks : ifBlock (elifBlock)* (elseBlock)?;
ifBlock : 'if' '('condition')' '{' body '}';
elifBlock : 'else' 'if' '(' condition ')' '{' body '}';
elseBlock : 'else' '{' body '}';

condition :  expr;

// while 语句
whileBlock : 'while' '(' condition ')' '{' body '}';

// for 语句
forBlock : 'for' '(' for1Block  ';' condition ';' for3Block ')' ('{' body '}'|';');
for1Block :  mID '=' expr (',' for1Block)?|;
for3Block : mID '=' expr (',' for3Block)?|;

// return 语句
returnBlock : 'return' (mINT|mID)? ';';

/* expr */
/*     : '(' expr ')'               #parens */
/*     | structMember               #structmember */
/*     | expr '[' expr ']'          #arrayIndex */
/*     | op='!' expr                   #Neg */
/*     | op='&' expr                #addressOf */
/*     | op='*' expr                #dereference */
/*     | expr op=('*' | '/' | '%') expr   #MulDiv */
/*     | expr op=('+' | '-') expr   #AddSub */
/*     | expr op=('==' | '!=' | '<' | '<=' | '>' | '>=') expr #Judge */
/*     | expr '&&' expr             # AND */
/*     | expr '||' expr             # OR */
/*     | (op='-')? mINT             #int */
/*     | (op='-')? mDOUBLE          #double */
/*     | mCHAR                       #char */
/*     | mSTRING                     #string */
/*     | mID                         #identifier */
/*     | func                       #function */
/*     ; */

expr : expression ;

primaryExpression
    :   Identifier
    |   Constant
    |   StringLiteral+
    |   '(' expression ')'
    ;

postfixExpression
    :   primaryExpression
    |   postfixExpression '[' expression ']' #subscript
    |   postfixExpression '(' argumentExpressionList? ')' #functionCall
    |   postfixExpression '.' Identifier #memberOfObject
    |   postfixExpression '->' Identifier #memberOfPointer
    |   postfixExpression '++' #postfixIncrement
    |   postfixExpression '--' #postfixDecrement
    ;

argumentExpressionList
    :   assignmentExpression
    |   argumentExpressionList ',' assignmentExpression
    ;

unaryExpression
    :   postfixExpression
    |   '++' unaryExpression
    |   '--' unaryExpression
    |   unaryOperator castExpression
    |   'sizeof' unaryExpression
    |   'sizeof' '(' typeName ')'
    ;

unaryOperator
    :   '&' | '*' | '+' | '-' | '~' | '!'
    ;

castExpression
    :   '(' typeName ')' castExpression
    |   unaryExpression
    /* |   DigitSequence // for */
    ;

multiplicativeExpression
    :   castExpression
    |   multiplicativeExpression '*' castExpression
    |   multiplicativeExpression '/' castExpression
    |   multiplicativeExpression '%' castExpression
    ;

additiveExpression
    :   multiplicativeExpression
    |   additiveExpression '+' multiplicativeExpression
    |   additiveExpression '-' multiplicativeExpression
    ;

shiftExpression
    :   additiveExpression
    |   shiftExpression '<<' additiveExpression
    |   shiftExpression '>>' additiveExpression
    ;

relationalExpression
    :   shiftExpression
    |   relationalExpression '<' shiftExpression
    |   relationalExpression '>' shiftExpression
    |   relationalExpression '<=' shiftExpression
    |   relationalExpression '>=' shiftExpression
    ;

equalityExpression
    :   relationalExpression
    |   equalityExpression '==' relationalExpression
    |   equalityExpression '!=' relationalExpression
    ;

andExpression
    :   equalityExpression
    |   andExpression '&' equalityExpression
    ;

exclusiveOrExpression
    :   andExpression
    |   exclusiveOrExpression '^' andExpression
    ;

inclusiveOrExpression
    :   exclusiveOrExpression
    |   inclusiveOrExpression '|' exclusiveOrExpression
    ;

logicalAndExpression
    :   inclusiveOrExpression
    |   logicalAndExpression '&&' inclusiveOrExpression
    ;

logicalOrExpression
    :   logicalAndExpression
    |   logicalOrExpression '||' logicalAndExpression
    ;

conditionalExpression
    :   logicalOrExpression ('?' expression ':' conditionalExpression)?
    ;

assignmentExpression
    :   conditionalExpression
    |   unaryExpression assignmentOperator assignmentExpression
    /* |   DigitSequence // for */
    ;

assignmentOperator
    :   '=' | '*=' | '/=' | '%=' | '+=' | '-=' | '<<=' | '>>=' | '&=' | '^=' | '|='
    ;

expression
    :   assignmentExpression
    |   expression ',' assignmentExpression
    ;

constantExpression
    :   conditionalExpression
    ;

mType : mBaseType pointer?;
mBaseType : ('int' | 'double' | 'char');

pointer : qualifiedPointer | pointer qualifiedPointer;
qualifiedPointer : '*' typeQualifierList?;

typeQualifierList : typeQualifier | typeQualifierList typeQualifier;

typeQualifier : 'const' | 'volatile';

mArray : mID '[' mINT ']';

mVoid : 'void';

mStruct : 'struct' mID;

structMember: (mID | arrayItem)'.'(mID | arrayItem);

arrayItem : mID '[' expr ']';


//函数
func : (strlenFunc | atoiFunc | printfFunc | scanfFunc | getsFunc | selfDefinedFunc);

//strlen
strlenFunc : 'strlen' '(' mID ')';

//atoi
atoiFunc : 'atoi' '(' mID ')' ;

//printf
printfFunc
    : 'printf' '(' (mSTRING | mID) (','expr)* ')';

//scanf
scanfFunc : 'scanf' '(' mSTRING (','('&')?(mID | arrayItem | structMember))* ')';

//gets
getsFunc : 'gets' '(' mID ')';

//Selfdefined
selfDefinedFunc : mID '('((argument | mID)(','(argument | mID))*)? ')';

argument : mINT | mDOUBLE | mCHAR | mSTRING;

mID : ID;

mINT : INT;

mDOUBLE : DOUBLE;

mCHAR : CHAR;

mSTRING : STRING;

mHEADER : HEADER;

//-------------词法规则----------------------------------------------

ID : [a-zA-Z_][0-9A-Za-z_]*;

INT : [0-9]+;

DOUBLE : [0-9]+'.'[0-9]+;

CHAR : '\''.'\'';

STRING : '"'.*?'"';


HEADER : [a-zA-Z]+ '.h'?;

Conjunction : '&&' | '||';

Operator : '!' | '+' | '-' | '*' | '/' | '==' | '!=' | '<' | '<=' | '>' | '>=';

//UnaryOperator :  '&' | '*' | '+' | '-' | '~' | '!';

LineComment: '//'.*?'\r'?'\n'   -> skip;

BlockComment:  '/*'.*?'*/'  -> skip;

WS : [ \t\r\n]+ -> skip ; // skip spaces, tabs, newlines

// New Lexical Elements --------------------------------

Digit : [0-9] ;

DigitSequence : Digit+ ;

Nondigit : [a-zA-Z_] ;

Identifer : Nondigit (Nondigit | Digit)* ;

Constant
  : IntegerConstant
  | FloatingConstant
  | CharacterConstant
  ;

IntegerConstant
  : [1-9] Digit*
  | '0'
  /* | '0' [0-7]* */
  /* | ('0x' | '0X') [0-9a-fA-F]+ */
  ;

FloatingConstant
  : DigitSequence '.' DigitSequence
  ;

CharacterConstant
  : '\'' . '\''
  ;

StringLiteral
  : '"' .* '"'
  ;
