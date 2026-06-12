import unittest
from unittest.mock import MagicMock
from src.enex_parser import EnexParser

class TestEnexParser(unittest.TestCase):
    def setUp(self):
        # Mock LinkResolver
        self.resolver = MagicMock()
        self.parser = EnexParser(
            resolver=self.resolver,
            vault_dir="test_vault",
            attachments_subdir="attachments"
        )

    def test_convert_enml_to_markdown_basic(self):
        enml = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/en-note.dtd">
        <en-note>
            <div>Hello World!</div>
            <div><b>Bold Text</b> and <i>Italic Text</i></div>
        </en-note>"""
        
        md_output = self.parser.convert_enml_to_markdown(enml, {}, "Notebook/note.md", "Notebook")
        self.assertIn("Hello World!", md_output)
        self.assertIn("**Bold Text**", md_output)
        self.assertIn("*Italic Text*", md_output)

    def test_convert_enml_to_markdown_todo(self):
        enml = """<?xml version="1.0" encoding="UTF-8"?>
        <en-note>
            <div><en-todo checked="false"/> Todo item 1</div>
            <div><en-todo checked="true"/> Todo item 2</div>
            <ul>
                <li><en-todo checked="false"/> List todo</li>
            </ul>
        </en-note>"""

        md_output = self.parser.convert_enml_to_markdown(enml, {}, "Notebook/note.md", "Notebook")
        self.assertIn("- [ ] Todo item 1", md_output)
        self.assertIn("- [x] Todo item 2", md_output)
        # Inside li, it should not have double dashes
        self.assertIn("- [ ] List todo", md_output)

    def test_convert_enml_to_markdown_highlight(self):
        enml = """<?xml version="1.0" encoding="UTF-8"?>
        <en-note>
            <div>Here is <span style="background-color: yellow;">highlighted text</span>.</div>
            <div>Another <span style="background: #ffff00;"><b>bold highlight</b></span>.</div>
        </en-note>"""

        md_output = self.parser.convert_enml_to_markdown(enml, {}, "Notebook/note.md", "Notebook")
        self.assertIn("Here is ==highlighted text==.", md_output)
        self.assertIn("Another ==**bold highlight**==.", md_output)

    def test_convert_enml_to_markdown_media(self):
        # Map MD5 hash to attachment filename
        media_map = {
            "a1b2c3d4": "my_image.png",
            "e5f67a8b": "document.pdf"
        }
        
        enml = """<?xml version="1.0" encoding="UTF-8"?>
        <en-note>
            <div>Check this image:</div>
            <en-media hash="a1b2c3d4" type="image/png"/>
            <div>And this pdf:</div>
            <en-media hash="e5f67a8b" type="application/pdf"/>
        </en-note>"""

        # Note is in "Notebook/note.md", relative to attachments folder "attachments/" which is at root level
        # So directory is "Notebook", relative path is "../attachments/"
        md_output = self.parser.convert_enml_to_markdown(enml, media_map, "Notebook/note.md", "Notebook")
        self.assertIn("![my_image.png](../attachments/my_image.png)", md_output)
        self.assertIn("[document.pdf](../attachments/document.pdf)", md_output)

    def test_convert_enml_to_markdown_internal_link(self):
        self.resolver.resolve_link.return_value = "../Work/Target_Note.md"

        enml = """<?xml version="1.0" encoding="UTF-8"?>
        <en-note>
            <div>Read this: <a href="evernote:///view/123/s1/guid-abc/456/">linked note</a></div>
        </en-note>"""

        md_output = self.parser.convert_enml_to_markdown(enml, {}, "Personal/note.md", "Personal")
        self.assertIn("[linked note](../Work/Target_Note.md)", md_output)
        self.resolver.resolve_link.assert_called_once_with("evernote:///view/123/s1/guid-abc/456/", "Personal/note.md")

    def test_extract_resource_long_filename(self):
        import xml.etree.ElementTree as ET
        import unittest.mock as mock
        
        # Setup element with very long filename
        long_filename = "A" * 200 + ".png"
        resource_xml = f"""
        <resource>
            <data encoding="base64">
                SGVsbG8gV29ybGQ=
            </data>
            <mime>image/png</mime>
            <resource-attributes>
                <file-name>{long_filename}</file-name>
            </resource-attributes>
        </resource>
        """
        elem = ET.fromstring(resource_xml)
        
        self.resolver.sanitize_filename.side_effect = lambda x: x
        
        with mock.patch("builtins.open", mock.mock_open()), mock.patch("os.path.exists", return_value=False):
            md5_hash, filename = self.parser.extract_resource(elem)
            
        self.assertEqual(len(filename), 150)
        self.assertTrue(filename.endswith(".png"))
        self.assertEqual(filename, "A" * 146 + ".png")

if __name__ == "__main__":
    unittest.main()
