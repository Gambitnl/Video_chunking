import unittest
from src.ui.helpers import StatusMessages

class TestCampaignTabs(unittest.TestCase):

    def test_empty_state_cta_html_generation(self):
        """Verify that the empty_state_cta method generates the correct HTML."""
        icon = "🚀"
        title = "Test Title"
        message = "Test message."
        cta_html = '<button>Click Me</button>'

        expected_html = f"""
        <div class="empty-state-card">
            <div class="empty-state-icon">{icon}</div>
            <h3>{title}</h3>
            <p>{message}</p>
            <div class="empty-state-actions">
                {cta_html}
            </div>
        </div>
        """

        # a little messy, but I have to remove the whitespace from both strings to compare them
        generated_html = StatusMessages.empty_state_cta(icon, title, message, cta_html)
        self.assertEqual("".join(generated_html.split()), "".join(expected_html.split()))

if __name__ == '__main__':
    unittest.main()
