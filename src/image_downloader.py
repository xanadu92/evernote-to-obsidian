import os
import re
import urllib.request
import urllib.parse
import hashlib
from src.link_resolver import LinkResolver

class ImageDownloader:
    """
    Scans Markdown files for external image URLs, downloads them to local vault
    attachments folder, and updates the markdown to reference the downloaded local copy.
    """
    def __init__(self, vault_dir, attachments_subdir="attachments"):
        self.vault_dir = os.path.abspath(vault_dir)
        self.attachments_subdir = attachments_subdir
        self.attachments_dir = os.path.join(self.vault_dir, self.attachments_subdir)
        self.resolver = LinkResolver(self.vault_dir)
        
        # User-Agent header to bypass bot restrictions on some CDN services
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Regex to match potential web links (HTTP/HTTPS)
        self.url_pattern = re.compile(
            r'https?://[^\s()<>\[\]"\']+'
        )

    def is_image_url(self, url):
        """
        Determines if a URL is likely an image link.
        """
        lower_url = url.lower()
        
        # 1. Handle Artstation imgproxy specifically
        if "imgproxy" in lower_url and "filename:" in lower_url:
            return True
            
        # 2. Match standard image file extensions
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg']
        
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        
        for ext in image_extensions:
            if path.endswith(ext):
                return True
                
        return False

    def extract_filename(self, url, content_bytes):
        """
        Extracts and sanitizes a valid filename from URL.
        """
        filename = None
        
        # 1. Try extracting from Artstation imgproxy syntax: filename:MyImage.png
        match = re.search(r'/filename:([^/]+)', url, re.IGNORECASE)
        if match:
            filename = match.group(1)
            
        # 2. Extract base name of standard URL path
        if not filename:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path
            filename = os.path.basename(path)
            
        # 3. Decode URL encoding and sanitize name
        if filename:
            filename = urllib.parse.unquote(filename)
            filename = self.resolver.sanitize_filename(filename)
        
        # 4. Fallback if filename extraction failed completely
        if not filename or filename == "Untitled":
            md5 = hashlib.md5(content_bytes).hexdigest()
            filename = f"image_{md5[:8]}.png"
            
        return filename

    def safe_url(self, url):
        """
        Quotes non-ascii characters in URL to prevent ascii encoding errors in urllib.
        """
        try:
            parsed = urllib.parse.urlparse(url)
            path_quoted = urllib.parse.quote(parsed.path, safe='/')
            query_quoted = urllib.parse.quote(parsed.query, safe='=&%')
            components = (
                parsed.scheme,
                parsed.netloc,
                path_quoted,
                parsed.params,
                query_quoted,
                parsed.fragment
            )
            return urllib.parse.urlunparse(components)
        except Exception:
            return url

    def download_image(self, url):
        """
        Downloads the image from external URL, checks for name collisions,
        saves to disk, and returns the relative path from the vault root.
        """
        try:
            quoted_url = self.safe_url(url)
            req = urllib.request.Request(quoted_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                
            md5_hash = hashlib.md5(content).hexdigest()
            filename = self.extract_filename(url, content)
            
            # Guarantee extension presence
            name_part, ext_part = os.path.splitext(filename)
            if not ext_part:
                ext_part = ".png"
                filename = name_part + ext_part
                
            dest_filepath = os.path.join(self.attachments_dir, filename)
            
            # Resolve collisions using MD5 hash prefix
            if os.path.exists(dest_filepath):
                with open(dest_filepath, 'rb') as f:
                    existing_hash = hashlib.md5(f.read()).hexdigest()
                if existing_hash != md5_hash:
                    filename = f"{name_part}_{md5_hash[:6]}{ext_part}"
                    dest_filepath = os.path.join(self.attachments_dir, filename)
            
            # Write out file
            with open(dest_filepath, 'wb') as f:
                f.write(content)
                
            # Return relative path from vault root (e.g. 'attachments/TemplateSetup.png')
            return os.path.join(self.attachments_subdir, filename).replace('\\', '/')
            
        except Exception as e:
            print(f"[!] Failed to download {url}: {e}")
            return None

    def _print_safe(self, template, filename):
        """
        Prints strings safely on Windows console where some unicode characters cause UnicodeEncodeError.
        """
        try:
            print(template.format(filename))
        except UnicodeEncodeError:
            safe_name = filename.encode('ascii', errors='replace').decode('ascii')
            print(template.format(safe_name))

    def process_markdown_file(self, filepath):
        """
        Scans markdown file for external image links, downloads them,
        replaces references with local paths and overwrites file.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"[!] Error reading file {filepath}: {e}")
            return False

        urls = self.url_pattern.findall(content)
        image_urls = list(set([url for url in urls if self.is_image_url(url)]))
        
        if not image_urls:
            return False

        self._print_safe("[*] Found " + str(len(image_urls)) + " external image link(s) in: {}", os.path.basename(filepath))
        
        modified = False
        note_dir = os.path.dirname(filepath)
        rel_attachments_dir = os.path.relpath(self.attachments_dir, note_dir).replace('\\', '/')

        for url in image_urls:
            local_rel_vault_path = self.download_image(url)
            if local_rel_vault_path:
                filename = os.path.basename(local_rel_vault_path)
                local_rel_note_path = os.path.join(rel_attachments_dir, filename).replace('\\', '/')
                
                # Check formatting scenarios
                md_link_pattern = re.compile(r'\[([^\]]*)\]\(' + re.escape(url) + r'\)')
                autolink_pattern = re.compile(r'<' + re.escape(url) + r'>')
                
                if md_link_pattern.search(content):
                    content = md_link_pattern.sub(rf'![\1]({local_rel_note_path})', content)
                elif autolink_pattern.search(content):
                    content = autolink_pattern.sub(f"![{filename}]({local_rel_note_path})", content)
                else:
                    content = content.replace(url, f"![{filename}]({local_rel_note_path})")
                
                modified = True

        if modified:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self._print_safe("[+] Updated: {}", os.path.basename(filepath))
                return True
            except Exception as e:
                print(f"[!] Error writing file {filepath}: {e}")
                
        return False

    def download_images_in_vault(self):
        """
        Walks vault directory, finding and processing all markdown files.
        """
        os.makedirs(self.attachments_dir, exist_ok=True)
        count = 0
        for root, _, files in os.walk(self.vault_dir):
            # Skip processing files inside the attachments directory itself
            if self.attachments_subdir in os.path.split(root):
                continue
                
            for file in files:
                if file.lower().endswith('.md'):
                    filepath = os.path.join(root, file)
                    if self.process_markdown_file(filepath):
                        count += 1
                        
        print(f"[*] Completed. {count} file(s) updated with downloaded images.")
        return True
