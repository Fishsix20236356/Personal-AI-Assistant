from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Security ---
    AUTH_ENABLED: bool = True
    APP_API_KEY: str = ""
    API_KEY_HEADER: str = "X-API-Key"
    USER_ID_HEADER: str = "X-User-Id"
    DEFAULT_USER_ID: str = "local-user"

    # --- CORS ---
    CORS_ALLOW_ORIGINS: str = "http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000"
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = "Authorization,Content-Type,X-API-Key,X-User-Id"

    # --- LLM ---
    LLM_PROVIDER: str = "qwen"
    LLM_MODEL: str = "qwen-plus"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    LLM_FALLBACK_PROVIDER: str | None = None
    LLM_FALLBACK_MODEL: str | None = None
    LLM_FALLBACK_API_KEY: str | None = None
    LLM_FALLBACK_BASE_URL: str | None = None

    # --- Embedding / Knowledge ---
    EMBED_MODEL: str = "text-embedding-3-small"
    EMBED_API_KEY: str = ""
    EMBED_BASE_URL: str = ""
    EMBED_DIMENSIONS: int = 1536
    VECTOR_DB_PATH: str = "tmp/lance_vectors"
    KNOWLEDGE_MAX_RESULTS: int = 8

    # --- Local DBs ---
    AGNO_DB_PATH: str = "tmp/agno_sessions.db"
    APP_META_DB_PATH: str = "tmp/app_meta.db"
    WECHAT_SEARCH_DB_PATH: str = "tmp/wechat_search.db"

    # --- File Ingestion ---
    WATCH_DIR: str = "data/documents"
    CHUNKING_STRATEGY: str = "semantic"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.5
    FILE_DEBOUNCE_MS: int = 800
    MAX_UPLOAD_SIZE_MB: int = 20

    # --- WeChat ---
    WECHAT_RAW_DB_PATH: str = "data/wechat_db/decrypted.db"
    WECHAT_SYNC_BATCH_SIZE: int = 5000

    # --- Runtime ---
    DEFAULT_TIMEZONE: str = "Asia/Shanghai"
    DAILY_REPORT_CRON: str = "0 8 * * *"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    WORKERS: int = 1

    @staticmethod
    def _split_csv(raw: str) -> list[str]:
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return self._split_csv(self.CORS_ALLOW_ORIGINS)

    @property
    def cors_allow_methods_list(self) -> list[str]:
        return self._split_csv(self.CORS_ALLOW_METHODS)

    @property
    def cors_allow_headers_list(self) -> list[str]:
        return self._split_csv(self.CORS_ALLOW_HEADERS)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
