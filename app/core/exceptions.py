class AppException(Exception):
    def __init__(self, error: str, detail: str, status_code: int = 400):
        self.error = error
        self.detail = detail
        self.status_code = status_code


class BusinessException(AppException):
    def __init__(self, detail: str):
        super().__init__(error="BusinessError", detail=detail, status_code=400)


class NotFoundException(AppException):
    def __init__(self, detail: str):
        super().__init__(error="NotFound", detail=detail, status_code=404)
