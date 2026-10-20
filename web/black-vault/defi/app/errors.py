class VaultError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(code)
        self.code = code
        self.message = message
        self.status = status
