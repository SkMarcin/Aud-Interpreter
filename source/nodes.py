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