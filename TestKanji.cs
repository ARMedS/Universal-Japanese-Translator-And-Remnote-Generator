using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

class TestKanji
{
    static void Main()
    {
        var kanjiToRadicals = new Dictionary<string, List<string>>();
        string kanjiDataPath = Path.Combine("kanji-deconstructed", "components-kc.csv");

        if (File.Exists(kanjiDataPath))
        {
            string[] csvLines = File.ReadAllLines(kanjiDataPath);
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