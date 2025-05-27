# source/interpreter/runtime_values.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Callable, TYPE_CHECKING
from source.utils import Position, RuntimeException

if TYPE_CHECKING:
    from source.interpreter.environment import Environment


class Value:
    def __init__(self, type_name: str):
        self.type_name: str = type_name

    def get_type_str(self) -> str:
        return self.type_name

    def is_true(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"<{self.type_name} Value>"
    
    def get_attribute(self, name: str, pos: Position) -> Value:
        raise RuntimeException(f"Type '{self.get_type_str()}' has no attribute '{name}'.", pos)
    
    def call_method(self, method_name: str, args: List['Value'], pos: Position, env: Environment) -> Value:
        try:
            attr = self.get_attribute(method_name, pos)
            raise RuntimeException(f"Property '{method_name}' of type '{self.get_type_str()}' is not callable.", pos)
        except RuntimeException as e:
            if "is not callable" in str(e):
                raise
            pass

        raise RuntimeException(f"Type '{self.get_type_str()}' has no method '{method_name}'.", pos)
    
    def is_null(self) -> bool:
        return False

# --- Simple Values ---
class IntValue(Value):
    def __init__(self, value: int):
        super().__init__("int")
        self.value: int = value
    def __repr__(self) -> str: return f"IntValue({self.value})"

class FloatValue(Value):
    def __init__(self, value: float):
        super().__init__("float")
        self.value: float = value
    def __repr__(self) -> str: return f"FloatValue({self.value})"

class StringValue(Value):
    def __init__(self, value: str):
        super().__init__("string")
        self.value: str = value
    def __repr__(self) -> str: return f"StringValue('{self.value}')"

class BoolValue(Value):
    def __init__(self, value: bool):
        super().__init__("bool")
        self.value: bool = value
    def is_true(self) -> bool: return self.value
    def __repr__(self) -> str: return f"BoolValue({self.value})"

class NullValue(Value):
    def __init__(self):
        super().__init__("null")
        self.value: None = None
    def is_true(self) -> bool: return False
    def __repr__(self) -> str: return "NullValue()"

# --- Composite Values ---
class ListValue(Value):
    def __init__(self, element_type_str: str, elements: List[Value]):
        super().__init__(f"List<{element_type_str}>")
        self.element_type_str: str = element_type_str
        self.elements: List[Value] = elements

    def call_method(self, name: str, args: List[Value], pos: Position, env: Environment) -> Value:
        if name == "get":
            if len(args) != 1 or not isinstance(args[0], IntValue):
                raise RuntimeException(f"List.get() expects 1 integer argument.", pos)
            idx = args[0].value
            if 0 <= idx < len(self.elements):
                return self.elements[idx]
            else:
                raise RuntimeException(f"List index {idx} out of bounds for list of size {len(self.elements)}.", pos)
            
        elif name == "len":
            return IntValue(len(self.elements))
        # Add other list methods if specified: append, remove, etc.
        raise RuntimeException(f"List has no method '{name}'.", pos)
    def __repr__(self) -> str: return f"ListValue[{self.element_type_str}]({[repr(e) for e in self.elements]})"


@dataclass
class FunctionSignature:
    name: str
    param_types: List[str] 
    return_type: str

class BuiltInFunction(Value):
    def __init__(self, name: str, signature: FunctionSignature, python_callable: Callable, needs_env: bool = False):
        super().__init__("builtin_function")
        self.name = name
        self.signature = signature
        self.python_callable = python_callable
        self.needs_env = needs_env

    def __repr__(self) -> str: return f"<BuiltInFunction {self.name}>"

    def call(self, args: List[Value], call_node_pos: Position, env: Environment) -> Value:

        # 1. Check argument count
        if len(args) != len(self.signature.param_types):
            raise RuntimeException(
                f"Function '{self.name}' expected {len(self.signature.param_types)} arguments, got {len(args)}.",
                call_node_pos
            )
        
        # 2. Check arg types and prepare for Python call
        processed_args = []
        for i, (arg_val, expected_type_str) in enumerate(zip(args, self.signature.param_types)):
            actual_type_str = arg_val.get_type_str()
            
            # Allow Audio to be passed where File is expected TODO: Think about this
            compatible = False
            if actual_type_str == expected_type_str:
                compatible = True

            if not compatible:
                raise RuntimeException(
                    f"Argument {i+1} for function '{self.name}': expected type '{expected_type_str}', got '{actual_type_str}'.",
                    call_node_pos
                )
            processed_args.append(arg_val)

        # 3. Call Python function
        final_args_for_callable = []
        if self.needs_env:
            final_args_for_callable.append(env)
        final_args_for_callable.extend(processed_args)

        try:
            result_val = self.python_callable(*final_args_for_callable)
        except RuntimeException as e:
            if e.position is None: e.position = call_node_pos
            raise e
        except ValueError as e:
            raise RuntimeException(f"Type conversion exception in '{self.name}': {e}", call_node_pos)
        except Exception as e:
            raise RuntimeException(f"Internal error during execution of built-in function '{self.name}': {type(e).__name__} {e}", call_node_pos)

        # 4. Check return type
        if not isinstance(result_val, Value):
            raise RuntimeException(f"Internal error: Built-in function '{self.name}' did not return a Value object (got {type(result_val)}).", call_node_pos)

        expected_return_type = self.signature.return_type
        actual_return_type = result_val.get_type_str()
        
        return_compatible = False
        if expected_return_type == "void":
            if isinstance(result_val, NullValue):
                return_compatible = True
        elif actual_return_type == expected_return_type:
            return_compatible = True

        if not return_compatible:
            raise RuntimeException(
                f"Built-in function '{self.name}' returned type '{actual_return_type}', but expected '{expected_return_type}'.",
                call_node_pos
            )
        return result_val


# --- File System Object Values ---
class FileValue(Value):
    def __init__(self, filename: str, parent: Optional[FolderValue] = None):
        super().__init__("File")
        self.filename: str = filename
        self.parent: Optional[FolderValue] = parent
        self._is_deleted: bool = False

    def get_attribute(self, name: str, pos: Position) -> Value:
        if name == "filename": return StringValue(self.filename)
        return super().get_attribute(name, pos)

    def _check_deleted(self, operation_name: str, pos: Position):
        if self._is_deleted:
            raise RuntimeException(f"Operation '{operation_name}' on deleted file '{self.filename}' is not allowed.", pos)

    def call_method(self, name: str, args: List[Value], pos: Position, env: Environment) -> Value:
        if name == "get_filename":
            if args: raise RuntimeException("File.get_filename() takes no arguments.", pos)
            return StringValue(self.filename)
        if name == "change_filename":
            self._check_deleted("change_filename", pos)
            if len(args) != 1 or not isinstance(args[0], StringValue):
                raise RuntimeException("File.change_filename() expects 1 string argument.", pos)
            old_name = self.filename
            self.filename = args[0].value
            return NullValue()
        if name == "move":
            self._check_deleted("move", pos)
            if len(args) != 1 or not isinstance(args[0], FolderValue):
                raise RuntimeException("File.move() expects 1 FolderValue argument.", pos)
            new_parent_folder = args[0]
            if new_parent_folder._is_deleted:
                 raise RuntimeException(f"Cannot move file to a deleted folder '{new_parent_folder.path_name}'.", pos)

            if self.parent: 
                self.parent._internal_remove_file(self)
            
            self.parent = new_parent_folder
            new_parent_folder._internal_add_file(self)
            return NullValue()
        if name == "delete":
            if self._is_deleted: return NullValue()

            if self.parent: 
                self.parent._internal_remove_file(self)
                self.parent = None
            self._is_deleted = True
            return NullValue()
        return super().call_method(name, args, pos, env)
    def __repr__(self) -> str: return f"FileValue('{self.filename}')"


class FolderValue(Value):
    def __init__(self, path: str, is_root: bool = False):
        super().__init__("Folder")
        self.path_name: str = path
        self._files: List[FileValue] = []
        self._subfolders: List[FolderValue] = []
        self.is_root: bool = is_root
        self._is_deleted: bool = False

    def _internal_add_file(self, file_val: FileValue):
        if file_val not in self._files: 
            self._files.append(file_val)
            file_val.parent = self
            file_val._is_deleted = False

    def _internal_remove_file(self, file_val: FileValue):
        if file_val in self._files: 
            self._files.remove(file_val)
            file_val.parent = None

    def get_attribute(self, name: str, pos: Position) -> Value:
        if name == "is_root": return BoolValue(self.is_root)
        return super().get_attribute(name, pos)

    def _check_deleted(self, operation_name: str, pos: Position):
        if self._is_deleted:
            raise RuntimeException(f"Operation '{operation_name}' on deleted folder '{self.path_name}' is not allowed.", pos)

    def call_method(self, name: str, args: List[Value], pos: Position, env: Environment) -> Value:
        self._check_deleted(name, pos)

        if name == "get_file":
            if len(args) != 1 or not isinstance(args[0], StringValue):
                raise RuntimeException("Folder.get_file() expects 1 string argument.", pos)
            fname_to_find = args[0].value
            for f_obj in self._files:
                if f_obj.filename == fname_to_find and not f_obj._is_deleted: 
                    return f_obj
            return NullValue()
        
        if name == "add_file":
            if len(args) != 1 or not isinstance(args[0], FileValue): # Accepts File or Audio TODO: Think about this
                raise RuntimeException("Folder.add_file() expects 1 File argument.", pos)
            
            file_to_add = args[0]
            if file_to_add._is_deleted:
                raise RuntimeException(f"Cannot add a deleted file '{file_to_add.filename}' to folder.", pos)

            if file_to_add.parent and file_to_add.parent != self:
                file_to_add.parent._internal_remove_file(file_to_add)
            
            self._internal_add_file(file_to_add)
            return NullValue()
        
        if name == "list_audio":
            if args: raise RuntimeException("Folder.list_audio() takes no arguments.", pos)
            audio_files = [f for f in self._files if isinstance(f, AudioValue) and not f._is_deleted]
            return ListValue("Audio", audio_files)
        
        if name == "list_files":
            if args: raise RuntimeException("Folder.list_files() takes no arguments.", pos)
            active_files = [f for f in self._files if not f._is_deleted]
            return ListValue("File", active_files)

        return super().call_method(name, args, pos, env)
    def __repr__(self) -> str: return f"FolderValue('{self.path_name}')"


class AudioValue(FileValue):
    def __init__(self, filename: str, parent: Optional[FolderValue] = None,
                 length: int = 0, bitrate: int = 0, title: Optional[str] = None):
        super().__init__(filename, parent)
        self.type_name = "Audio"
        self.length_ms: int = length
        self.bitrate_kbps: int = bitrate
        # If title is None, derive from filename (e.g., "song" from "song.mp3")
        if title is None:
            self.title = filename.split('.')[0] if '.' in filename else filename
        else:
            self.title = title

    def get_attribute(self, name: str, pos: 'Position') -> Value:
        if name == "length": return IntValue(self.length_ms)
        if name == "bitrate": return IntValue(self.bitrate_kbps)
        if name == "title": return StringValue(self.title)
        return super().get_attribute(name, pos) # Delegate to FileValue for "filename"

    def call_method(self, name: str, args: List[Value], pos: 'Position', env: 'Environment') -> Value:
        self._check_deleted(name, pos)

        if name == "change_title":
            if len(args) != 1 or not isinstance(args[0], StringValue):
                raise RuntimeException("Audio.change_title() expects 1 string argument.", pos)
            self.title = args[0].value
            return NullValue()
        # Add other Audio methods : cut, concat, change_format, change_volume
        return super().call_method(name, args, pos, env) # Delegate to FileValue methods
    def __repr__(self) -> str: return f"AudioValue('{self.filename}', title='{self.title}')"