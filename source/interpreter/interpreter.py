from typing import Any, List, Callable

from source.nodes import *
from source.visitor import NodeVisitor
from source.interpreter.runtime_values import Value, IntValue, FloatValue, StringValue, BoolValue, NullValue, ListValue, \
                                         FileValue, FolderValue, AudioValue, BuiltInFunction
from source.interpreter.environment import Environment
from source.utils import Position, RuntimeError, Config

class Interpreter(NodeVisitor):
    def __init__(self, config: Optional[Config] = None):
        self.config = config if config else Config()
        self._input_buffer: List[str] = []
        self._input_buffer_idx: int = 0
        self.env: Environment = Environment(config=self.config, input_retriever=self._get_mock_input)
        self.last_value: Value = NullValue()

    def set_input_data(self, data: List[str]):
        self._input_buffer = data
        self._input_buffer_idx = 0

    def _get_mock_input(self) -> Optional[str]:
        if self._input_buffer_idx < len(self._input_buffer):
            val = self._input_buffer[self._input_buffer_idx]
            self._input_buffer_idx += 1
            return val
        return None 

    def _error(self, message: str, node: Optional[ParserNode] = None):
        pos = node.start_position if node else (Position(0,0) if self.env.call_stack else None)
        raise RuntimeError(message, pos)
    
    def _error(self, message: str, node: Optional[ParserNode] = None, pos: Optional[Position] = None):
        error_pos = pos
        if not error_pos and node:
            error_pos = node.start_position
        if not error_pos:
            error_pos = Position(0, 0)
        raise RuntimeError(message, error_pos)

    def interpret_program(self, program_node: ProgramNode) -> Optional[Value]:
        try:
            self.visit(program_node)
            return self.last_value
        except RuntimeError as e:
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
        # Flags propagate up

    def visit_VariableDeclarationNode(self, node: VariableDeclarationNode):
        self.visit(node.value) # Evaluate expression, result in self.last_value
        value_to_assign = self.last_value

        declared_type_str = self.env.get_type_str_from_ast_type(node.var_type, node.start_position)
        self.env.type_check_compatibility(declared_type_str, value_to_assign, node.value.start_position,
                                          f"In declaration of '{node.identifier_name}': ")

        self.env.declare_variable(node.identifier_name, value_to_assign, node.start_position)
        self.last_value = NullValue() # Statement has no value

    def visit_AssignmentNode(self, node: AssignmentNode):
        self.visit(node.value) # RHS
        rhs_value = self.last_value

        if isinstance(node.identifier, IdentifierNode):
            var_name = node.identifier.name
            # This will handle pass-by-reference for primitives correctly due to Scope.assign logic
            self.env.assign_variable(var_name, rhs_value, node.identifier.start_position)
        elif isinstance(node.identifier, MemberAccessNode):
            # obj.member = value
            self.visit(node.identifier.object_expr)
            obj_to_mutate = self.last_value # e.g., AudioValue instance
            member_name = node.identifier.member_name

            # This requires a generic set_attribute or specific logic
            if hasattr(obj_to_mutate, 'set_attribute_value'): # Ideal generic way
                 obj_to_mutate.set_attribute_value(member_name, rhs_value, node.identifier.start_position)
            # Specific example for Audio.title (if no generic set_attribute)
            elif isinstance(obj_to_mutate, AudioValue) and member_name == "title":
                if not isinstance(rhs_value, StringValue):
                    self._error(f"Cannot assign non-string to Audio.title.", node.value)
                obj_to_mutate.title = rhs_value.value # Directly mutate the .title field
            # Add other mutable attributes for File, Folder, Audio
            else:
                self._error(f"Cannot assign to member '{member_name}' of type '{obj_to_mutate.get_type_str()}'.", node.identifier)
        else:
            self._error("Invalid left-hand side in assignment.", node.identifier)
        
        self.last_value = NullValue()


    def visit_IfStatementNode(self, node: IfStatementNode):
        self.visit(node.condition)
        condition_value = self.last_value
        self.env.type_check_compatibility("bool", condition_value, node.condition.start_position, "If condition: ")

        if condition_value.is_true():
            self.visit(node.if_block)
        elif node.else_block:
            self.visit(node.else_block)
        self.last_value = NullValue()


    def visit_WhileLoopNode(self, node: WhileLoopNode):
        while True:
            self.visit(node.condition)
            condition_value = self.last_value
            self.env.type_check_compatibility("bool", condition_value, node.condition.start_position, "While condition: ")

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
        # Function defined in ProgramNode, no action here 
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
        element_type_str = "unknown" # Default for empty or to be inferred

        if node.elements:
            first_elem_node = node.elements[0]
            self.visit(first_elem_node)
            first_element_value = self.last_value
            elements_values.append(first_element_value)
            element_type_str = first_element_value.get_type_str() # Infer from first

            for i in range(1, len(node.elements)):
                elem_node = node.elements[i]
                self.visit(elem_node)
                current_element_value = self.last_value
                # Type check homogeneity (simplistic, could allow subtypes if list type is supertype)
                self.env.type_check_compatibility(element_type_str, current_element_value, elem_node.start_position,
                                                  "List literal element: ")
                elements_values.append(current_element_value)
        
        self.last_value = ListValue(element_type_str, elements_values)

    def visit_ConstructorCallNode(self, node: ConstructorCallNode):
        args_values: List[Value] = [self.visit(arg_node) or self.last_value for arg_node in node.arguments]

        type_name = node.type_name
        # TODO: Proper arity and type checking for constructors based on their implicit signatures
        if type_name == "File":
            if len(args_values) != 1 or not isinstance(args_values[0], StringValue):
                self._error(f"File constructor expects 1 string argument (path).", node)
            self.last_value = FileValue(args_values[0].value)
        elif type_name == "Folder":
            if len(args_values) != 1 or not isinstance(args_values[0], StringValue):
                 self._error(f"Folder constructor expects 1 string argument (path).", node)
            self.last_value = FolderValue(args_values[0].value)
        elif type_name == "Audio":
            if len(args_values) != 1 or not isinstance(args_values[0], StringValue):
                 self._error(f"Audio constructor expects 1 string argument (path).", node)
            self.last_value = AudioValue(args_values[0].value, title=args_values[0].value)
        else:
            self._error(f"Unknown constructor type '{type_name}'.", node)

    # --- Binary and Unary Operations ---
    def _apply_binary_op(self, node, op_symbol: str, 
                         int_op: Optional[Callable[[int,int], Any]] = None, 
                         float_op: Optional[Callable[[float,float], Any]] = None,
                         str_op: Optional[Callable[[str,str], Any]] = None,
                         bool_op: Optional[Callable[[bool,bool], Any]] = None,
                         obj_op: Optional[Callable[[Value,Value], Any]] = None # For File/Folder/Null comparison
                        ):
        self.visit(node.left)
        left = self.last_value
        self.visit(node.right)
        right = self.last_value
        
        result = None
        res_val = None

        if isinstance(left, IntValue) and isinstance(right, IntValue) and int_op:
            result = int_op(left.value, right.value)
            if isinstance(result, bool): res_val = BoolValue(result)
            elif isinstance(result, int): res_val = IntValue(result)
            # If int_op can result in float (e.g. true division), handle FloatValue(result)
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
        elif obj_op and (isinstance(left, (FileValue, FolderValue, NullValue)) or isinstance(right, (FileValue, FolderValue, NullValue))):
            # Specific for ==, != on File/Folder/Null
            result = obj_op(left, right)
            if isinstance(result, bool): res_val = BoolValue(result)

        if res_val is not None:
            self.last_value = res_val
            return

        self._error(f"Operator '{op_symbol}' cannot be applied to types '{left.get_type_str()}' and '{right.get_type_str()}'.", node)

    def visit_AddNode(self, node: AddNode):
        # Special string concat
        self.visit(node.left); left = self.last_value
        self.visit(node.right); right = self.last_value
        if isinstance(left, StringValue) and isinstance(right, StringValue):
            self.last_value = StringValue(left.value + right.value)
            return
        self._apply_binary_op(node, "+", int_op=lambda a,b:a+b, float_op=lambda a,b:a+b)
        
    def visit_SubtractNode(self, node: SubtractNode): self._apply_binary_op(node, "-", int_op=lambda a,b:a-b, float_op=lambda a,b:a-b)
    def visit_MultiplyNode(self, node: MultiplyNode): self._apply_binary_op(node, "*", int_op=lambda a,b:a*b, float_op=lambda a,b:a*b)
    
    def visit_DivideNode(self, node: DivideNode):
        self.visit(node.left); left = self.last_value
        self.visit(node.right); right = self.last_value
        if right.value == 0: self._error("Division by zero.", node)

        if isinstance(left, IntValue) and isinstance(right, IntValue):
            self.last_value = IntValue(left.value // right.value)
        elif isinstance(left, (FloatValue)) and isinstance(right, (FloatValue)):
            self.last_value = FloatValue(float(left.value) / float(right.value))
        else:
            self._error(f"Operator '/' cannot be applied to types '{left.get_type_str()}' and '{right.get_type_str()}'.", node)

    def _compare_objects(self, left: Value, right: Value) -> bool:
        # For File/Folder/Null comparison (==, !=)
        if type(left) != type(right):
            return False
        if isinstance(left, NullValue):
            return True
        if isinstance(left, FileValue):
            return left.filename == right.filename and left.parent is right.parent
        if isinstance(left, FolderValue):
            return left.path_name == right.path_name and left.is_root == right.is_root
        return False

    def visit_EqualsNode(self, node: EqualsNode): 
        self._apply_binary_op(node, "==", int_op=lambda a,b:a==b, float_op=lambda a,b:a==b, 
                              str_op=lambda a,b:a==b, bool_op=lambda a,b:a==b,
                              obj_op=self._compare_objects)
    def visit_NotEqualsNode(self, node: NotEqualsNode):
        self._apply_binary_op(node, "!=", int_op=lambda a,b:a!=b, float_op=lambda a,b:a!=b,
                              str_op=lambda a,b:a!=b, bool_op=lambda a,b:a!=b,
                              obj_op=lambda l,r: not self._compare_objects(l,r))

    def visit_LessThanNode(self, node: LessThanNode): self._apply_binary_op(node, "<", int_op=lambda a,b:a<b, float_op=lambda a,b:a<b)
    def visit_LessThanOrEqualNode(self, node: LessThanOrEqualNode): self._apply_binary_op(node, "<=", int_op=lambda a,b:a<=b, float_op=lambda a,b:a<=b)
    def visit_GreaterThanNode(self, node: GreaterThanNode): self._apply_binary_op(node, ">", int_op=lambda a,b:a>b, float_op=lambda a,b:a>b)
    def visit_GreaterThanOrEqualNode(self, node: GreaterThanOrEqualNode): self._apply_binary_op(node, ">=", int_op=lambda a,b:a>=b, float_op=lambda a,b:a>=b)

    def visit_LogicalAndNode(self, node: LogicalAndNode):
        self.visit(node.left); left_val = self.last_value
        self.env.type_check_compatibility("bool", left_val, node.left.start_position, "Logical AND left operand: ")
        if not left_val.is_true(): self.last_value = BoolValue(False)
        else:
            self.visit(node.right); right_val = self.last_value
            self.env.type_check_compatibility("bool", right_val, node.right.start_position, "Logical AND right operand: ")
            self.last_value = BoolValue(right_val.is_true())

    def visit_LogicalOrNode(self, node: LogicalOrNode):
        self.visit(node.left); left_val = self.last_value
        self.env.type_check_compatibility("bool", left_val, node.left.start_position, "Logical OR left operand: ")
        if left_val.is_true(): self.last_value = BoolValue(True)
        else:
            self.visit(node.right); right_val = self.last_value
            self.env.type_check_compatibility("bool", right_val, node.right.start_position, "Logical OR right operand: ")
            self.last_value = BoolValue(right_val.is_true())

    def visit_UnaryMinusNode(self, node: UnaryMinusNode):
        self.visit(node.operand); val = self.last_value
        if isinstance(val, IntValue): self.last_value = IntValue(-val.value)
        elif isinstance(val, FloatValue): self.last_value = FloatValue(-val.value)
        else: self._error(f"Unary minus cannot be applied to type {val.get_type_str()}.", node)

    def visit_FunctionCallNode(self, node: FunctionCallNode):
        args_values: List[Value] = [self.visit(arg_node) or self.last_value for arg_node in node.arguments]

        callable_target: Any = None
        obj_context: Optional[Value] = None

        if isinstance(node.function_name, IdentifierNode): # Regular function: my_func()
            func_name_str = node.function_name.name
            callable_target = self.env.lookup_function(func_name_str, node.function_name.start_position)
        elif isinstance(node.function_name, MemberAccessNode): # Method call: obj.method()
            # node.function_name is the MemberAccessNode (e.g., `my_folder.list_files`)
            # This MemberAccessNode is NOT visited to get a value; it identifies the target.
            member_access_node = node.function_name
            self.visit(member_access_node.object_expr) # Evaluate the object part: `my_folder`
            obj_context = self.last_value # This is the FolderValue, FileValue, etc.
            method_name = member_access_node.member_name
            
            if not hasattr(obj_context, 'call_method'):
                 self._error(f"Type '{obj_context.get_type_str()}' does not support method calls.", member_access_node.object_expr)
            
            # We don't get callable_target yet; obj_context.call_method will resolve it
            # For now, set callable_target to a placeholder or the method name string
            callable_target = method_name # Method name to be dispatched by obj_context.call_method

        else: # Should not happen with the current grammar
            self._error(f"Cannot call expression of type {type(node.function_name).__name__}.", node.function_name)

        # --- Actual Call Dispatch ---
        if isinstance(callable_target, BuiltInFunction):
            self.last_value = callable_target.call(args_values, node.start_position)
        
        elif isinstance(callable_target, FunctionDefinitionNode): # User-defined function
            user_func_node = callable_target
            if len(args_values) != len(user_func_node.parameters):
                self._error(f"Function '{user_func_node.identifier_name}' expected {len(user_func_node.parameters)} arguments, got {len(args_values)}.", node)

            self.env.push_call_context(user_func_node.identifier_name, node.start_position)
            for param_node, arg_val in zip(user_func_node.parameters, args_values):
                param_type_str = self.env.get_type_str_from_ast_type(param_node.param_type, param_node.start_position)
                self.env.type_check_compatibility(param_type_str, arg_val, node.start_position, # TODO: Use arg_node position
                                                  f"Argument for param '{param_node.param_name}': ")
                self.env.declare_variable(param_node.param_name, arg_val, param_node.start_position)

            self.visit(user_func_node.body) # Execute

            expected_return_type_str = self.env.get_type_str_from_ast_type(user_func_node.return_type, user_func_node.return_type.start_position)
            
            if not self.env.return_pending and expected_return_type_str != "void":
                self._error(f"Function '{user_func_node.identifier_name}' must return a '{expected_return_type_str}'.", user_func_node.body.end_position)
            
            actual_returned_value = self.env.return_value if self.env.return_pending else NullValue()
            
            self.env.type_check_compatibility(expected_return_type_str, actual_returned_value, node.start_position, # TODO: Return stmt pos
                                              f"Return value of '{user_func_node.identifier_name}': ")
            
            self.last_value = actual_returned_value
            self.env.return_pending = False
            self.env.return_value = NullValue() # Reset for next call
            self.env.pop_call_context()

        elif obj_context is not None and isinstance(callable_target, str): # Method call (callable_target is method_name)
            method_name = callable_target
            self.last_value = obj_context.call_method(method_name, args_values, node.start_position)
            
        else:
            self._error(f"Internal: Cannot execute call for target '{str(callable_target)}'.", node)


    def visit_MemberAccessNode(self, node: MemberAccessNode):
        # This is for `obj.attribute` access (not method call `obj.method()`)
        self.visit(node.object_expr)
        obj_val = self.last_value
        member_name = node.member_name

        if not hasattr(obj_val, 'get_attribute'):
            self._error(f"Type '{obj_val.get_type_str()}' does not support attribute access.", node.object_expr)
        
        self.last_value = obj_val.get_attribute(member_name, node.start_position)


    # Default for unhandled AST nodes
    def visit(self, node: Any, *args, **kwargs):
        if node is None: # Should ideally not happen if AST is well-formed
            self._error(f"Interpreter encountered an unexpected None node during visitation.", Position(0,0)) # Generic position
            return NullValue() # Or some other safe default
        
        method_name = 'visit_' + type(node).__name__
        visitor_method = getattr(self, method_name, None)
        if visitor_method:
            return visitor_method(node, *args, **kwargs)
        else:
            # Fallback for nodes that don't produce value or aren't directly visited for execution
            # (like TypeNode, ParameterNode). If they are visited, it's likely an error in traversal.
            if isinstance(node, (TypeNode, ListTypeNode, ParameterNode)):
                 # These are structural, not executable in the typical sense.
                 # Their information is used by other visitors (e.g., VarDecl, FuncDef).
                 # Visiting them directly means something is off.
                 print(f"Warning: Direct visitation of structural node {type(node).__name__} occurred. This is unusual.")
                 return None 
            else:
                 self._error(f"Interpreter has no visitor method for AST node type: {type(node).__name__}", node if isinstance(node, ParserNode) else None)