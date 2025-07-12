# Aud Interpreter
## Project Topic
A language for manipulating audio files in various formats. Basic modifications of audio files are available. It is also possible to operate on the structure of files and directories, and search for audio files.

## Language Features
Static, strong typing.
Mutable variable values.
Passing values to functions by reference.

## Project Structure
```
repository
├── source/
│   └── ...
├── tests/
│   └── ...
├── main.py
├── README.md
└── config.json
```
### Running
The main executable file is main.py
The following are the available runtime arguments:
```
  -h, --help                    help with program usage
  -c CONFIG, --config CONFIG    Path to the configuration file

  source (mutually exclusive):
  -f FILE, --file FILE          Path to the source code file
  -s STRING, --string STRING    Source code as an argument

  mode (mutually exclusive):
  -l, --lex                     Only run the Lexer and display tokens
  -p, --parse                   Run Lexer, create and display the parse tree
  -t, --type-check              Additional static type checking
```
Not specifying a mode results in full program execution.

```
python3 main.py -s "print("Hello world");" -l
python3 main.py -f "examples/example.aud"
```

### Options
Loading code from a file
```
-f filename
```
Loading configuration data
```
-s config_file
```

### Configuration Data
Can be loaded using the `-s` option, otherwise default values will be used.
Example data stored in config.json:
- `MAX_FUNC_DEPTH` - maximum function call depth
- `MAX_REC_DEPTH` - maximum recursion depth
- `MAX_STRING_LENGTH` - maximum string value length
- `MAX_IDENTIFIER_LENGTH` - maximum identifier length
- `MAX_COMMENT_LENGTH` - maximum comment length
- `MAX_FOLDER_DEPTH` - maximum folder tree creation depth

## Variable Shadowing
Variables are available in the current block and all its nested blocks. They are not available outside their scope.
```
int x = 5;
if(true) {
    x = 7; /* Correct */
}

if (true) {
   int y = 6;
}
int y = 7; /* Incorrect, variable y has already been declared in this scope */
```

It is possible to shadow variables in a nested code block; after the block ends, the value of the shadowed variable returns.
```
int x = 5;
if (true) {
    int x = 0; /* Correct */
}

/* x now has a value of 5 */
```

Example in a function:
```
int var = 100;

func void test_shadowing(int parameter) {
    string var = "Local";
    /* Does not generate an error, this is a different variable */

    parameter = parameter * 2;
    /* Value changed by reference */
}

test_shadowing(var);
print("Global variable after function: " + itos(global_var));
/* After exiting the function, var has a value of 200 */
```


## Types
### Simple:
 - `bool`
 - `int`
 - `float`
 - `string`
### Complex:
Complex types have attributes (read-only) and methods. They can accept null values.

### Folder
Attributes:
- `List<File> files`
- `List<Folder> subfolders`
- `bool is_root`

Methods:
- `Folder(string path)`
- `File get_file(string filename)`
- `void add_file(File file)`
- `void remove_file(string filename)`
- `List<File> list_files()`
- `List<Folder> list_subfolders()`
- `List<Audio> list_audio()`
- `Folder get_subfolder(string name)`

### File
Attributes:
- `string filename`
- `Folder parent`

Methods:
- `File(string filename)`
- `string get_filename()`
- `void change_filename(string filename)`
- `void move(Folder new_parent)`
- `void delete()`

### Audio
Inherits from File

Attributes:
- `int length` - in milliseconds
- `int bitrate`
- `string title`

Methods:
- `Audio(string filename)`
- `void cut(int start, int end)` – cuts a fragment of the audio file, start and end in milliseconds
- `void concat(Audio sound_file)` – adds a second audio file to the end of the first
- `void change_title(string new_title)`
- `void change_format(string new_format)`
- `void change_volume(float amount)`

## Data Structures
A list implementation is required for creating a list of files in a directory.
It is possible to create lists of each of the built-in types, only one type per list.
A list is created as follows:
```
List<int> list = [12, 15, -34];
```

## Comments
Comments can be placed between `/* */` symbols.

## Operator Precedence

| Operator     | Precedence | Associativity |
| ------------ | -------- | ------------- |
| `-` (negation) | 6        | None          |
| `*`          | 5        | Left-to-right |
| `/`          | 5        | Left-to-right |
| `+`          | 4        | Left-to-right |
| `-` (subtraction) | 4        | Left-to-right |
| `>`          | 3        | None          |
| `>=`         | 3        | None          |
| `<`          | 3        | None          |
| `<=`         | 3        | None          |
| `==`         | 3        | None          |
| `!=`         | 3        | None          |
| `&&`         | 2        | Left-to-right |
| `\|\|`       | 1        | Left-to-right |

### Types used with operators
Arithmetic operators `-`, `+`, `/`, `*` operate on `int` values; the `+` operator also allows concatenating two `string` variables.

Relational operators `>`, `>=`, `<`, `<=` can be used to compare `int` values.

