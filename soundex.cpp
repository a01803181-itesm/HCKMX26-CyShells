#include <iostream>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <cctype>
#include <fstream>
#include <regex>
#include <vector>

using std::cout;
using std::string;
using std::vector;

void to_upper (string& word) {
    for (char& letter : word) {
        letter = std::toupper (letter);
    }
}

string upperString(string s)
{
    for (char &c : s)
    {
        c = std::toupper(c);
    }

    return s;
}

string soundex (string word) {
    if (word.empty()) {
        return "";
    }

    to_upper (word);
    char first_letter = word [0];
    std::string soundex_code (1, first_letter);

    string filtered;

    for (int i = 1; i < word.length(); i++) {
        char c = word[i];

        if (c != 'A' and c != 'E' and c != 'I' and c != 'O' and c != 'U' and c != 'H' and c != 'W' and c != 'Y') {
            filtered += c;
        }
    }

    std::map <char, int> soundex_map = { {'B', 1}, {'F', 1}, {'P', 1}, {'V', 1},
                                         {'C', 2}, {'G', 2}, {'J', 2}, {'K', 2}, {'Q', 2}, {'S', 2}, {'X', 2}, {'Z', 2},
                                         {'D', 3}, {'T', 3},
                                         {'L', 4},
                                         {'M', 5}, {'N', 5},
                                         {'R', 6} };

    for (char letter : filtered) {
        if (soundex_map.find(letter) != soundex_map.end()) {
            soundex_code += std::to_string(soundex_map[letter]);
        }
    }

    if (soundex_code.length() < 7) {
        soundex_code.append(7 - soundex_code.length(), '0');
    }

    if (soundex_code.length() > 7) {
        for (int i = soundex_code.length() - 1; i >= 7; i--) {
            soundex_code.erase(i, 1);
        }
    }

    return soundex_code;

}

struct word {
    std::string text;
    int line;
    int column;
};

bool read_words(const string input_file_name, vector<word>& words)
{
    std::ifstream input_file(input_file_name);
    if (input_file.fail()) {
        return false;
    }
    std::regex reg_exp("[a-zA-Z]+");
    std::smatch match;
    string text;
    int line = 0;
    int column = 0;
    while (std::getline(input_file, text)) {
        ++line;
        column = 1;
        while (std::regex_search(text, match, reg_exp)) {
            column += match.position();
            words.push_back({match.str(), line, column});
            column += match.length();
            text = match.suffix().str();
        }
    }
    return true;
}

std::unordered_map<string, vector<string>> soundexVectors (string file)
{
    std::unordered_map<string, vector<string>> um;
    std::ifstream txt(file);

    if (not txt.is_open())
    {
        cout << "Error reading: " << file << "\n";
        return um;
    }

    string word;
    string code;

    while (txt >> word)
    {
        code = soundex(word);
        um[code].push_back(word);
    }

    return um;
}

template <typename T>
void printVec(vector<T> vec)
{
    bool first = true;

    for (size_t i = 0; i < vec.size(); ++i)
    {
        if (first)
        {
            cout << vec[i];
            first = false;
        }
        else
        {
            cout << ", " << vec[i];
        }
    }
    cout << "\n";
}

std::unordered_set<string> loadTxt(const string& file)
{
    std::unordered_set<string> us;
    std::ifstream in(file);
    string w;

    if (!in.is_open())
    {
        cout << "Unable to read file: " << file << "\n";
        return us;
    }

    while (in >> w)
    {
        us.insert (upperString (w));
    }

    return us;
}

bool incorrect(const string& word, const std::unordered_set<string>& txt)
{
    return txt.find(word) == txt.end();
}

int main (int argc, char* argv[])
{
    // Checa que se haya puesto solamente un archivo de input
    if (argc != 2)
    {
        cout << "The program needs 2 arguments.\n";
        return 0;
    }

    // El fileName solo es el nombre del input y el vector son todas las palabras del input.
    string fileName = argv[1];
    vector<word> words;

    /*
    Hice la funcion loadtxt para cargar el archivo solo una vez,
    El um es el soundex del txt
    El set guarda las palabras incorrectas del input
    */
    std::unordered_set<string> correctWords = loadTxt("words.txt");
    std::unordered_map<string, vector<string>> soundexTxt = soundexVectors("words.txt");
    std::map<string, word> badWords;

    // Esto llama la funcion incorrect, para ver que palabras estan mal escritas y las guarda en badWords
    if (read_words(fileName, words))
    {
        string upper;
        for (word w : words)
        {
            upper = upperString(w.text);

            if (incorrect (upper, correctWords)) // Esto checa si la palabra esta mal escrita
            {
                if (badWords.find(upper) == badWords.end()) // Si sí, checa si es la primera vez que se escribe mal de esa forma. Lo checa todo en
                                                            // mayúsculas para que no importe si en el og esta en mayúscula o minúscula
                {
                    badWords[upper] = w;  // Guarda la palabra junto con la fila y columna en la que aparece y luego la imprime
                    cout << "Unrecognized word: \"" << w.text << "\". First found at line " << w.line << ", column " << w.column << ". \n";

                    string soundex_word = soundex(w.text); // Saca el soundex de la palabra que esta mal

                    if (soundexTxt.find(soundex_word) != soundexTxt.end()) // Checa si ese soundex existe en el map de la lista de palabras que están bien
                    {
                        auto suggestions = soundexTxt[soundex_word]; // Si sí existe entonces guarda las palabras con ese soundex en el vector 'suggestions'
                        cout << "Suggestions: ";

                        printVec(suggestions);
                    }
                    else
                    {
                         cout << "No suggestions.\n";
                    }

                cout << "\n";
                }
            }
        }
    }

    else
    {
        cout << "Unable to read file: "
             << fileName << "\n";
    }

    return 0;
}