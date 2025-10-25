import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.batch_processor import BatchProcessor

class TestBatchProcessor(unittest.TestCase):

    @patch('src.batch_processor.DDSessionProcessor')
    def test_process_batch_calls_processor_for_each_file(self, mock_dd_processor):
        """Test that DDSessionProcessor is called for each file in the batch."""
        # Arrange
        mock_instance = MagicMock()
        mock_dd_processor.return_value = mock_instance
        mock_instance.process.return_value = {'output_files': {'full_transcript': '/fake/path/file1_full.txt'}}

        files = [Path('file1.m4a'), Path('file2.m4a')]
        batch_processor = BatchProcessor()

        # Act
        report = batch_processor.process_batch(files)

        # Assert
        self.assertEqual(mock_instance.process.call_count, 2)
        self.assertEqual(len(report.processed_files), 2)
        self.assertEqual(len(report.failed_files), 0)

    @patch('src.batch_processor.DDSessionProcessor')
    def test_process_batch_handles_exceptions(self, mock_dd_processor):
        """Test that exceptions during processing are caught and reported."""
        # Arrange
        mock_instance = MagicMock()
        mock_dd_processor.return_value = mock_instance
        mock_instance.process.side_effect = [Exception("Test Error"), {'output_files': {'full_transcript': '/fake/path/file2_full.txt'}}]

        files = [Path('file1.m4a'), Path('file2.m4a')]
        batch_processor = BatchProcessor()

        # Act
        report = batch_processor.process_batch(files)

        # Assert
        self.assertEqual(mock_instance.process.call_count, 2)
        self.assertEqual(len(report.processed_files), 1)
        self.assertEqual(len(report.failed_files), 1)
        self.assertEqual(report.failed_files[0]['file'], str(Path('file1.m4a')))
        self.assertEqual(report.failed_files[0]['error'], 'Test Error')

if __name__ == '__main__':
    unittest.main()