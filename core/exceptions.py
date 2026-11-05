class AppException(Exception):
    """Base exception for application errors."""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class AuthenticationError(AppException):
    def __init__(self, message="Credenciais inválidas"):
        super().__init__(message, status_code=401)

class NotFoundError(AppException):
    def __init__(self, message="Recurso não encontrado"):
        super().__init__(message, status_code=404)

class ConflictError(AppException):
    def __init__(self, message="O recurso já existe"):
        super().__init__(message, status_code=409)

class ValidationError(AppException):
    def __init__(self, message="Dados inválidos"):
        super().__init__(message, status_code=422)
