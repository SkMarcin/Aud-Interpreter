from typing import List, Any, Optional
from dataclasses import dataclass
from source.utils import Position

@dataclass
class ParserNode:
    start_position: Position
    end_position: Position

# --- EXPRESSION NODES---
@dataclass
class ExpressionNode(ParserNode):
    pass

@dataclass
class IntLiteralNode(ExpressionNode):
    value: int

@dataclass
class FloatLiteralNode(ExpressionNode):
    value: float

@dataclass
class StringLiteralNode(ExpressionNode):
    value: str

@dataclass
class BoolLiteralNode(ExpressionNode):
    value: bool

@dataclass
class NullLiteralNode(ExpressionNode):
    pass 

@dataclass
class IdentifierNode(ExpressionNode):
    name: str

@dataclass
class ListLiteralNode(ExpressionNode):
    elements: List[ExpressionNode]

# --- BINARY OPERATORS ---
@dataclass
class AddNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class SubtractNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class MultiplyNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class DivideNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class EqualsNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class NotEqualsNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class LessThanNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class LessThanOrEqualNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class GreaterThanNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class GreaterThanOrEqualNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class LogicalAndNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class LogicalOrNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

@dataclass
class UnaryMinusNode(ExpressionNode):
    operand: ExpressionNode

@dataclass
class FunctionCallNode(ExpressionNode):
    function_name: ExpressionNode
    arguments: List[ExpressionNode]

@dataclass
class MemberAccessNode(ExpressionNode):
    object_expr: ExpressionNode
    member_name: str

@dataclass
class ConstructorCallNode(ExpressionNode):
    type_name: str
    arguments: List[ExpressionNode]

# --- TYPE NODES ---
@dataclass
class TypeNode(ParserNode):
    type_name: str

@dataclass
class ListTypeNode(TypeNode):
    child_type_node: TypeNode

# --- STATEMENT NODES ---
@dataclass
class StatementNode(ParserNode):
    pass

@dataclass
class CodeBlockNode(ParserNode):
    statements: List[StatementNode]

@dataclass
class VariableDeclarationNode(StatementNode):
    var_type: TypeNode
    identifier_name: str
    value: ExpressionNode

@dataclass
class IfStatementNode(StatementNode):
    condition: ExpressionNode
    if_block: CodeBlockNode
    else_block: Optional[CodeBlockNode]

@dataclass
class WhileLoopNode(StatementNode):
    condition: ExpressionNode
    body: CodeBlockNode

@dataclass
class AssignmentNode(StatementNode):
    identifier: ExpressionNode
    value: ExpressionNode

@dataclass
class ReturnStatementNode(StatementNode):
    value: Optional[ExpressionNode]

@dataclass
class FunctionCallStatementNode(StatementNode):
    call_expression: FunctionCallNode

@dataclass
class ExpressionStatementNode(StatementNode):
    expression: ExpressionNode


# --- FUNCTION DEFINITION ---
@dataclass
class ParameterNode(ParserNode):
    param_type: TypeNode
    param_name: str

@dataclass
class FunctionDefinitionNode(StatementNode):
    return_type: TypeNode
    identifier_name: str
    parameters: List[ParameterNode]
    body: CodeBlockNode

@dataclass
class ProgramNode(ParserNode):
    definitions: List[FunctionDefinitionNode]
    statements: List[StatementNode]