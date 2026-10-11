import unittest

from ujt.parser import ParseError, parse_translation
from ujt.radicals import RadicalIndex
from ujt.config import KANJI_CSV


class ParserTests(unittest.TestCase):
    def test_plain_json(self) -> None:
        raw = '{"japanese":"太い木","chunks":[{"jp":"太い","en":"thick","romaji":"futoi"},{"jp":"木","en":"tree","romaji":"ki"}]}'
        t = parse_translation(raw)
        self.assertEqual(t.japanese, "太い木")
        self.assertEqual(len(t.chunks), 2)
        self.assertEqual(t.chunks[0].jp, "太い")
        self.assertEqual(t.chunks[0].romaji, "futoi")

    def test_markdown_fence(self) -> None:
        raw = 'Here you go:\n```json\n{"japanese":"はい","chunks":[{"jp":"はい","en":"yes"}]}\n```\n'
        t = parse_translation(raw)
        self.assertEqual(t.japanese, "はい")
        self.assertEqual(t.chunks[0].en, "yes")

    def test_rejects_empty(self) -> None:
        with self.assertRaises(ParseError):
            parse_translation("not json at all")


class RadicalTests(unittest.TestCase):
    def test_lookup(self) -> None:
        idx = RadicalIndex(KANJI_CSV)
        formatted = idx.format_for_prompt("丸")
        self.assertTrue(formatted.startswith("丸("), formatted)


if __name__ == "__main__":
    unittest.main()
