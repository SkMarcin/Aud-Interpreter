from typing import Any, List, Optional, Dict

from source.nodes import *
from source.visitor import NodeVisitor
from source.type_checker.symbol_table import SymbolTable, GlobalSymbolTable, TypeSignature, FunctionTypeSignature
from source.utils import Position, TypeMismatchException

class TypeChecker(NodeVisitor):
    """
    Performs static type analysis.
    """
    def __init__(self):
        self.global_symbol_table: GlobalSymbolTable = GlobalSymbolTable()
        self.current_scope: SymbolTable = self.global_symbol_table
        self.current_function_return_type: Optional[TypeSignature] = None

        self._register_builtin_function_signatures()
        self._define_builtin_object_members()

    def _register_builtin_function_signatures(self):
        def register_func(name: str, param_types_str: List[str], return_type_str: str):
            param_sigs = [self.global_symbol_table.get_type_signature(pt) for pt in param_types_str]
            return_sig = self.global_symbol_table.get_type_signature(return_type_str)
            self.global_symbol_table.register_function(name, FunctionTypeSignature(param_sigs, return_sig), Position(0,0))

        register_func("print", ["string"], "void")
        register_func("input", [], "string")
        register_func("stoi", ["string"], "int")
        register_func("itos", ["int"], "string")
        register_func("stof", ["string"], "float")
        register_func("ftos", ["float"], "string")
        register_func("itof", ["int"], "float")
        register_func("ftoi", ["float"], "int")
        register_func("btos", ["bool"], "string")
        register_func("atof", ["Audio"], "File")
        register_func("ftoa", ["File"], "Audio")

    def _define_builtin_object_members(self):
        # type_name -> { property_name -> TypeSignature }
        self.builtin_properties: Dict[str, Dict[str, TypeSignature]] = {
            "File": {
                "filename": self.global_symbol_table.get_type_signature("string"),
                "parent": self.global_symbol_table.get_type_signature("Folder"),
            },
            "Folder": {
                "is_root": self.global_symbol_table.get_type_signature("bool"),
                "name": self.global_symbol_table.get_type_signature("string"),
                # Maybe change those to methods only
                "files": self.global_symbol_table.get_type_signature("List", self.global_symbol_table.get_type_signature("File")),
                "subfolders": self.global_symbol_table.get_type_signature("List", self.global_symbol_table.get_type_signature("Folder")),
            },
            "Audio": {
                "length": self.global_symbol_table.get_type_signature("int"),
                "bitrate": self.global_symbol_table.get_type_signature("int"),
                "title": self.global_symbol_table.get_type_signature("string"),
            }
        }

        # type_name -> { method_name -> FunctionTypeSignature }
        self.builtin_methods: Dict[str, Dict[str, FunctionTypeSignature]] = {
            "List": {
                "get": FunctionTypeSignature(
                    [self.global_symbol_table.get_type_signature("int")],
                    TypeSignature("any")
                ),
                "len": FunctionTypeSignature([], self.global_symbol_table.get_type_signature("int")),
            },
            "File": {
                "get_filename": FunctionTypeSignature([], self.global_symbol_table.get_type_signature("string")),
                "change_filename": FunctionTypeSignature([self.global_symbol_table.get_type_signature("string")], self.global_symbol_table.get_type_signature("void")),
                "move": FunctionTypeSignature([self.global_symbol_table.get_type_signature("Folder")], self.global_symbol_table.get_type_signature("void")),
                "delete": FunctionTypeSignature([], self.global_symbol_table.get_type_signature("void")),
            },
            "Folder": {
                "get_file": FunctionTypeSignature([self.global_symbol_table.get_type_signature("string")], self.global_symbol_table.get_type_signature("File")),
                "add_file": FunctionTypeSignature([self.global_symbol_table.get_type_signature("File")], self.global_symbol_table.get_type_signature("void")),
                "remove_file": FunctionTypeSignature([self.global_symbol_table.get_type_signature("string")], self.global_symbol_table.get_type_signature("void")),
                "list_files": FunctionTypeSignature([], self.global_symbol_table.get_type_signature("List", self.global_symbol_table.get_type_signature("File"))),
                "list_subfolders": FunctionTypeSignature([], self.global_symbol_table.get_type_signature("List", self.global_symbol_table.get_type_signature("Folder"))),
                "list_audio": FunctionTypeSignature([], self.global_symbol_table.get_type_signature("List", self.global_symbol_table.get_type_signature("Audio"))),
                "get_subfolder": FunctionTypeSignature([self.global_symbol_table.get_type_signature("string")], self.global_symbol_table.get_type_signature("Folder")),
                "get_name": FunctionTypeSignature([], self.global_symbol_table.get_type_signature("string")),
            },
            "Audio": {
                "cut": FunctionTypeSignature([self.global_symbol_table.get_type_signature("int"), self.global_symbol_table.get_type_signature("int")], self.global_symbol_table.get_type_signature("void")),
                "concat": FunctionTypeSignature([self.global_symbol_table.get_type_signature("Audio")], self.global_symbol_table.get_type_signature("void")),
                "change_title": FunctionTypeSignature([self.global_symbol_table.get_type_signature("string")], self.global_symbol_table.get_type_signature("void")),
                "change_format": FunctionTypeSignature([self.global_symbol_table.get_type_signature("string")], self.global_symbol_table.get_type_signature("void")),
                "change_volume": FunctionTypeSignature([self.global_symbol_table.get_type_signature("float")], self.global_symbol_table.get_type_signature("void")),
            }
        }

    def _enter_scope(self):
        self.current_scope = SymbolTable(parent=self.current_scope)

    def _exit_scope(self):
        if self.current_scope.parent is not None:
            self.current_scope = self.current_scope.parent
        else:
            raise SystemError("TypeChecker: Cannot exit global scope.")

    def _error(self, message: str, node: ParserNode):
        raise TypeMismatchException(node.start_position, message)

    def check(self, program_node: ProgramNode):
        try:
            for func_def_node in program_node.definitions:
                param_sigs = [self._ast_type_to_type_signature(p.param_type) for p in func_def_node.parameters]
                return_sig = self._ast_type_to_type_signature(func_def_node.return_type)
                func_sig = FunctionTypeSignature(param_sigs, return_sig)
                self.global_symbol_table.register_function(
                    func_def_node.identifier_name, func_sig, func_def_node.start_position
                )

            for stmt in program_node.statements:
                self.visit(stmt)

            self.current_scope = self.global_symbol_table
            self.current_function_return_type = None
        except TypeMismatchException as e:
            print(str(e))
            return None
        except Exception as e:
            print(f"[Type Checker Internal Error] {type(e).__name__}: {e}")
            return None

    def _ast_type_to_type_signature(self, ast_type_node: TypeNode) -> TypeSignature:
        if isinstance(ast_type_node, ListTypeNode):
            child_type_sig = self._ast_type_to_type_signature(ast_type_node.child_type_node)
            return self.global_symbol_table.get_type_signature("List", child_type_sig)
        return self.global_symbol_table.get_type_signature(ast_type_node.type_name)

    def _get_expression_type(self, node: ExpressionNode) -> TypeSignature:
        if node is None:
            self._error(f"TypeChecker encountered an unexpected None expression node.", Position(0,0))
            return TypeSignature("any")

        method_name = 'visit_' + type(node).__name__
        visitor_method = getattr(self, method_name, None)

        if not visitor_method:
            self._error(f"TypeChecker has no visitor method for expression type: {type(node).__name__}", node)
            return TypeSignature("any")

        inferred_type = visitor_method(node)
        if not isinstance(inferred_type, TypeSignature):
            self._error(f"Internal TypeChecker Error: Visitor for {type(node).__name__} did not return a TypeSignature.", node)
            return TypeSignature("any")

        return inferred_type

    # --- Node Visitor Methods ---

    def visit_ProgramNode(self, node: ProgramNode):
        pass

    def visit_CodeBlockNode(self, node: CodeBlockNode):
        self._enter_scope()
        for stmt in node.statements:
            self.visit(stmt)
        self._exit_scope()

    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode):
        declared_type_sig = self._ast_type_to_type_signature(node.var_type)
        expr_type_sig = self._get_expression_type(node.value) # Infer type of value expression

        if not declared_type_sig.is_compatible_with(expr_type_sig):
            self._error(f"Cannot assign expression of type '{expr_type_sig.to_string()}' "
                        f"to variable '{node.identifier_name}' of type '{declared_type_sig.to_string()}'.", node.value)

        self.current_scope.declare_variable(node.identifier_name, declared_type_sig, node.start_position)

    def visit_AssignmentNode(self, node: AssignmentNode):
        # LHS can be IdentifierNode or MemberAccessNode
        target_type_sig: Optional[TypeSignature] = None
        if isinstance(node.identifier, IdentifierNode):
            var_name = node.identifier.name
            target_type_sig = self.current_scope.get_variable_type(var_name)
            if target_type_sig is None:
                self._error(f"Undeclared variable '{var_name}' referenced.", node.identifier)
        elif isinstance(node.identifier, MemberAccessNode):
            target_type_sig = self._get_expression_type(node.identifier)
        else:
            self._error("Invalid left-hand side in assignment. Must be an identifier or member access.", node.identifier)

        rhs_type_sig = self._get_expression_type(node.value) # Get type of RHS expression

        if not target_type_sig.is_compatible_with(rhs_type_sig):
            self._error(f"Cannot assign expression of type '{rhs_type_sig.to_string()}' "
                        f"to target of type '{target_type_sig.to_string()}'.", node.value)

    def visit_IfStatementNode(self, node: IfStatementNode):
        condition_type = self._get_expression_type(node.condition)
        if not self.global_symbol_table.get_type_signature("bool").is_compatible_with(condition_type):
            self._error(f"If statement condition must be of type 'bool', got '{condition_type.to_string()}'.", node.condition)
        self.visit(node.if_block)
        if node.else_block:
            self.visit(node.else_block)

    def visit_WhileLoopNode(self, node: WhileLoopNode):
        condition_type = self._get_expression_type(node.condition)
        if not self.global_symbol_table.get_type_signature("bool").is_compatible_with(condition_type):
            self._error(f"While loop condition must be of type 'bool', got '{condition_type.to_string()}'.", node.condition)
        self.visit(node.body)

    def visit_ReturnStatementNode(self, node: ReturnStatementNode):
        if self.current_function_return_type is None:
            self._error("Return statement used outside of a function.", node)

        return_value_type = self.global_symbol_table.get_type_signature("void")
        if node.value:
            return_value_type = self._get_expression_type(node.value)

        if not self.current_function_return_type.is_compatible_with(return_value_type):
            self._error(f"Function declared to return '{self.current_function_return_type.to_string()}', "
                        f"but attempting to return '{return_value_type.to_string()}'.", node)


    def visit_FunctionDefinitionNode(self, node: FunctionDefinitionNode):
        previous_return_type = self.current_function_return_type
        self.current_function_return_type = self._ast_type_to_type_signature(node.return_type)

        self._enter_scope()

        for param in node.parameters:
            param_type_sig = self._ast_type_to_type_signature(param.param_type)
            self.current_scope.declare_variable(param.param_name, param_type_sig, param.start_position)

        self.visit(node.body)

        if self.current_function_return_type != self.global_symbol_table.get_type_signature("void"):
            pass

        self._exit_scope()
        self.current_function_return_type = previous_return_type

    def visit_ExpressionStatementNode(self, node: ExpressionStatementNode):
        self._get_expression_type(node.expression)

    def visit_FunctionCallStatementNode(self, node: FunctionCallStatementNode):
        self.visit_FunctionCallNode(node.call_expression)


    # --- Expression Type Inference Methods ---

    def visit_IntLiteralNode(self, node: IntLiteralNode) -> TypeSignature:
        return self.global_symbol_table.get_type_signature("int")

    def visit_FloatLiteralNode(self, node: FloatLiteralNode) -> TypeSignature:
        return self.global_symbol_table.get_type_signature("float")

    def visit_StringLiteralNode(self, node: StringLiteralNode) -> TypeSignature:
        return self.global_symbol_table.get_type_signature("string")

    def visit_BoolLiteralNode(self, node: BoolLiteralNode) -> TypeSignature:
        return self.global_symbol_table.get_type_signature("bool")

    def visit_NullLiteralNode(self, node: NullLiteralNode) -> TypeSignature:
        return self.global_symbol_table.get_type_signature("null")

    def visit_IdentifierNode(self, node: IdentifierNode) -> TypeSignature:
        var_type = self.current_scope.get_variable_type(node.name)
        if var_type is None:
            self._error(f"Undeclared identifier '{node.name}'.", node)
        return var_type

    def visit_ListLiteralNode(self, node: ListLiteralNode) -> TypeSignature:
        if not node.elements:
            return self.global_symbol_table.get_type_signature("List", self.global_symbol_table.get_type_signature("null"))

        inferred_element_type = self._get_expression_type(node.elements[0])
        for i in range(1, len(node.elements)):
            current_elem_type = self._get_expression_type(node.elements[i])

            if not inferred_element_type.is_compatible_with(current_elem_type) and \
               not current_elem_type.is_compatible_with(inferred_element_type):
                self._error(f"List literal elements must be of compatible types. "
                            f"Element {i+1} has type '{current_elem_type.to_string()}', "
                            f"expected compatible with '{inferred_element_type.to_string()}'.", node.elements[i])

            # If current element type is more specific (e.g., List<File> then Audio), update inferred type
            if current_elem_type.is_compatible_with(inferred_element_type) and not inferred_element_type.is_compatible_with(current_elem_type):
                inferred_element_type = current_elem_type

        return self.global_symbol_table.get_type_signature("List", inferred_element_type)

    def visit_ConstructorCallNode(self, node: ConstructorCallNode) -> TypeSignature:
        constructor_name = node.type_name
        constructor_type_sig = self.global_symbol_table.get_type_signature(constructor_name)

        if len(node.arguments) != 1:
            self._error(f"Constructor '{constructor_name}' expects 1 argument, got {len(node.arguments)}.", node)
        arg_type = self._get_expression_type(node.arguments[0])
        expected_arg_type = self.global_symbol_table.get_type_signature("string")
        if not expected_arg_type.is_compatible_with(arg_type):
            self._error(f"Constructor '{constructor_name}' expects a '{expected_arg_type.to_string()}' argument, got '{arg_type.to_string()}'.", node.arguments[0])

        return constructor_type_sig

    def _visit_binary_op_node(self, node: ExpressionNode, op_symbol: str) -> TypeSignature:
        left_type = self._get_expression_type(node.left)
        right_type = self._get_expression_type(node.right)

        if op_symbol in ["+", "-", "*", "/"]:
            if (left_type.base_type == "int" and right_type.base_type == "int") or (left_type.base_type == "float" and right_type.base_type == "float"):
                if left_type.base_type == "float":
                    return self.global_symbol_table.get_type_signature("float")
                return self.global_symbol_table.get_type_signature("int")
            if op_symbol == "+" and left_type.base_type == "string" and right_type.base_type == "string":
                return self.global_symbol_table.get_type_signature("string")
            self._error(f"Operator '{op_symbol}' not defined for types '{left_type.to_string()}' and '{right_type.to_string()}'.", node)

        elif op_symbol in ["==", "!=", "<", "<=", ">", ">="]:
            # Numeric comparisons: int with int
            if (left_type.base_type == "int" and right_type.base_type == "int"):
                return self.global_symbol_table.get_type_signature("bool")
            # Numeric comparisons: float with float
            if (left_type.base_type == "float" and right_type.base_type == "float"):
                return self.global_symbol_table.get_type_signature("bool")
            # String comparison: string with string
            if (left_type.base_type == "string" and right_type.base_type == "string"):
                return self.global_symbol_table.get_type_signature("bool")
            # Boolean comparison: bool with bool
            if (left_type.base_type == "bool" and right_type.base_type == "bool"):
                return self.global_symbol_table.get_type_signature("bool")

            # Object equality (==, !=) can compare any two types if one can be null
            if op_symbol in ["==", "!="] and (left_type.is_compatible_with(right_type) or right_type.is_compatible_with(left_type)):
                return self.global_symbol_table.get_type_signature("bool")

            self._error(f"Operator '{op_symbol}' not defined for types '{left_type.to_string()}' and '{right_type.to_string()}'.", node)

        elif op_symbol in ["&&", "||"]:
            if not self.global_symbol_table.get_type_signature("bool").is_compatible_with(left_type):
                self._error(f"Left operand of '{op_symbol}' must be 'bool', got '{left_type.to_string()}'.", node.left)
            if not self.global_symbol_table.get_type_signature("bool").is_compatible_with(right_type):
                self._error(f"Right operand of '{op_symbol}' must be 'bool', got '{right_type.to_string()}'.", node.right)
            return self.global_symbol_table.get_type_signature("bool")

    def visit_AddNode(self, node: AddNode) -> TypeSignature: return self._visit_binary_op_node(node, "+")
    def visit_SubtractNode(self, node: SubtractNode) -> TypeSignature: return self._visit_binary_op_node(node, "-")
    def visit_MultiplyNode(self, node: MultiplyNode) -> TypeSignature: return self._visit_binary_op_node(node, "*")
    def visit_DivideNode(self, node: DivideNode) -> TypeSignature: return self._visit_binary_op_node(node, "/")

    def visit_EqualsNode(self, node: EqualsNode) -> TypeSignature: return self._visit_binary_op_node(node, "==")
    def visit_NotEqualsNode(self, node: NotEqualsNode) -> TypeSignature: return self._visit_binary_op_node(node, "!=")
    def visit_LessThanNode(self, node: LessThanNode) -> TypeSignature: return self._visit_binary_op_node(node, "<")
    def visit_LessThanOrEqualNode(self, node: LessThanOrEqualNode) -> TypeSignature: return self._visit_binary_op_node(node, "<=")
    def visit_GreaterThanNode(self, node: GreaterThanNode) -> TypeSignature: return self._visit_binary_op_node(node, ">")
    def visit_GreaterThanOrEqualNode(self, node: GreaterThanOrEqualNode) -> TypeSignature: return self._visit_binary_op_node(node, ">=")
    def visit_LogicalAndNode(self, node: LogicalAndNode) -> TypeSignature: return self._visit_binary_op_node(node, "&&")
    def visit_LogicalOrNode(self, node: LogicalOrNode) -> TypeSignature: return self._visit_binary_op_node(node, "||")

    def visit_UnaryMinusNode(self, node: UnaryMinusNode) -> TypeSignature:
        operand_type = self._get_expression_type(node.operand)
        if operand_type.base_type == "int": return self.global_symbol_table.get_type_signature("int")
        if operand_type.base_type == "float": return self.global_symbol_table.get_type_signature("float")
        self._error(f"Unary minus cannot be applied to type '{operand_type.to_string()}'.", node)

    def visit_FunctionCallNode(self, node: FunctionCallNode) -> TypeSignature:
        func_sig: Optional[FunctionTypeSignature] = None

        if isinstance(node.function_name, MemberAccessNode):
            # Method call: obj.method()
            obj_type = self._get_expression_type(node.function_name.object_expr)
            method_name = node.function_name.member_name

            if obj_type.base_type == "null":
                self._error(f"Attempted to call method '{method_name}' on a null object.", node.function_name.object_expr)

            if obj_type.base_type in self.builtin_methods and method_name in self.builtin_methods[obj_type.base_type]:
                func_sig = self.builtin_methods[obj_type.base_type][method_name]
                # Special handling for List.get() return type based on actual list type
                if obj_type.base_type == "List" and method_name == "get":
                    func_sig = FunctionTypeSignature(func_sig.param_types, obj_type.child_type)
            elif obj_type.base_type == "Audio" and "File" in self.builtin_methods and method_name in self.builtin_methods["File"]:
                func_sig = self.builtin_methods["File"][method_name]
            else:
                self._error(f"Type '{obj_type.to_string()}' has no method '{method_name}'.", node.function_name)

        elif isinstance(node.function_name, IdentifierNode):
            # Regular function call: func_name()
            func_name = node.function_name.name
            func_sig = self.global_symbol_table.get_function_signature(func_name)
            if func_sig is None:
                self._error(f"Undefined function '{func_name}' called.", node.function_name)
        else:
            self._error(f"Cannot call expression of type {type(node.function_name).__name__}. Must be an identifier or member access.", node.function_name)

        if func_sig is None:
            self._error(f"Internal TypeChecker Error: Could not resolve function/method '{node.function_name}'.", node)


        # Check argument count
        if len(node.arguments) != len(func_sig.param_types):
            self._error(f"Function/method '{node.function_name.name}' expected {len(func_sig.param_types)} arguments, but got {len(node.arguments)}.", node)

        # Check argument types
        for i, (arg_node, expected_param_type_sig) in enumerate(zip(node.arguments, func_sig.param_types)):
            actual_arg_type_sig = self._get_expression_type(arg_node)
            if not expected_param_type_sig.is_compatible_with(actual_arg_type_sig):
                self._error(f"Argument {i+1} for function/method '{node.function_name.name}': expected type '{expected_param_type_sig.to_string()}', got '{actual_arg_type_sig.to_string()}'.", arg_node)

        return func_sig.return_type


    def visit_MemberAccessNode(self, node: MemberAccessNode) -> TypeSignature:
        obj_type = self._get_expression_type(node.object_expr)
        member_name = node.member_name

        if obj_type.base_type == "null":
            self._error(f"Attempted to access member '{member_name}' on a null object.", node.object_expr)

        if obj_type.base_type in self.builtin_properties and member_name in self.builtin_properties[obj_type.base_type]:
            return self.builtin_properties[obj_type.base_type][member_name]

        if obj_type.base_type == "Audio" and "File" in self.builtin_properties and member_name in self.builtin_properties["File"]:
            return self.builtin_properties["File"][member_name]

        self._error(f"Type '{obj_type.to_string()}' has no accessible property '{member_name}'.", node)

    def visit_TypeNode(self, node: TypeNode): pass
    def visit_ListTypeNode(self, node: ListTypeNode): pass
    def visit_ParameterNode(self, node: ParameterNode): pass

    def visit(self, node: Any, *args, **kwargs):
        if node is None:
            self._error(f"TypeChecker encountered an unexpected None node.", Position(0,0))
            return None

        method_name = 'visit_' + type(node).__name__
        visitor_method = getattr(self, method_name, None)

        if not visitor_method:
            self._error(f"TypeChecker has no visitor method for AST node type: {type(node).__name__}", node)
            return None

        return visitor_method(node, *args, **kwargs)