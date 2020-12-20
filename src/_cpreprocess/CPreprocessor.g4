grammar CPreprocessor;

macro
    : line (NL line)* EOF
    ;

line
    : defineStat
    | includeStat
    | ifdefStat
    | ifndefStat
    | elseStat
    | endifStat
    | text
    |   // 空行
    ;

defineStat
    : '#define' macroID restOfLine?;

includeStat
    : '#include' '"' filename '"'   # includeCur
    | '#include' '<' filename '>'   # includeSys
    ;
filename: ID '.h'?;

ifdefStat
    : '#ifdef' macroID;

ifndefStat
    : '#ifndef' macroID;

elseStat
    : '#else';

endifStat
    : '#endif';

text: (ID | OP)+;

macroID: ID | OP;

restOfLine: (ID | OP)+;

ID: [A-Za-z0-9_]+;
OP: (~('a'..'z' | 'A'..'Z' | '0'..'9' | '\t' | '\r' | '\n' | ' ' | '_'))+;

NL          : '\r'? '\n';
WS          : (' ' | '\t')-> skip; // toss out whitespace