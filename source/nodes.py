from typing import List, Any
from dataclasses import dataclass
from source.tokens import Token

@dataclass
class ParserNode:
    pass

@dataclass
class StatementNode:
    pass


# --- EXPRESSION NODES ---
@dataclass
class ExpressionNode(ParserNode):
    expression: Any


# --- TYPE NODES ---
@dataclass
class TypeNode(ParserNode):
    type_token: Token

@dataclass
class ListTypeNode(TypeNode):
    child_type_node: TypeNode


# --- VARIABLE DECLARATION ---
@dataclass
class VariableDeclarationNode(StatementNode):
    var_type: TypeNode
    identifier: Token
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