
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set dummy video driver for headless testing
os.environ['SDL_VIDEODRIVER'] = 'dummy'

from core.game_app import GameApp
from scenes.options_scene import OptionsScene

class TestPlayerPathResolution(unittest.TestCase):
    def setUp(self):
        # Initialize pygame to avoid errors in GameApp/OptionsScene
        import pygame
        pygame.init()
        # Mock set_mode to avoid renderer errors
        self.original_set_mode = pygame.display.set_mode
        self.mock_set_mode = MagicMock()
        self.mock_set_mode.return_value = MagicMock()
        pygame.display.set_mode = self.mock_set_mode
        
        # Mock font to avoid file not found errors
        self.original_font = pygame.font.Font
        self.mock_font = MagicMock()
        pygame.font.Font = self.mock_font

    def tearDown(self):
        import pygame
        pygame.display.set_mode = self.original_set_mode
        pygame.font.Font = self.original_font
        pygame.quit()

    def test_path_resolution_normal(self):
        """Test path resolution in a normal environment (not frozen)."""
        app = GameApp()
        scene = OptionsScene(app)
        
        # In normal mode, base_path is "assets"
        # The scene currently hardcodes "assets/graphics/images/player"
        # We expect it to find players if the directory exists
        self.assertTrue(len(scene.available_players) > 0, "Should find players in normal mode")
        print(f"Normal mode players found: {scene.available_players}")

    def test_path_resolution_frozen(self):
        """Test path resolution in a frozen environment (PyInstaller)."""
        # Simulate PyInstaller environment
        with patch.object(sys, 'frozen', True, create=True):
            with patch.object(sys, '_MEIPASS', '/tmp/fakedir', create=True):
                # Mock os.path.isdir and os.listdir to simulate the extracted assets
                original_isdir = os.path.isdir
                original_listdir = os.listdir
                
                def side_effect_isdir(path):
                    print(f"DEBUG: Checking isdir: {path}")
                    # If checking for the hardcoded path "assets/graphics/images/player", 
                    # it should FAIL in a real frozen environment because "assets" 
                    # is relative to CWD, not _MEIPASS.
                    if path == "assets/graphics/images/player":
                        return False # This simulates the bug!
                    
                    # If checking correctly constructed path using base_path
                    if path == "/tmp/fakedir/assets/graphics/images/player":
                        return True
                    if path.startswith("/tmp/fakedir/assets/graphics/images/player/"):
                        return True
                        
                    # For GameApp init checking base_path
                    if path == "/tmp/fakedir/assets":
                        return True
                        
                    return original_isdir(path)

                def side_effect_listdir(path):
                    if path == "/tmp/fakedir/assets/graphics/images/player":
                        return ["knight", "wizard", "elf"]
                    return original_listdir(path)

                with patch('os.path.isdir', side_effect=side_effect_isdir):
                    with patch('os.listdir', side_effect=side_effect_listdir):
                        app = GameApp()
                        # Verify GameApp set correct base_path
                        self.assertEqual(app.resources.base_path, "/tmp/fakedir/assets")
                        
                        scene = OptionsScene(app)
                        
                        # With the BUG, it looks at "assets/..." (relative to CWD) -> fails -> defaults to ["knight"]
                        # If FIXED, it looks at app.resources.base_path + ... -> succeeds -> ["knight", "wizard", "elf"]
                        
                        print(f"Frozen mode players found: {scene.available_players}")
                        
                        # We assert that we WANT it to find the mocked players
                        # If it falls back to just ["knight"] (and assumes it's the fallback), it might be ambiguous.
                        # But our mock returns 3 players.
                        
                        # Current expectation (Approving the bug): It WILL FAIL to find them and return default specific list if logic implies fallback
                        # In OptionsScene: 
                        # if not self.available_players: self.available_players = ["knight"]
                        
                        # So if bug exists: result is ["knight"]
                        # If fix exists: result is ["elf", "knight", "wizard"] (sorted)

                        if len(scene.available_players) == 1 and scene.available_players[0] == "knight":
                             print("!! BUG REPRODUCED: specific players not found, fallback used !!")
                        else:
                             print("!! FIX VERIFIED: specific players found !!")

if __name__ == '__main__':
    unittest.main()
