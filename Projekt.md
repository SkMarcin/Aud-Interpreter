# Projekt wstępny
## Temat projektu
Język do manipulowania na plikach audio w różnych formatach. Dostępne są podstawowe modyfikacje plików audio. Możliwe jest również operowanie na strukturze plików i katalogów, wyszukiwanie plików audio.

## Cechy języka
Typowanie statyczne, silne.\
Wartość zmiennej mutowalna.\
Przekazywanie wartości do funkcji za pomocą referencji.

## Struktura projektu
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
### Uruchamianie
Głównym plikiem uruchomieniowym jest main.py\
Standardowo przyjmowany argument jest uznawany za kod.
```
python3 main.py "print("Hello world");"
```

### Opcje
Wczytanie kodu z pliku
```
-f nazwa_pliku
```
Wczytanie danych konfiguracyjnych
```
-s plik_konfiguracyjny
```

### Dane konfiguracyjne
Mogą zostać wczytane przy użyciu opcji `-s`, w przeciwnym razie zostanę przyjęte standardowe wartości. \
Przykładowe dane przechowywane w pliku config.json
- `MAX_FUNC_DEPTH` - maksymalna głębokość wołania funkcji
- `MAX_REC_DEPTH` - maksymalna głębokość rekursji
- `MAX_STRING_LENGTH` - maksymalna długość wartości string
- `MAX_IDENTIFIER_LENGTH` - maksymalna długość identyfikatora
- `MAX_COMMENT_LENGTH` - maksymalna długość komentarza
- `MAX_FOLDER_DEPTH` - maksymalna głębokość tworzenia drzewa folderu

## Przykrywanie zmiennych
Zmienne są dostępne w bieżącym bloku i wszystkich jego zagnieżdżonych blokach. Nie są dostępne poza swoim zakresem.
```
int x = 5;
if(true) {
    x = 7; /* Poprawne */
}

if (true) {
   int y = 6;
}
int y = 7; /* Niepoprawne */
```

Możliwe jest przykrywanie zmiennych w zagnieżdżonym bloku kodu, po zakończeniu bloku wraca wartość przykrytej zmiennej.
```
int x = 5;
if (true) {
    int x = 0; /* Poprawne */
}

/* x ma teraz wartość 5 */
```

Przykład w funkcji.
```
int var = 100;

func void test_shadowing(int parameter) {
    string var = "Lokalna";
    /* Nie generuje błędu, jest to inna zmienna */

    parameter = parameter * 2;
    /* Zmieniona wartość po referencji */
}

test_shadowing(var);
print("Zmienna globalna po funkcji: " + itos(global_var));
/* Po wyjściu z funkcji, var ma wartość 200 */
```


## Typy
### Proste:
 - `bool`
 - `int`
 - `float`
 - `string`
### Złożone:
### Folder
Atrybuty:
- `List<File> files`
- `List<Folder> subfolders`
- `bool is_root`

Metody:
- `Folder(string path)`
- `File get_file(string filename)`
- `void add_file(File file)`
- `void remove_file(string filename) `
- `List<File> list_files()`
- `List<Folder> list_subfolders()`
- `List<Audio> list_audio()`
- `Folder get_subfolder(string name)`

### File
Atrybuty:
- `string filename`
- `Folder parent`

Metody:
- `File(string filename)`
- `string get_filename()`
- `void change_filename(string filename)`
- `void move(Folder new_parent)`
- `void delete()`

### Audio
Dziedziczy po File

Atrybuty:
- `int length`
- `int bitrate`
- `string title`

Metody:
- `Audio(string filename)`
- `void cut(int start, int end)` – wycina fragment pliku audio, start i koniec w milisekundach
- `void concat(Audio sound_file)` – dodaje drugi plik audio na końcu pierwszego
- `void change_title(string new_title)`
- `void change_format(string new_format)`
- `void change_volume(float amount)`

