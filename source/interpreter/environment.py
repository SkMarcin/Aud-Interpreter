# source/interpreter/environment.py
from __future__ import annotations
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from source.nodes import FunctionDefinitionNode, Position, TypeNode, ListTypeNode
from source.utils import RuntimeError
from source.interpreter.runtime_values import Value, NullValue, BuiltInFunction, FunctionSignature, \
    IntValue, FloatValue, StringValue, BoolValue, ListValue, FileValue, FolderValue, AudioValue

MAX_FUNC_DEPTH = 50

class Scope:
    def __init__(self, parent_scope: Optional[Scope] = None):
        self.variables: Dict[str, Value] = {}
        self.parent: Optional[Scope] = parent_scope

    def declare(self, name: str, value: Value, pos: Position):
        if name in self.variables:
            raise RuntimeError(f"Variable '{name}' already declared in this scope.", pos)
        self.variables[name] = value

    def assign(self, name: str, value_to_assign: Value, pos: Position) -> bool:
        target_var_obj = self.get(name)

        if target_var_obj:
            # Type compatibility check (crucial)
            existing_type_str = target_var_obj.get_type_str()
            new_type_str = value_to_assign.get_type_str()
            if existing_type_str != new_type_str:
                raise RuntimeError(f"Type mismatch: Cannot assign {new_type_str} to {existing_type_str} variable '{name}'.", pos)

            if isinstance(target_var_obj, (IntValue, FloatValue, StringValue, BoolValue)):
                # For primitive types, modify the internal .value
                # Ensure value_to_assign is also of a compatible primitive type
                if type(target_var_obj) == type(value_to_assign):
                    target_var_obj.value = value_to_assign.value
                # TODO: Handle int-to-float coercion on assignment if target is FloatValue and source is IntValue
                # elif isinstance(target_var_obj, FloatValue) and isinstance(value_to_assign, IntValue):
                #    target_var_obj.value = float(value_to_assign.value)
                else:
                    raise RuntimeError(f"Type mismatch assigning to primitive '{name}'. Expected {target_var_obj.get_type_str()}, got {value_to_assign.get_type_str()}.", pos)
            else:
                # For complex types (File, Folder, List, Audio), assignment rebinds the name in the *innermost* scope where 'name' was found
                # This requires finding which scope 'name' is in and updating self.variables[name] there.
                # The current Scope.assign searches parents. The assignment should happen in the scope where `name` is defined.
                
                # Simplified: assign by rebinding in the current scope if found, else parent
                # This logic needs to be precise for correct shadowing and updates.
                # The most straightforward for complex types is to rebind in the scope where `name` is found.
                # Let `_find_scope_for_assign` help here.
                scope_to_update = self._find_scope_for_update(name)
                if scope_to_update:
                    scope_to_update.variables[name] = value_to_assign
                else:
                    return False 
            return True
            
        return False # Variable not found in this scope or its parents

    def get(self, name: str) -> Optional[Value]:
        if name in self.variables:
            return self.variables[name]
        elif self.parent:
            return self.parent.get(name)
        return None

    def _find_scope_for_update(self, name: str) -> Optional[Scope]:
        # Helper to find the exact scope where 'name' is defined for updating complex type references
        if name in self.variables:
            return self
        elif self.parent:
            return self.parent._find_scope_for_update(name)
        return None


class CallContext:
    def __init__(self, name: str = "<global_context>"):
        self.name = name
        self.scopes: List[Scope] = [Scope()]

    def current_scope(self) -> Scope: return self.scopes[-1]
    def enter_scope(self): self.scopes.append(Scope(parent_scope=self.current_scope()))
    def exit_scope(self):
        if len(self.scopes) > 1: self.scopes.pop()
        else: raise SystemError("Cannot exit base scope of a call context.")

    def declare_variable(self, name: str, value: Value, pos: Position):
        self.current_scope().declare(name, value, pos)

    def assign_variable(self, name: str, value: Value, pos: Position) -> bool:
        return self.current_scope().assign(name, value, pos)

    def get_variable(self, name: str) -> Optional[Value]:
        return self.current_scope().get(name)


