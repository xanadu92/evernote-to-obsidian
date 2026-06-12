from mcp.server.fastmcp import FastMCP
from src.backup_manager import BackupManager
from src.link_resolver import LinkResolver
from src.enex_parser import EnexParser
from src.image_downloader import ImageDownloader

# Create an MCP server instance named 'evernote-to-obsidian'
mcp = FastMCP("evernote-to-obsidian")

@mcp.tool()
def sync_evernote(
    db_path: str = "evernote_backup.db",
    export_dir: str = "evernote_exports",
    force_init: bool = False
) -> str:
    """
    Sync Evernote cloud notes to a local SQLite database and export them as ENEX files.
    
    Args:
        db_path: Path to the local sqlite backup database (default: 'evernote_backup.db').
        export_dir: Directory where ENEX files will be exported (default: 'evernote_exports').
        force_init: Force reinitialization of OAuth credentials.
    """
    try:
        manager = BackupManager(db_path=db_path, export_dir=export_dir)
        if force_init:
            if not manager.init_db(force=True):
                return "Failed to initialize database (OAuth setup failed)."
        if not manager.sync():
            return "Failed to sync Evernote notes."
        if not manager.export():
            return "Failed to export ENEX files."
        return "Evernote cloud synchronization and ENEX export completed successfully."
    except Exception as e:
        return f"Error during sync: {str(e)}"

@mcp.tool()
def convert_enex(
    input_dir: str = "evernote_exports",
    output_dir: str = "obsidian_vault",
    attachments_subdir: str = "attachments",
    download_images: bool = False
) -> str:
    """
    Convert exported ENEX files to Obsidian-compatible Markdown.
    
    Args:
        input_dir: Source folder containing ENEX files (default: 'evernote_exports').
        output_dir: Obsidian Vault destination folder (default: 'obsidian_vault').
        attachments_subdir: Subdirectory name inside output folder for attachment files (default: 'attachments').
        download_images: Download external images and localize references in Markdown.
    """
    try:
        resolver = LinkResolver(obsidian_vault_dir=output_dir)
        parser = EnexParser(
            resolver=resolver,
            vault_dir=output_dir,
            attachments_subdir=attachments_subdir
        )
        if not parser.convert_all(enex_dir=input_dir):
            return "Failed to convert ENEX files to Markdown."
        
        result_msg = "ENEX to Markdown conversion completed successfully."
        if download_images:
            downloader = ImageDownloader(vault_dir=output_dir, attachments_subdir=attachments_subdir)
            downloader.download_images_in_vault()
            result_msg += " External images downloaded and references updated."
        return result_msg
    except Exception as e:
        return f"Error during conversion: {str(e)}"

@mcp.tool()
def download_images(
    vault_dir: str = "obsidian_vault",
    attachments_subdir: str = "attachments"
) -> str:
    """
    Scan Markdown files in the Obsidian vault, download external images, and update references.
    
    Args:
        vault_dir: Obsidian Vault folder (default: 'obsidian_vault').
        attachments_subdir: Subdirectory name for storing downloaded attachments (default: 'attachments').
    """
    try:
        downloader = ImageDownloader(vault_dir=vault_dir, attachments_subdir=attachments_subdir)
        downloader.download_images_in_vault()
        return "Image downloading and reference updating completed successfully."
    except Exception as e:
        return f"Error during image download: {str(e)}"

@mcp.tool()
def run_all(
    db_path: str = "evernote_backup.db",
    export_dir: str = "evernote_exports",
    output_dir: str = "obsidian_vault",
    attachments_subdir: str = "attachments",
    force_init: bool = False,
    download_images: bool = False
) -> str:
    """
    Execute all steps sequentially: sync cloud, convert to markdown, and download images (if enabled).
    
    Args:
        db_path: Path to the local sqlite backup database (default: 'evernote_backup.db').
        export_dir: Directory where ENEX files will be exported (default: 'evernote_exports').
        output_dir: Obsidian Vault destination folder (default: 'obsidian_vault').
        attachments_subdir: Subdirectory name inside output folder for attachment files (default: 'attachments').
        force_init: Force reinitialization of OAuth credentials.
        download_images: Download external images and localize references in Markdown.
    """
    try:
        # Step 1: Sync
        manager = BackupManager(db_path=db_path, export_dir=export_dir)
        if force_init:
            if not manager.init_db(force=True):
                return "Failed to initialize database during step 1 (Sync)."
        if not manager.sync() or not manager.export():
            return "Failed to sync or export Evernote notes in step 1 (Sync)."

        # Step 2: Convert
        resolver = LinkResolver(obsidian_vault_dir=output_dir)
        parser = EnexParser(
            resolver=resolver,
            vault_dir=output_dir,
            attachments_subdir=attachments_subdir
        )
        if not parser.convert_all(enex_dir=export_dir):
            return "Failed to convert ENEX files in step 2 (Convert)."

        # Step 3: Download Images
        if download_images:
            downloader = ImageDownloader(vault_dir=output_dir, attachments_subdir=attachments_subdir)
            downloader.download_images_in_vault()
            return "All steps (sync, convert, image download) completed successfully."
        
        return "All steps (sync, convert) completed successfully."
    except Exception as e:
        return f"Error during run_all: {str(e)}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
