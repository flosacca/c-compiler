grammar CPreprocessor;

macro
    : line (NL line)* EOF
    ;

line
    : defineStat    // 定义宏
    | undefStat     // 取消宏
    | includeStat   // 包含头文件
    | ifdefStat     // ifdef
    | ifndefStat    // ifndef
    | elseStat      // else
    | endifStat     // endif
    | text          // 普通文本
    |               // 空行
    ;

defineStat
    : WS? '#define' WS macroID (WS restOfLine)?
    ;

undefStat
    : WS? '#undef' WS macroID WS?;

includeStat
    : WS? '#include' WS '"' WS? filename WS? '"' WS?   # includeCur
    | WS? '#include' WS '<' WS? filename WS? '>' WS?   # includeSys
    ;
filename: ID '.h'?;

ifdefStat
    : WS? '#ifdef' WS macroID WS?;

ifndefStat
    : WS? '#ifndef' WS macroID WS?;

elseStat
    : WS? '#else' WS?;

endifStat
    : WS? '#endif' WS?;

text: .*?;

macroID: (ID | OP)+;

restOfLine: (WS? (ID | OP | DOUBLE_QUOTE)+ WS?)+;

ID: [A-Za-z0-9_]+;
OP: (~('a'..'z' | 'A'..'Z' | '0'..'9' | '\t' | '\r' | '\n' | ' ' | '_' | '"'))+;
DOUBLE_QUOTE: '"';

NL          : '\r'? '\n' | '\r';
WS          : (' ' | '\t')+; // whitespace