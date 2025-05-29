# source/interpreter/runtime_values.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Callable, TYPE_CHECKING
from source.utils import Position, RuntimeException
from source.type_checker.symbol_table import FunctionTypeSignature

import os
import shutil
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError, PydubException

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

    def set_attribute_value(self, name: str, value: Value, pos: Position):
        # By default, attributes are read-only unless specifically overridden by a subclass
        raise RuntimeException(f"Cannot assign to attribute '{name}' of type '{self.get_type_str()}'. Attributes are read-only.", pos)

    def call_method(self, method_name: str, args: List['Value'], pos: Position, env: Environment) -> Value:
        raise RuntimeException(f"Type '{self.get_type_str()}' has no method '{method_name}'.", pos)

    def is_null(self) -> bool:
        return False

    def clone(self) -> Value:
        return self

# --- Simple Values ---
class IntValue(Value):
    def __init__(self, value: int):
        super().__init__("int")
        self.value: int = value
    def __repr__(self) -> str: return f"IntValue({self.value})"
    def clone(self) -> IntValue:
        return IntValue(self.value)

class FloatValue(Value):
    def __init__(self, value: float):
        super().__init__("float")
        self.value: float = value
    def __repr__(self) -> str: return f"FloatValue({self.value})"
    def clone(self) -> FloatValue:
        return FloatValue(self.value)

class StringValue(Value):
    def __init__(self, value: str):
        super().__init__("string")
        self.value: str = value
    def __repr__(self) -> str: return f"StringValue('{self.value}')"
    def clone(self) -> StringValue:
        return StringValue(self.value)

class BoolValue(Value):
    def __init__(self, value: bool):
        super().__init__("bool")
        self.value: bool = value
    def is_true(self) -> bool: return self.value
    def __repr__(self) -> str: return f"BoolValue({self.value})"
    def clone(self) -> BoolValue:
        return BoolValue(self.value)

class NullValue(Value):
    def __init__(self):
        super().__init__("null")
        self.value: None = None
    def is_true(self) -> bool: return False
    def is_null(self) -> bool: return True
    def __repr__(self) -> str: return "NullValue()"
    def clone(self) -> NullValue:
        return self

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
            if args: raise RuntimeException("List.len() takes no arguments.", pos)
            return IntValue(len(self.elements))

        return super().call_method(name, args, pos, env)
    def __repr__(self) -> str: return f"ListValue[{self.element_type_str}]({[repr(e) for e in self.elements]})"
    def clone(self) -> ListValue:
        return ListValue(self.element_type_str, list(self.elements))


class BuiltInFunction(Value):
    def __init__(self, name: str, signature: FunctionTypeSignature, python_callable: Callable, needs_env: bool = False, needs_pos: bool = False):
        super().__init__("builtin_function")
        self.name = name
        self.signature = signature
        self.python_callable = python_callable
        self.needs_env = needs_env
        self.needs_pos = needs_pos

    def __repr__(self) -> str: return f"<BuiltInFunction {self.name}>"

    def call(self, args: List[Value], call_node_pos: Position, env: Environment) -> Value:
        processed_args = []
        for i, arg_val in enumerate(args):
            processed_args.append(arg_val)

        # Call Python function
        additional_args = []
        if self.needs_env:
            additional_args.append(env)
        if self.needs_pos:
            additional_args.append(call_node_pos)
        processed_args.extend(additional_args)

        try:
            result_val = self.python_callable(*processed_args)
        except RuntimeException as e:
            if e.position is None: e.position = call_node_pos
            raise e
        except (ValueError, OSError, PydubException) as e:
            raise RuntimeException(f"Operation exception in '{self.name}': {type(e).__name__} {e}", call_node_pos)
        except Exception as e:
            raise RuntimeException(f"Internal error during execution of built-in function '{self.name}': {type(e).__name__} {e}", call_node_pos)

        # Check returned Value
        if not isinstance(result_val, Value):
            raise RuntimeException(f"Internal error: Built-in function '{self.name}' did not return a Value object (got {type(result_val)}).", call_node_pos)

        return result_val


