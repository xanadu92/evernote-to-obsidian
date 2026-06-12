import unittest
from unittest.mock import MagicMock, patch
from src.mcp_server import sync_evernote, convert_enex, download_images, run_all

class TestMcpServer(unittest.TestCase):
    @patch('src.mcp_server.BackupManager')
    def test_sync_evernote_success(self, mock_backup_manager):
        mock_instance = MagicMock()
        mock_backup_manager.return_value = mock_instance
        mock_instance.sync.return_value = True
        mock_instance.export.return_value = True
        
        res = sync_evernote(force_init=False)
        self.assertEqual(res, "Evernote cloud synchronization and ENEX export completed successfully.")
        mock_backup_manager.assert_called_once_with(db_path="evernote_backup.db", export_dir="evernote_exports")
        mock_instance.sync.assert_called_once()
        mock_instance.export.assert_called_once()

    @patch('src.mcp_server.BackupManager')
    def test_sync_evernote_force_init(self, mock_backup_manager):
        mock_instance = MagicMock()
        mock_backup_manager.return_value = mock_instance
        mock_instance.init_db.return_value = True
        mock_instance.sync.return_value = True
        mock_instance.export.return_value = True
        
        res = sync_evernote(force_init=True)
        self.assertEqual(res, "Evernote cloud synchronization and ENEX export completed successfully.")
        mock_instance.init_db.assert_called_once_with(force=True)

    @patch('src.mcp_server.BackupManager')
    def test_sync_evernote_failure(self, mock_backup_manager):
        mock_instance = MagicMock()
        mock_backup_manager.return_value = mock_instance
        mock_instance.sync.return_value = False
        
        res = sync_evernote(force_init=False)
        self.assertEqual(res, "Failed to sync Evernote notes.")
        
    @patch('src.mcp_server.EnexParser')
    @patch('src.mcp_server.LinkResolver')
    def test_convert_enex_success(self, mock_resolver, mock_parser):
        mock_resolver_instance = MagicMock()
        mock_resolver.return_value = mock_resolver_instance
        mock_parser_instance = MagicMock()
        mock_parser.return_value = mock_parser_instance
        mock_parser_instance.convert_all.return_value = True
        
        res = convert_enex(download_images=False)
        self.assertEqual(res, "ENEX to Markdown conversion completed successfully.")
        mock_resolver.assert_called_once_with(obsidian_vault_dir="obsidian_vault")
        mock_parser.assert_called_once_with(
            resolver=mock_resolver_instance,
            vault_dir="obsidian_vault",
            attachments_subdir="attachments"
        )
        mock_parser_instance.convert_all.assert_called_once_with(enex_dir="evernote_exports")

    @patch('src.mcp_server.ImageDownloader')
    def test_download_images_success(self, mock_downloader):
        mock_instance = MagicMock()
        mock_downloader.return_value = mock_instance
        
        res = download_images()
        self.assertEqual(res, "Image downloading and reference updating completed successfully.")
        mock_downloader.assert_called_once_with(vault_dir="obsidian_vault", attachments_subdir="attachments")
        mock_instance.download_images_in_vault.assert_called_once()

    @patch('src.mcp_server.ImageDownloader')
    @patch('src.mcp_server.EnexParser')
    @patch('src.mcp_server.LinkResolver')
    @patch('src.mcp_server.BackupManager')
    def test_run_all_success_with_images(self, mock_backup_manager, mock_resolver, mock_parser, mock_downloader):
        mock_bm = MagicMock()
        mock_backup_manager.return_value = mock_bm
        mock_bm.sync.return_value = True
        mock_bm.export.return_value = True
        
        mock_res = MagicMock()
        mock_resolver.return_value = mock_res
        
        mock_p = MagicMock()
        mock_parser.return_value = mock_p
        mock_p.convert_all.return_value = True
        
        mock_dl = MagicMock()
        mock_downloader.return_value = mock_dl
        
        res = run_all(download_images=True)
        self.assertEqual(res, "All steps (sync, convert, image download) completed successfully.")
        mock_bm.sync.assert_called_once()
        mock_p.convert_all.assert_called_once()
        mock_dl.download_images_in_vault.assert_called_once()

if __name__ == "__main__":
    unittest.main()