Relational operators `==`, `!=` can operate on `int`, `string`, `File`, and `Folder` values.

#### Comparing File and Folder
The path to the file/folder and the parent are compared.

## Functions
Values are passed to functions by reference.
### Function Creation
The language allows the user to create functions by providing:
- return value type
- function identifier
- list of arguments
- function body
```
func int add_numbers(int x, int y) {
    return x + y;
}
```
The `return` statement is used to end `void` functions.

### Built-in Functions
`void print(string text)`
Responsible for sending text to standard output.

`string input()`
Reads text from standard input.

`string btos(bool value)`
Converts a boolean value to a string ("true" or "false").

`int stoi(string text)`
Converts a `string` value to an `int`.

`string itos(int number)`
Converts an `int` value to a `string`.

`float stof(string text)`
Converts a `string` value to a `float`.

`string ftos(float number)`
Converts a `float` value to a `string`. The non-zero fractional part is preserved.

`float itof(int number)`
Converts an `int` value to a `float`. The fractional part is 0.

`int ftoi(float number)`
Converts a `float` value to an `int`. The fractional part is truncated.

`File atof(Audio file)`
Converts an `Audio` type to a `File`. This involves removing the additional attributes of the Audio type.

`File ftoa(Audio file)`
Converts a `File` type to an `Audio`. An attempt is made to load the file as Audio.

## Conditional Statement
A conditional statement consists of a condition, an if block, and an else block.
```
bool condition = true;
if (condition) {
    print("condition is true");
} else {
    print("condition is false");
}
```

## Loop
Executes a block of code as long as the condition is true.
```
int i = 1;
while (i < 10) {
    i = i + 1;
}
```

## Errors
In case of an error, the line and character number in the line, as well as the type of error, are recorded.

Example error message:
```
[5, 26] Invalid value
[7, 12] Missing parentheses
```

Below is a list of example errors for subsequent stages. These are not all possible errors.

### Lexer
#### - Invalid symbol
Occurrence of an incorrect character for a given position in the code.
```
int x = 1 ? 2;
```


#### - Missing comment close
Missing comment termination symbol.
```
int x = 4;
/* comment here
int y = 5;

...

print("program finished");
```

#### - Max string length exceeded
When the length of the read string value exceeds the limit set by the `MAX_STRING_LENGTH` option.
```
string text = "aaaaa ... aaaaa";
```

#### - Max identifier length exceeded

The identifier length exceeded the MAX_IDENTIFIER_LENGTH limit.

```
int very_long_variable_name = 10;
```
#### - Max comment length exceeded

The comment length exceeded the MAX_COMMENT_LENGTH limit.

#### - Invalid value
Incorrect variable value. Parsing can continue.
```
int x = 34a7;
```

### Parser
#### - Unexpected token
General error about an unexpected token, when it doesn't fall within the scope of other Parser errors.
```
int x = ;
```
```
int x = 5
int y = 1;
```
```
int x = 3 * (5 + 4;
```

### Type checker
#### - Invalid condition
Incorrect type of conditional expression (not `bool`).
```
if (2 + 5) {
    int x = 0;
}
```

#### - Invalid type
Incorrect value for a given type.
```
int x = "abc";
```

#### - Invalid argument type for function/method
Incorrect argument type.
```
func int add(int a, int b) {
    return a + b;
}
int result = add("hello", 5);
```

#### - Function/Method redeclaration
Attempt to declare a function with a name that already exists.
```
func void my_func() {}
func void my_func() {}
```

### Interpreter
#### - Undeclared variable
Assigning a value to a variable undeclared in the current scope.
```
int x = 5;
y = 3;
```

#### - Type conversion exception
Inability to convert a value to another type.
```
int x = stoi("abc");
```

#### - File not found
Occurs during an audio file operation when the file has been moved and cannot be operated on.
```
Audio file = new Audio("song.mp3"); /* correct */

/* At this point, the file is deleted/moved */

file.change_title("new_name"); /* error */
```

#### - List index out of bounds
Attempt to access a list element at an index that is outside the list's bounds.
```
List<int> numbers = [10, 20];
print(itos(numbers.get(2)));
```

#### - Division by zero
Attempt to perform division by 0.
```
int x = 10 / 0;
```

#### - Call stack limit exceeded
More recursive function calls than allowed by the `MAX_FUNC_DEPTH` configuration.
```
func int recursion(int value) {
    return value + recursion(value + 1);
}

int result = recursion(1);
```

## Operation Description
### Lexical Analysis
The goal is to transform a sequence of characters into a sequence of tokens, with detection of potential errors.
1. `SourceReader`
Reads raw characters, normalizes line endings, and tracks position.

2. `Cleaner` - Removes whitespace and block comments from the SourceReader stream.

3. `Lexer` - Transforms the cleaned character stream into tokens (values, keywords, simple tokens, etc.), according to the grammar.

