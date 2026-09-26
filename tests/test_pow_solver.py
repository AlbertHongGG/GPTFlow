import base64
import json

import pytest

from gpt_flow.infrastructure.sentinel.pow_solver import SentinelPoWSolver, sentinel_hash


class TestSentinelPoWSolver:
    """Test suite for OpenAI Sentinel Proof-of-Work algorithm."""

    def test_sentinel_hash_basic(self) -> None:
        """Test sentinel_hash produces deterministic 8-character hex strings."""
        h1 = sentinel_hash("hello")
        h2 = sentinel_hash("hello")
        assert h1 == h2
        assert len(h1) == 8
        assert isinstance(h1, str)

        # Different input yields different hash
        h3 = sentinel_hash("world")
        assert h1 != h3

    def test_sentinel_hash_empty_string(self) -> None:
        """Test hashing empty string."""
        h = sentinel_hash("")
        assert len(h) == 8

    def test_pow_solver_solution(self) -> None:
        """Test solving a mock PoW puzzle with low difficulty."""
        solver = SentinelPoWSolver()

        # Very easy difficulty "f" means virtually any hash <= "f" will match quickly
        seed = "test-seed-12345"
        difficulty = "ffff"

        pow_token, b64_payload = solver.solve(seed, difficulty, max_attempts=500_000)

        assert pow_token.startswith("gAAAAAB")
        assert pow_token.endswith("~S")

        # Decode payload to verify structure
        decoded = base64.b64decode(b64_payload).decode("utf-8")
        payload = json.loads(decoded)

        # Structure must contain [2774, date, 4395630592, nonce, ...]
        assert isinstance(payload, list)
        assert len(payload) >= 4
        nonce = payload[3]
        assert isinstance(nonce, int)

        # Re-compute hash and verify inequality
        h = sentinel_hash(seed + b64_payload)
        assert h[: len(difficulty)] <= difficulty

    def test_pow_solver_timeout_handling(self) -> None:
        """Test solver respects iteration limits on impossible difficulties."""
        solver = SentinelPoWSolver()
        from gpt_flow.domain.exceptions import PoWComputationError

        with pytest.raises(PoWComputationError, match="Failed to solve"):
            solver.solve("seed", "00000000000000", max_attempts=10)
