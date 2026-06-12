import os
import unittest
from src.link_resolver import LinkResolver

class TestLinkResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = LinkResolver(obsidian_vault_dir="test_vault")

    def test_sanitize_filename(self):
        self.assertEqual(self.resolver.sanitize_filename("Simple Title"), "Simple Title")
        self.assertEqual(self.resolver.sanitize_filename("Title/With/Slashes"), "Title_With_Slashes")
        self.assertEqual(self.resolver.sanitize_filename("Title:With:Colons"), "Title_With_Colons")
        self.assertEqual(self.resolver.sanitize_filename("  Trim Spaces.  "), "Trim Spaces")
        self.assertEqual(self.resolver.sanitize_filename("A" * 150), "A" * 120)
        self.assertEqual(self.resolver.sanitize_filename("B" * 150 + ".md"), "B" * 117 + ".md")

    def test_parse_evernote_timestamp(self):
        self.assertEqual(self.resolver.parse_evernote_timestamp("20260612T010712Z"), "20260612_010712")
        self.assertEqual(self.resolver.parse_evernote_timestamp("invalid"), "invalid")

    def test_resolve_duplicates(self):
        # Setup duplicate notes in the resolver
        note1_data = {
            "guid": "guid1",
            "title": "Meeting Notes",
            "notebook": "Work",
            "timestamp": "20260610_100000",
            "sanitized_title": "Meeting Notes"
        }
        note2_data = {
            "guid": "guid2",
            "title": "Meeting Notes",
            "notebook": "Personal",
            "timestamp": "20260611_120000",
            "sanitized_title": "Meeting Notes"
        }
        self.resolver.title_to_notes = {
            "Meeting Notes": [note1_data, note2_data]
        }
        self.resolver.guid_to_note = {
            "guid1": note1_data,
            "guid2": note2_data
        }
        # Run resolution
        self.resolver._resolve_duplicates()

        # Check outcomes
        note1 = self.resolver.guid_to_note["guid1"]
        note2 = self.resolver.guid_to_note["guid2"]

        self.assertEqual(note1["filename"], "Meeting Notes_20260610_100000.md")
        self.assertEqual(note2["filename"], "Meeting Notes_20260611_120000.md")

        self.assertEqual(note1["rel_path"].replace('\\', '/'), "Work/Meeting Notes_20260610_100000.md")
        self.assertEqual(note2["rel_path"].replace('\\', '/'), "Personal/Meeting Notes_20260611_120000.md")

    def test_resolve_link(self):
        # Set up a target note in index
        self.resolver.guid_to_note = {
            "a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6": {
                "guid": "a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6",
                "title": "Target Note",
                "notebook": "Work",
                "rel_path": "Work/Target Note.md"
            }
        }

        # Test resolving from a note in same notebook
        # Note path: "Work/Source Note.md" (dir is "Work")
        resolved = self.resolver.resolve_link(
            "evernote:///view/12345/s123/a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6/5678/",
            current_note_relpath="Work/Source Note.md"
        )
        # Should be relative within same folder: "Target Note.md"
        self.assertEqual(resolved, "Target Note.md")

        # Test resolving from a note in a different notebook
        # Note path: "Personal/Other Note.md" (dir is "Personal")
        resolved_diff = self.resolver.resolve_link(
            "evernote:///view/12345/s123/a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6/5678/",
            current_note_relpath="Personal/Other Note.md"
        )
        # Should be relative: "../Work/Target Note.md"
        self.assertEqual(resolved_diff, "../Work/Target Note.md")

if __name__ == "__main__":
    unittest.main()
