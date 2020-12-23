from antlr4 import *


class RuleContextWithAltNum(ParserRuleContext):
    def __init__(self, parent = None, invokingState: int = None):
        super().__init__(parent, invokingState)
        self.altNum = 0 # This is ATN.INVALID_ALT_NUMBER

    def getAltNumber(self):
        return self.altNum

    def setAltNumber(self, altNum: int):
        self.altNum = altNum
