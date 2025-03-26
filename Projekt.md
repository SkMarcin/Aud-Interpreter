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


## Typy
### Proste:
 - `bool`
 - `int`
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
- `void change_volume(int amount)`

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

### Funkcje wbudowane
`void print(string text)`\
Odpowiada za wysyłanie tekstu na wyjście standardowe.

`string input()`\
Wczytuje tekst z wejścia standardowego.

`int stoi(string text)`\
Konwersja wartości string na int.

`string itos(int number)`\
Konwersja wartości int na string.

`File atof(Audio file)`\
Konwersja typu `Audio na file.

`File ftoa(Audio file)`\
Konwersja typu `File` na `Audio`.

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

#### - Unexpected token
Brak średnika na końcu wyrażenia.
```
int x = 5
int y = 1;
```
#### - Missing parentheses
Brakujący jeden z nawiasów.
```
int x = 3 * (5 + 4;
```

#### - Invalid declaration
Błąd w deklaracji funkcji, np. brakujący typ.
```
func test(int x) {
    return x
}
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

statement               = variable_declaration
                        | assignment
                        | function_declaration
                        | function_call
                        | if_statement
                        | while_loop
                        | return_statement
                        | print_statement
                        | input_statement
                        | comment ;

type                    = "int"
                        | "bool"
                        | "string"
                        | "Folder"
                        | "File"
                        | "Audio" ;
list_type               = "List", "<", type, ">" ;

input_statement         = "input", "(", ")", ";" ;
print_statement         = "print", "(", expression, ")", ";" ;
while_loop              = "while", "(", expression, ")", "{", { statement }, "}" ;
if_statement            = "if", "(", expression, ")",
                            "{", { statement }, "}",
                            [ "else", "{", { statement }, "}" ] ;

parameter_list          = type, identifier, { ",", type, identifier } ;
function_declaration    = "func", type, identifier, "(", [ parameter_list ] ")",
                            "{", { statement }, "}" ;
return_statement        = "return" expression ";" ;
function_call           = identifier, "(", [ argument_list ], ")" ;

assignment              = identifier, "=", expression, ";" ;
variable_declaration    = type, identifier, "=", expression, ";" ;

logical                 = expression, ( "&&" | "||" ), expression ;
comparison              = expression, ( "==" | "!=" | "<" | "<=" | ">" | ">=" ), expression ;
expression              = term, { ("+" | "-"), term } ;
term                    = factor, { ("*" | "/"), factor } ;
factor                  = number
                        | identifier
                        | function_call
                        | identifier, { method_call }
                        | "(", expression, ")"
                        | "-" factor ;

constructor_call        = ( "File" | "Folder" | "Audio" ), "(", arguments, ")";
method_call             = ".", identifier, "(", arguments, ")";

argument_list           = expression { "," expression } ;
arguments               = [ argument_list ] ;

list                    = "[", [ expression, { ",", expression } ], "]";

comment                 = "/*", { any_character_except_*/ }, "*/" ;

string                  = '"', { any_unicode_symbol }, '"'
number                  = "0" | digit_positive, { digit } ;
boolean                 = "true" | "false" ;
identifier              = letter, { letter | digit | "_" } ;
digit                   = "0" | digit_positive;
digit_positive          = "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
letter                  = (* małe i wielkie litery alfabetu *);
```
