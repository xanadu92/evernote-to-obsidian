import os
import sys
import re
import urllib.request
import urllib.parse
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

vault_path = Path(r"d:\AIProject\Evernote\obsidian_vault")
clippings_path = vault_path / "Clippings"
attachments_path = vault_path / "attachments"

if not attachments_path.exists():
    attachments_path.mkdir(parents=True)

md_pattern = re.compile(r'!\[(.*?)\]\((https?://[^\)]+)\)')
img_tag_pattern = re.compile(r'<img[^>]+src=["\'](https?://[^"\']+)["\'][^>]*>')

# Fake user agent to avoid 403 Forbidden
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
urllib.request.install_opener(opener)

total_downloaded = 0
total_files_updated = 0

for filepath in clippings_path.rglob("*.md"):
    print(f"Processing {filepath.name}...")
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Could not read {filepath}: {e}")
        continue
        
    original_content = content
    
    # Process markdown images
    def repl_md(match):
        global total_downloaded
        alt_text = match.group(1)
        url = match.group(2)
        
        # Determine filename
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            # Fallback if no filename
            import hashlib
            filename = hashlib.md5(url.encode()).hexdigest() + ".jpg"
            
        local_filepath = attachments_path / filename
        
        if not local_filepath.exists():
            try:
                print(f"  Downloading {url} to {filename}...")
                urllib.request.urlretrieve(url, local_filepath)
                total_downloaded += 1
            except Exception as e:
                print(f"  Failed to download {url}: {e}")
                return match.group(0) # Do not replace if failed
                
        # Calculate relative path from markdown file to attachment
        rel_path = os.path.relpath(local_filepath, filepath.parent).replace('\\', '/')
        return f"![{alt_text}]({rel_path})"
        
    content = md_pattern.sub(repl_md, content)
    
    # Process HTML images
    def repl_img_tag(match):
        global total_downloaded
        url = match.group(1)
        
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            import hashlib
            filename = hashlib.md5(url.encode()).hexdigest() + ".jpg"
            
        local_filepath = attachments_path / filename
        
        if not local_filepath.exists():
            try:
                print(f"  Downloading {url} to {filename}...")
                urllib.request.urlretrieve(url, local_filepath)
                total_downloaded += 1
            except Exception as e:
                print(f"  Failed to download {url}: {e}")
                return match.group(0)
                
        rel_path = os.path.relpath(local_filepath, filepath.parent).replace('\\', '/')
        full_tag = match.group(0)
        return full_tag.replace(url, rel_path)
        
    content = img_tag_pattern.sub(repl_img_tag, content)
    
    if content != original_content:
        try:
            filepath.write_text(content, encoding="utf-8")
            total_files_updated += 1
            print(f"  Updated links in {filepath.name}")
        except Exception as e:
            print(f"  Failed to save {filepath.name}: {e}")

print(f"\nDone! Downloaded {total_downloaded} images and updated {total_files_updated} files.")
