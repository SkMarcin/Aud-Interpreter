from dataclasses import dataclass
from typing import Dict, List, Optional
from source.utils import Position, TypeMismatchException

@dataclass(frozen=True)
class TypeSignature:
    base_type: str
    child_type: Optional['TypeSignature'] = None

    def to_string(self) -> str:
        if self.base_type == "List" and self.child_type:
            return f"List<{self.child_type.to_string()}>"
        return self.base_type

    def is_compatible_with(self, other: 'TypeSignature') -> bool:
        if self.base_type == other.base_type:
            if self.base_type == "List":
                return self.child_type.is_compatible_with(other.child_type)
            return True

        if self.base_type == "void" and other.base_type == "null":
            return True
        if self.base_type == "File" and other.base_type == "Audio":
            return True
        if other.base_type == "null" and self.base_type != "void":
            return self.base_type in ["File", "Folder", "Audio", "List", "string"]

        return False

@dataclass(frozen=True)
class FunctionTypeSignature:
    param_types: List[TypeSignature]
    return_type: TypeSignature

class SymbolTable:
    def __init__(self, parent: Optional['SymbolTable'] = None):
        self.variables: Dict[str, TypeSignature] = {} # variable name -> TypeSignature
        self.parent: Optional['SymbolTable'] = parent

    def declare_variable(self, name: str, type_sig: TypeSignature, pos: Position):
        if name in self.variables:
            raise TypeMismatchException(pos, f"Variable '{name}' already declared in this scope.")
        self.variables[name] = type_sig

    def get_variable_type(self, name: str) -> Optional[TypeSignature]:
        if name in self.variables:
            return self.variables[name]
        elif self.parent:
            return self.parent.get_variable_type(name)
        return None

    def __repr__(self):
        return f"SymbolTable(vars={list(self.variables.keys())}, parent={'Yes' if self.parent else 'No'})"

class GlobalSymbolTable(SymbolTable):
    def __init__(self):
        super().__init__()
        self.functions: Dict[str, FunctionTypeSignature] = {} # function name -> FunctionTypeSignature

        self.builtin_simple_types: Dict[str, TypeSignature] = {
            "int": TypeSignature("int"),
            "float": TypeSignature("float"),
            "bool": TypeSignature("bool"),
            "string": TypeSignature("string"),
            "void": TypeSignature("void"),
            "null": TypeSignature("null"),
            "File": TypeSignature("File"),
            "Folder": TypeSignature("Folder"),
            "Audio": TypeSignature("Audio"),
        }

    def register_function(self, name: str, func_sig: FunctionTypeSignature, pos: Position):
        if name in self.functions:
            raise TypeMismatchException(pos, f"Function '{name}' already defined.")
        self.functions[name] = func_sig

    def get_function_signature(self, name: str) -> Optional[FunctionTypeSignature]:
        return self.functions.get(name)

    def get_type_signature(self, type_name: str, child_type_sig: Optional[TypeSignature] = None) -> TypeSignature:
        if type_name == "List":
            return TypeSignature("List", child_type_sig)

        sig = self.builtin_simple_types.get(type_name)
        return sig
