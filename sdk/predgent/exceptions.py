class PredGentError(Exception):
    """Base exception for PredGent SDK"""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class AuthError(PredGentError):
    """Invalid or missing API key"""
    pass

class InsufficientCreditsError(PredGentError):
    """Not enough credits to perform action"""
    pass

class MarketNotFoundError(PredGentError):
    """Market does not exist"""
    pass

class ValidationError(PredGentError):
    """Invalid input"""
    pass