class Environment:
    def __init__(self):
        self.call_stack: List[CallContext] = [CallContext()]
        self.user_functions: Dict[str, FunctionDefinitionNode] = {}
        self.built_in_functions: Dict[str, BuiltInFunction] = {}
        self._init_built_in_functions()

        self.return_pending: bool = False
        self.return_value: Value = NullValue()

    def _init_built_in_functions(self):
        # print(string text) -> void
        def builtin_print(text: StringValue) -> NullValue:
            print(text.value)
            return NullValue()
        self.built_in_functions["print"] = BuiltInFunction("print", FunctionSignature("print", ["string"], "void"), builtin_print)

        # string input() -> string
        def builtin_input() -> StringValue: return StringValue(input())
        self.built_in_functions["input"] = BuiltInFunction("input", FunctionSignature("input", [], "string"), builtin_input)
        
        # int stoi(string text) -> int
        def builtin_stoi(text: StringValue) -> IntValue:
            try: return IntValue(int(text.value))
            except ValueError: raise RuntimeError(f"Cannot convert string '{text.value}' to int.")
        self.built_in_functions["stoi"] = BuiltInFunction("stoi", FunctionSignature("stoi", ["string"], "int"), builtin_stoi)

        # string itos(int number) -> string
        def builtin_itos(num: IntValue) -> StringValue: return StringValue(str(num.value))
        self.built_in_functions["itos"] = BuiltInFunction("itos", FunctionSignature("itos", ["int"], "string"), builtin_itos)

        # ... (stof, ftos, itof, ftoi as in thought process) ...

        # File atof(Audio file) -> File
        def builtin_atof(audio_file: AudioValue) -> FileValue:
            return FileValue(audio_file.filename, audio_file.parent)
        self.built_in_functions["atof"] = BuiltInFunction("atof", FunctionSignature("atof", ["Audio"], "File"), builtin_atof)
        
        # Audio ftoa(File file) -> Audio (Assuming typo correction)
        def builtin_ftoa(file_val: FileValue) -> AudioValue:
            if isinstance(file_val, AudioValue): return file_val
            print(f"[SIM] Converting File '{file_val.filename}' to Audio.")
            return AudioValue(file_val.filename, file_val.parent, title=file_val.filename)
        self.built_in_functions["ftoa"] = BuiltInFunction("ftoa", FunctionSignature("ftoa", ["File"], "Audio"), builtin_ftoa)


    def current_context(self) -> CallContext: return self.call_stack[-1]
    def global_context(self) -> CallContext: return self.call_stack[0]

    def push_call_context(self, func_name: str, pos: Position):
        if len(self.call_stack) >= MAX_FUNC_DEPTH:
            raise RuntimeError(f"Maximum function call depth ({MAX_FUNC_DEPTH}) exceeded.", pos)
        self.call_stack.append(CallContext(func_name))

    def pop_call_context(self):
        if len(self.call_stack) > 1: self.call_stack.pop()
        else: raise SystemError("Attempted to pop global call context.")

    def declare_variable(self, name: str, value: Value, pos: Position):
        self.current_context().declare_variable(name, value, pos)

    def assign_variable(self, name: str, value: Value, pos: Position):
        # Try current context's scope chain
        if self.current_context().assign_variable(name, value, pos):
            return
        # If not in current context, try global (if current is not already global)
        if self.current_context() is not self.global_context():
            if self.global_context().assign_variable(name, value, pos):
                return
        raise RuntimeError(f"Undeclared variable '{name}' used in assignment.", pos)

    def get_variable(self, name: str, pos: Position) -> Value:
        val = self.current_context().get_variable(name)
        if val is not None: return val
        if self.current_context() is not self.global_context():
            val = self.global_context().get_variable(name)
            if val is not None: return val
        raise RuntimeError(f"Undeclared variable '{name}' referenced.", pos)

    def register_function(self, name: str, node: FunctionDefinitionNode):
        if name in self.user_functions or name in self.built_in_functions:
            raise RuntimeError(f"Function '{name}' already defined.", node.start_position)
        self.user_functions[name] = node

    def lookup_function(self, name: str, pos: Position) -> Any: # FunctionDefinitionNode or BuiltInFunction
        if name in self.built_in_functions: return self.built_in_functions[name]
        if name in self.user_functions: return self.user_functions[name]
        raise RuntimeError(f"Undefined function '{name}' called.", pos)

    def get_type_str_from_ast_type(self, type_node: TypeNode, pos: Position) -> str:
        if isinstance(type_node, ListTypeNode):
            child_type_str = self.get_type_str_from_ast_type(type_node.child_type_node, pos)
            return f"List<{child_type_str}>"
        elif isinstance(type_node, TypeNode):
            return type_node.type_name
        raise RuntimeError(f"Unknown AST type node: {type_node}", pos) # Should not happen

    def type_check_compatibility(self, expected_type_str: str, actual_value: Value, error_pos: Position, error_msg_prefix: str = ""):
        actual_type_str = actual_value.get_type_str()
        compatible = False
        if expected_type_str == actual_type_str:
            compatible = True
        elif expected_type_str == "File" and isinstance(actual_value, AudioValue): # Audio is a File
            compatible = True
        if expected_type_str == "void" and actual_type_str == "null":
            compatible = True
        
        if not compatible:
            full_error_msg = f"{error_msg_prefix}Type mismatch. Expected '{expected_type_str}', got '{actual_type_str}'."
            raise RuntimeError(full_error_msg, error_pos)