## Struktury danych
Wymagana jest implementacja listy do tworzenia listy plików w katalogu.
Możliwe jest tworzenie list każdego z wbudowanych typów, tylko jednego na listę.\
Lista tworzona jest w następujący sposób:
```
List<int> lista = [12, 15, -34];
```

## Komentarze
Komentarze można umieszczać między symbolami `/*  */`

## Priorytety operatorów

| Operator     | Priorytet | Asocjacyjność |
| ------------ | -------- | ------------- |
| `-` (negacja) | 6        | Brak          |
| `*`          | 5        | Lewostronna     |
| `/`          | 5        | Lewostronna     |
| `+`          | 4        | Lewostronna     |
| `-` (odejmowanie) | 4        | Lewostronna     |
| `>`          | 3        | Brak          |
| `>=`         | 3        | Brak          |
| `<`          | 3        | Brak          |
| `<=`         | 3        | Brak          |
| `==`         | 3        | Brak          |
| `!=`         | 3        | Brak          |
| `&&`         | 2        | Lewostronna     |
| `\|\|`       | 1        | Lewostronna     |

### Typy stosowane z operatorami
Operatory arytmetyczne `-`, `+`, `/`, `*` operują na wartościach typu `int`, operator `+` pozwala również na łączenie dwóch zmiennych typu `string`.

Za pomocą operatorów relacyjnych `>`, `>=`, `<`, `<=` można porównywać wartości typu `int`.

Za pomocą operatorów relacynych `==`, `!=` można operować na wartościach typu `int`, `string`, `File` oraz `Folder`.

#### Porównywanie File i Folder
Porównywana jest ścieżka do pliku/folderu i rodzic (parent).

## Funkcje
Wartości są przekazywane do funkcji przez referencję.
### Tworzenie funkcji
Język umożliwia użytkownikowi tworzenie funkcji poprzez podanie:
- zwracanego typu wartości
- identyfikatora funkcji
- listy argumentów
- ciała funkcji
```
func int add_numbers(int x, int y) {
    return x + y;
}
```
Do zakończenia funkcji typu `void`s używana jest instrukcja `return`.

### Funkcje wbudowane
`void print(string text)`\
Odpowiada za wysyłanie tekstu na wyjście standardowe.

`string input()`\
Wczytuje tekst z wejścia standardowego.

`int stoi(string text)`\
Konwersja wartości `string` na `int`.

`string itos(int number)`\
Konwersja wartości `int` na `string`.

`float stof(string text)`\
Konwersja wartości `string` na `float`.

`string ftos(float number)`\
Konwersja wartości `float` na `string`. Zapisywana jest niezerowa część ułamkowa.

`float itof(int number)`\
Konwersja wartości `int` na `float`. Część ułamkowa wynosi 0.

`int ftoi(float number)`\
Konwersja wartości `float` na `int`. Część ułamkowa jest obcinana (truncation).

`File atof(Audio file)`\
Konwersja typu `Audio` na `File`. Polega na usunięciu dodatkowych atrybutów typu Audio.

`File ftoa(Audio file)`\
Konwersja typu `File` na `Audio`. Podjęta jest próba wczytania pliku jako Audio.

## Instrukcja warunkowa
Instrukcja warunkowa składa się z warunku, bloku if i bloku else.
```
bool condition = true;
if (condition) {
    print("condition is true");
} else {
    print("condition is false");
}
```

## Pętla
Wykonuje blok kodu dopóki warunek jest prawdziwy.
```
int i = 1;
while (i < 10) {
    i = i + 1;
}
```

## Błędy
W przypadku wystąpienia błędu zapisywana jest linijka i numer znaku w linijce oraz rodzaj błędu.

Przykładowy komunikat o błędzie:
```
[5, 26] Invalid value
[7, 12] Missing parentheses
```

Poniżej lista przykładowych błędów dla kolejnych etapów.

### Lekser
#### - Invalid symbol
Wystąpienie błędnego znaku dla danego miejsca w kodzie.
```
int x = 1 ? 2;
```


