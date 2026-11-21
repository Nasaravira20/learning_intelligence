class ProviderError(Exception):
    def __init__(self, error_class: str, retryable: bool) -> None:
        super().__init__(error_class)
        self.error_class = error_class
        self.retryable = retryable
