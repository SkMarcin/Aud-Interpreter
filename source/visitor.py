from typing import Any

from source.tokens import TokenType
from source.nodes import *

class NodeVisitor:
    def visit(self, node: Any, *args, **kwargs) -> Any:
        """
        Dispatches to the appropriate visit_NodeType method.
        """
        if node is None:
            return self.visit_None(node, *args, **kwargs)

        method_name = 'visit_' + type(node).__name__
        visitor_method = getattr(self, method_name)
        return visitor_method(node, *args, **kwargs)

    def visit_None(self, node: None, *args, **kwargs) -> Any:
        """Handles cases where an optional node is None."""
        return None

class ASTPrinter(NodeVisitor):
    def __init__(self, indent_char: str = "  ", initial_indent: int = -1):
        self.indent_char = indent_char
        self.current_indent_level = initial_indent

    def _print_with_indent(self, message: str):
        self._increase_indent()
        print(f"{self.indent_char * self.current_indent_level}{message}")
        self._decrease_indent()

    def _increase_indent(self):
        self.current_indent_level += 1

    def _decrease_indent(self):
        self.current_indent_level -= 1

    # --- Visitor Methods for Each Node Type ---

    def visit_ProgramNode(self, node: ProgramNode):
        self._print_with_indent("ProgramNode:")
        self._increase_indent()
        for stmt in node.statements:
            self.visit(stmt)
        self._decrease_indent()

    def visit_FunctionDefinitionNode(self, node: FunctionDefinitionNode):
        param_str = ", ".join([f"{p.param_name.value}: {self.visit(p.param_type, for_param=True)}" for p in node.parameters])
        self._print_with_indent(f"FunctionDefinitionNode: {node.identifier.value}({param_str}) -> {self.visit(node.return_type, for_param=True)}")
        self._increase_indent()
        self._print_with_indent("FunctionBody:")
        self.visit(node.body)
        self._decrease_indent()

    def visit_FunctionBodyNode(self, node: FunctionBodyNode):
        self._increase_indent()
        for stmt in node.block_statements:
            self.visit(stmt)
        self.visit(node.return_statement)
        self._decrease_indent()

    def visit_ParameterNode(self, node: ParameterNode):
        self._print_with_indent(f"ParameterNode: {node.param_name.value}")
        self._increase_indent()
        self.visit(node.param_type)
        self._decrease_indent()

    def visit_TypeNode(self, node: TypeNode, for_param=False):
        type_name = node.type_token.value if node.type_token else "UnknownType"
        if for_param:
            return type_name
        self._print_with_indent(f"TypeNode: {type_name}")

    def visit_ListTypeNode(self, node: ListTypeNode, for_param=False):
        child_type_str = self.visit(node.child_type_node, for_param=True)
        list_type_name = f"List<{child_type_str}>"
        if for_param:
            return list_type_name
        self._print_with_indent(f"ListTypeNode: {list_type_name}")

    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode):
        self._print_with_indent(f"VariableDeclarationNode: {node.identifier.value}")
        self._increase_indent()
        self._print_with_indent("Type:")
        self._increase_indent()
        self.visit(node.var_type)
        self._decrease_indent()
        self._print_with_indent("Value:")
        self._increase_indent()
        self.visit(node.value)
        self._decrease_indent()
        self._decrease_indent()

    def visit_AssignmentNode(self, node: AssignmentNode):
        self._print_with_indent("AssignmentNode:")
        self._increase_indent()
        self._print_with_indent("Target:")
        self.visit(node.identifier) # LHS can be complex
        self._print_with_indent("Value:")
        self.visit(node.value)
        self._decrease_indent()

    def visit_IfStatementNode(self, node: IfStatementNode):
        self._print_with_indent("IfStatementNode:")
        self._increase_indent()
        self._print_with_indent("Condition:")
        self.visit(node.condition)
        self._print_with_indent("IfBlock:")
        self.visit(node.if_block)
        if node.else_block:
            self._print_with_indent("ElseBlock:")
            self.visit(node.else_block)
        self._decrease_indent()

    def visit_WhileLoopNode(self, node: WhileLoopNode):
        self._print_with_indent("WhileLoopNode:")
        self._increase_indent()
        self._print_with_indent("Condition:")
        self.visit(node.condition)
        self._print_with_indent("Body:")
        self.visit(node.body)
        self._decrease_indent()

    def visit_ReturnStatementNode(self, node: ReturnStatementNode):
        self._print_with_indent("ReturnStatementNode:")
        if node.value:
            self._increase_indent()
            self.visit(node.value)
            self._decrease_indent()
        else:
            self._increase_indent()
            self._print_with_indent(" (no value)")
            self._decrease_indent()

    def visit_CodeBlockNode(self, node: CodeBlockNode):
        self._increase_indent()
        self._print_with_indent("CodeBlockNode:")
        self._increase_indent()
        for stmt in node.statements:
            self.visit(stmt)
        self._decrease_indent()
        self._decrease_indent()

    def visit_ExpressionStatementNode(self, node: ExpressionStatementNode):
        self._print_with_indent("ExpressionStatementNode:")
        self._increase_indent()
        self.visit(node.expression)
        self._decrease_indent()

    def visit_FunctionCallStatementNode(self, node: FunctionCallStatementNode):
        self._print_with_indent("FunctionCallStatementNode:")
        self._increase_indent()
        self.visit(node.call_expression)
        self._decrease_indent()

    # --- Expression Nodes ---
    def visit_LiteralNode(self, node: LiteralNode):
        val_repr = repr(node.token.value)
        if node.token.type == TokenType.LITERAL_STRING and len(val_repr) > 30:
            val_repr = val_repr[:27] + "...'"
        self._increase_indent()
        self._print_with_indent(f"LiteralNode: {node.token.type.name}({val_repr})")
        self._decrease_indent()

    def visit_IdentifierNode(self, node: IdentifierNode):
        self._increase_indent()
        self._print_with_indent(f"IdentifierNode: {node.token.value}")
        self._decrease_indent()

    def visit_BinaryOpNode(self, node: BinaryOpNode):
        self._print_with_indent(f"BinaryOpNode: {node.operator.value} ({node.operator.type.name})")
        self._increase_indent()
        self._print_with_indent("Left:")
        self.visit(node.left)
        self._print_with_indent("Right:")
        self.visit(node.right)
        self._decrease_indent()

    def visit_UnaryOpNode(self, node: UnaryOpNode):
        self._print_with_indent(f"UnaryOpNode: {node.operator.value} ({node.operator.type.name})")
        self._increase_indent()
        self._print_with_indent("Operand:")
        self.visit(node.operand)
        self._decrease_indent()

    def visit_FunctionCallNode(self, node: FunctionCallNode):
        self._print_with_indent("FunctionCallNode:")
        self._increase_indent()
        self._print_with_indent("FunctionName/Access:")
        self.visit(node.function_name)
        if node.arguments:
            self._print_with_indent("Arguments:")
            self._increase_indent()
            for arg in node.arguments:
                self.visit(arg)
            self._decrease_indent()
        else:
            self._print_with_indent("Arguments: (none)")
        self._decrease_indent()

    def visit_MemberAccessNode(self, node: MemberAccessNode):
        self._print_with_indent(f"MemberAccessNode: . {node.member_name.value}")
        self._increase_indent()
        self._print_with_indent("Object:")
        self.visit(node.object_expr)
        self._decrease_indent()

    def visit_ConstructorCallNode(self, node: ConstructorCallNode):
        self._print_with_indent(f"ConstructorCallNode: new {node.type_token.value}")
        self._increase_indent()
        if node.arguments:
            self._print_with_indent("Arguments:")
            self._increase_indent()
            for arg in node.arguments:
                self.visit(arg)
            self._decrease_indent()
        else:
            self._print_with_indent("Arguments: (none)")
        self._decrease_indent()

    def visit_ListLiteralNode(self, node: ListLiteralNode):
        self._print_with_indent("ListLiteralNode:")
        self._increase_indent()
        if node.elements:
            self._print_with_indent("Elements:")
            self._increase_indent()
            for elem in node.elements:
                self.visit(elem)
            self._decrease_indent()
        else:
            self._print_with_indent("Elements: (empty)")
        self._decrease_indent()

    def visit_None(self, node: None):
        self._print_with_indent("(None)")