# --- File System Object Values ---
class FileValue(Value):
    def __init__(self, raw_path: str, pos: Position, parent_folder_obj: Optional[FolderValue] = None):
        super().__init__("File")
        self._fs_path: str = os.path.abspath(raw_path)
        self.filename: str = os.path.basename(self._fs_path)

        self.parent: Optional[FolderValue] = parent_folder_obj

        self._is_deleted: bool = False

        if not os.path.exists(self._fs_path) or not os.path.isfile(self._fs_path):
            raise RuntimeException(f"File '{raw_path}' not found or is not a regular file.", pos)

    def _check_deleted(self, operation_name: str, pos: Position):
        if self._is_deleted:
            raise RuntimeException(f"Operation '{operation_name}' on deleted file '{self.filename}' is not allowed.", pos)
        if not os.path.exists(self._fs_path):
            raise RuntimeException(f"File '{self.filename}' ({self._fs_path}) no longer exists on the file system.", pos)
        if not os.path.isfile(self._fs_path):
            raise RuntimeException(f"Path '{self.filename}' ({self._fs_path}) is no longer a file.", pos)


    def get_attribute(self, name: str, pos: Position) -> Value:
        self._check_deleted(f"accessing attribute '{name}'", pos)
        if name == "filename": return StringValue(self.filename)
        if name == "parent": return self.parent if self.parent else NullValue()

        return super().get_attribute(name, pos)

    # set_attribute_value inherits from Value and is read-only by default.
    # No specific mutable attributes for FileValue are defined by methods other than change_filename.

    def call_method(self, name: str, args: List[Value], pos: Position, env: Environment) -> Value:
        self._check_deleted(name, pos)

        if name == "get_filename":
            if args: raise RuntimeException("File.get_filename() takes no arguments.", pos)
            return StringValue(self.filename)

        elif name == "change_filename":
            new_filename = args[0].value
            current_dir = os.path.dirname(self._fs_path)
            new_path = os.path.join(current_dir, new_filename)

            try:
                os.rename(self._fs_path, new_path)
                self._fs_path = new_path
                self.filename = new_filename
            except OSError as e:
                raise RuntimeException(f"Failed to change filename from '{self.filename}' to '{new_filename}': {e}", pos)
            return NullValue()

        elif name == "move":
            new_parent_folder_obj: FolderValue = args[0]
            new_parent_folder_obj._check_deleted(f"move file into '{new_parent_folder_obj.path_name}'", pos)

            if not os.path.isdir(new_parent_folder_obj.path_name):
                 raise RuntimeException(f"Destination folder '{new_parent_folder_obj.path_name}' does not exist or is not a directory.", pos)

            destination_path = os.path.join(new_parent_folder_obj.path_name, self.filename)

            try:
                shutil.move(self._fs_path, destination_path)
                if self.parent:
                    self.parent._internal_remove_file(self)
                self.parent = new_parent_folder_obj
                self.parent._internal_add_file(self)
                self._fs_path = destination_path
            except shutil.Error as e:
                raise RuntimeException(f"Failed to move file '{self.filename}' to '{new_parent_folder_obj.path_name}': {e}", pos)
            return NullValue()

        elif name == "delete":
            if self._is_deleted: return NullValue()

            try:
                if os.path.exists(self._fs_path):
                    os.remove(self._fs_path)
                if self.parent:
                    self.parent._internal_remove_file(self)
                self.parent = None
                self._is_deleted = True
            except OSError as e:
                raise RuntimeException(f"Failed to delete file '{self.filename}': {e}", pos)
            return NullValue()

        return super().call_method(name, args, pos, env)

    def __repr__(self) -> str: return f"FileValue('{self._fs_path}')"


