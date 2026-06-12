import argparse
import sys
import os
from src.backup_manager import BackupManager
from src.link_resolver import LinkResolver
from src.enex_parser import EnexParser

def main():
    """
    Main command-line interface entry point.
    """
    parser = argparse.ArgumentParser(
        description="Evernote to Obsidian Markdown migration CLI tool."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")
    
    # Subcommand: sync
    sync_parser = subparsers.add_parser("sync", help="Sync Evernote cloud to local database and export to ENEX files")
    sync_parser.add_argument("--db", default="evernote_backup.db", help="Path to local sqlite backup database")
    sync_parser.add_argument("--export-dir", default="evernote_exports", help="Temporary folder to export ENEX files")
    sync_parser.add_argument("--force-init", action="store_true", help="Force reinitialize OAuth connection")
    
    # Subcommand: convert
    convert_parser = subparsers.add_parser("convert", help="Convert ENEX files to Obsidian Markdown notes")
    convert_parser.add_argument("--input", default="evernote_exports", help="Source folder of ENEX files")
    convert_parser.add_argument("--output", default="obsidian_vault", help="Obsidian Vault destination folder")
    convert_parser.add_argument("--attachments", default="attachments", help="Subdirectory inside output folder for attachments")
    convert_parser.add_argument("--download-images", action="store_true", help="Download external images and localize links")
    
    # Subcommand: download-images
    dl_parser = subparsers.add_parser("download-images", help="Scan Markdown files, download external images and localize links")
    dl_parser.add_argument("--vault", default="obsidian_vault", help="Obsidian Vault destination folder")
    dl_parser.add_argument("--attachments", default="attachments", help="Subdirectory inside vault folder for attachments")
    
    # Subcommand: run-all
    all_parser = subparsers.add_parser("run-all", help="Perform both sync and conversion in sequence")
    all_parser.add_argument("--db", default="evernote_backup.db", help="Path to local sqlite backup database")
    all_parser.add_argument("--export-dir", default="evernote_exports", help="Temporary folder to export ENEX files")
    all_parser.add_argument("--output", default="obsidian_vault", help="Obsidian Vault destination folder")
    all_parser.add_argument("--attachments", default="attachments", help="Subdirectory inside output folder for attachments")
    all_parser.add_argument("--force-init", action="store_true", help="Force reinitialize OAuth connection")
    all_parser.add_argument("--download-images", action="store_true", help="Download external images and localize links")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "sync":
        manager = BackupManager(db_path=args.db, export_dir=args.export_dir)
        if args.force_init:
            success = manager.init_db(force=True)
            if not success:
                sys.exit(1)
        success = manager.sync()
        if not success:
            sys.exit(1)
        success = manager.export()
        if not success:
            sys.exit(1)
        print("[+] Sync and export finished successfully.")

    elif args.command == "convert":
        resolver = LinkResolver(obsidian_vault_dir=args.output)
        parser = EnexParser(
            resolver=resolver, 
            vault_dir=args.output, 
            attachments_subdir=args.attachments
        )
        success = parser.convert_all(enex_dir=args.input)
        if not success:
            sys.exit(1)
        print("[+] Conversion finished successfully.")
        
        if args.download_images:
            print("\n=== Step 3: Downloading External Images ===")
            from src.image_downloader import ImageDownloader
            downloader = ImageDownloader(vault_dir=args.output, attachments_subdir=args.attachments)
            downloader.download_images_in_vault()

    elif args.command == "download-images":
        print("=== Scanning and Downloading External Images ===")
        from src.image_downloader import ImageDownloader
        downloader = ImageDownloader(vault_dir=args.vault, attachments_subdir=args.attachments)
        downloader.download_images_in_vault()

    elif args.command == "run-all":
        # 1. Sync
        print("=== Step 1: Syncing from Evernote ===")
        manager = BackupManager(db_path=args.db, export_dir=args.export_dir)
        if args.force_init:
            if not manager.init_db(force=True):
                sys.exit(1)
        if not manager.sync():
            sys.exit(1)
        if not manager.export():
            sys.exit(1)

        # 2. Convert
        print("\n=== Step 2: Converting ENEX to Markdown ===")
        resolver = LinkResolver(obsidian_vault_dir=args.output)
        parser = EnexParser(
            resolver=resolver, 
            vault_dir=args.output, 
            attachments_subdir=args.attachments
        )
        if not parser.convert_all(enex_dir=args.export_dir):
            sys.exit(1)
            
        # 3. Download Images (Optional)
        if args.download_images:
            print("\n=== Step 3: Downloading External Images ===")
            from src.image_downloader import ImageDownloader
            downloader = ImageDownloader(vault_dir=args.output, attachments_subdir=args.attachments)
            downloader.download_images_in_vault()
            
        print("[+] Run-all completed successfully.")

if __name__ == "__main__":
    main()
