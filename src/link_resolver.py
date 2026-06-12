import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

class LinkResolver:
    """
    Scans ENEX files to map Evernote internal GUIDs to final Markdown paths,
    handling naming conflicts and resolving cross-note hyperlinks.
    """

    def __init__(self, obsidian_vault_dir):
        self.vault_dir = os.path.abspath(obsidian_vault_dir)
        # Maps note GUID -> dict(title, filename, rel_path)
        self.guid_to_note = {}
        # Maps title -> list of dict(guid, file_path) to detect/resolve duplicates
        self.title_to_notes = {}
        # Simple set to keep track of processed files to avoid re-parsing
        self.indexed_files = set()

    def sanitize_filename(self, name, max_len=120):
        """
        Removes invalid filesystem characters from the note title and limits length.
        """
        if not name:
            return "Untitled"
        # Replace characters that are invalid on Windows/macOS/Linux
        sanitized = re.sub(r'[\\/*?:"<>|]', "_", name)
        sanitized = sanitized.strip().strip('.')
        
        if len(sanitized) > max_len:
            name_part, ext_part = os.path.splitext(sanitized)
            if len(ext_part) <= 10:
                cut_len = max_len - len(ext_part)
                sanitized = name_part[:cut_len] + ext_part
            else:
                sanitized = sanitized[:max_len]
        return sanitized

    def parse_evernote_timestamp(self, ts_str):
        """
        Parses Evernote XML timestamp (format: YYYYMMDDTHHMMSSZ)
        and returns a filesystem-friendly string.
        """
        if not ts_str:
            return ""
        try:
            # Parse YYYYMMDDTHHMMSSZ
            dt = datetime.strptime(ts_str.strip(), "%Y%m%dT%H%M%SZ")
            return dt.strftime("%Y%m%d_%H%M%S")
        except ValueError:
            return ts_str.strip()

    def scan_enex_files(self, enex_dir):
        """
        First pass: scans all .enex files in the directory and indexes all notes.
        """
        enex_dir = os.path.abspath(enex_dir)
        if not os.path.exists(enex_dir):
            print(f"[!] Directory not found: {enex_dir}")
            return

        print("[*] Scan pass 1: Indexing all Evernote notes and mapping GUIDs...")
        
        # We process each ENEX file. The file name usually represents the Notebook name.
        for root_dir, _, files in os.walk(enex_dir):
            for file in files:
                if file.lower().endswith('.enex'):
                    file_path = os.path.join(root_dir, file)
                    notebook_name = os.path.splitext(file)[0]
                    self._index_enex_file(file_path, notebook_name)

        # Post-process duplicates
        self._resolve_duplicates()

    def _index_enex_file(self, file_path, notebook_name):
        if file_path in self.indexed_files:
            return
        self.indexed_files.add(file_path)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for note in root.findall('note'):
                title_elem = note.find('title')
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Untitled"
                
                created_elem = note.find('created')
                created_ts = created_elem.text if created_elem is not None else ""
                formatted_ts = self.parse_evernote_timestamp(created_ts)

                # Look for GUID in <guid> or <note-attributes><guid>
                guid = None
                guid_elem = note.find('guid')
                if guid_elem is not None and guid_elem.text:
                    guid = guid_elem.text.strip()
                else:
                    attrs = note.find('note-attributes')
                    if attrs is not None:
                        guid_attr = attrs.find('guid')
                        if guid_attr is not None and guid_attr.text:
                            guid = guid_attr.text.strip()

                if not guid:
                    # If no GUID is present, fallback to generated hash from title and timestamp
                    guid = f"fallback_{hash(title + created_ts)}"

                note_info = {
                    "guid": guid,
                    "title": title,
                    "notebook": notebook_name,
                    "timestamp": formatted_ts,
                    "sanitized_title": self.sanitize_filename(title)
                }

                self.guid_to_note[guid] = note_info
                self.title_to_notes.setdefault(title, []).append(note_info)

        except Exception as e:
            print(f"[!] Error indexing {file_path}: {e}")

    def _resolve_duplicates(self):
        """
        Identifies duplicate note titles and appends creation timestamps to resolve conflicts.
        """
        for title, notes in self.title_to_notes.items():
            if len(notes) == 1:
                note = notes[0]
                filename = f"{note['sanitized_title']}.md"
                note["filename"] = filename
                # Output relative path to vault: Notebook_Name/Filename.md
                note["rel_path"] = os.path.join(self.sanitize_filename(note["notebook"]), filename)
            else:
                print(f"[*] Handling duplicate title '{title}' ({len(notes)} occurrences)")
                # Sort notes by timestamp to keep them ordered, if available
                for i, note in enumerate(notes):
                    suffix = f"_{note['timestamp']}" if note["timestamp"] else f"_{i+1}"
                    filename = f"{note['sanitized_title']}{suffix}.md"
                    note["filename"] = filename
                    note["rel_path"] = os.path.join(self.sanitize_filename(note["notebook"]), filename)

    def resolve_link(self, href, current_note_relpath=None):
        """
        Translates an Evernote internal link to a relative path pointing to the converted Markdown.
        Returns the converted link path if found, otherwise None.
        
        Evernote link format: evernote:///view/[userId]/[shardId]/[noteGuid]/[notebookGuid]/
        """
        if not href or not href.startswith("evernote:///view/"):
            return None

        # Extract note GUID (it's the 3rd component of path in evernote:///view/user/shard/noteGuid/...)
        # URL parts: evernote:///view/{userId}/{shardId}/{noteGuid}/{notebookGuid}/
        match = re.search(r'evernote:///view/[^/]+/[^/]+/([a-f0-9-]+)', href, re.IGNORECASE)
        if not match:
            return None

        note_guid = match.group(1)
        target_note = self.guid_to_note.get(note_guid)
        if not target_note:
            return None

        # Calculate relative path from current note's location to the target note
        target_relpath = target_note["rel_path"]
        if current_note_relpath:
            # We want to find relative path from current_note_relpath directory to target_relpath
            current_dir = os.path.dirname(current_note_relpath)
            # Both paths are relative to the vault root, so we can use os.path.relpath
            # Replace backslashes with forward slashes for cross-platform Markdown compatibility
            rel_link = os.path.relpath(target_relpath, current_dir).replace('\\', '/')
            return rel_link
        
        return target_relpath.replace('\\', '/')
