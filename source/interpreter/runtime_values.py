# source/interpreter/runtime_values.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Callable
from source.utils import RuntimeError
from source.nodes import Position  # Forward declaration for type hints


class Value:
    def __init__(self, type_name: str):
        self.type_name: str = type_name

    def get_type_str(self) -> str:
        return self.type_name

    def is_true(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"<{self.type_name} Value>"

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
    def is_truthy(self) -> bool: return self.value
    def __repr__(self) -> str: return f"BoolValue({self.value})"

class NullValue(Value):
    def __init__(self):
        super().__init__("null")
        self.value: None = None
    def is_truthy(self) -> bool: return False
    def __repr__(self) -> str: return "NullValue()"

# --- Composite Values ---
class ListValue(Value):
    def __init__(self, element_type_str: str, elements: List[Value]):
        super().__init__(f"List<{element_type_str}>")
        self.element_type_str: str = element_type_str
        self.elements: List[Value] = elements

    def call_method(self, name: str, args: List[Value], pos: Position) -> Value:
        if name == "get":
            if len(args) != 1 or not isinstance(args[0], IntValue):
                raise RuntimeError(f"List.get() expects 1 integer argument.", pos)
            idx = args[0].value
            if 0 <= idx < len(self.elements):
                return self.elements[idx]
            else:
                raise RuntimeError(f"List index {idx} out of bounds for list of size {len(self.elements)}.", pos)
            
        elif name == "len":
            return IntValue(len(self.elements))
        # Add other list methods if specified: append, remove, etc.
        raise RuntimeError(f"List has no method '{name}'.", pos)
    def __repr__(self) -> str: return f"ListValue[{self.element_type_str}]({[repr(e) for e in self.elements]})"


@dataclass
class FunctionSignature:
    name: str
    param_types: List[str] 
    return_type: str

class BuiltInFunction(Value):
    def __init__(self, name: str, signature: FunctionSignature, python_callable: Callable):
        super().__init__("builtin_function")
        self.name = name
        self.signature = signature
        self.python_callable = python_callable

    def __repr__(self) -> str: return f"<BuiltInFunction {self.name}>"

    def call(self, args: List[Value], call_node_pos: Position) -> Value:
        # 1. Check argument count
        if len(args) != len(self.signature.param_types):
            raise RuntimeError(
                f"Function '{self.name}' expected {len(self.signature.param_types)} arguments, got {len(args)}.",
                call_node_pos
            )
        # 2. Check arg types
        processed_args = []
        for i, (arg_val, expected_type_str) in enumerate(zip(args, self.signature.param_types)):
            actual_type_str = arg_val.get_type_str()
            compatible = False
            if actual_type_str == expected_type_str:
                compatible = True

            if not compatible:
                raise RuntimeError(
                    f"Argument {i+1} for function '{self.name}': expected type '{expected_type_str}', got '{actual_type_str}'.",
                    call_node_pos
                )
            processed_args.append(arg_val)

        # 3. Call Python function
        try:
            result_val = self.python_callable(*processed_args)
        except RuntimeError as e:
            if e.position is None: e.position = call_node_pos
            raise e
        except Exception as e:
            raise RuntimeError(f"Error during execution of built-in function '{self.name}': {e}", call_node_pos)


        # 4. Check return type
        if not isinstance(result_val, Value):
            raise RuntimeError(f"Internal error: Built-in function '{self.name}' did not return a Value object.", call_node_pos)

        expected_return_type = self.signature.return_type
        actual_return_type = result_val.get_type_str()

        return_compatible = False
        if expected_return_type == "void" and isinstance(result_val, NullValue):
            return_compatible = True
        elif expected_return_type == actual_return_type:
            return_compatible = True

        if not return_compatible:
            raise RuntimeError(
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

    def get_attribute(self, name: str, pos: Position) -> Value:
        if name == "filename": return StringValue(self.filename)
        raise RuntimeError(f"File has no attribute '{name}'.", pos)

    def call_method(self, name: str, args: List[Value], pos: Position) -> Value:
        if name == "get_filename":
            if args: raise RuntimeError("File.get_filename() takes no arguments.", pos)
            return StringValue(self.filename)
        if name == "change_filename":
            if len(args) != 1 or not isinstance(args[0], StringValue):
                raise RuntimeError("File.change_filename() expects 1 string argument.", pos)
            self.filename = args[0].value
            print(f"[SIM] File '{self.filename}' (was some_old_name) name changed to '{args[0].value}'.")
            return NullValue()
        if name == "move":
            if len(args) != 1 or not isinstance(args[0], FolderValue):
                raise RuntimeError("File.move() expects 1 Folder argument.", pos)
            if self.parent: self.parent._internal_remove_file(self)
            self.parent = args[0]
            args[0]._internal_add_file(self)
            print(f"[SIM] File '{self.filename}' moved to folder '{args[0].path_name}'.")
            return NullValue()
        if name == "delete":
            if args: raise RuntimeError("File.delete() takes no arguments.", pos)
            if self.parent: self.parent._internal_remove_file(self)
            print(f"[SIM] File '{self.filename}' deleted.")
            return NullValue()
        raise RuntimeError(f"File has no method '{name}'.", pos)
    def __repr__(self) -> str: return f"FileValue('{self.filename}')"


class FolderValue(Value):
    def __init__(self, path: str, is_root: bool = False):
        super().__init__("Folder")
        self.path_name: str = path
        self._files: List[FileValue] = []
        self._subfolders: List[FolderValue] = []
        self.is_root: bool = is_root

    def _internal_add_file(self, file_val: FileValue):
        if file_val not in self._files: self._files.append(file_val)
    def _internal_remove_file(self, file_val: FileValue):
        if file_val in self._files: self._files.remove(file_val)
    def _internal_add_subfolder(self, folder_val: FolderValue):
        if folder_val not in self._subfolders: self._subfolders.append(folder_val)
    def _internal_remove_subfolder(self, folder_val: FolderValue):
        if folder_val in self._subfolders: self._subfolders.remove(folder_val)

    def get_attribute(self, name: str, pos: Position) -> Value:
        if name == "is_root": return BoolValue(self.is_root)
        raise RuntimeError(f"Folder has no attribute '{name}'.", pos)

    def call_method(self, name: str, args: List[Value], pos: Position) -> Value:
        if name == "get_file":
            if len(args) != 1 or not isinstance(args[0], StringValue):
                raise RuntimeError("Folder.get_file() expects 1 string argument.", pos)
            fname_to_find = args[0].value
            for f_obj in self._files:
                if f_obj.filename == fname_to_find: return f_obj
            return NullValue()
        if name == "add_file":
            if len(args) != 1 or not isinstance(args[0], FileValue):
                raise RuntimeError("Folder.add_file() expects 1 File argument.", pos)
            file_to_add = args[0]
            if file_to_add.parent: file_to_add.parent._internal_remove_file(file_to_add)
            file_to_add.parent = self
            self._internal_add_file(file_to_add)
            print(f"[SIM] File '{file_to_add.filename}' added to folder '{self.path_name}'.")
            return NullValue()
        # ... Implement other Folder methods: remove_file, list_files, list_subfolders, list_audio, get_subfolder
        if name == "list_files":
            if args: raise RuntimeError("Folder.list_files() takes no arguments.", pos)
            return ListValue("File", list(self._files))
        if name == "list_subfolders":
            if args: raise RuntimeError("Folder.list_subfolders() takes no arguments.", pos)
            return ListValue("Folder", list(self._subfolders))
        if name == "list_audio":
            if args: raise RuntimeError("Folder.list_audio() takes no arguments.", pos)
            audio_files = [f for f in self._files if isinstance(f, AudioValue)]
            return ListValue("Audio", audio_files)
        if name == "get_subfolder":
            return NullValue() # Placeholder
        raise RuntimeError(f"Folder has no method '{name}'.", pos)
    def __repr__(self) -> str: return f"FolderValue('{self.path_name}')"


class AudioValue(FileValue):
    def __init__(self, filename: str, parent: Optional[FolderValue] = None,
                 length: int = 0, bitrate: int = 0, title: str = ""):
        super().__init__(filename, parent)
        self.type_name = "Audio"
        self.length_ms: int = length
        self.bitrate_kbps: int = bitrate
        self.title: str = title if title else filename

    def get_attribute(self, name: str, pos: Position) -> Value:
        if name == "length": return IntValue(self.length_ms)
        if name == "bitrate": return IntValue(self.bitrate_kbps)
        if name == "title": return StringValue(self.title)
        try: return super().get_attribute(name, pos) # Delegate to FileValue
        except RuntimeError:
            raise RuntimeError(f"Audio has no attribute '{name}'.", pos)

    def call_method(self, name: str, args: List[Value], pos: Position) -> Value:
        if name == "cut":
            if len(args) != 2 or not isinstance(args[0], IntValue) or not isinstance(args[1], IntValue):
                raise RuntimeError("Audio.cut() expects 2 integer arguments (start, end).", pos)
            start_ms, end_ms = args[0].value, args[1].value
            # Simplified simulation
            if 0 <= start_ms < end_ms <= self.length_ms : self.length_ms = end_ms - start_ms
            else: raise RuntimeError(f"Invalid cut parameters for audio '{self.title}'.", pos)
            print(f"[SIM] Audio '{self.title}' cut. New length: {self.length_ms}ms.")
            return NullValue()
        if name == "concat":
            # ... implementation
            print(f"[SIM] Audio concat called on '{self.title}'.")
            return NullValue()
        if name == "change_title":
            if len(args) != 1 or not isinstance(args[0], StringValue):
                raise RuntimeError("Audio.change_title() expects 1 string argument.", pos)
            self.title = args[0].value
            print(f"[SIM] Audio '{self.filename}' title changed to '{self.title}'.")
            return NullValue()
        # ... Implement other Audio methods: change_format, change_volume
        try: return super().call_method(name, args, pos) # Delegate to FileValue
        except RuntimeError:
            raise RuntimeError(f"Audio has no method '{name}'.", pos)
    def __repr__(self) -> str: return f"AudioValue('{self.filename}', title='{self.title}')"