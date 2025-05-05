
class ParserNode:
    pass

class ExpressionNode(ParserNode):
    def __init__(self, expression):
        self.expression = expression