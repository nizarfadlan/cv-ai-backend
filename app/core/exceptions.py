from fastapi import HTTPException, status


class FileUploadException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class FileSizeException(HTTPException):
    def __init__(self, max_size: int):
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {max_size} bytes",
        )


class FileTypeException(HTTPException):
    def __init__(self, allowed_types: list):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type not supported. Allowed types: {', '.join(allowed_types)}",
        )


class DocumentNotFoundException(HTTPException):
    def __init__(self, document_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
        )


class EvaluationNotFoundException(HTTPException):
    def __init__(self, evaluation_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with id {evaluation_id} not found",
        )


class LLMServiceException(Exception):
    """Exception raised for LLM service errors"""

    pass


class RAGServiceException(Exception):
    """Exception raised for RAG service errors"""

    pass
