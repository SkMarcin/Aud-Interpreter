# source/interpreter/interpreter.py
from typing import Any, List, Callable, Optional

from source.nodes import *
from source.visitor import NodeVisitor
from source.interpreter.runtime_values import Value, IntValue, FloatValue, StringValue, BoolValue, NullValue, ListValue, \
                                         FileValue, FolderValue, AudioValue, BuiltInFunction
from source.interpreter.environment import Environment
from source.utils import Position, RuntimeException, Config

class Interpreter(NodeVisitor):
    def __init__(self, config: Optional[Config] = None):
        self.config = config if config else Config()
        self._input_buffer: List[str] = []
        self._input_buffer_idx: int = 0
        self.env: Environment = Environment(config=self.config)
        self.last_value: Value = NullValue()

    def set_input_data(self, data: List[str]):
        self._input_buffer = data
        self._input_buffer_idx = 0
        self.env.input_retriever = self._get_mock_input

    def _get_mock_input(self) -> Optional[str]:
        if self._input_buffer_idx < len(self._input_buffer):
            val = self._input_buffer[self._input_buffer_idx]
            self._input_buffer_idx += 1
            return val
        return None

    def _error(self, message: str, node: Optional[ParserNode] = None):
        pos = node.start_position if node else (Position(0,0) if self.env.call_stack else None)
        raise RuntimeException(message, pos)

    def interpret_program(self, program_node: ProgramNode) -> Optional[Value]:
        try:
            self.visit(program_node)
            return self.last_value
        except RuntimeException as e:
            print(str(e))
            return None
        except Exception as e:
            print(f"[Interpreter Internal Error] {type(e).__name__}: {e}")
            return None


    # --- Visitor Methods ---
    def visit_ProgramNode(self, node: ProgramNode):
        for stmt in node.definitions:
            self.env.register_function(stmt.identifier_name, stmt)

        for stmt in node.statements:
            if not isinstance(stmt, FunctionDefinitionNode):
                self.visit(stmt)
                if self.env.return_pending : self._error("Return statement outside of function.", stmt)

    def visit_CodeBlockNode(self, node: CodeBlockNode):
        self.env.current_context().enter_scope()
        for stmt in node.statements:
            self.visit(stmt)
            if self.env.return_pending:
                break
        self.env.current_context().exit_scope()

    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode):
        self.visit(node.value)
        value_to_assign = self.last_value

        self.env.declare_variable(node.identifier_name, value_to_assign, node.start_position)
        self.last_value = NullValue()

    def visit_AssignmentNode(self, node: AssignmentNode):
        self.visit(node.value) # RHS
        rhs_value = self.last_value

        if isinstance(node.identifier, IdentifierNode):
            var_name = node.identifier.name
            self.env.assign_variable(var_name, rhs_value, node.identifier.start_position)
        elif isinstance(node.identifier, MemberAccessNode):
            # obj.member = value
            self.visit(node.identifier.object_expr)
            obj_to_mutate = self.last_value
            member_name = node.identifier.member_name

            obj_to_mutate.set_attribute_value(member_name, rhs_value, node.identifier.start_position)
        else:
            self._error("Invalid left-hand side in assignment.", node.identifier)

        self.last_value = NullValue()


    def visit_IfStatementNode(self, node: IfStatementNode):
        self.visit(node.condition)
        condition_value = self.last_value

        if condition_value.is_true():
            self.visit(node.if_block)
        elif node.else_block:
            self.visit(node.else_block)
        self.last_value = NullValue()


    def visit_WhileLoopNode(self, node: WhileLoopNode):
        while True:
            self.visit(node.condition)
            condition_value = self.last_value

            if not condition_value.is_true(): break

            self.visit(node.body)

            if self.env.return_pending: break
        self.last_value = NullValue()


    def visit_ReturnStatementNode(self, node: ReturnStatementNode):
        if node.value:
            self.visit(node.value)
            self.env.return_value = self.last_value
        else:
            self.env.return_value = NullValue()
        self.env.return_pending = True

    def visit_FunctionDefinitionNode(self, node: FunctionDefinitionNode):
        self.last_value = NullValue()

    def visit_ExpressionStatementNode(self, node: ExpressionStatementNode):
        self.visit(node.expression)
        self.last_value = NullValue()

    def visit_FunctionCallStatementNode(self, node: FunctionCallStatementNode):
        self.visit(node.call_expression)
        self.last_value = NullValue()

    # --- Expression Nodes (set self.last_value) ---
    def visit_IntLiteralNode(self, node: IntLiteralNode):
        self.last_value = IntValue(node.value)

    def visit_FloatLiteralNode(self, node: FloatLiteralNode):
        self.last_value = FloatValue(node.value)

    def visit_StringLiteralNode(self, node: StringLiteralNode):
        self.last_value = StringValue(node.value)

    def visit_BoolLiteralNode(self, node: BoolLiteralNode):
        self.last_value = BoolValue(node.value)

    def visit_NullLiteralNode(self, node: NullLiteralNode):
        self.last_value = NullValue()

    def visit_IdentifierNode(self, node: IdentifierNode):
        self.last_value = self.env.get_variable(node.name, node.start_position)

    def visit_ListLiteralNode(self, node: ListLiteralNode):
        elements_values: List[Value] = []
        element_type_str = "unknown"

        if node.elements:
            first_elem_node = node.elements[0]
            self.visit(first_elem_node)
            first_element_value = self.last_value
            elements_values.append(first_element_value)
            element_type_str = first_element_value.get_type_str()

            for i in range(1, len(node.elements)):
                elem_node = node.elements[i]
                self.visit(elem_node)
                current_element_value = self.last_value
                elements_values.append(current_element_value)

        self.last_value = ListValue(element_type_str, elements_values)

    def visit_ConstructorCallNode(self, node: ConstructorCallNode):
        args_values: List[Value] = []
        for arg_node in node.arguments:
            self.visit(arg_node)
            args_values.append(self.last_value)

        type_name = node.type_name
        if type_name == "File":
            self.last_value = FileValue(args_values[0].value, node.start_position)
        elif type_name == "Folder":
            self.last_value = FolderValue(args_values[0].value, node.start_position)
        elif type_name == "Audio":
            self.last_value = AudioValue(args_values[0].value, node.start_position)
        else:
            self._error(f"Unknown constructor type '{type_name}'.", node)

    # --- Binary and Unary Operations ---
    def _perform_binary_operation(self, left: Value, right: Value, node_for_error: ParserNode, op_symbol: str,
                         int_op: Optional[Callable[[int,int], Any]] = None,
                         float_op: Optional[Callable[[float,float], Any]] = None,
                         str_op: Optional[Callable[[str,str], Any]] = None,
                         bool_op: Optional[Callable[[bool,bool], Any]] = None,
                         obj_op: Optional[Callable[[Value,Value], Any]] = None
                        ) -> Value:
        result = None
        res_val = None

        if isinstance(left, IntValue) and isinstance(right, IntValue) and int_op:
            result = int_op(left.value, right.value)
            if isinstance(result, bool): res_val = BoolValue(result)
            elif isinstance(result, int): res_val = IntValue(result)
        elif isinstance(left, (IntValue, FloatValue)) and isinstance(right, (IntValue, FloatValue)) and float_op:
            l_f = float(left.value)
            r_f = float(right.value)
            result = float_op(l_f, r_f)
            if isinstance(result, bool): res_val = BoolValue(result)
            elif isinstance(result, float): res_val = FloatValue(result)
        elif isinstance(left, StringValue) and isinstance(right, StringValue) and str_op:
            result = str_op(left.value, right.value)
            if isinstance(result, bool): res_val = BoolValue(result)
            elif isinstance(result, str): res_val = StringValue(result)
        elif isinstance(left, BoolValue) and isinstance(right, BoolValue) and bool_op:
            result = bool_op(left.value, right.value)
            if isinstance(result, bool): res_val = BoolValue(result)
        elif obj_op and (isinstance(left, (FileValue, FolderValue, NullValue, ListValue)) or isinstance(right, (FileValue, FolderValue, NullValue, ListValue))):
            result = obj_op(left, right)
            if isinstance(result, bool): res_val = BoolValue(result)

        if res_val is not None:
            return res_val

        self._error(f"Operator '{op_symbol}' cannot be applied to types '{left.get_type_str()}' and '{right.get_type_str()}'.", node_for_error)

    def visit_AddNode(self, node: AddNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, "+", int_op=lambda a,b:a+b, float_op=lambda a,b:a+b, str_op=lambda a,b:a+b)

    def visit_SubtractNode(self, node: SubtractNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, "-", int_op=lambda a,b:a-b, float_op=lambda a,b:a-b)

    def visit_MultiplyNode(self, node: MultiplyNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, "*", int_op=lambda a,b:a*b, float_op=lambda a,b:a*b)

    def visit_DivideNode(self, node: DivideNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value

        if right.value == 0: self._error("Division by zero.", node)

        self.last_value = self._perform_binary_operation(left, right, node, "/", int_op=lambda a,b:a//b, float_op=lambda a,b:a/b)

    def _compare_objects(self, left: Value, right: Value) -> bool:
        if left.is_null() and right.is_null():
            return True
        if left.is_null() != right.is_null():
            return False

        if isinstance(left, FileValue) and isinstance(right, FileValue):
            parent_match = False
            if left.parent is None and right.parent is None:
                parent_match = True
            elif left.parent is not None and right.parent is not None:
                parent_match = (left.parent.path_name == right.parent.path_name)
            return left._fs_path == right._fs_path and parent_match

        if isinstance(left, FolderValue) and isinstance(right, FolderValue):
            return left.path_name == right.path_name and left.is_root == right.is_root

        return False

    def visit_EqualsNode(self, node: EqualsNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, "==", int_op=lambda a,b:a==b, float_op=lambda a,b:a==b,
                              str_op=lambda a,b:a==b, bool_op=lambda a,b:a==b,
                              obj_op=self._compare_objects)

    def visit_NotEqualsNode(self, node: NotEqualsNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, "!=", int_op=lambda a,b:a!=b, float_op=lambda a,b:a!=b,
                              str_op=lambda a,b:a!=b, bool_op=lambda a,b:a!=b,
                              obj_op=lambda l,r: not self._compare_objects(l,r))

    def visit_LessThanNode(self, node: LessThanNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, "<", int_op=lambda a,b:a<b, float_op=lambda a,b:a<b)

    def visit_LessThanOrEqualNode(self, node: LessThanOrEqualNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, "<=", int_op=lambda a,b:a<=b, float_op=lambda a,b:a<=b)

    def visit_GreaterThanNode(self, node: GreaterThanNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, ">", int_op=lambda a,b:a>b, float_op=lambda a,b:a>b)

    def visit_GreaterThanOrEqualNode(self, node: GreaterThanOrEqualNode):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        self.last_value = self._perform_binary_operation(left, right, node, ">=", int_op=lambda a,b:a>=b, float_op=lambda a,b:a>=b)

    def visit_LogicalAndNode(self, node: LogicalAndNode):
        self.visit(node.left); left_val = self.last_value
        if not left_val.is_true(): self.last_value = BoolValue(False)
        else:
            self.visit(node.right); right_val = self.last_value
            self.last_value = BoolValue(right_val.is_true())

    def visit_LogicalOrNode(self, node: LogicalOrNode):
        self.visit(node.left); left_val = self.last_value
        if left_val.is_true(): self.last_value = BoolValue(True)
        else:
            self.visit(node.right); right_val = self.last_value
            self.last_value = BoolValue(right_val.is_true())

    def visit_UnaryMinusNode(self, node: UnaryMinusNode):
        self.visit(node.operand); val = self.last_value
        if isinstance(val, IntValue): self.last_value = IntValue(-val.value)
        elif isinstance(val, FloatValue): self.last_value = FloatValue(-val.value)
        else: self._error(f"Unary minus cannot be applied to type {val.get_type_str()}.", node)

    def visit_FunctionCallNode(self, node: FunctionCallNode):
        args_values: List[Value] = []
        for arg_node in node.arguments:
            self.visit(arg_node)
            args_values.append(self.last_value)

        callable_target: Any = None
        obj_context: Optional[Value] = None

        is_method_call = isinstance(node.function_name, MemberAccessNode)

        if is_method_call:
            member_access_node = node.function_name

            self.visit(member_access_node.object_expr)
            obj_context = self.last_value

            method_name_str = member_access_node.member_name

            if obj_context.is_null():
                self._error(f"Attempted to access member '{method_name_str}' on null object.", member_access_node.object_expr)

            callable_target = method_name_str
        else:
            func_name_node = node.function_name
            if not isinstance(func_name_node, IdentifierNode):
                self._error(f"Cannot call expression of type {type(func_name_node).__name__}.", func_name_node)

            func_name_str = func_name_node.name
            callable_target = self.env.lookup_function(func_name_str, func_name_node.start_position)

        # --- Actual Call Dispatch ---
        if isinstance(callable_target, BuiltInFunction):
            self.last_value = callable_target.call(args_values, node.start_position, self.env)

        elif isinstance(callable_target, FunctionDefinitionNode): # User-defined function
            user_func_node = callable_target
            self.env.push_call_context(user_func_node.identifier_name, node.start_position)

            # declare params as variables
            for param_node, arg_val in zip(user_func_node.parameters, args_values):
                self.env.declare_variable(param_node.param_name, arg_val, param_node.start_position)

            self.visit(user_func_node.body) # Execute

            returned_value = self.env.return_value
            is_explicit_return = self.env.return_pending

            self.env.return_pending = False
            self.env.return_value = NullValue()

            return_type_name = user_func_node.return_type.type_name

            if isinstance(user_func_node.return_type, ListTypeNode):
                return_type_name = "List"

            if return_type_name == "void":
                if is_explicit_return and not isinstance(returned_value, NullValue):
                    self._error(f"Void function '{user_func_node.identifier_name}' cannot return a value.",
                                user_func_node)
                self.last_value = NullValue()
            else:
                if not is_explicit_return:
                    self._error(f"Function '{user_func_node.identifier_name}' must return a '{return_type_name}'.",
                                user_func_node)
                # To avoid references between Contexts
                if isinstance(returned_value, (IntValue, FloatValue, StringValue, BoolValue)):
                    self.last_value = returned_value.clone()
                else:
                    self.last_value = returned_value

            self.env.pop_call_context()

        elif obj_context is not None and isinstance(callable_target, str): # Method call (callable_target is method_name)
            method_name = callable_target
            self.last_value = obj_context.call_method(method_name, args_values, node.start_position, self.env)

        else:
            self._error(f"Internal: Cannot execute call for target '{str(callable_target)}'.", node)


    def visit_MemberAccessNode(self, node: MemberAccessNode):
        self.visit(node.object_expr)
        obj_val = self.last_value
        member_name = node.member_name

        if obj_val.is_null():
            self._error(f"Attempted to access member '{member_name}' on null object.", node.object_expr)

        self.last_value = obj_val.get_attribute(member_name, node.start_position)

    def visit_TypeNode(self, node: TypeNode): pass # Structural
    def visit_ListTypeNode(self, node: ListTypeNode): pass # Structural
    def visit_ParameterNode(self, node: ParameterNode): pass # Structural

    # Default for unhandled nodes
    def visit(self, node: Any, *args, **kwargs):
        if node is None:
            self._error(f"Interpreter encountered an unexpected None node.", Position(0,0))
            return

        method_name = 'visit_' + type(node).__name__
        visitor_method = getattr(self, method_name, None)

        if not visitor_method:
            self._error(f"Interpreter has no visitor method for AST node type: {type(node).__name__}", node)
            return

        return visitor_method(node, *args, **kwargs)