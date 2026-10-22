from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(default="claude-opus-5-5", alias="SOCIOSCOPE_LLM_MODEL")
    data_dir: Path = Field(default=Path("data"), alias="SOCIOSCOPE_DATA_DIR")
    user_agent: str = Field(
        default="socioscope/0.1 (+https://github.com/; research; contact via repo issues)",
        alias="SOCIOSCOPE_USER_AGENT",
    )
    # Hosts whose WAF rejects non-browser User-Agents (403). Each entry is documented in
    # design/data-sources.md; the fetcher sends a generic browser UA to these hosts only.
    browser_ua_hosts: list[str] = Field(
        default=["www.meti.go.jp"], alias="SOCIOSCOPE_BROWSER_UA_HOSTS"
    )
    # SEC EDGAR requires a User-Agent that identifies the requester (name + contact). Left unset,
    # sec.gov answers 403 and the pipeline reports the source as skipped (fail-closed).
    sec_contact: str | None = Field(default=None, alias="SOCIOSCOPE_SEC_CONTACT")
    browser_user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        alias="SOCIOSCOPE_BROWSER_USER_AGENT",
    )

    def __repr__(self) -> str:  # never leak the key
        return f"Settings(llm_model={self.llm_model!r}, data_dir={str(self.data_dir)!r})"