#### - Missing comment close
Brakujący symbol zakończenia komentarza.
```
int x = 4;
/* comment here
int y = 5;

...

print("program finished");
```

#### - Max string length exceeded
Kiedy długość wczytywanej wartości string przekroczy limit ustawiony przez opcję `MAX_STRING_LENGTH`.
```
string text = "aaaaa ... aaaaa";
```

#### - Max identifier length exceeded

Długość identyfikatora przekroczyła limit MAX_IDENTIFIER_LENGTH.

```
int bardzo_dluga_nazwa_zmiennej = 10;
```
#### - Max comment length exceeded

Długość komentarza przekroczyła limit MAX_COMMENT_LENGTH.

#### - Invalid value
Błędna wartość zmiennej. Można kontynuować przeglądanie.
```
int x = 34a7;
```

### Parser
#### - Unexpected token
Ogólny błąd o niespodziewanym tokenie, kiedy nie łapie się w zakresie innych błędów Parsera.
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

### Interpreter
#### - Invalid condition
Błędny typ wyrażenia warunkowego (nie `bool`).
```
if (2 + 5) {
    int x = 0;
}
```

#### - Undeclared variable
Przypisanie wartości do niezadeklarownej w danym zakresie zmiennej.
```
int x = 5;
y = 3;
```

#### - Invalid type
Błędny wartość dla danego typu.
```
int x = "abc";
```

#### - Type conversion exception
Brak możliwości konwersji wartości na inny typ.
```
int x = stoi("abc");
```

#### - File not found
Występujący podczas operacji na pliku audio, kiedy plik został przeniesiony i nie można wykonać na nim operacji.
```
Audio file = new Audio("song.mp3"); /* poprawne */

/* W tym momencie usunięty/przeniesiony plik */

file.change_title("new_name"); /* błąd */
```

#### - Recursion limit
Więcej rekurencyjnych wywołań funkcji niż w konfiguracji `MAX_REC_DEPTH`.
```
func int recursion(int value) {
    return value + recursion(value + 1);
}

int result = recursion(1);
```

## Gramatyka

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

literal                 = integer_literal | float_literal | string_literal | boolean_literal ;
integer_literal         = digit_positive, { digit } | "0" ;
float_literal           = digit, { digit }, ".", { digit } ;
string_literal          = '"', { any_unicode_symbol }, '"' ;
boolean_literal         = "true" | "false" ;
list                    = "[", [ expression, { ",", expression } ], "]";

constructor_call        = ( "File" | "Folder" | "Audio" ), "(", [ argument_list ], ")";
member_access           = factor, ".", identifier, [ "(", [ argument_list ], ")" ];
argument_list           = expression { "," expression } ;

identifier              = letter, { letter | digit | "_" } ;
digit                   = "0" | digit_positive;
digit_positive          = "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
letter                  = (* małe i wielkie litery alfabetu *);
```

## Przykład kodu
``` cpp
func void process_folder(Folder current_folder, Folder short_tracks_folder, float min_duration_secs) {

    List<File> files_in_folder = current_folder.list_files();
    int i = 0;
    int num_files = files_in_folder.len();

    while (i < num_files) {
        File current_file = files_in_folder.get(i);
        string filename = current_file.get_filename();

        Audio audio_version = file_to_audio(current_file);

        if (audio_version != null) {
            string title = audio_version.title;
            float duration = audio_version.duration;
            int bitrate = audio_version.bitrate;

            if (duration < min_duration_secs) {
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
        process_folder(subfolders.get(j), short_tracks_folder, min_duration_secs);
        j = j + 1;
    }
}

string source_path = "path/to/my/music/collection";
string short_tracks_path = "path/to/my/short_tracks";
float minimum_duration = 60.0;

Folder music_collection = Folder(source_path);
Folder short_tracks_dest = Folder(short_tracks_path);

if (music_collection != null && short_tracks_dest != null) {
    process_folder(music_collection, short_tracks_dest, minimum_duration);
    print("Processing complete.");
} else {
    print("Error: Could not access source or destination folder.");
}
```