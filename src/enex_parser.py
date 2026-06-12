import os
import re
import base64
import hashlib
import mimetypes
import xml.etree.ElementTree as ET
import yaml
from datetime import datetime
from bs4 import BeautifulSoup
from markdownify import markdownify as md

class EnexParser:
    """
    Parses ENEX files and converts them to Obsidian-compatible Markdown
    notes and extracted attachments.
    """

    def __init__(self, resolver, vault_dir, attachments_subdir="attachments"):
        self.resolver = resolver
        self.vault_dir = os.path.abspath(vault_dir)
        self.attachments_subdir = attachments_subdir
        self.attachments_dir = os.path.join(self.vault_dir, self.attachments_subdir)

        # Mappings of mime types to extensions for fallback naming
        self.mime_extensions = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/gif": ".gif",
            "application/pdf": ".pdf",
            "text/plain": ".txt",
        }

    def convert_all(self, enex_dir):
        """
        Main entry point for converting all ENEX files in a directory.
        First ensures the link resolver has scanned the files.
        """
        enex_dir = os.path.abspath(enex_dir)
        if not os.path.exists(enex_dir):
            print(f"[!] Source directory does not exist: {enex_dir}")
            return False

        # Scan files with resolver if not already indexed
        if not self.resolver.guid_to_note:
            self.resolver.scan_enex_files(enex_dir)

        print("[*] Scan pass 2: Converting notes and saving markdown...")
        os.makedirs(self.attachments_dir, exist_ok=True)

        for root_dir, _, files in os.walk(enex_dir):
            for file in files:
                if file.lower().endswith('.enex'):
                    file_path = os.path.join(root_dir, file)
                    notebook_name = os.path.splitext(file)[0]
                    self.convert_enex_file(file_path, notebook_name)
        return True

    def convert_enex_file(self, file_path, notebook_name):
        """
        Parses a single ENEX file and writes all its notes as markdown.
        """
        print(f"[*] Processing notebook: {notebook_name}...")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for note in root.findall('note'):
                self.convert_note(note, notebook_name)
        except Exception as e:
            print(f"[!] Error processing notebook file {file_path}: {e}")

    def convert_note(self, note_elem, notebook_name):
        """
        Converts a single XML <note> element to a markdown file.
        """
        title_elem = note_elem.find('title')
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Untitled"

        # Look up resolved note info from the link resolver
        # We need to find the correct note matching GUID
        guid = None
        guid_elem = note_elem.find('guid')
        if guid_elem is not None and guid_elem.text:
            guid = guid_elem.text.strip()
        else:
            attrs = note_elem.find('note-attributes')
            if attrs is not None:
                guid_attr = attrs.find('guid')
                if guid_attr is not None and guid_attr.text:
                    guid = guid_attr.text.strip()

        if not guid:
            created_elem = note_elem.find('created')
            created_ts = created_elem.text if created_elem is not None else ""
            guid = f"fallback_{hash(title + created_ts)}"

        note_info = self.resolver.guid_to_note.get(guid)
        if not note_info:
            print(f"[!] Warning: Note '{title}' (GUID: {guid}) was not found in pass 1 index. Skipping.")
            return

        rel_path = note_info["rel_path"]
        final_filepath = os.path.join(self.vault_dir, rel_path)

        # Ensure parent directories exist
        os.makedirs(os.path.dirname(final_filepath), exist_ok=True)

        # Extract timestamps
        created_elem = note_elem.find('created')
        created_ts = created_elem.text if created_elem is not None else ""
        updated_elem = note_elem.find('updated')
        updated_ts = updated_elem.text if updated_elem is not None else created_ts

        # Extract tags
        tags = [tag.text.strip() for tag in note_elem.findall('tag') if tag.text]

        # Extract attachments and build hash-to-filename map
        media_map = {}
        for resource in note_elem.findall('resource'):
            res_hash, res_filename = self.extract_resource(resource)
            if res_hash and res_filename:
                media_map[res_hash] = res_filename

        # Extract and convert content
        content_elem = note_elem.find('content')
        content_xml = content_elem.text if content_elem is not None and content_elem.text else ""

        markdown_body = self.convert_enml_to_markdown(
            content_xml, 
            media_map, 
            rel_path,
            note_info["notebook"]
        )

        # Write final markdown file with frontmatter
        frontmatter = {
            "title": title,
            "created": self.format_iso_timestamp(created_ts),
            "updated": self.format_iso_timestamp(updated_ts),
            "tags": tags
        }

        try:
            with open(final_filepath, 'w', encoding='utf-8') as f:
                f.write("---\n")
                yaml.dump(frontmatter, f, allow_unicode=True, default_flow_style=False)
                f.write("---\n\n")
                f.write(markdown_body)
        except Exception as e:
            print(f"[!] Error writing note file {final_filepath}: {e}")

    def extract_resource(self, resource_elem):
        """
        Decodes a base64 resource and saves it to the attachments directory.
        Returns (md5_hash, filename).
        """
        data_elem = resource_elem.find('data')
        if data_elem is None or not data_elem.text:
            return None, None

        try:
            # Base64 data can have newlines, clean them up
            base64_data = re.sub(r'\s+', '', data_elem.text.strip())
            data_bytes = base64.b64decode(base64_data)
        except Exception as e:
            print(f"[!] Error decoding base64 resource: {e}")
            return None, None

        # Calculate MD5 hash
        md5_hash = hashlib.md5(data_bytes).hexdigest()

        # Find mime type and map extension
        mime_elem = resource_elem.find('mime')
        mime_type = mime_elem.text.strip() if mime_elem is not None and mime_elem.text else ""
        
        ext = mimetypes.guess_extension(mime_type)
        if not ext:
            ext = self.mime_extensions.get(mime_type, ".bin")

        # Find file name
        filename = None
        attrs = resource_elem.find('resource-attributes')
        if attrs is not None:
            filename_elem = attrs.find('file-name')
            if filename_elem is not None and filename_elem.text:
                filename = filename_elem.text.strip()

        if not filename:
            filename = f"attachment_{md5_hash}{ext}"
        else:
            # Sanitize the filename to prevent folder escape
            filename = self.resolver.sanitize_filename(filename)
            # Limit length to prevent filesystem errors (MAX_PATH or 255 char limit)
            if len(filename) > 150:
                name_part, ext_part = os.path.splitext(filename)
                if len(ext_part) <= 10:
                    cut_len = 150 - len(ext_part)
                    filename = name_part[:cut_len] + ext_part
                else:
                    filename = filename[:150]

        # Ensure filename is unique within the attachments directory
        # If conflict, append hash snippet to avoid collision
        dest_filepath = os.path.join(self.attachments_dir, filename)
        if os.path.exists(dest_filepath):
            # Check if file has same hash, if so we don't need to overwrite
            with open(dest_filepath, 'rb') as f:
                existing_hash = hashlib.md5(f.read()).hexdigest()
            if existing_hash != md5_hash:
                name_part, ext_part = os.path.splitext(filename)
                filename = f"{name_part}_{md5_hash[:6]}{ext_part}"
                dest_filepath = os.path.join(self.attachments_dir, filename)

        try:
            with open(dest_filepath, 'wb') as f:
                f.write(data_bytes)
        except Exception as e:
            print(f"[!] Error saving attachment {dest_filepath}: {e}")
            return None, None

        return md5_hash, filename

    def convert_enml_to_markdown(self, content_xml, media_map, note_rel_path, notebook):
        """
        Converts Evernote ENML XML string to Obsidian Markdown.
        """
        if not content_xml:
            return ""

        # Extract content inside <en-note>...</en-note>
        # ENXML typically contains CDATA wrapping complete HTML document
        try:
            # Parse XML/XHTML content
            soup = BeautifulSoup(content_xml, 'xml')
            en_note = soup.find('en-note')
            if not en_note:
                # Fallback to general html parser
                soup = BeautifulSoup(content_xml, 'html.parser')
                en_note = soup.find('en-note')
                if not en_note:
                    en_note = soup
        except Exception as e:
            print(f"[!] Error parsing ENML content: {e}")
            return content_xml

        # Calculate relative path to attachments folder from the note's directory
        # E.g., if note is in Notebook/Note.md and attachments are in attachments/
        # the directory of the note is Notebook/
        # Relative path from Notebook/ to attachments/ is ../attachments/
        note_dir = os.path.dirname(note_rel_path)
        attachments_rel_dir = os.path.relpath(self.attachments_subdir, note_dir).replace('\\', '/')

        # Preprocess tags before passing to markdownify
        self.preprocess_enml_elements(en_note, media_map, note_rel_path, attachments_rel_dir)

        # Convert to Markdown
        html_str = en_note.decode_contents()
        
        # Configure markdownify to strip en-note wrapper but keep lists, tables, etc.
        markdown_text = md(
            html_str,
            heading_style="ATX",
            bullets="-",
            autolinks=True
        )

        return markdown_text.strip()

    def preprocess_enml_elements(self, soup, media_map, note_rel_path, attachments_rel_dir):
        """
        Preprocesses Evernote-specific tags (checkboxes, highlights, attachments, links).
        """
        # 1. Convert <en-todo> checklists
        for todo in soup.find_all('en-todo'):
            checked = todo.get('checked') == 'true'
            box_str = "[x] " if checked else "[ ] "
            
            # Check if this checkbox is part of a list item
            in_li = todo.find_parent('li') is not None
            if not in_li:
                box_str = "- " + box_str
                
            todo.replace_with(soup.new_string(box_str))

        # 2. Convert <span style="background-color: yellow;"> highlights
        for span in soup.find_all('span'):
            style = span.get('style', '')
            if 'background-color' in style or 'background:' in style:
                # We wrap the contents of the span with Obsidian highlights ==content==
                # Preserve inline children using unwrap
                start_marker = soup.new_string("==")
                end_marker = soup.new_string("==")
                span.insert(0, start_marker)
                span.append(end_marker)
                span.unwrap()

        # 3. Convert <en-media> elements to standard markdown links/images
        for media in soup.find_all('en-media'):
            media_hash = media.get('hash')
            media_type = media.get('type', '')
            
            filename = media_map.get(media_hash)
            if filename:
                rel_file_path = os.path.join(attachments_rel_dir, filename).replace('\\', '/')
                
                if media_type.startswith('image/'):
                    # Standard Markdown image: ![filename](path)
                    new_tag = soup.new_tag('img', src=rel_file_path, alt=filename)
                    media.replace_with(new_tag)
                else:
                    # Standard Markdown link: [filename](path)
                    new_tag = soup.new_tag('a', href=rel_file_path)
                    new_tag.string = filename
                    media.replace_with(new_tag)
            else:
                media.replace_with(soup.new_string(f"[Missing Attachment: {media_hash}]"))

        # 4. Resolve internal evernote links to local note markdown links
        for a in soup.find_all('a'):
            href = a.get('href')
            if href and href.startswith('evernote:///view/'):
                resolved = self.resolver.resolve_link(href, note_rel_path)
                if resolved:
                    a['href'] = resolved

    def format_iso_timestamp(self, ts_str):
        """
        Converts Evernote timestamp format (YYYYMMDDTHHMMSSZ) to ISO 8601 string.
        """
        if not ts_str:
            return ""
        try:
            dt = datetime.strptime(ts_str.strip(), "%Y%m%dT%H%M%SZ")
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return ts_str.strip()