class FolderValue(Value):
    def __init__(self, raw_path: str, pos: Position):
        super().__init__("Folder")
        self.path_name: str = os.path.abspath(raw_path)
        self.name: str = os.path.basename(raw_path)
        self._files: list[FileValue] = []

        self.is_root: bool = False

        self._is_deleted: bool = False

        if not os.path.exists(self.path_name) or not os.path.isdir(self.path_name):
            raise RuntimeException(f"Folder '{raw_path}' not found or is not a directory.", pos)

    def _internal_add_file(self, file_val: FileValue):
        # This is for internal tracking of which FileValue objects are logically "in" this folder object.
        # The physical file system operation should precede this call if a move/copy is involved.
        if file_val not in self._files: # Prevent duplicates for logical tracking
            self._files.append(file_val)
            file_val.parent = self
            file_val._is_deleted = False

    def _internal_remove_file(self, file_val: FileValue):
        # For internal tracking.
        if file_val in self._files:
            self._files.remove(file_val)

    def _check_deleted(self, operation_name: str, pos: Position):
        if self._is_deleted:
            raise RuntimeException(f"Operation '{operation_name}' on deleted folder '{self.path_name}' is not allowed.", pos)
        if not os.path.exists(self.path_name):
            raise RuntimeException(f"Folder '{self.path_name}' no longer exists on the file system.", pos)
        if not os.path.isdir(self.path_name):
            raise RuntimeException(f"Path '{self.path_name}' is no longer a directory.", pos)


    def get_attribute(self, name: str, pos: Position) -> Value:
        self._check_deleted(f"accessing attribute '{name}'", pos)
        if name == "is_root": return BoolValue(self.is_root)

        if name == "files": return self.call_method("list_files", [], pos, env=None)
        if name == "subfolders": return self.call_method("list_subfolders", [], pos, env=None)
        if name == "name": return self.call_method("get_name", [], pos, env=None)

        return super().get_attribute(name, pos)

    def call_method(self, name: str, args: List[Value], pos: Position, env: Environment) -> Value:
        self._check_deleted(name, pos)

        if name == "get_file":
            fname_to_find = args[0].value

            full_path = os.path.join(self.path_name, fname_to_find)
            if os.path.isfile(full_path):
                try:
                    return AudioValue(full_path, pos, parent_folder_obj=self)
                except RuntimeException: # Fallback to File if not audio
                    return FileValue(full_path, pos, parent_folder_obj=self)
            return NullValue()

        elif name == "add_file":
            file_to_add = args[0]
            file_to_add._check_deleted("add_file", pos)

            # If the file is not already physically in this folder, copy it.
            if os.path.abspath(os.path.dirname(file_to_add._fs_path)) != self.path_name:
                destination_path = os.path.join(self.path_name, file_to_add.filename)
                try:
                    shutil.copy2(file_to_add._fs_path, destination_path)
                    file_to_add._fs_path = destination_path
                except shutil.Error as e:
                    raise RuntimeException(f"Failed to add file '{file_to_add.filename}' to folder '{self.path_name}': {e}", pos)

            # Update logical tracking (if it was moved from another logical parent)
            if file_to_add.parent and file_to_add.parent != self:
                file_to_add.parent._internal_remove_file(file_to_add)
            self._internal_add_file(file_to_add)
            return NullValue()

        elif name == "remove_file":
            if len(args) != 1 or not isinstance(args[0], StringValue):
                raise RuntimeException("Folder.remove_file() expects 1 string argument (filename).", pos)
            fname_to_remove = args[0].value
            full_path = os.path.join(self.path_name, fname_to_remove)

            if os.path.isfile(full_path):
                try:
                    os.remove(full_path)
                    for f_obj in list(self._files):
                        if f_obj.filename == fname_to_remove and f_obj.parent == self:
                            self._internal_remove_file(f_obj)
                            f_obj._is_deleted = True
                            f_obj.parent = None # Clear parent on the object itself
                            break
                except OSError as e:
                    raise RuntimeException(f"Failed to remove file '{fname_to_remove}' from folder '{self.path_name}': {e}", pos)
            else:
                raise RuntimeException(f"File '{fname_to_remove}' not found in folder '{self.path_name}'.", pos)
            return NullValue()

        elif name == "list_files":
            files_in_folder = []
            try:
                for item_name in os.listdir(self.path_name):
                    item_path = os.path.join(self.path_name, item_name)
                    if os.path.isfile(item_path):
                        file_val = FileValue(item_path, pos, parent_folder_obj=self)
                        files_in_folder.append(file_val)
            except OSError as e:
                raise RuntimeException(f"Failed to list files in folder '{self.path_name}': {e}", pos)
            return ListValue("File", files_in_folder)

        elif name == "list_subfolders":
            subfolders_in_folder = []
            try:
                for item_name in os.listdir(self.path_name):
                    item_path = os.path.join(self.path_name, item_name)
                    if os.path.isdir(item_path):
                        try:
                            subfolders_in_folder.append(FolderValue(item_path, pos))
                        except RuntimeException as e:
                            print(f"Warning: Could not create FolderValue for '{item_path}': {e}")
                            continue
            except OSError as e:
                raise RuntimeException(f"Failed to list subfolders in folder '{self.path_name}': {e}", pos)
            return ListValue("Folder", subfolders_in_folder)

        elif name == "list_audio":
            audio_files = []
            try:
                for item_name in os.listdir(self.path_name):
                    item_path = os.path.join(self.path_name, item_name)
                    if os.path.isfile(item_path):
                        try:
                            audio_val = AudioValue(item_path, pos, parent_folder_obj=self)
                            audio_files.append(audio_val)
                        except RuntimeException:
                            continue
            except OSError as e:
                raise RuntimeException(f"Failed to list audio files in folder '{self.path_name}': {e}", pos)
            return ListValue("Audio", audio_files)

        elif name == "get_subfolder":
            subfolder_name = args[0].value
            full_path = os.path.join(self.path_name, subfolder_name)
            if os.path.isdir(full_path):
                return FolderValue(full_path, pos)
            return NullValue()

        elif name == "get_name":
            name = self.name
            if name:
                return StringValue(name)
            return NullValue()

        return super().call_method(name, args, pos, env)

    def __repr__(self) -> str: return f"FolderValue('{self.path_name}')"


