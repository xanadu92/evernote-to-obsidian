import os
import subprocess
import sys

class BackupManager:
    """
    Manages Evernote note synchronization and backup by wrapping the
    'evernote-backup' command-line interface.
    """

    def __init__(self, db_path="evernote_backup.db", export_dir="evernote_exports"):
        self.db_path = os.path.abspath(db_path)
        self.export_dir = os.path.abspath(export_dir)

    def run_cmd(self, args):
        """
        Executes a command-line argument list and streams output to stdout/stderr.
        """
        try:
            print(f"[*] Running command: {' '.join(args)}")
            result = subprocess.run(args, check=True, text=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"[!] Command failed: {e}", file=sys.stderr)
            return False
        except FileNotFoundError:
            print("[!] Error: 'evernote-backup' command not found. Please ensure it is installed and in your PATH.", file=sys.stderr)
            return False

    def init_db(self, force=False):
        """
        Initializes the evernote-backup database.
        Runs 'evernote-backup init-db --oauth' to authenticate the user.
        """
        if os.path.exists(self.db_path) and not force:
            print(f"[*] Database file '{self.db_path}' already exists. Skipping initialization.")
            return True

        print("[*] Initializing Evernote backup database...")
        print("[*] A browser window will open shortly to authenticate with your Evernote account.")
        
        args = ["evernote-backup", "init-db", "--database", self.db_path]
        return self.run_cmd(args)

    def sync(self):
        """
        Synchronizes the local database with the Evernote Cloud.
        """
        if not os.path.exists(self.db_path):
            print("[!] Database not initialized. Initializing database first...")
            if not self.init_db():
                return False

        print("[*] Syncing Evernote cloud database to local backup...")
        args = ["evernote-backup", "sync", "--database", self.db_path]
        return self.run_cmd(args)

    def export(self, output_dir=None):
        """
        Exports synchronized notes from the local database to ENEX format.
        By default, notes are exported into separate files grouped by notebook.
        """
        target_dir = os.path.abspath(output_dir) if output_dir else self.export_dir
        os.makedirs(target_dir, exist_ok=True)

        print(f"[*] Exporting Evernote database to ENEX files in: {target_dir}")
        args = ["evernote-backup", "export", "--database", self.db_path, target_dir]
        return self.run_cmd(args)
