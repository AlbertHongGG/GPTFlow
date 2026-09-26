import base64
import json
import logging

from gpt_flow.domain.entities import AuthCredentials, SentinelTokens
from gpt_flow.domain.exceptions import SentinelChallengeError
from gpt_flow.domain.interfaces import IHttpClient, ISentinelSolver
from gpt_flow.infrastructure.sentinel.pow_solver import SentinelPoWSolver

logger = logging.getLogger("gpt_flow.sentinel.service")


class SentinelService(ISentinelSolver):
    """Orchestrates communication with OpenAI Sentinel security endpoints."""

    def __init__(
        self,
        http_client: IHttpClient,
        backend_api_url: str = "https://chatgpt.com/backend-api",
        pow_solver: SentinelPoWSolver | None = None,
    ) -> None:
        self.http_client = http_client
        self.backend_api_url = backend_api_url
        self.pow_solver = pow_solver or SentinelPoWSolver()

    def _get_base_headers(self, credentials: AuthCredentials) -> dict[str, str]:
        return {
            "authorization": f"Bearer {credentials.access_token}",
            "oai-device-id": credentials.device_id,
            "oai-language": self.pow_solver.language,
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://chatgpt.com",
            "referer": "https://chatgpt.com/",
            "user-agent": self.pow_solver.user_agent,
        }

    async def get_tokens(self, credentials: AuthCredentials) -> SentinelTokens:
        """Execute prepare -> PoW solve -> finalize handshake to acquire fresh tokens."""
        base_headers = self._get_base_headers(credentials)

        # 1. Prepare
        init_p = self.pow_solver.build_initial_p_token()
        prep_url = f"{self.backend_api_url}/sentinel/chat-requirements/prepare"
        logger.debug("Requesting sentinel chat-requirements prepare...")

        prep_resp = await self.http_client.request(
            method="POST",
            url=prep_url,
            headers=base_headers,
            json={"p": init_p},
            cookies=credentials.cookies,
        )

        prep_data = prep_resp.json()
        prepare_token = prep_data.get("prepare_token")
        if not prepare_token:
            raise SentinelChallengeError(
                "Missing prepare_token in sentinel prepare response."
            )

        pow_req = prep_data.get("proofofwork", {})
        pow_token: str | None = None

        # 2. Solve PoW if required
        if pow_req.get("required"):
            seed = pow_req.get("seed", "")
            difficulty = pow_req.get("difficulty", "")
            logger.debug(f"Solving PoW for seed {seed} with difficulty {difficulty}...")
            pow_token, _ = self.pow_solver.solve(seed, difficulty)

        # 3. Finalize
        fin_url = f"{self.backend_api_url}/sentinel/chat-requirements/finalize"
        finalize_body = {
            "prepare_token": prepare_token,
            "proofofwork": pow_token,
        }

        # If turnstile dx is present in prep_data, include if needed
        turnstile_info = prep_data.get("turnstile", {})
        if turnstile_info.get("required"):
            logger.warning(
                "Turnstile required by sentinel prepare. Proceeding with dx challenge."
            )

        logger.debug("Finalizing sentinel chat-requirements...")
        fin_resp = await self.http_client.request(
            method="POST",
            url=fin_url,
            headers=base_headers,
            json=finalize_body,
            cookies=credentials.cookies,
        )

        fin_data = fin_resp.json()
        req_token = fin_data.get("token")
        if not req_token:
            raise SentinelChallengeError(
                "Sentinel finalize did not return a valid chat token."
            )

        logger.info(
            "Successfully acquired fresh OpenAI Sentinel chat-requirements token."
        )
        return SentinelTokens(
            chat_requirements_token=req_token,
            proof_token=pow_token or "",
            turnstile_token=None,
        )

    async def send_ping(
        self,
        credentials: AuthCredentials,
        sentinel_tokens: SentinelTokens,
        seq: int,
        conversation_id: str | None = None,
        last_message_id: str | None = None,
    ) -> None:
        """Send background heartbeat ping to Sentinel endpoint."""
        extra_data = {
            "v": 1,
            "sequence_number": seq,
            "signals": {
                "ping_source": "session_observer_background_submit"
                if seq == 0
                else "conversation_heartbeat",
                "so_token_present": "1",
                "turnstile_token_present": "0",
                "proof_token_present": "1" if sentinel_tokens.proof_token else "0",
                "prepare_token_present": "1",
                "chat_requirements_token_present": "1",
            },
            "conversation_id": f"WEB:{conversation_id}" if conversation_id else None,
            "last_message_id": last_message_id,
        }
        b64_extra = base64.b64encode(json.dumps(extra_data).encode("utf-8")).decode(
            "utf-8"
        )

        headers = {
            **self._get_base_headers(credentials),
            "openai-sentinel-extra-data": b64_extra,
            "openai-sentinel-chat-requirements-token": sentinel_tokens.chat_requirements_token,
            "openai-sentinel-proof-token": sentinel_tokens.proof_token,
        }

        ping_url = f"{self.backend_api_url}/sentinel/ping"
        try:
            await self.http_client.request(
                method="POST",
                url=ping_url,
                headers=headers,
                cookies=credentials.cookies,
            )
        except Exception as e:
            logger.debug(f"Sentinel ping ignored error: {e}")