### Syntactic Analysis
The goal of this stage is to build the parse tree.

`Parser` performs the conversion from a stream of tokens to various types of `ParserNode` according to grammar rules.

### Static Verification
The goal is static semantic analysis and type checking.

`TypeChecker` traverses the parse tree using the visitor pattern:
- saves variables and function definitions to local/global `SymbolTable` scopes.
- Checks whether all are declared appropriately before use or if there are no double declarations.
- Verifies assignment types based on `TypeSignature` and `FunctionTypeSignature` type and function signatures.

### Interpretation
The goal is to execute the code.

`Interpreter` traverses the parse tree using the visitor pattern:
- The `Environment` stores the current program execution state and built-in and user functions.
- There are function call contexts (`CallContext`), each containing a stack of scopes (`Scopes`).
- Scopes store variables available at a given level.
- Values are stored as a `Value` class.

## Grammar

```
program                 = { statement } ;

statement               = block_statement | function_definition

block_statement         = variable_declaration
                        | assignment
                        | function_call
                        | if_statement
                        | while_loop
                        | expression;

code_block              = "{", { block_statement }, "}"
function_body           = "{", { block_statement }, return_statement, "}" ;

type                    = "void"
                        | "int"
                        | "bool"
                        | "string"
                        | "Folder"
                        | "File"
                        | "Audio"
                        | list_type ;
list_type               = "List", "<", type, ">" ;

while_loop              = "while", "(", expression, ")", code_block ;
if_statement            = "if", "(", expression, ")",
                            code_block,
                            [ "else", code_block ] ;

parameter_list          = type, identifier, { ",", type, identifier } ;
function_definition     = "func", type, identifier, "(", [ parameter_list ] ")",
                            function_body ;
return_statement        = "return", [ expression ] ";" ;

function_call           = identifier, "(", [ argument_list ], ")" ;

assignment              = identifier, "=", expression, ";" ;
variable_declaration    = type, identifier, "=", expression, ";" ;

expression              = logical_or ;
logical_or              = logical_and, { "||", logical_and } ;
logical_and             = comparison, { "&&", comparison } ;
comparison              = additive_expression, [ ( "==" | "!=" | "<" | "<=" | ">" | ">=" ), additive_expression ] ;
additive_expression     = term, { ("+" | "-"), term } ;
term                    = unary_expression, { ("*" | "/"), unary_expression } ;
unary_expression        = ( "-" )? factor ;
factor                  = literal
                        | identifier
                        | function_call
                        | member_access
                        | constructor_call
                        | list
                        | "(", expression, ")" ;

literal                 = integer_literal | float_literal | string_literal | boolean_literal | null_literal;
integer_literal         = digit_positive, { digit } | "0" ;
float_literal           = digit, { digit }, ".", { digit } ;
string_literal          = '"', { any_unicode_symbol }, '"' ;
boolean_literal         = "true" | "false" ;
null_literal            = "null" ;
list                    = "[", [ expression, { ",", expression } ], "]";

constructor_call        = ( "File" | "Folder" | "Audio" ), "(", [ argument_list ], ")";
member_access           = factor, ".", identifier, [ "(", [ argument_list ], ")" ];
argument_list           = expression { "," expression } ;

identifier              = letter, { letter | digit | "_" } ;
digit                   = "0" | digit_positive;
digit_positive          = "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
letter                  = (* lowercase and uppercase alphabet letters *);
```

## Code Example
``` cpp
func void process_folder(Folder current_folder, Folder short_tracks_folder,  min_duration_ms) {

    List<File> files_in_folder = current_folder.list_files();
    int i = 0;
    int num_files = files_in_folder.len();

    while (i < num_files) {
        File current_file = files_in_folder.get(i);
        string filename = current_file.get_filename();

        Audio audio_version = file_to_audio(current_file);

        if (audio_version != null) {
            string title = audio_version.title;
            int duration = audio_version.duration;
            int bitrate = audio_version.bitrate;

            if (duration < min_duration_ms) {
                current_file.move(short_tracks_folder);
            }

        } else {
            print("  Not a recognized audio file or error during conversion.");
        }
        i = i + 1;
    }

    List<Folder> subfolders = current_folder.list_subfolders();
    int j = 0;
    int num_subfolders = subfolders.len();
    while (j < num_subfolders) {
        process_folder(subfolders.get(j), short_tracks_folder, min_duration_ms);
        j = j + 1;
    }
    return;
}

string source_path = "path/to/my/music/collection";
string short_tracks_path = "path/to/my/short_tracks";
int minimum_duration = 10000;

Folder music_collection = Folder(source_path);
Folder short_tracks_dest = Folder(short_tracks_path);

if (music_collection != null && short_tracks_dest != null) {
    process_folder(music_collection, short_tracks_dest, minimum_duration);
    print("Processing complete.");
} else {
    print("Error: Could not access source or destination folder.");
}
```
