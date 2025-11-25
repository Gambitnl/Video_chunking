
import logging
import threading
import time
import unittest
from unittest.mock import patch

from src.interactive_clarifier import InteractiveClarifier

# Disable logging for tests to keep the output clean
logging.disable(logging.CRITICAL)


class TestInteractiveClarifier(unittest.TestCase):

    def test_ask_question_and_submit_response(self):
        """Test asking a question and submitting a response."""
        clarifier = InteractiveClarifier(timeout=1)
        item_id = "item_1"
        response_container = []

        def ask():
            response = clarifier.ask_question(
                "What is the color?", 1, item_id)
            response_container.append(response)

        ask_thread = threading.Thread(target=ask)
        ask_thread.start()

        time.sleep(0.05)  # Allow ask_thread to add the question
        self.assertEqual(len(clarifier.get_sorted_questions()), 1)

        clarifier.submit_response(item_id, "blue")
        ask_thread.join()

        self.assertEqual(len(response_container), 1)
        self.assertEqual(response_container[0], "blue")
        # Verify that the question is removed after being answered
        self.assertEqual(len(clarifier.get_sorted_questions()), 0)

    def test_get_sorted_questions(self):
        """Test that get_sorted_questions returns a correctly sorted list."""
        clarifier = InteractiveClarifier(timeout=0.1)

        # Use threads to ask questions so the main thread doesn't block
        threads = [
            threading.Thread(target=clarifier.ask_question,
                             args=("Low priority", 10, "item_low")),
            threading.Thread(target=clarifier.ask_question,
                             args=("High priority", 1, "item_high")),
            threading.Thread(target=clarifier.ask_question,
                             args=("Mid priority", 5, "item_mid"))
        ]
        for t in threads:
            t.start()

        time.sleep(0.05)  # Allow threads to add questions

        sorted_questions = clarifier.get_sorted_questions()
        self.assertEqual(len(sorted_questions), 3)
        self.assertEqual(sorted_questions[0].priority, 1)
        self.assertEqual(sorted_questions[1].priority, 5)
        self.assertEqual(sorted_questions[2].priority, 10)

        # Cleanup: join threads
        for t in threads:
            t.join()

    def test_timeout_handling(self):
        """Test that a question times out and is removed."""
        clarifier = InteractiveClarifier(timeout=0.1)

        with patch('src.interactive_clarifier._logger') as mock_logger:
            response = clarifier.ask_question(
                "This will time out", 1, "item_timeout")
            self.assertIsNone(response)
            # Verify the question is removed after timeout
            self.assertEqual(len(clarifier.get_sorted_questions()), 0)
            mock_logger.warning.assert_called_with("Question timed out for item_id: %s", "item_timeout")


    def test_question_limit_enforcement(self):
        """Test that no more questions can be added if the limit is reached."""
        clarifier = InteractiveClarifier(max_questions=1, timeout=0.1)

        # This thread will ask the first question and block
        t1 = threading.Thread(target=clarifier.ask_question,
                              args=("First question", 1, "item_1"))
        t1.start()
        time.sleep(0.05)  # Let t1 add its question

        with patch('src.interactive_clarifier._logger') as mock_logger:
            response = clarifier.ask_question("Second question", 1, "item_2")
            self.assertIsNone(response)
            mock_logger.warning.assert_called_with(
                "Question limit (%s) reached. Skipping new question: %s", 1, "Second question"
            )

        # Verify state
        self.assertEqual(len(clarifier.get_sorted_questions()), 1)
        t1.join() # Wait for timeout
        self.assertEqual(len(clarifier.get_sorted_questions()), 0)

    def test_thread_safety_and_cleanup(self):
        """Test concurrent requests and ensure all are cleaned up correctly."""
        clarifier = InteractiveClarifier(timeout=0.5, max_questions=10)
        num_threads = 5
        threads = []
        responses = [None] * num_threads

        def worker(index):
            item_id = f"item_{index}"
            res = clarifier.ask_question(
                f"Question {item_id}", 1, item_id)
            responses[index] = res

        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        time.sleep(0.1)
        self.assertEqual(len(clarifier.get_sorted_questions()), num_threads)

        # Respond to only some of them
        clarifier.submit_response("item_1", "response_1")
        clarifier.submit_response("item_3", "response_3")

        for thread in threads:
            thread.join()

        # Check responses
        self.assertEqual(responses[1], "response_1")
        self.assertEqual(responses[3], "response_3")
        self.assertIsNone(responses[0]) # Timed out
        self.assertIsNone(responses[2]) # Timed out
        self.assertIsNone(responses[4]) # Timed out

        # CRITICAL: Verify that all questions, answered or timed out, are removed
        self.assertEqual(len(clarifier.get_sorted_questions()), 0)


if __name__ == '__main__':
    unittest.main()
