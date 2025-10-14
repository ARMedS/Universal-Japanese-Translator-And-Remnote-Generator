using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

class TestKanji
{
    static void Main()
    {
        var kanjiToRadicals = new Dictionary<string, List<string>>();
        string kanjiDataPath = Path.Combine(Directory.GetCurrentDirectory(), "components-kc.csv");
        Console.WriteLine($"[TestKanji] Looking for CSV at: {kanjiDataPath}");
        if (File.Exists(kanjiDataPath))
        {
            Console.WriteLine("[TestKanji] CSV found.");
            string[] csvLines = File.ReadAllLines(kanjiDataPath, System.Text.Encoding.UTF8);
            Console.WriteLine($"[TestKanji] Read {csvLines.Length} lines.");
            // ... (rest unchanged, but add sample print if needed)
        }
        else
        {
            Console.WriteLine("[TestKanji] CSV not found!");
            return;
        }

        if (File.Exists(kanjiDataPath))
        {
            string[] csvLines = File.ReadAllLines(kanjiDataPath, System.Text.Encoding.UTF8);
            foreach (string line in csvLines)
            {
                if (!string.IsNullOrWhiteSpace(line))
                {
                    string[] parts = line.Split(',');
                    if (parts.Length >= 2)
                    {
                        string kanji = parts[0].Trim();
                        var radicals = new List<string>();
                        for (int i = 1; i < parts.Length; i++)
                        {
                            string radical = parts[i].Trim();
                            if (!string.IsNullOrEmpty(radical))
                            {
                                radicals.Add(radical);
                            }
                        }
                        if (!string.IsNullOrEmpty(kanji) && radicals.Any())
                        {
                            kanjiToRadicals[kanji] = radicals;
                        }
                    }
                }
            }
            Console.WriteLine($"Loaded {kanjiToRadicals.Count} kanji entries.");

            // Test some known kanji
            TestKanjiLookup(kanjiToRadicals, "丸");
            TestKanjiLookup(kanjiToRadicals, "及");
            TestKanjiLookup(kanjiToRadicals, "刃");
            TestKanjiLookup(kanjiToRadicals, "食"); // Test a kanji that might not exist
        }
        else
        {
            Console.WriteLine("CSV file not found!");
        }
    }

    static void TestKanjiLookup(Dictionary<string, List<string>> dict, string kanji)
    {
        if (dict.TryGetValue(kanji, out var radicals))
        {
            Console.WriteLine($"{kanji} -> {string.Join(", ", radicals)}");
        }
        else
        {
            Console.WriteLine($"{kanji} -> not found");
        }
    }
}