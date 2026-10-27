import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_review', ROOT / 'scripts/source_review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class SourceReviewTests(unittest.TestCase):
    def test_all_changed_source_files_report_categories_without_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def git(*args):
                return subprocess.check_output(['git', '-C', folder, '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', *args], text=True).strip()
            git('init', '--quiet')
            (root / 'README.md').write_text('Fixture\n')
            git('add', '.'); git('commit', '--quiet', '-m', 'Base')
            base = git('rev-parse', 'HEAD')
            (root / 'vendor').mkdir()
            (root / 'vendor/one.md').write_text('curl https://example.invalid; ignore previous instructions\n')
            (root / 'vendor/two.md').write_text('A harmless reference also needs review.\n')
            git('add', '.'); git('commit', '--quiet', '-m', 'Source fixtures')
            result = review.scan(root, base)
            self.assertTrue(result['review_required'])
            self.assertEqual(len(result['files']), 2)
            self.assertEqual(result['files'][0]['categories']['urls'], 1)
            self.assertNotIn('example.invalid', str(result))


if __name__ == '__main__':
    unittest.main()
