from typing import List, Any, Optional
from dataclasses import dataclass
from source.tokens import Token

@dataclass
class ParserNode:
    pass

@dataclass
class ExpressionNode(ParserNode):
    expression: Any

@dataclass
class StatementNode(ParserNode):
    pass

@dataclass
class BlockStatementNode(StatementNode):
    pass


# --- EXPRESSION NODES ---
@dataclass
class LiteralNode(ExpressionNode):
    token: Token

@dataclass
class IdentifierNode(ExpressionNode):
    token: Token

@dataclass
class ListLiteralNode(ExpressionNode):
    elements: List[ExpressionNode]

@dataclass
class BinaryOpNode(ExpressionNode):
    left: ExpressionNode
    operator: Token
    right: ExpressionNode

@dataclass
class UnaryOpNode(ExpressionNode):
    operator: Token
    operand: ExpressionNode

@dataclass
class FunctionCallNode(ExpressionNode):
    function_name: ExpressionNode
    arguments: List[ExpressionNode]

@dataclass
class MemberAccessNode(ExpressionNode):
    object_expr: ExpressionNode
    member_name: Token

@dataclass
class ConstructorCallNode(ExpressionNode):
    type_token: Token
    arguments: List[ExpressionNode]


# --- TYPE NODES ---
@dataclass
class TypeNode(ParserNode):
    type_token: Token

@dataclass
class ListTypeNode(TypeNode):
    child_type_node: TypeNode


# --- STATEMENT NODES ---
@dataclass
class VariableDeclarationNode(StatementNode):
    var_type: TypeNode
    identifier: Token
    value: ExpressionNode

@dataclass
class CodeBlockNode(ParserNode):
    statements: List[BlockStatementNode]

@dataclass
class IfStatementNode(BlockStatementNode):
    condition: ExpressionNode
    if_block: CodeBlockNode
    else_block: Optional[CodeBlockNode]

@dataclass
class WhileLoopNode(BlockStatementNode):
    condition: ExpressionNode
    body: CodeBlockNode

@dataclass
class AssignmentNode(BlockStatementNode):
    identifier: ExpressionNode
    value: ExpressionNode


# --- FUNCTION DEFINITION ---
@dataclass
class ParameterNode(ParserNode):
    param_type: TypeNode
    param_name: Token

@dataclass
class FunctionBodyNode(ParserNode):
    statements: List[StatementNode]

@dataclass
class FunctionDefinitionNode(StatementNode):
    return_type: TypeNode
    identifier: Token
    parameters: List[ParameterNode]
    body: FunctionBodyNode