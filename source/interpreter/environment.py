# source/interpreter/environment.py
from __future__ import annotations
from typing import Dict, List, Optional, Any, Callable
from source.nodes import FunctionDefinitionNode, Position
from source.utils import RuntimeException, Config
from source.type_checker.symbol_table import TypeSignature, FunctionTypeSignature
from source.interpreter.runtime_values import Value, NullValue, BuiltInFunction, \
    IntValue, FloatValue, StringValue, BoolValue, ListValue, FileValue, FolderValue, AudioValue

MAX_FUNC_DEPTH = 50

class Scope:
    def __init__(self, parent_scope: Optional[Scope] = None):
        self.variables: Dict[str, Value] = {}
        self.parent: Optional[Scope] = parent_scope

    def declare(self, name: str, value: Value, pos: Position):
        if name in self.variables:
            raise RuntimeException(f"Variable '{name}' already declared in this scope.", pos)
        self.variables[name] = value

    def assign(self, name: str, value_to_assign: Value, pos: Position) -> bool:
        scope_to_update = self._find_scope_for_update(name)
        if not scope_to_update:
            return False

        target_var_obj = scope_to_update.variables[name]

        if isinstance(target_var_obj, (IntValue, FloatValue, StringValue, BoolValue)) and \
            type(target_var_obj) == type(value_to_assign):
                target_var_obj.value = value_to_assign.value
        else:
            # For complex types (File, Folder, List, Audio) assignment rebinds the name to new value
            scope_to_update.variables[name] = value_to_assign
        return True

    def get(self, name: str) -> Optional[Value]:
        if name in self.variables:
            return self.variables[name]
        elif self.parent:
            return self.parent.get(name)
        return None

    def _find_scope_for_update(self, name: str) -> Optional[Scope]:
        # Helper to find the scope where 'name' is defined
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
    def __init__(self, config: Optional[Config] = None,
                 input_retriever: Optional[Callable[[], Optional[str]]] = None):
        self.config = config if config else Config()
        self.max_func_depth = self.config.max_func_depth

        self.call_stack: List[CallContext] = [CallContext("<module>")] # Global context
        self.user_functions: Dict[str, FunctionDefinitionNode] = {}
        self.built_in_functions: Dict[str, BuiltInFunction] = {}

        self.input_retriever = input_retriever # For mock input
        self._init_built_in_functions()

        self.return_pending: bool = False
        self.return_value: Value = NullValue()

    def _init_built_in_functions(self):
        # print(string text) -> void
        def builtin_print(text: StringValue) -> NullValue:
            print(text.value)
            return NullValue()
        self.built_in_functions["print"] = BuiltInFunction("print", FunctionTypeSignature([TypeSignature("string")], TypeSignature("void")), builtin_print)

        # string input() -> string
        def builtin_input(env: Environment) -> StringValue:
            if env.input_retriever:
                line = env.input_retriever()
                if line is not None: return StringValue(line)
                else: raise RuntimeException("Attempted to read past end of mock input.")
            else: # Fallback to real input
                try: return StringValue(input())
                except EOFError: raise RuntimeException("EOF encountered while reading input.")
        self.built_in_functions["input"] = BuiltInFunction("input", FunctionTypeSignature([], TypeSignature("string")), builtin_input, needs_env=True)

        # int stoi(string text) -> int
        def builtin_stoi(text: StringValue) -> IntValue:
            try: return IntValue(int(text.value))
            except ValueError: raise RuntimeException(f"Cannot convert string '{text.value}' to int.")
        self.built_in_functions["stoi"] = BuiltInFunction("stoi", FunctionTypeSignature([TypeSignature("string")], TypeSignature("int")), builtin_stoi)

        # string itos(int number) -> string
        def builtin_itos(num: IntValue) -> StringValue: return StringValue(str(num.value))
        self.built_in_functions["itos"] = BuiltInFunction("itos", FunctionTypeSignature([TypeSignature("int")], TypeSignature("string")), builtin_itos)

        # float stof(string text) -> float
        def builtin_stof(text: StringValue) -> FloatValue:
            try: return FloatValue(float(text.value))
            except ValueError: raise RuntimeException(f"Cannot convert string '{text.value}' to float.")
        self.built_in_functions["stof"] = BuiltInFunction("stof", FunctionTypeSignature([TypeSignature("string")], TypeSignature("float")), builtin_stof)

        # string ftos(float number) -> string
        def builtin_ftos(num: FloatValue) -> StringValue:
            s = str(num.value)
            if '.' not in s: s += '.0'
            return StringValue(s)
        self.built_in_functions["ftos"] = BuiltInFunction("ftos", FunctionTypeSignature([TypeSignature("float")], TypeSignature("string")), builtin_ftos)

        # float itof(int number) -> float
        def builtin_itof(num: IntValue) -> FloatValue:
            return FloatValue(float(num.value))
        self.built_in_functions["itof"] = BuiltInFunction("itof", FunctionTypeSignature([TypeSignature("int")], TypeSignature("float")), builtin_itof)

        # File atof(Audio file) -> File
        def builtin_atof(audio_file: AudioValue, pos: Position) -> FileValue:
            return FileValue(audio_file._fs_path, pos, parent_folder_obj=audio_file.parent)
        self.built_in_functions["atof"] = BuiltInFunction("atof", FunctionTypeSignature([TypeSignature("Audio")], TypeSignature("File")), builtin_atof, needs_pos=True)

        # int ftoi(float number) -> int
        def builtin_ftoi(num: FloatValue) -> IntValue:
            return IntValue(int(num.value))
        self.built_in_functions["ftoi"] = BuiltInFunction("ftoi", FunctionTypeSignature([TypeSignature("float")], TypeSignature("int")), builtin_ftoi)

        # string btos(bool val) -> string
        def builtin_btos(val: BoolValue) -> StringValue:
            return StringValue("true" if val.value else "false")
        self.built_in_functions["btos"] = BuiltInFunction("btos", FunctionTypeSignature([TypeSignature("bool")], TypeSignature("string")), builtin_btos)

        # Audio ftoa(File file) -> Audio
        def builtin_ftoa(file_val: FileValue, pos: Position) -> Value:
            import os
            file_val._check_deleted("ftoa", pos)
            if not os.path.exists(file_val._fs_path) or not os.path.isfile(file_val._fs_path):
                return NullValue()
            try:
                return AudioValue(file_val._fs_path, pos, parent_folder_obj=file_val.parent)
            except RuntimeException:
                return NullValue()
        self.built_in_functions["ftoa"] = BuiltInFunction("ftoa", FunctionTypeSignature([TypeSignature("File")], TypeSignature("Audio")), builtin_ftoa, needs_pos=True)


    def current_context(self) -> CallContext: return self.call_stack[-1]
    def global_context(self) -> CallContext: return self.call_stack[0]

    def push_call_context(self, func_name: str, pos: Position):
        if len(self.call_stack) >= self.max_func_depth:
            raise RuntimeException(f"Maximum function call depth ({self.max_func_depth}) exceeded.", pos)
        self.call_stack.append(CallContext(func_name))

    def pop_call_context(self):
        if len(self.call_stack) > 1: self.call_stack.pop()
        else: raise SystemError("Attempted to pop global call context.")

    def declare_variable(self, name: str, value: Value, pos: Position):
        self.current_context().declare_variable(name, value, pos)

    def assign_variable(self, name: str, value: Value, pos: Position):
        if not self.current_context().assign_variable(name, value, pos):
            raise RuntimeException(f"Undeclared variable '{name}' referenced.", pos)

    def get_variable(self, name: str, pos: Position) -> Value:
        val = self.current_context().get_variable(name)
        if val is None:
            raise RuntimeException(f"Undeclared variable '{name}' referenced.", pos)
        return val

    def register_function(self, name: str, node: FunctionDefinitionNode):
        if name in self.user_functions or name in self.built_in_functions:
            raise RuntimeException(f"Function '{name}' already defined.", node.start_position)
        self.user_functions[name] = node

    def lookup_function(self, name: str, pos: Position) -> Any: # FunctionDefinitionNode or BuiltInFunction
        if name in self.built_in_functions: return self.built_in_functions[name]
        if name in self.user_functions: return self.user_functions[name]
        raise RuntimeException(f"Undefined function '{name}' called.", pos)

    # def get_type_str_from_ast_type(self, type_node: TypeNode, pos: Position) -> str:
    #     if isinstance(type_node, ListTypeNode):
    #         child_type_str = self.get_type_str_from_ast_type(type_node.child_type_node, pos)
    #         return f"List<{child_type_str}>"
    #     elif isinstance(type_node, TypeNode):
    #         return type_node.type_name

    # def type_check_compatibility(self, expected_type_str: str, actual_value: Value, error_pos: Position, error_msg_prefix: str = ""):
    #     actual_type_str = actual_value.get_type_str()
    #     compatible = False
    #     if expected_type_str == actual_type_str:
    #         compatible = True
    #     if expected_type_str == "void" and actual_type_str == "null":
    #         compatible = True
    #     if expected_type_str == "File" and actual_type_str == "Audio":
    #         compatible = True

    #     if not compatible:
    #         full_error_msg = f"{error_msg_prefix}Type mismatch. Expected '{expected_type_str}', got '{actual_type_str}'."
    #         raise RuntimeException(full_error_msg, error_pos)