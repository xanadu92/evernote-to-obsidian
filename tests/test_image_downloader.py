import os
import unittest
from unittest.mock import MagicMock, patch, mock_open
from src.image_downloader import ImageDownloader

class TestImageDownloader(unittest.TestCase):
    def setUp(self):
        self.downloader = ImageDownloader(vault_dir="test_vault", attachments_subdir="attachments")

    def test_is_image_url(self):
        # Standard image extensions
        self.assertTrue(self.downloader.is_image_url("https://example.com/image.png"))
        self.assertTrue(self.downloader.is_image_url("https://example.com/photo.JPEG"))
        self.assertTrue(self.downloader.is_image_url("http://site.org/assets/pic.webp?query=123"))
        
        # Artstation imgproxy (contains 'imgproxy' and 'filename:')
        self.assertTrue(self.downloader.is_image_url("https://ue-cdn.artstation.com/imgproxy/abc/filename:TemplateSetup.png/resizing:fit"))
        
        # Non-image URLs
        self.assertFalse(self.downloader.is_image_url("https://example.com/index.html"))
        self.assertFalse(self.downloader.is_image_url("https://example.com/api/get_data"))

    def test_extract_filename(self):
        # 1. Artstation imgproxy filename extraction
        url_art = "https://ue-cdn.artstation.com/imgproxy/abc/filename:TemplateSetup.png/fit"
        self.assertEqual(self.downloader.extract_filename(url_art, b""), "TemplateSetup.png")
        
        # 2. Standard URL path filename extraction
        url_std = "https://example.com/images/bg_main.jpg?v=2"
        self.assertEqual(self.downloader.extract_filename(url_std, b""), "bg_main.jpg")
        
        # 3. Fallback to hash if no filename can be found
        url_none = "https://example.com/images/"
        content = b"fake image bytes"
        filename = self.downloader.extract_filename(url_none, content)
        self.assertTrue(filename.startswith("image_"))
        self.assertTrue(filename.endswith(".png"))

    @patch('urllib.request.urlopen')
    def test_download_image(self, mock_urlopen):
        # Mocking urlopen response
        mock_response = MagicMock()
        mock_response.read.return_value = b"image_data_bytes"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Target file should be in test_vault/attachments/TemplateSetup.png
        url = "https://ue-cdn.artstation.com/imgproxy/abc/filename:TemplateSetup.png/fit"
        
        with patch("builtins.open", mock_open()) as mock_file, patch("os.path.exists", return_value=False):
            rel_path = self.downloader.download_image(url)
            
        self.assertEqual(rel_path, "attachments/TemplateSetup.png")
        mock_file.assert_called_once_with(os.path.abspath("test_vault/attachments/TemplateSetup.png"), 'wb')

    def test_process_markdown_file_replacements(self):
        # Mock markdown content containing:
        # 1. Markdown link: [My Image](http...)
        # 2. Autolink: <http...>
        # 3. Plain URL text: http...
        
        url_1 = "https://example.com/img1.png"
        url_2 = "https://ue-cdn.artstation.com/imgproxy/filename:TemplateSetup.png"
        url_3 = "https://example.com/img3.jpg"
        
        markdown_content = f"""# Test Document
Here is a normal link: [Normal Page](https://example.com/index.html)
Here is a markdown image link: [Image Title]({url_1})
Here is an autolink of an image: <{url_2}>
Here is a plain text URL:
{url_3}
"""

        # Patch downloader methods to return fake local relative paths
        self.downloader.download_image = MagicMock(side_effect=lambda u: {
            url_1: "attachments/img1.png",
            url_2: "attachments/TemplateSetup.png",
            url_3: "attachments/img3.jpg"
        }.get(u))

        # We need to test process_markdown_file. It reads/writes filepath.
        m = mock_open(read_data=markdown_content)
        
        # We simulate the note located at: 'test_vault/Unreal/Note.md'
        # Inside the file, relative path from 'Unreal/' to 'attachments/' is '../attachments'
        filepath = os.path.abspath("test_vault/Unreal/Note.md")
        
        with patch("builtins.open", m), patch("os.path.exists", return_value=True):
            success = self.downloader.process_markdown_file(filepath)
            
        self.assertTrue(success)
        
        # Get the written content
        written_content = "".join([call.args[0] for call in m().write.call_args_list])
        
        # Verify replacements:
        # 1. [Image Title](https://example.com/img1.png) -> ![Image Title](../attachments/img1.png)
        self.assertIn("![Image Title](../attachments/img1.png)", written_content)
        # 2. <https://ue-cdn.artstation.com/...TemplateSetup.png> -> ![TemplateSetup.png](../attachments/TemplateSetup.png)
        self.assertIn("![TemplateSetup.png](../attachments/TemplateSetup.png)", written_content)
        # 3. plain URL -> ![img3.jpg](../attachments/img3.jpg)
        self.assertIn("![img3.jpg](../attachments/img3.jpg)", written_content)
        # 4. Normal link must remain unchanged
        self.assertIn("[Normal Page](https://example.com/index.html)", written_content)

    def test_safe_url(self):
        url_korean = "https://example.com/images/한글이미지.png?query=테스트"
        safe_url = self.downloader.safe_url(url_korean)
        self.assertEqual(safe_url, "https://example.com/images/%ED%95%9C%EA%B8%80%EC%9D%B4%EB%AF%B8%EC%A7%80.png?query=%ED%85%8C%EC%8A%A4%ED%8A%B8")

if __name__ == "__main__":
    unittest.main()
