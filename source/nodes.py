from source.tokens import Token

class ParserNode:
    pass

class ExpressionNode(ParserNode):
    def __init__(self, expression):
        self.expression = expression

# --- TYPE NODES ---
class TypeNode(ParserNode):
    pass

class SimpleTypeNode(TypeNode):
    def __init__(self, type_token: Token):
        self.type_token = type_token

class ListTypeNode(TypeNode):
    def __init__(self, type_token: Token, child_node: TypeNode):
        self.type_token = type_token
        self.child_node = child_node


# --- VARIABLE DECLARATION ---
class VariableDeclarationNode(ParserNode):
    def __init__(self, var_type: TypeNode, identifier: Token, value: ExpressionNode):
        self.var_type = var_type
        self.identifier = identifier
        self.value=value