class AudioValue(FileValue):
    def __init__(self, raw_path: str, pos: Position, parent_folder_obj: Optional[FolderValue] = None):
        super().__init__(raw_path, pos, parent_folder_obj=parent_folder_obj)
        self.type_name = "Audio"

        self.length_ms: int = 0
        self.bitrate_kbps: int = 0
        self.title: str = ""

        try:
            audio_segment = AudioSegment.from_mp3(self._fs_path)
            self.length_ms = int(audio_segment.duration_seconds * 1000)
            self.bitrate_kbps = int(audio_segment.frame_rate * audio_segment.frame_width * 8 / 1000) if audio_segment.frame_rate else 0
            self.title = os.path.splitext(self.filename)[0]
            if hasattr(audio_segment, 'tags') and audio_segment.tags and 'title' in audio_segment.tags:
                self.title = audio_segment.tags['title']

        except (CouldntDecodeError, FileNotFoundError, PydubException, Exception) as e:
            raise RuntimeException(f"Failed to load audio file '{self.filename}': {e}", pos)

    def get_attribute(self, name: str, pos: Position) -> Value:
        self._check_deleted(f"accessing attribute '{name}'", pos)
        if name == "length": return IntValue(self.length_ms)
        if name == "bitrate": return IntValue(self.bitrate_kbps)
        if name == "title": return StringValue(self.title)
        return super().get_attribute(name, pos)

    # set_attribute_value inherits from Value and is read-only by default,
    # as `change_title` method is provided.

    def call_method(self, name: str, args: List[Value], pos: Position, env: Environment) -> Value:
        self._check_deleted(name, pos)

        audio_segment: Optional[AudioSegment] = None
        try:
            audio_segment = AudioSegment.from_mp3(self._fs_path)
        except (CouldntDecodeError, FileNotFoundError, PydubException) as e:
            raise RuntimeException(f"Could not load audio data for '{self.filename}': {e}", pos)

        if name == "cut":
            start_ms = args[0].value
            end_ms = args[1].value

            if not (0 <= start_ms <= end_ms <= self.length_ms):
                raise RuntimeException(f"Cut range [{start_ms}, {end_ms}] is out of bounds for audio of length {self.length_ms}ms.", pos)

            try:
                cut_segment = audio_segment[start_ms:end_ms]
                cut_segment.export(self._fs_path, format=os.path.splitext(self._fs_path)[1][1:])
                self.length_ms = int(cut_segment.duration_seconds * 1000)
            except PydubException as e:
                raise RuntimeException(f"Failed to cut audio file '{self.filename}': {e}", pos)
            return NullValue()

        elif name == "concat":
            other_audio = args[0]
            other_audio._check_deleted("concat", pos)

            try:
                other_audio_segment = AudioSegment.from_file(other_audio._fs_path)
                combined_segment = audio_segment + other_audio_segment
                combined_segment.export(self._fs_path, format=os.path.splitext(self._fs_path)[1][1:])
                self.length_ms = int(combined_segment.duration_seconds * 1000)
            except PydubException as e:
                raise RuntimeException(f"Failed to concatenate audio file '{self.filename}' with '{other_audio.filename}': {e}", pos)
            return NullValue()

        elif name == "change_title":
            new_title = args[0].value
            self.title = new_title

            try:
                audio_segment.export(self._fs_path, format=os.path.splitext(self._fs_path)[1][1:], tags={'title': new_title})
            except PydubException as e:
                raise RuntimeException(f"Failed to update title for '{self.filename}': {e}", pos)
            return NullValue()

        elif name == "change_format":
            new_format = args[0].value.lower()
            if not new_format.isalnum() or len(new_format) > 5:
                raise RuntimeException(f"Invalid format '{new_format}'. Must be a short alphanumeric string (e.g., 'mp3', 'wav').", pos)

            original_path_no_ext, _ = os.path.splitext(self._fs_path)
            new_path = f"{original_path_no_ext}.{new_format}"

            try:
                audio_segment.export(new_path, format=new_format)
                os.remove(self._fs_path)
                self._fs_path = new_path
                self.filename = os.path.basename(new_path)
            except PydubException as e:
                raise RuntimeException(f"Failed to change format of '{self.filename}' to '{new_format}': {e}", pos)
            return NullValue()

        elif name == "change_volume":
            amount_db = args[0].value

            try:
                new_segment = audio_segment.apply_gain(amount_db)
                new_segment.export(self._fs_path, format=os.path.splitext(self._fs_path)[1][1:])
            except PydubException as e:
                raise RuntimeException(f"Failed to change volume for '{self.filename}': {e}", pos)
            return NullValue()

        return super().call_method(name, args, pos, env)

    def __repr__(self) -> str: return f"AudioValue('{self._fs_path}', title='{self.title}')"