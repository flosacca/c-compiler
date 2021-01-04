class MacroError(Exception):
    def __init__(self, msg: str, filepath: str, ctx=None):
        super().__init__()
        if ctx:
            self.line = ctx.start.line  # 错误出现位置
            self.column = ctx.start.column
        else:
            self.line = 0
            self.column = 0
        self.filepath = filepath
        self.msg = msg

    def __str__(self):
        return 'MacroError ({}): line {}, column {}, {}'.format(self.filepath, self.line, self.column, self.msg)
