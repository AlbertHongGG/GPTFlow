import base64
import json
import logging
import time
from typing import Any

from gpt_flow.domain.exceptions import PoWComputationError

logger = logging.getLogger("gpt_flow.sentinel.pow")


def sentinel_hash(s: str) -> str:
    """Execute OpenAI Sentinel's custom FNV-1a / Murmur hybrid 32-bit hash."""
    mask = 0xFFFFFFFF
    e = 2166136261

    for char in s:
        code = ord(char)
        e = (e ^ code) & mask
        e = (e * 16777619) & mask

    e = (e ^ (e >> 16)) & mask
    e = (e * 2246822507) & mask
    e = (e ^ (e >> 13)) & mask
    e = (e * 3266489909) & mask
    e = (e ^ (e >> 16)) & mask

    return f"{e:08x}"


class SentinelPoWSolver:
    """Generates environmental fingerprints and solves OpenAI Proof-of-Work challenges."""

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        client_version: str = "prod-0d62007364a43c10125c91f7dcc21675e9b9a893",
        language: str = "zh-TW",
        session_id: str = "b47bb3cc-da06-4508-a7f2-24f924b00b65",
    ) -> None:
        self.user_agent = user_agent
        self.client_version = client_version
        self.language = language
        self.session_id = session_id

    def build_initial_p_token(self) -> str:
        """Build initial 'p' token for /chat-requirements/prepare."""
        now_date = time.strftime("%a %b %d %Y %H:%M:%S GMT+0800 (台北標準時間)")
        now_ms = time.time() * 1000

        data = [
            2774,
            now_date,
            4395630592,
            1,
            self.user_agent,
            "https://chatgpt.com/cdn-cgi/challenge-platform/scripts/jsd/api.js?onload=jsdOnload",
            self.client_version,
            self.language,
            f"{self.language},zh,en-US,en",
            1,
            "serial−[object Serial]",
            "__reactContainer$6yryycfsglf",
            "__oai_so_pc",
            36202,
            self.session_id,
            "",
            32,
            now_ms,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ]
        serialized = json.dumps(data, separators=(",", ":"))
        return "gAAAAAC" + base64.b64encode(serialized.encode("utf-8")).decode("utf-8")

    def solve(
        self,
        seed: str,
        difficulty: str,
        max_attempts: int = 1_000_000,
    ) -> tuple[str, str]:
        """
        Solve Proof-of-Work puzzle for given seed and difficulty.

        Returns:
            Tuple of (pow_token, base64_payload)
        """
        start_time = time.time()
        now_date = time.strftime("%a %b %d %Y %H:%M:%S GMT+0800 (台北標準時間)")
        now_ms = time.time() * 1000
        diff_len = len(difficulty)

        for nonce in range(max_attempts):
            elapsed_ms = int((time.time() - start_time) * 1000)
            data: list[Any] = [
                2774,
                now_date,
                4395630592,
                nonce,
                self.user_agent,
                "https://chatgpt.com/sentinel/20260810913b/sdk.js",
                self.client_version,
                self.language,
                f"{self.language},zh,en-US,en",
                elapsed_ms,
                "keyboard−[object Keyboard]",
                "location",
                "jsdOnload",
                190196,
                self.session_id,
                "",
                32,
                now_ms,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ]
            serialized = json.dumps(data, separators=(",", ":"))
            b64_payload = base64.b64encode(serialized.encode("utf-8")).decode("utf-8")

            hash_result = sentinel_hash(seed + b64_payload)
            if hash_result[:diff_len] <= difficulty:
                logger.debug(
                    f"PoW solved in {nonce} iterations (hash: {hash_result} <= {difficulty})"
                )
                pow_token = "gAAAAAB" + b64_payload + "~S"
                return pow_token, b64_payload

        raise PoWComputationError(
            f"Failed to solve PoW within {max_attempts} iterations for difficulty {difficulty}"
        )
