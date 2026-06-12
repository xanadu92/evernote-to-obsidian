import os
import re
import sys

# Reconfigure stdout/stderr to use UTF-8 encoding on Windows consoles
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def update_attachment_paths(vault_dir):
    vault_dir = os.path.abspath(vault_dir)
    attachments_dir = os.path.abspath(os.path.join(vault_dir, "attachments"))
    
    if not os.path.exists(attachments_dir):
        print(f"[!] Attachments directory not found at: {attachments_dir}")
        return
        
    print(f"[*] Starting link update in vault: {vault_dir}")
    print(f"[*] Attachments folder is at: {attachments_dir}")
    
    # Pattern to match: !?[alt_text]((../)*attachments/filename)
    # Group 1: !?[alt_text](
    # Group 2: filename (with optional sub-path)
    pattern = re.compile(r'(!?\[.*?\]\()(?:\.\./)*attachments/([^)]+)\)')
    
    total_files_checked = 0
    total_files_updated = 0
    total_links_updated = 0
    
    for root, dirs, files in os.walk(vault_dir):
        # Skip the attachments directory itself and the .obsidian config directory
        if os.path.commonpath([root, attachments_dir]) == attachments_dir:
            continue
        if ".obsidian" in root.split(os.sep):
            continue
            
        for file in files:
            if not file.lower().endswith('.md'):
                continue
                
            total_files_checked += 1
            file_path = os.path.join(root, file)
            note_dir = os.path.dirname(file_path)
            
            # Compute new relative path from this note's folder to the attachments folder
            # E.g. "../../attachments"
            new_rel_attachments = os.path.relpath(attachments_dir, note_dir).replace('\\', '/')
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"[!] Error reading {file_path}: {e}")
                continue
                
            def replace_link(match):
                prefix = match.group(1)
                filename = match.group(2)
                # Construct updated relative link
                return f"{prefix}{new_rel_attachments}/{filename})"
                
            new_content, count = pattern.subn(replace_link, content)
            
            if count > 0:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"[+] Updated {count} links in: {os.path.relpath(file_path, vault_dir)}")
                    total_files_updated += 1
                    total_links_updated += count
                except Exception as e:
                    print(f"[!] Error writing {file_path}: {e}")
                    
    print("\n=== Update Summary ===")
    print(f"Total Markdown files scanned: {total_files_checked}")
    print(f"Markdown files updated: {total_files_updated}")
    print(f"Total attachment links resolved: {total_links_updated}")

if __name__ == "__main__":
    vault_path = r"d:\AIProject\Evernote\obsidian_vault"
    update_attachment_paths(vault_path)
